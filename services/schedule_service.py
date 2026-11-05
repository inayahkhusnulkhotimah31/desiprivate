"""
DESI PRIVAT - Schedule Service
Layanan cerdas penjadwalan les, deteksi bentrokan jadwal, jadwal berulang,
persetujuan, peringatan keterlambatan respons mentor, dan pergantian mentor.
"""
from datetime import datetime, timedelta
from config import Config
from services.database_service import query_db, execute_db
from services.audit_service import log_audit
from services.notification_service import create_notification, notify_admins
from services.whatsapp_service import send_whatsapp_message

def calculate_end_time(start_time_str, duration_minutes):
    """Menghitung waktu selesai (HH:MM) dari waktu mulai dan durasi menit."""
    dt = datetime.strptime(start_time_str, "%H:%M")
    end_dt = dt + timedelta(minutes=int(duration_minutes))
    return end_dt.strftime("%H:%M")

def check_schedule_conflict(mentor_id, student_id, schedule_date, start_time, end_time, exclude_schedule_id=None):
    """
    Memeriksa bentrokan jadwal untuk mentor dan siswa pada tanggal dan jam tertentu.
    Overlapping check: existing_start < new_end AND existing_end > new_start
    """
    mentor_conflict = None
    student_conflict = None

    # 1. Cek bentrokan jadwal mentor
    mentor_query = """
        SELECT s.id, s.title, s.schedule_date, s.start_time, s.end_time, s.status,
               m.full_name as mentor_name, st.full_name as student_name
        FROM schedules s
        JOIN mentors m ON s.mentor_id = m.id
        JOIN students st ON s.student_id = st.id
        WHERE s.mentor_id = ?
          AND s.schedule_date = ?
          AND s.status NOT IN ('ditolak', 'dibatalkan')
          AND s.start_time < ? AND s.end_time > ?
    """
    mentor_params = [mentor_id, schedule_date, end_time, start_time]
    if exclude_schedule_id:
        mentor_query += " AND s.id != ?"
        mentor_params.append(exclude_schedule_id)

    m_row = query_db(mentor_query, mentor_params, one=True)
    if m_row:
        mentor_conflict = dict(m_row)

    # 2. Cek bentrokan jadwal siswa
    student_query = """
        SELECT s.id, s.title, s.schedule_date, s.start_time, s.end_time, s.status,
               m.full_name as mentor_name, st.full_name as student_name
        FROM schedules s
        JOIN mentors m ON s.mentor_id = m.id
        JOIN students st ON s.student_id = st.id
        WHERE s.student_id = ?
          AND s.schedule_date = ?
          AND s.status NOT IN ('ditolak', 'dibatalkan')
          AND s.start_time < ? AND s.end_time > ?
    """
    student_params = [student_id, schedule_date, end_time, start_time]
    if exclude_schedule_id:
        student_query += " AND s.id != ?"
        student_params.append(exclude_schedule_id)

    s_row = query_db(student_query, student_params, one=True)
    if s_row:
        student_conflict = dict(s_row)

    has_conflict = bool(mentor_conflict or student_conflict)
    messages = []
    if mentor_conflict:
        messages.append(f"Mentor {mentor_conflict['mentor_name']} telah memiliki jadwal ({mentor_conflict['start_time']} - {mentor_conflict['end_time']}) untuk siswa {mentor_conflict['student_name']}.")
    if student_conflict:
        messages.append(f"Siswa {student_conflict['student_name']} telah memiliki jadwal ({student_conflict['start_time']} - {student_conflict['end_time']}) bersama mentor {student_conflict['mentor_name']}.")

    return {
        "has_conflict": has_conflict,
        "mentor_conflict": mentor_conflict,
        "student_conflict": student_conflict,
        "message": " & ".join(messages) if messages else "Waktu tersedia, tidak ada bentrokan jadwal."
    }

