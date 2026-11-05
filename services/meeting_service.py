"""
DESI PRIVAT - Meeting & Period Calculation Service
Layanan perhitungan otomatis siklus periode dan nomor pertemuan les:
- 8 pertemuan valid dihitung sebagai 1 periode
- Rumus Periode: ((total pertemuan - 1) // 8) + 1
- Rumus Pertemuan: ((total pertemuan - 1) % 8) + 1
- Format: Pertemuan {nomor_pertemuan} ({nomor_periode})
- Pengelolaan baseline riwayat awal siswa lama
- Pencegahan perhitungan ganda saat edit/reload
"""
from services.database_service import query_db, execute_db
from services.audit_service import log_audit

MEETINGS_PER_PERIOD = 8

def calculate_period_and_meeting(total_valid_meetings):
    """
    Menghitung nomor periode dan nomor pertemuan berdasarkan total pertemuan valid.
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
    Menghitung total pertemuan kumulatif dari kombinasi periode dan nomor pertemuan.
    Contoh:
    Periode 1, Pertemuan 1 -> Total 1
    Periode 4, Pertemuan 3 -> Total (4 - 1) * 8 + 3 = 27
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

def get_student_meeting_stats(student_id, db_path=None):
    """
    Mengambil statistik pertemuan lengkap untuk seorang siswa:
    - Offset awal siswa lama (sebelum sistem)
    - Jumlah absensi hadir tercatat di sistem
    - Total pertemuan diselesaikan (offset + sistem)
    - Periode & pertemuan terakhir
    - Periode & pertemuan berikutnya yang akan dijalani
    """
    student = query_db(
        "SELECT id, full_name, initial_meeting_offset, initial_offset_notes, initial_offset_set_at FROM students WHERE id = ?",
        (student_id,),
        one=True,
        db_path=db_path
    )
    if not student:
        return None

    initial_offset = student["initial_meeting_offset"] or 0

    # Ambil seluruh absensi valid (hadir) siswa ini
    attendances = query_db(
        """
        SELECT id, schedule_id, status, recorded_at, meeting_number, period_number, cumulative_meeting
        FROM attendance
        WHERE student_id = ? AND status = 'hadir'
        ORDER BY recorded_at ASC, id ASC
        """,
        (student_id,),
        db_path=db_path
    )
    valid_count = len(attendances)
    total_completed = initial_offset + valid_count

    if total_completed > 0:
        last_p, last_m, last_str = calculate_period_and_meeting(total_completed)
    else:
        last_p, last_m, last_str = 0, 0, "Belum ada"

    next_p, next_m, next_str = calculate_period_and_meeting(total_completed + 1)

    return {
        "student_id": student["id"],
        "student_name": student["full_name"],
        "initial_offset": initial_offset,
        "valid_attendance_count": valid_count,
        "total_completed": total_completed,
        "total_meetings": total_completed,
        "last_period": last_p,
        "last_meeting": last_m,
        "last_meeting_str": last_str,
        "next_period": next_p,
        "next_meeting": next_m,
        "next_meeting_str": next_str,
        "offset_notes": student["initial_offset_notes"],
        "offset_set_at": student["initial_offset_set_at"]
    }

def record_or_update_attendance(
    schedule_id, student_id, mentor_id, status,
    notes="", topics_covered="", progress_notes="",
    skills_mastered="", difficulties="", recommendations="",
    db_path=None
):
    """
    Mencatat atau memperbarui absensi dengan perhitungan nomor pertemuan & periode otomatis.
    - Status 'hadir': dihitung sebagai pertemuan valid, nomor bertambah.
    - Status 'izin' / 'tidak_hadir': TIDAK dihitung sebagai pertemuan valid.
    - Edit absensi yang sudah 'hadir': nomor pertemuan & periode dipertahankan (tidak bertambah).
    - Mencegah absensi ganda pada schedule_id yang sama.
    - Sinkronisasi permanen dengan riwayat materi & perkembangan belajar.
    """
    stats = get_student_meeting_stats(student_id, db_path=db_path)
    if not stats:
        return {"success": False, "message": "Data siswa tidak ditemukan."}

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
                # Pertahankan nomor lama
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
                recorded_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, notes, topics_covered, progress_notes, m_num, p_num, cum_num, existing["id"]),
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
                schedule_id, student_id, mentor_id, status, notes,
                topics_covered, progress_notes, meeting_number, period_number, cumulative_meeting
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (schedule_id, student_id, mentor_id, status, notes,
             topics_covered, progress_notes, m_num, p_num, cum_num),
            db_path=db_path
        )
        is_update = False

    # Tandai jadwal sebagai selesai jika hadir
    if status == "hadir":
        execute_db(
            "UPDATE schedules SET status = 'disetujui' WHERE id = ?",
            (schedule_id,),
            db_path=db_path
        )

    # Sinkronisasi ke tabel student_progress jika ada materi/catatan
    sched = query_db(
        "SELECT program_id, schedule_date FROM schedules WHERE id = ?",
        (schedule_id,),
        one=True,
        db_path=db_path
    )
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

    return {
        "success": True,
        "is_update": is_update,
        "attendance_id": att_id,
        "status": status,
        "meeting_number": m_num,
        "period_number": p_num,
        "cumulative_meeting": cum_num,
        "meeting_label": meeting_label
    }

def set_student_initial_history(student_id, initial_offset, notes="", admin_user_id=None, db_path=None):
    """
    Mengatur riwayat awal pertemuan siswa lama sebelum menggunakan sistem.
    Melakukan resequencing otomatis pada absensi hadir di sistem yang sudah tercatat
    sehingga penomoran periode dan pertemuan tetap berurutan dan akurat tanpa duplikasi.
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

    # Resequence absensi 'hadir' yang sudah ada
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
            f"Mengubah baseline awal pertemuan siswa {student['full_name']} dari {old_offset} menjadi {offset}. Pertemuan berikutnya: {new_stats['next_meeting_str']}."
        )

    return {
        "success": True,
        "student_name": student["full_name"],
        "old_offset": old_offset,
        "new_offset": offset,
        "stats": new_stats
    }

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
