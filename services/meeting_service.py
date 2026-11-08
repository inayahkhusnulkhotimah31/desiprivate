"""
DESI PRIVAT - Meeting & Period Calculation Service
Layanan perhitungan otomatis siklus periode dan nomor pertemuan les:
- 1 periode = 8 pertemuan valid dihitung dari absensi aktual (status 'hadir')
- Rumus Periode: ((total pertemuan - 1) // 8) + 1
- Rumus Pertemuan: ((total pertemuan - 1) % 8) + 1
- Format:
  * Periode 1: Pertemuan 1 s.d Pertemuan 8
  * Periode 2: Pertemuan 1 [2] s.d Pertemuan 8 [2]
  * Periode 3: Pertemuan 1 [3] s.d Pertemuan 8 [3]
- Perhitungan periode INDEPENDEN untuk setiap program yang diikuti siswa
- Pengelolaan baseline riwayat awal siswa lama per program tanpa membuat absensi fiktif
- Resequencing otomatis dan pencegahan perhitungan ganda saat edit/reload
"""
from services.database_service import query_db, execute_db
from services.audit_service import log_audit

MEETINGS_PER_PERIOD = 8

def format_meeting_label(period_number, meeting_number, style="bracket"):
    """
    Format label nomor pertemuan dan periode:
    - style='bracket': Periode 1 -> 'Pertemuan 1', Periode 2 -> 'Pertemuan 1 [2]'
    - style='paren': 'Pertemuan 1 (1)', 'Pertemuan 1 (2)'
    """
    try:
        p = int(period_number)
        m = int(meeting_number)
    except (TypeError, ValueError):
        return "-"

    if p <= 0 or m <= 0:
        return "-"

    if style == "bracket":
        if p == 1:
            return f"Pertemuan {m}"
        return f"Pertemuan {m} [{p}]"
    else:
        return f"Pertemuan {m} ({p})"