def create_schedule_proposal(title, program_id, student_id, mentor_id, schedule_date, start_time, duration_minutes, session_notes, created_by_user_id, status="menunggu_persetujuan_admin"):
    """
    Membuat sesi jadwal les. Jika status disetujui, langsung berstatus FIX.
    Melakukan pengecekan bentrokan terlebih dahulu.
    """
    end_time = calculate_end_time(start_time, duration_minutes)

    # Deteksi bentrokan
    conflict = check_schedule_conflict(mentor_id, student_id, schedule_date, start_time, end_time)
    if conflict["has_conflict"]:
        return {
            "success": False,
            "message": f"Gagal membuat jadwal: {conflict['message']}",
            "conflict": conflict
        }

    approved_by = created_by_user_id if status == "disetujui" else None

    # Simpan jadwal ke database
    query = """
        INSERT INTO schedules (
            title, program_id, student_id, mentor_id, schedule_date, start_time, end_time,
            duration_minutes, status, student_confirmation_status, mentor_response_status,
            session_notes, created_by, approved_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'bersedia', 'dikonfirmasi', ?, ?, ?)
    """
    schedule_id = execute_db(query, (
        title or "Sesi Les Privat",
        program_id,
        student_id,
        mentor_id,
        schedule_date,
        start_time,
        end_time,
        int(duration_minutes),
        status,
        session_notes,
        created_by_user_id,
        approved_by
    ))

    # Ambil detail untuk notifikasi
    st_info = query_db("SELECT full_name FROM students WHERE id = ?", (student_id,), one=True)
    m_info = query_db("SELECT full_name FROM mentors WHERE id = ?", (mentor_id,), one=True)
    st_name = st_info["full_name"] if st_info else "Siswa"
    m_name = m_info["full_name"] if m_info else "Mentor"

    # Beritahu Admin
    notify_admins(
        "Jadwal Les Baru Terbit (Fix)",
        f"Jadwal les fix telah diterbitkan untuk {st_name} bersama {m_name} pada {schedule_date} pukul {start_time}.",
        "jadwal",
        "/admin/schedules"
    )

    return {
        "success": True,
        "schedule_id": schedule_id,
        "message": "Jadwal les resmi berhasil dibuat dan siap dilaksanakan (Fix)."
    }

def generate_recurring_schedules(
    title, program_id, student_id, mentor_id, days_of_week_list,
    start_date_str=None, end_date_str=None, start_time="16:00",
    duration_minutes=90, notes="", created_by_user_id=1
):
    """
    Membuat rangkaian jadwal berulang mingguan.
    Mengecek bentrokan pada SETIAP tanggal terlebih dahulu.
    Jika ada bentrokan pada salah satu tanggal, mengembalikan daftar tanggal yang bermasalah.
    """
    end_time = calculate_end_time(start_time, duration_minutes)
    if not start_date_str:
        start_dt = datetime.now()
        start_date_str = start_dt.strftime("%Y-%m-%d")
    else:
        start_dt = datetime.strptime(str(start_date_str).strip(), "%Y-%m-%d")

    if not end_date_str:
        end_dt = start_dt + timedelta(days=28)
        end_date_str = end_dt.strftime("%Y-%m-%d")
    else:
        end_dt = datetime.strptime(str(end_date_str).strip(), "%Y-%m-%d")

    target_days = [int(d) for d in days_of_week_list]
    matched_dates = []
    curr = start_dt
    while curr <= end_dt:
        if curr.weekday() in target_days:
            matched_dates.append(curr.strftime("%Y-%m-%d"))
        curr += timedelta(days=1)

    if not matched_dates:
        return {
            "success": False,
            "message": "Tidak ada hari yang sesuai dalam rentang tanggal yang dipilih."
        }

    # Periksa bentrokan untuk semua tanggal
    conflicts_found = []
    for d_str in matched_dates:
        conf = check_schedule_conflict(mentor_id, student_id, d_str, start_time, end_time)
        if conf["has_conflict"]:
            conflicts_found.append({
                "date": d_str,
                "message": conf["message"]
            })

    if conflicts_found:
        conflict_details = "; ".join([f"{c['date']}: {c['message']}" for c in conflicts_found])
        return {
            "success": False,
            "message": f"Terdapat bentrokan jadwal pada tanggal: {conflict_details}. Silakan sesuaikan waktu atau tanggal terlebih dahulu.",
            "conflicts": conflicts_found
        }

    # Simpan aturan jadwal berulang
    days_str = ",".join(str(d) for d in target_days)
    rule_id = execute_db("""
        INSERT INTO recurring_schedule_rules (
            program_id, student_id, mentor_id, days_of_week, start_date, end_date,
            start_time, duration_minutes, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        program_id, student_id, mentor_id, days_str, start_date_str, end_date_str,
        start_time, int(duration_minutes), notes
    ))

    # Masukkan setiap sesi ke tabel schedules
    created_schedule_ids = []
    for d_str in matched_dates:
        sid = execute_db("""
            INSERT INTO schedules (
                title, program_id, student_id, mentor_id, schedule_date, start_time, end_time,
                duration_minutes, status, student_confirmation_status, mentor_response_status,
                is_recurring, recurring_rule_id, session_notes, created_by, approved_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'disetujui', 'bersedia', 'dikonfirmasi', 1, ?, ?, ?, ?)
        """, (
            title or f"Sesi Les Rutin ({d_str})",
            program_id,
            student_id,
            mentor_id,
            d_str,
            start_time,
            end_time,
            int(duration_minutes),
            rule_id,
            notes,
            created_by_user_id,
            created_by_user_id
        ))
        created_schedule_ids.append(sid)

    notify_admins(
        "Jadwal Berulang Berhasil Dibuat",
        f"Dibuat {len(created_schedule_ids)} sesi jadwal berulang untuk periode {start_date_str} s/d {end_date_str}.",
        "jadwal",
        "/admin/schedules"
    )

    return {
        "success": True,
        "rule_id": rule_id,
        "count": len(created_schedule_ids),
        "message": f"Berhasil membuat {len(created_schedule_ids)} sesi jadwal rutin tanpa bentrokan."
    }

def approve_schedule(schedule_id, admin_user_id):
    """Menyetujui jadwal les oleh Admin."""
    schedule = query_db("""
        SELECT s.*, st.full_name as student_name, m.full_name as mentor_name,
               m.user_id as mentor_user_id, p.phone as parent_phone
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN mentors m ON s.mentor_id = m.id
        JOIN parents p ON st.parent_id = p.id
        WHERE s.id = ?
    """, (schedule_id,), one=True)

    if not schedule:
        return {"success": False, "message": "Jadwal tidak ditemukan."}

    execute_db("""
        UPDATE schedules
        SET status = 'disetujui', approved_by = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (admin_user_id, schedule_id))

    # Notifikasi ke Mentor
    if schedule["mentor_user_id"]:
        create_notification(
            schedule["mentor_user_id"],
            "Jadwal Mengajar Disetujui",
            f"Jadwal mengajar dengan {schedule['student_name']} pada {schedule['schedule_date']} pukul {schedule['start_time']} telah disetujui Admin. Mohon segera konfirmasi.",
            "jadwal",
            "/mentor/schedules"
        )

    # Kirim/Simulasikan WhatsApp ke Wali Murid
    if schedule["parent_phone"]:
        send_whatsapp_message(
            schedule["parent_phone"],
            f"Halo Ayah/Bunda dari {schedule['student_name']},\nJadwal les privat DESI PRIVAT telah disetujui untuk tanggal {schedule['schedule_date']} pukul {schedule['start_time']}-{schedule['end_time']} WIB bersama {schedule['mentor_name']}.",
            "konfirmasi_jadwal"
        )

    # Audit log
    admin_user = query_db("SELECT username FROM users WHERE id = ?", (admin_user_id,), one=True)
    admin_name = admin_user["username"] if admin_user else "admin"
    log_audit(
        admin_user_id,
        admin_name,
        "SETUJUI_JADWAL",
        "schedules",
        schedule_id,
        f"Menyetujui jadwal ID {schedule_id} ({schedule['student_name']} - {schedule['schedule_date']})"
    )

    return {"success": True, "message": "Jadwal berhasil disetujui dan notifikasi telah dikirimkan."}