def calculate_period_and_meeting(total_valid_meetings):
    """
    Menghitung nomor periode dan nomor pertemuan berdasarkan total pertemuan valid.
    Kompatibel dengan pengujian dan tampilan sistem.
    Contoh:
    1 -> Periode 1, Pertemuan 1 -> 'Pertemuan 1 (1)'
    8 -> Periode 1, Pertemuan 8 -> 'Pertemuan 8 (1)'
    9 -> Periode 2, Pertemuan 1 -> 'Pertemuan 1 (2)'
    16 -> Periode 2, Pertemuan 8 -> 'Pertemuan 8 (2)'
    17 -> Periode 3, Pertemuan 1 -> 'Pertemuan 1 (3)'
    41 -> Periode 6, Pertemuan 1 -> 'Pertemuan 1 (6)'
    """
    try:
        total = int(total_valid_meetings)
    except (TypeError, ValueError):
        total = 0

    if total <= 0:
        return 0, 0, "-"

    period_number = ((total - 1) // MEETINGS_PER_PERIOD) + 1
    meeting_number = ((total - 1) % MEETINGS_PER_PERIOD) + 1
    formatted = f"Pertemuan {meeting_number} ({period_number})"
    return period_number, meeting_number, formatted

def calculate_total_from_period_and_meeting(period_number, meeting_number):
    """
    Menghitung total pertemuan kumulatif dari kombinasi periode dan nomor pertemuan terakhir.
    Contoh:
    Periode 1, Pertemuan 1 -> Total 1
    Periode 1, Pertemuan 8 -> Total 8
    Periode 2, Pertemuan 1 -> Total 9
    Periode 4, Pertemuan 3 -> Total (4 - 1) * 8 + 3 = 27
    Periode 6, Pertemuan 0 -> Total (6 - 1) * 8 = 40
    """
    try:
        p = int(period_number)
        m = int(meeting_number)
    except (TypeError, ValueError):
        return 0

    if p <= 0 or m < 0:
        return 0
    if m == 0:
        return (p - 1) * MEETINGS_PER_PERIOD
    return ((p - 1) * MEETINGS_PER_PERIOD) + m

def get_student_program_meeting_stats(student_id, program_id, db_path=None):
    """
    Mengambil statistik pertemuan independen untuk kombinasi (student_id, program_id):
    - Offset awal siswa lama untuk program ini
    - Jumlah absensi hadir tercatat di sistem untuk program ini
    - Total pertemuan diselesaikan (offset program + absensi sistem)
    - Periode & nomor pertemuan saat ini serta sesi berikutnya
    """
    student = query_db(
        "SELECT id, full_name, initial_meeting_offset, initial_offset_notes, initial_offset_set_at FROM students WHERE id = ?",
        (student_id,),
        one=True,
        db_path=db_path
    )
    if not student:
        return None

    program = query_db(
        "SELECT id, name FROM programs WHERE id = ?",
        (program_id,),
        one=True,
        db_path=db_path
    )
    program_name = program["name"] if program else f"Program {program_id}"

    # Cari data pendaftaran program
    sp = query_db(
        """
        SELECT id, initial_periods_completed, initial_last_meeting, initial_offset_total,
               initial_offset_notes, initial_offset_set_at, initial_offset_set_by
        FROM student_programs
        WHERE student_id = ? AND program_id = ?
        """,
        (student_id, program_id),
        one=True,
        db_path=db_path
    )

    if sp and (sp["initial_offset_total"] is not None and sp["initial_offset_total"] > 0):
        initial_offset = sp["initial_offset_total"]
        initial_period = sp["initial_periods_completed"] or 0
        initial_meeting = sp["initial_last_meeting"] or 0
        offset_notes = sp["initial_offset_notes"] or ""
        offset_set_at = sp["initial_offset_set_at"]
    elif sp and (sp["initial_periods_completed"] or sp["initial_last_meeting"]):
        initial_period = sp["initial_periods_completed"] or 0
        initial_meeting = sp["initial_last_meeting"] or 0
        initial_offset = calculate_total_from_period_and_meeting(initial_period, initial_meeting)
        offset_notes = sp["initial_offset_notes"] or ""
        offset_set_at = sp["initial_offset_set_at"]
    else:
        # Fallback kompatibilitas mundur ke initial_meeting_offset pada siswa jika hanya ada 1 program
        initial_offset = student["initial_meeting_offset"] or 0
        if initial_offset > 0:
            initial_period, initial_meeting, _ = calculate_period_and_meeting(initial_offset)
        else:
            initial_period, initial_meeting = 0, 0
        offset_notes = student["initial_offset_notes"] or ""
        offset_set_at = student["initial_offset_set_at"]

    # Ambil jumlah absensi valid (status = hadir) KHUSUS program ini
    att_row = query_db(
        """
        SELECT COUNT(a.id) as valid_count
        FROM attendance a
        JOIN schedules s ON a.schedule_id = s.id
        WHERE a.student_id = ? AND s.program_id = ? AND a.status = 'hadir'
        """,
        (student_id, program_id),
        one=True,
        db_path=db_path
    )
    valid_count = att_row["valid_count"] if att_row else 0
    total_completed = initial_offset + valid_count

    if total_completed > 0:
        last_p, last_m, last_str = calculate_period_and_meeting(total_completed)
        last_bracket = format_meeting_label(last_p, last_m, style="bracket")
    else:
        last_p, last_m, last_str, last_bracket = 0, 0, "Belum ada", "Belum ada"

    next_p, next_m, next_str = calculate_period_and_meeting(total_completed + 1)
    next_bracket = format_meeting_label(next_p, next_m, style="bracket")

    return {
        "student_id": student["id"],
        "student_name": student["full_name"],
        "program_id": program_id,
        "program_name": program_name,
        "student_program_id": sp["id"] if sp else None,
        "initial_offset": initial_offset,
        "initial_period": initial_period,
        "initial_meeting": initial_meeting,
        "valid_attendance_count": valid_count,
        "total_completed": total_completed,
        "total_meetings": total_completed,
        "last_period": last_p,
        "last_meeting": last_m,
        "last_meeting_str": last_str,
        "last_meeting_bracket": last_bracket,
        "next_period": next_p,
        "next_meeting": next_m,
        "next_meeting_str": next_str,
        "next_meeting_bracket": next_bracket,
        "offset_notes": offset_notes,
        "offset_set_at": offset_set_at
    }

def get_student_meeting_stats(student_id, program_id=None, db_path=None):
    """
    Mengambil statistik pertemuan siswa:
    - Jika program_id diberikan: kembalikan statistik spesifik program tersebut.
    - Jika program_id None: kembalikan agregat seluruh program yang diikuti siswa,
      dengan daftar statistik per program pada key 'programs_stats'.
    """
    if program_id is not None:
        return get_student_program_meeting_stats(student_id, program_id, db_path=db_path)

    student = query_db(
        "SELECT id, full_name, initial_meeting_offset, initial_offset_notes, initial_offset_set_at FROM students WHERE id = ?",
        (student_id,),
        one=True,
        db_path=db_path
    )
    if not student:
        return None

    # Cari seluruh program yang diikuti siswa
    active_progs = query_db(
        """
        SELECT sp.program_id, pr.name as program_name
        FROM student_programs sp
        JOIN programs pr ON sp.program_id = pr.id
        WHERE sp.student_id = ?
        ORDER BY sp.id ASC
        """,
        (student_id,),
        db_path=db_path
    )

    programs_stats = []
    total_completed_all = 0
    valid_count_all = 0
    initial_offset_all = 0

    if active_progs:
        for p in active_progs:
            p_stat = get_student_program_meeting_stats(student_id, p["program_id"], db_path=db_path)
            if p_stat:
                programs_stats.append(p_stat)
                total_completed_all += p_stat["total_completed"]
                valid_count_all += p_stat["valid_attendance_count"]
                initial_offset_all += p_stat["initial_offset"]

    # Fallback jika belum memiliki record di student_programs
    if not programs_stats:
        initial_offset_all = student["initial_meeting_offset"] or 0
        att_all = query_db(
            "SELECT COUNT(*) as c FROM attendance WHERE student_id = ? AND status = 'hadir'",
            (student_id,),
            one=True,
            db_path=db_path
        )
        valid_count_all = att_all["c"] if att_all else 0
        total_completed_all = initial_offset_all + valid_count_all

    # Ambil primary program stat untuk nilai default
    primary = programs_stats[0] if programs_stats else None
    if primary:
        last_p = primary["last_period"]
        last_m = primary["last_meeting"]
        last_str = primary["last_meeting_str"]
        last_bracket = primary["last_meeting_bracket"]
        next_p = primary["next_period"]
        next_m = primary["next_meeting"]
        next_str = primary["next_meeting_str"]
        next_bracket = primary["next_meeting_bracket"]
    else:
        if total_completed_all > 0:
            last_p, last_m, last_str = calculate_period_and_meeting(total_completed_all)
            last_bracket = format_meeting_label(last_p, last_m, style="bracket")
        else:
            last_p, last_m, last_str, last_bracket = 0, 0, "Belum ada", "Belum ada"
        next_p, next_m, next_str = calculate_period_and_meeting(total_completed_all + 1)
        next_bracket = format_meeting_label(next_p, next_m, style="bracket")

    return {
        "student_id": student["id"],
        "student_name": student["full_name"],
        "initial_offset": initial_offset_all,
        "valid_attendance_count": valid_count_all,
        "total_completed": total_completed_all,
        "total_meetings": total_completed_all,
        "last_period": last_p,
        "last_meeting": last_m,
        "last_meeting_str": last_str,
        "last_meeting_bracket": last_bracket,
        "next_period": next_p,
        "next_meeting": next_m,
        "next_meeting_str": next_str,
        "next_meeting_bracket": next_bracket,
        "offset_notes": student["initial_offset_notes"],
        "offset_set_at": student["initial_offset_set_at"],
        "programs_stats": programs_stats,
        "programs_count": len(programs_stats)
    }

def record_or_update_attendance(
    schedule_id, student_id, mentor_id, status,
    notes="", topics_covered="", progress_notes="",
    skills_mastered="", difficulties="", recommendations="",
    db_path=None
):
    """
    Mencatat atau memperbarui absensi dengan perhitungan nomor pertemuan & periode independen per program.
    - Status 'hadir': dihitung sebagai pertemuan valid pada program terkait.
    - Status 'izin' / 'tidak_hadir': TIDAK dihitung sebagai pertemuan valid.
    - Edit absensi yang sudah 'hadir': nomor pertemuan & periode dipertahankan (tidak bertambah).
    - Mencegah absensi ganda pada schedule_id yang sama.
    """
    sched = query_db(
        "SELECT program_id, schedule_date FROM schedules WHERE id = ?",
        (schedule_id,),
        one=True,
        db_path=db_path
    )
    program_id = sched["program_id"] if sched else None

    # Ambil statistik khusus program dari jadwal ini
    stats = get_student_program_meeting_stats(student_id, program_id, db_path=db_path) if program_id else get_student_meeting_stats(student_id, db_path=db_path)
    if not stats:
        return {"success": False, "message": "Data siswa atau program tidak ditemukan."}

    existing = query_db(
        "SELECT * FROM attendance WHERE schedule_id = ?",
        (schedule_id,),
        one=True,
        db_path=db_path
    )

    if existing:
        # Sedang mengedit absensi yang sudah ada
        old_status = existing["status"]
        if status == "hadir":
            if old_status == "hadir" and existing["cumulative_meeting"]:
                # Pertahankan nomor lama yang sudah tersimpan
                cum_num = existing["cumulative_meeting"]
                p_num = existing["period_number"]
                m_num = existing["meeting_number"]
            else:
                # Baru diubah menjadi 'hadir'
                cum_num = stats["total_completed"] + 1
                p_num, m_num, _ = calculate_period_and_meeting(cum_num)
        else:
            # Diubah menjadi izin / tidak hadir
            cum_num = None
            p_num = None
            m_num = None

        execute_db(
            """
            UPDATE attendance
            SET status = ?, notes = ?, topics_covered = ?, progress_notes = ?,
                meeting_number = ?, period_number = ?, cumulative_meeting = ?,
                program_id = COALESCE(?, program_id),
                recorded_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, notes, topics_covered, progress_notes, m_num, p_num, cum_num, program_id, existing["id"]),
            db_path=db_path
        )
        att_id = existing["id"]
        is_update = True
    else:
        # Absensi baru
        if status == "hadir":
            cum_num = stats["total_completed"] + 1
            p_num, m_num, _ = calculate_period_and_meeting(cum_num)
        else:
            cum_num = None
            p_num = None
            m_num = None

        att_id = execute_db(
            """
            INSERT INTO attendance (
                schedule_id, student_id, mentor_id, program_id, status, notes,
                topics_covered, progress_notes, meeting_number, period_number, cumulative_meeting
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (schedule_id, student_id, mentor_id, program_id, status, notes,
             topics_covered, progress_notes, m_num, p_num, cum_num),
            db_path=db_path
        )
        is_update = False

    # Tandai jadwal sebagai disetujui / selesai jika hadir
    if status == "hadir":
        execute_db(
            "UPDATE schedules SET status = 'disetujui' WHERE id = ?",
            (schedule_id,),
            db_path=db_path
        )

    # Sinkronisasi ke tabel student_progress jika ada materi/catatan
    if sched and (topics_covered or progress_notes or skills_mastered):
        prog_id = sched["program_id"]
        s_date = sched["schedule_date"]
        existing_sp = query_db(
            "SELECT id FROM student_progress WHERE schedule_id = ?",
            (schedule_id,),
            one=True,
            db_path=db_path
        )
        if existing_sp:
            execute_db(
                """
                UPDATE student_progress
                SET topics_covered = ?, skills_mastered = ?, difficulties = ?,
                    recommendations = ?, additional_notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE schedule_id = ?
                """,
                (topics_covered, skills_mastered, difficulties, recommendations, progress_notes, schedule_id),
                db_path=db_path
            )
        else:
            execute_db(
                """
                INSERT INTO student_progress (
                    schedule_id, student_id, mentor_id, program_id, session_date,
                    topics_covered, skills_mastered, difficulties, recommendations, additional_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (schedule_id, student_id, mentor_id, prog_id, s_date,
                 topics_covered, skills_mastered, difficulties, recommendations, progress_notes),
                db_path=db_path
            )

    meeting_label = f"Pertemuan {m_num} ({p_num})" if (status == "hadir" and m_num) else "-"
    meeting_label_bracket = format_meeting_label(p_num, m_num, style="bracket") if (status == "hadir" and m_num) else "-"

    return {
        "success": True,
        "is_update": is_update,
        "attendance_id": att_id,
        "status": status,
        "meeting_number": m_num,
        "period_number": p_num,
        "cumulative_meeting": cum_num,
        "meeting_label": meeting_label,
        "meeting_label_bracket": meeting_label_bracket
    }

def set_student_program_initial_history(student_id, program_id, last_period, last_meeting, notes="", admin_user_id=None, db_path=None):
    """
    Mengatur riwayat awal pertemuan siswa lama KHUSUS untuk satu program tertentu.
    - last_period: Periode terakhir yang dijalani (misal 3)
    - last_meeting: Pertemuan terakhir pada periode tersebut (1 s.d 8, misal 5)
    - total_offset: ((last_period - 1) * 8) + last_meeting = 21 pertemuan awal
    - Menata ulang (resequence) nomor pertemuan pada absensi hadir sistem untuk program ini.
    - TIDAK membuat absensi fiktif/palsu.
    """
    student = query_db("SELECT id, full_name FROM students WHERE id = ?", (student_id,), one=True, db_path=db_path)
    if not student:
        return {"success": False, "message": "Siswa tidak ditemukan."}

    program = query_db("SELECT id, name FROM programs WHERE id = ?", (program_id,), one=True, db_path=db_path)
    if not program:
        return {"success": False, "message": "Program les tidak ditemukan."}

    try:
        p_val = max(1, int(last_period))
        m_val = max(0, min(8, int(last_meeting)))
    except (TypeError, ValueError):
        p_val = 1
        m_val = 0

    total_offset = calculate_total_from_period_and_meeting(p_val, m_val)

    # Cek apakah pendaftaran student_programs ada
    sp = query_db(
        "SELECT id FROM student_programs WHERE student_id = ? AND program_id = ?",
        (student_id, program_id),
        one=True,
        db_path=db_path
    )

    if sp:
        execute_db(
            """
            UPDATE student_programs
            SET initial_periods_completed = ?,
                initial_last_meeting = ?,
                initial_offset_total = ?,
                initial_offset_notes = ?,
                initial_offset_set_at = CURRENT_TIMESTAMP,
                initial_offset_set_by = ?
            WHERE id = ?
            """,
            (p_val, m_val, total_offset, notes.strip(), admin_user_id, sp["id"]),
            db_path=db_path
        )
    else:
        execute_db(
            """
            INSERT INTO student_programs (
                student_id, program_id, status, initial_periods_completed,
                initial_last_meeting, initial_offset_total, initial_offset_notes,
                initial_offset_set_at, initial_offset_set_by
            ) VALUES (?, ?, 'aktif', ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
            """,
            (student_id, program_id, p_val, m_val, total_offset, notes.strip(), admin_user_id),
            db_path=db_path
        )

    # Resequence absensi program ini
    resequence_student_program_attendances(student_id, program_id, db_path=db_path)

    # Hitung preview hasil
    new_stats = get_student_program_meeting_stats(student_id, program_id, db_path=db_path)

    # Catat ke audit log
    if admin_user_id:
        user_row = query_db("SELECT username FROM users WHERE id = ?", (admin_user_id,), one=True, db_path=db_path)
        u_name = user_row["username"] if user_row else "admin"
        log_audit(
            admin_user_id,
            u_name,
            "ATUR_RIWAYAT_AWAL_PROGRAM",
            "student_programs",
            student_id,
            f"Mengatur riwayat awal program {program['name']} siswa {student['full_name']}: "
            f"Periode {p_val}, Pertemuan {m_val} (Offset: {total_offset}). "
            f"Pertemuan berikutnya: {new_stats['next_meeting_bracket']}.",
            module_name="Program Siswa"
        )

    return {
        "success": True,
        "student_name": student["full_name"],
        "program_name": program["name"],
        "period": p_val,
        "meeting": m_val,
        "total_offset": total_offset,
        "stats": new_stats
    }

def set_student_initial_history(student_id, initial_offset, notes="", admin_user_id=None, db_path=None):
    """
    Fungsi legacy: Mengatur riwayat awal pertemuan siswa lama sebelum menggunakan sistem.
    Tetap dipertahankan untuk backward-compatibility dengan kode dan pengujian lama.
    Juga otomatis memperbarui program aktif pertama siswa jika ada.
    """
    try:
        offset = max(0, int(initial_offset))
    except (TypeError, ValueError):
        offset = 0

    student = query_db("SELECT * FROM students WHERE id = ?", (student_id,), one=True, db_path=db_path)
    if not student:
        return {"success": False, "message": "Siswa tidak ditemukan."}

    old_offset = student["initial_meeting_offset"] or 0

    execute_db(
        """
        UPDATE students
        SET initial_meeting_offset = ?,
            initial_offset_notes = ?,
            initial_offset_set_at = CURRENT_TIMESTAMP,
            initial_offset_set_by = ?
        WHERE id = ?
        """,
        (offset, notes.strip(), admin_user_id, student_id),
        db_path=db_path
    )

    # Sinkronisasi ke student_programs aktif pertama jika ada
    sp = query_db(
        "SELECT id, program_id FROM student_programs WHERE student_id = ? AND status = 'aktif' ORDER BY id ASC LIMIT 1",
        (student_id,),
        one=True,
        db_path=db_path
    )
    if sp:
        p_val = ((offset - 1) // MEETINGS_PER_PERIOD) + 1 if offset > 0 else 0
        m_val = ((offset - 1) % MEETINGS_PER_PERIOD) + 1 if offset > 0 else 0
        execute_db(
            """
            UPDATE student_programs
            SET initial_periods_completed = ?,
                initial_last_meeting = ?,
                initial_offset_total = ?,
                initial_offset_notes = ?,
                initial_offset_set_at = CURRENT_TIMESTAMP,
                initial_offset_set_by = ?
            WHERE id = ?
            """,
            (p_val, m_val, offset, notes.strip(), admin_user_id, sp["id"]),
            db_path=db_path
        )
        resequence_student_program_attendances(student_id, sp["program_id"], db_path=db_path)
    else:
        resequence_student_attendances(student_id, db_path=db_path)

    # Hitung preview hasil
    new_stats = get_student_meeting_stats(student_id, db_path=db_path)

    # Catat ke audit log
    if admin_user_id:
        user_row = query_db("SELECT username FROM users WHERE id = ?", (admin_user_id,), one=True, db_path=db_path)
        u_name = user_row["username"] if user_row else "admin"
        log_audit(
            admin_user_id,
            u_name,
            "ATUR_RIWAYAT_AWAL_PERTEMUAN",
            "students",
            student_id,
            f"Mengubah baseline awal pertemuan siswa {student['full_name']} dari {old_offset} menjadi {offset}. Pertemuan berikutnya: {new_stats['next_meeting_str']}.",
            module_name="Siswa"
        )

    return {
        "success": True,
        "student_name": student["full_name"],
        "old_offset": old_offset,
        "new_offset": offset,
        "stats": new_stats
    }

def resequence_student_program_attendances(student_id, program_id, db_path=None):
    """
    Menata ulang penomoran kumulatif, periode, dan nomor pertemuan untuk
    seluruh absensi 'hadir' siswa ini KHUSUS pada program tertentu.
    """
    sp = query_db(
        "SELECT initial_offset_total FROM student_programs WHERE student_id = ? AND program_id = ?",
        (student_id, program_id),
        one=True,
        db_path=db_path
    )
    offset = (sp["initial_offset_total"] or 0) if sp else 0

    records = query_db(
        """
        SELECT a.id
        FROM attendance a
        JOIN schedules s ON a.schedule_id = s.id
        WHERE a.student_id = ? AND s.program_id = ? AND a.status = 'hadir'
        ORDER BY a.recorded_at ASC, a.id ASC
        """,
        (student_id, program_id),
        db_path=db_path
    )

    current_cum = offset
    for r in records:
        current_cum += 1
        p_num, m_num, _ = calculate_period_and_meeting(current_cum)
        execute_db(
            """
            UPDATE attendance
            SET cumulative_meeting = ?, period_number = ?, meeting_number = ?, program_id = ?
            WHERE id = ?
            """,
            (current_cum, p_num, m_num, program_id, r["id"]),
            db_path=db_path
        )

def resequence_student_attendances(student_id, db_path=None):
    """
    Menata ulang penomoran kumulatif, periode, dan nomor pertemuan untuk
    seluruh absensi 'hadir' siswa ini agar selalu runtut dan sinkron dengan initial_offset.
    """
    student = query_db("SELECT initial_meeting_offset FROM students WHERE id = ?", (student_id,), one=True, db_path=db_path)
    if not student:
        return

    offset = student["initial_meeting_offset"] or 0

    records = query_db(
        """
        SELECT id
        FROM attendance
        WHERE student_id = ? AND status = 'hadir'
        ORDER BY recorded_at ASC, id ASC
        """,
        (student_id,),
        db_path=db_path
    )

    current_cum = offset
    for r in records:
        current_cum += 1
        p_num, m_num, _ = calculate_period_and_meeting(current_cum)
        execute_db(
            """
            UPDATE attendance
            SET cumulative_meeting = ?, period_number = ?, meeting_number = ?
            WHERE id = ?
            """,
            (current_cum, p_num, m_num, r["id"]),
            db_path=db_path
        )