def mentor_respond_schedule(schedule_id, mentor_user_id, response_choice, reason=""):
    """
    Mentor mengonfirmasi atau menyatakan tidak bisa mengajar.
    response_choice: 'dikonfirmasi' atau 'tidak_bisa'
    """
    schedule = query_db("""
        SELECT s.*, m.id as mentor_record_id, m.full_name as mentor_name,
               st.full_name as student_name
        FROM schedules s
        JOIN mentors m ON s.mentor_id = m.id
        JOIN students st ON s.student_id = st.id
        WHERE s.id = ? AND m.user_id = ?
    """, (schedule_id, mentor_user_id), one=True)

    if not schedule:
        return {"success": False, "message": "Jadwal tidak ditemukan atau Anda tidak berwenang atas jadwal ini."}

    if response_choice == "dikonfirmasi":
        execute_db("""
            UPDATE schedules
            SET mentor_response_status = 'dikonfirmasi',
                mentor_response_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (schedule_id,))
        msg = "Jadwal berhasil dikonfirmasi. Terima kasih atas kesiapan Anda mengajar."
    elif response_choice == "tidak_bisa":
        if not reason or not reason.strip():
            return {"success": False, "message": "Wajib memberikan alasan jika tidak dapat mengajar."}

        execute_db("""
            UPDATE schedules
            SET mentor_response_status = 'perlu_mentor_pengganti',
                mentor_response_notes = ?,
                mentor_response_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reason.strip(), schedule_id))

        # Beritahu Admin bahwa jadwal memerlukan mentor pengganti
        notify_admins(
            "Perlu Mentor Pengganti Segera",
            f"Mentor {schedule['mentor_name']} tidak dapat mengajar {schedule['student_name']} pada {schedule['schedule_date']} ({schedule['start_time']}). Alasan: {reason}",
            "penggantian",
            "/admin/schedules"
        )
        msg = "Penolakan jadwal telah dicatat dan Admin telah diberitahu untuk menyiapkan mentor pengganti."
    else:
        return {"success": False, "message": "Pilihan respons tidak valid."}

    return {"success": True, "message": msg}

def check_overdue_mentor_responses():
    """
    Mengecek jadwal resmi (disetujui) yang status mentornya masih 'menunggu_konfirmasi'
    dan telah melewati batas waktu respons yang ditentukan.
    """
    timeout_hours = Config.SCHEDULE_RESPONSE_TIMEOUT_HOURS
    query = """
        SELECT s.id, s.title, s.schedule_date, s.start_time, s.end_time, s.created_at,
               m.full_name as mentor_name, m.phone as mentor_phone,
               st.full_name as student_name
        FROM schedules s
        JOIN mentors m ON s.mentor_id = m.id
        JOIN students st ON s.student_id = st.id
        WHERE s.status = 'disetujui'
          AND s.mentor_response_status = 'menunggu_konfirmasi'
          AND (
            julianday('now') - julianday(s.updated_at) >= (? / 24.0)
            OR date(s.schedule_date) <= date('now', '+1 day')
          )
        ORDER BY s.schedule_date ASC
    """
    return query_db(query, (timeout_hours,))

def get_eligible_replacement_mentors(schedule_id):
    """
    Mencari daftar mentor aktif yang dapat menggantikan mentor saat ini,
    beserta informasi apakah jadwalnya bentrok atau bebas.
    """
    schedule = query_db("SELECT * FROM schedules WHERE id = ?", (schedule_id,), one=True)
    if not schedule:
        return []

    mentors = query_db("""
        SELECT id, full_name, phone, expertise, bio
        FROM mentors
        WHERE status = 'aktif' AND id != ?
        ORDER BY full_name ASC
    """, (schedule["mentor_id"],))

    result = []
    for m in mentors:
        conf = check_schedule_conflict(
            m["id"],
            schedule["student_id"],
            schedule["schedule_date"],
            schedule["start_time"],
            schedule["end_time"],
            exclude_schedule_id=schedule["id"]
        )
        result.append({
            "mentor": dict(m),
            "has_conflict": conf["has_conflict"],
            "conflict_message": conf["message"]
        })
    return result

def execute_mentor_replacement(schedule_id, replacement_mentor_id, reason, admin_user_id):
    """
    Menjalankan pergantian mentor untuk jadwal tertentu:
    - Menyimpan catatan ke tabel mentor_replacements
    - Memperbarui mentor_id di tabel schedules
    - Mereset status respons mentor menjadi 'menunggu_konfirmasi'
    - Mengirim notifikasi ke mentor awal, mentor baru, dan wali murid
    - Mencatat audit log
    """
    schedule = query_db("""
        SELECT s.*, st.full_name as student_name, p.phone as parent_phone,
               m_old.full_name as old_mentor_name, m_old.user_id as old_mentor_user_id
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN parents p ON st.parent_id = p.id
        JOIN mentors m_old ON s.mentor_id = m_old.id
        WHERE s.id = ?
    """, (schedule_id,), one=True)

    if not schedule:
        return {"success": False, "message": "Jadwal tidak ditemukan."}

    new_mentor = query_db("SELECT * FROM mentors WHERE id = ?", (replacement_mentor_id,), one=True)
    if not new_mentor:
        return {"success": False, "message": "Mentor pengganti tidak ditemukan."}

    # Cek bentrokan untuk mentor baru
    conf = check_schedule_conflict(
        replacement_mentor_id,
        schedule["student_id"],
        schedule["schedule_date"],
        schedule["start_time"],
        schedule["end_time"],
        exclude_schedule_id=schedule_id
    )
    if conf["has_conflict"]:
        return {
            "success": False,
            "message": f"Mentor pengganti tidak dapat dipilih: {conf['message']}"
        }

    # 1. Catat ke tabel mentor_replacements
    execute_db("""
        INSERT INTO mentor_replacements (
            schedule_id, original_mentor_id, replacement_mentor_id, reason, changed_by
        ) VALUES (?, ?, ?, ?, ?)
    """, (schedule_id, schedule["mentor_id"], replacement_mentor_id, reason, admin_user_id))

    # 2. Perbarui schedules
    execute_db("""
        UPDATE schedules
        SET mentor_id = ?,
            mentor_response_status = 'menunggu_konfirmasi',
            mentor_response_notes = NULL,
            mentor_response_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (replacement_mentor_id, schedule_id))

    # 3. Notifikasi ke Mentor Pengganti
    if new_mentor["user_id"]:
        create_notification(
            new_mentor["user_id"],
            "Penugasan Mentor Pengganti",
            f"Anda ditugaskan sebagai mentor pengganti untuk {schedule['student_name']} pada {schedule['schedule_date']} pukul {schedule['start_time']}. Alasan pergantian: {reason}. Mohon konfirmasi kesiapan Anda.",
            "penggantian",
            "/mentor/schedules"
        )

    # 4. Notifikasi ke Mentor Lama
    if schedule["old_mentor_user_id"]:
        create_notification(
            schedule["old_mentor_user_id"],
            "Pembaruan Jadwal Mengajar",
            f"Jadwal sesi {schedule['schedule_date']} dengan {schedule['student_name']} telah dialihkan ke mentor pengganti ({new_mentor['full_name']}).",
            "info",
            "/mentor/schedules"
        )

    return {
        "success": True,
        "message": f"Berhasil mengganti mentor menjadi {new_mentor['full_name']}."
    }

# ========================================================
# JADWAL RUTIN MINGGUAN (LANGSUNG DITETAPKAN ADMIN)
# ========================================================
DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

def check_routine_schedule_conflict(mentor_id, day_of_week, start_time, end_time, exclude_id=None, student_id=None, db_path=None):
    """
    Memeriksa apakah ada bentrokan pada jadwal rutin mentor atau siswa:
    - Apakah mentor sudah memiliki jadwal rutin lain di hari dan jam yang bertabrakan?
    - Apakah siswa sudah memiliki jadwal rutin lain di hari dan jam yang bertabrakan?
    """
    try:
        dow = int(day_of_week)
    except (TypeError, ValueError):
        return {"has_conflict": False, "message": ""}

    # 1. Cek bentrokan jadwal rutin mentor
    query_m = """
        SELECT rs.id, rs.start_time, rs.end_time, rs.day_of_week,
               st.full_name as student_name, m.full_name as mentor_name,
               pr.name as program_name
        FROM routine_schedules rs
        JOIN students st ON rs.student_id = st.id
        JOIN mentors m ON rs.mentor_id = m.id
        JOIN programs pr ON rs.program_id = pr.id
        WHERE rs.mentor_id = ? AND rs.day_of_week = ? AND rs.status = 'aktif'
    """
    params_m = [mentor_id, dow]
    if exclude_id:
        query_m += " AND rs.id != ?"
        params_m.append(exclude_id)

    existing_m = query_db(query_m, params_m, db_path=db_path)
    for ex in existing_m:
        # Cek overlap: max(start1, start2) < min(end1, end2)
        if max(ex["start_time"], start_time) < min(ex["end_time"], end_time):
            day_name = DAY_NAMES[dow] if 0 <= dow < 7 else f"Hari {dow}"
            return {
                "has_conflict": True,
                "conflict_type": "mentor",
                "message": f"Bentrok jadwal mentor: {ex['mentor_name']} telah memiliki jadwal mengajar pada hari {day_name} pukul {ex['start_time']} - {ex['end_time']} untuk siswa {ex['student_name']} ({ex['program_name']})."
            }

    # 2. Cek bentrokan jadwal rutin siswa (jika student_id diberikan)
    if student_id:
        query_s = """
            SELECT rs.id, rs.start_time, rs.end_time, rs.day_of_week,
                   st.full_name as student_name, m.full_name as mentor_name,
                   pr.name as program_name
            FROM routine_schedules rs
            JOIN students st ON rs.student_id = st.id
            JOIN mentors m ON rs.mentor_id = m.id
            JOIN programs pr ON rs.program_id = pr.id
            WHERE rs.student_id = ? AND rs.day_of_week = ? AND rs.status = 'aktif'
        """
        params_s = [student_id, dow]
        if exclude_id:
            query_s += " AND rs.id != ?"
            params_s.append(exclude_id)

        existing_s = query_db(query_s, params_s, db_path=db_path)
        for ex in existing_s:
            if max(ex["start_time"], start_time) < min(ex["end_time"], end_time):
                day_name = DAY_NAMES[dow] if 0 <= dow < 7 else f"Hari {dow}"
                return {
                    "has_conflict": True,
                    "conflict_type": "student",
                    "message": f"Bentrok jadwal siswa: Siswa {ex['student_name']} sudah memiliki jadwal les pada hari {day_name} pukul {ex['start_time']} - {ex['end_time']} bersama mentor {ex['mentor_name']} ({ex['program_name']})."
                }

    return {"has_conflict": False, "message": "Waktu tersedia, tidak ada bentrokan."}

def create_routine_schedule(student_id, program_id, mentor_id, day_of_week, start_time, end_time, subject_info="", notes="", db_path=None):
    """
    Membuat satu slot jadwal rutin mingguan siswa dengan validasi bentrokan.
    """
    conflict = check_routine_schedule_conflict(mentor_id, day_of_week, start_time, end_time, student_id=student_id, db_path=db_path)
    if conflict["has_conflict"]:
        return {"success": False, "message": conflict["message"]}

    rs_id = execute_db("""
        INSERT INTO routine_schedules (
            student_id, program_id, mentor_id, day_of_week,
            start_time, end_time, subject_info, notes, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'aktif')
    """, (student_id, program_id, mentor_id, int(day_of_week), start_time, end_time, subject_info.strip(), notes.strip()), db_path=db_path)

    return {
        "success": True,
        "id": rs_id,
        "message": f"Jadwal rutin hari {DAY_NAMES[int(day_of_week)]} ({start_time} - {end_time}) berhasil ditetapkan."
    }

def update_routine_schedule(routine_id, day_of_week, start_time, end_time, mentor_id=None, subject_info="", notes="", db_path=None):
    """
    Memperbarui slot jadwal rutin mingguan yang sudah ada (dengan pengecekan bentrokan).
    Riwayat absensi masa lalu tetap aman.
    """
    curr = query_db("SELECT * FROM routine_schedules WHERE id = ?", (routine_id,), one=True, db_path=db_path)
    if not curr:
        return {"success": False, "message": "Jadwal rutin tidak ditemukan."}

    m_id = mentor_id if mentor_id else curr["mentor_id"]
    conflict = check_routine_schedule_conflict(m_id, day_of_week, start_time, end_time, exclude_id=routine_id, student_id=curr["student_id"], db_path=db_path)
    if conflict["has_conflict"]:
        return {"success": False, "message": conflict["message"]}

    execute_db("""
        UPDATE routine_schedules
        SET day_of_week = ?, start_time = ?, end_time = ?, mentor_id = ?,
            subject_info = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (int(day_of_week), start_time, end_time, m_id, subject_info.strip(), notes.strip(), routine_id), db_path=db_path)

    return {"success": True, "message": "Jadwal rutin mingguan berhasil diperbarui."}

def delete_routine_schedule(routine_id, db_path=None):
    """
    Menghapus satu slot jadwal rutin mingguan. Riwayat pertemuan masa lalu tetap terjaga.
    """
    execute_db("DELETE FROM routine_schedules WHERE id = ?", (routine_id,), db_path=db_path)
    return {"success": True, "message": "Jadwal rutin berhasil dihapus."}

def get_routine_schedules(student_id=None, mentor_id=None, day_of_week=None, status="aktif", db_path=None):
    """
    Mengambil daftar jadwal rutin mingguan lengkap dengan informasi siswa, mentor, dan program.
    """
    conditions = []
    args = []
    if student_id:
        conditions.append("rs.student_id = ?")
        args.append(student_id)
    if mentor_id:
        conditions.append("rs.mentor_id = ?")
        args.append(mentor_id)
    if day_of_week is not None and day_of_week != "":
        conditions.append("rs.day_of_week = ?")
        args.append(int(day_of_week))
    if status:
        conditions.append("rs.status = ?")
        args.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT rs.*,
               st.full_name as student_name, st.school as student_school, st.grade as student_grade,
               m.full_name as mentor_name, m.phone as mentor_phone,
               pr.name as program_name,
               p.full_name as parent_name, p.phone as parent_phone
        FROM routine_schedules rs
        JOIN students st ON rs.student_id = st.id
        JOIN mentors m ON rs.mentor_id = m.id
        JOIN programs pr ON rs.program_id = pr.id
        LEFT JOIN parents p ON st.parent_id = p.id
        {where_clause}
        ORDER BY rs.day_of_week ASC, rs.start_time ASC
    """
    rows = query_db(query, args, db_path=db_path)
    result = []
    for r in rows:
        d = dict(r)
        dow = d["day_of_week"]
        d["day_name"] = DAY_NAMES[dow] if 0 <= dow < 7 else f"Hari {dow}"
        result.append(d)
    return result

def get_mentor_today_routine(mentor_id, db_path=None):
    """
    Mengambil jadwal rutin yang dijadwalkan untuk hari ini bagi mentor tertentu.
    """
    today_dow = datetime.now().weekday()
    return get_routine_schedules(mentor_id=mentor_id, day_of_week=today_dow, db_path=db_path)
