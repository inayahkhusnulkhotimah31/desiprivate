"""
DESI PRIVAT - Report & Export Service
Layanan agregasi data laporan untuk Admin dan Pemilik serta pembuatan file ekspor CSV.
Semua data rahasia seperti hash password dan token disaring keluar dari laporan.
"""
import csv
import io
import datetime
from services.database_service import query_db

def get_dashboard_summary():
    """Mengambil kartu ringkasan untuk dashboard Admin dan Pemilik."""
    # 1. Siswa Aktif
    st_active = query_db("SELECT COUNT(*) as c FROM students WHERE status = 'aktif'", one=True)["c"]
    # 2. Mentor Aktif
    m_active = query_db("SELECT COUNT(*) as c FROM mentors WHERE status = 'aktif'", one=True)["c"]
    # 3. Program Aktif
    p_active = query_db("SELECT COUNT(*) as c FROM programs WHERE status = 'aktif'", one=True)["c"]
    # 4. Jadwal / Sesi Hari Ini:
    # Menghitung sesi spesifik hari ini di schedules DAN jadwal rutin mingguan aktif yang jatuh pada hari ini
    today_dow = datetime.date.today().weekday()
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    routine_today_cnt = query_db("""
        SELECT COUNT(*) as c
        FROM routine_schedules rs
        JOIN students st ON rs.student_id = st.id AND st.status = 'aktif'
        WHERE rs.day_of_week = ? AND rs.status = 'aktif'
    """, (today_dow,), one=True)["c"]
    
    specific_today_cnt = query_db("""
        SELECT COUNT(*) as c
        FROM schedules s
        WHERE s.schedule_date = ? AND s.status NOT IN ('dibatalkan', 'ditolak')
    """, (today_str,), one=True)["c"]
    
    today_schedules = routine_today_cnt + specific_today_cnt
    # 5. Jadwal Menunggu Konfirmasi / Persetujuan
    pending_approval = query_db("SELECT COUNT(*) as c FROM schedules WHERE status IN ('menunggu_persetujuan_admin', 'menunggu_konfirmasi_siswa')", one=True)["c"]
    # 6. Jadwal Bermasalah / Butuh Mentor Pengganti
    needs_replacement = query_db("SELECT COUNT(*) as c FROM schedules WHERE mentor_response_status = 'perlu_mentor_pengganti'", one=True)["c"]
    # 7. Sesi Selesai (Memiliki absensi tercatat)
    completed_sessions = query_db("SELECT COUNT(*) as c FROM attendance", one=True)["c"]
    # 8. Sesi Valid Bulan Ini
    monthly_sessions = query_db("""
        SELECT COUNT(*) as c FROM attendance
        WHERE status = 'hadir' AND strftime('%Y-%m', recorded_at) = strftime('%Y-%m', 'now')
    """, one=True)["c"]
    # 9. Total Pergantian Mentor
    total_replacements = query_db("SELECT COUNT(*) as c FROM mentor_replacements", one=True)["c"]
    # 10. Total Orang Tua & Admin
    total_parents = query_db("SELECT COUNT(*) as c FROM parents WHERE status = 'aktif'", one=True)["c"]
    total_admins = query_db("SELECT COUNT(*) as c FROM users WHERE role = 'admin' AND is_active = 1", one=True)["c"]

    # 11. Statistik Rasio Kehadiran Realtime
    att_ratio_row = query_db("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'hadir' THEN 1 ELSE 0 END) as hadir,
            SUM(CASE WHEN status != 'hadir' THEN 1 ELSE 0 END) as belum_hadir
        FROM attendance
    """, one=True)
    total_att = (att_ratio_row["total"] or 0) if att_ratio_row else 0
    hadir_att = (att_ratio_row["hadir"] or 0) if att_ratio_row else 0
    belum_att = (att_ratio_row["belum_hadir"] or 0) if att_ratio_row else 0

    if total_att > 0:
        attendance_attended_pct = round((hadir_att / total_att) * 100)
        attendance_absent_pct = 100 - attendance_attended_pct
    else:
        attendance_attended_pct = 0
        attendance_absent_pct = 0

    return {
        "active_students": st_active,
        "active_mentors": m_active,
        "active_programs": p_active,
        "today_schedules": today_schedules,
        "pending_schedules": pending_approval,
        "needs_replacement": needs_replacement,
        "completed_sessions": completed_sessions,
        "monthly_sessions": monthly_sessions,
        "total_replacements": total_replacements,
        "total_parents": total_parents,
        "total_admins": total_admins,
        "attendance_attended_pct": attendance_attended_pct,
        "attendance_absent_pct": attendance_absent_pct,
        "attendance_attended_count": hadir_att,
        "attendance_absent_count": belum_att,
        "total_attendance_records": total_att
    }

def get_students_report(status_filter=None, program_filter=None, search=None):
    """Laporan data siswa dengan filter."""
    conditions = []
    args = []

    if status_filter:
        conditions.append("s.status = ?")
        args.append(status_filter)
    if program_filter:
        conditions.append("sp.program_id = ?")
        args.append(program_filter)
    if search:
        conditions.append("(s.full_name LIKE ? OR s.school LIKE ? OR p.full_name LIKE ?)")
        term = f"%{search}%"
        args.extend([term, term, term])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT s.id, s.full_name, s.school, s.grade, s.birth_date, s.address, s.status, s.created_at,
               p.full_name as parent_name, p.phone as parent_phone,
               GROUP_CONCAT(DISTINCT pr.name) as enrolled_programs
        FROM students s
        JOIN parents p ON s.parent_id = p.id
        LEFT JOIN student_programs sp ON s.id = sp.student_id AND sp.status = 'aktif'
        LEFT JOIN programs pr ON sp.program_id = pr.id
        {where_clause}
        GROUP BY s.id
        ORDER BY s.full_name ASC
    """
    return query_db(query, args)

def get_mentors_report(status_filter=None, search=None):
    """Laporan data mentor beserta beban mengajar aktif."""
    conditions = []
    args = []
    if status_filter:
        conditions.append("m.status = ?")
        args.append(status_filter)
    if search:
        conditions.append("(m.full_name LIKE ? OR m.expertise LIKE ?)")
        term = f"%{search}%"
        args.extend([term, term])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT m.id, m.full_name, m.phone, m.email, m.expertise, m.bio, m.status, m.created_at,
               m.address, m.latitude, m.longitude, m.fee_per_session, m.fee_per_session_4,
               (SELECT COUNT(*) FROM schedules s WHERE s.mentor_id = m.id AND s.status = 'disetujui' AND date(s.schedule_date) >= date('now')) as active_schedules_count,
               (SELECT COUNT(*) FROM schedules s WHERE s.mentor_id = m.id AND s.mentor_response_status = 'menunggu_konfirmasi') as pending_responses_count,
               (SELECT COUNT(*) FROM mentor_student_program_fees mspf WHERE mspf.mentor_id = m.id) as custom_fees_count
        FROM mentors m
        {where_clause}
        ORDER BY m.full_name ASC
    """
    return query_db(query, args)

def _enrich_schedule_meeting_info(rows, db_path=None):
    """
    Memperkaya data jadwal/absensi dengan nomor pertemuan & periode jika sesi terlaksana.
    Menggunakan data tersimpan di DB, atau menghitung dinamis jika belum terisi.
    Sesi siswa berhalangan atau mentor berhalangan tidak menambah hitungan pertemuan (None).
    """
    results = []
    stats_cache = {}

    for r in rows:
        item = dict(r)
        is_conducted = (
            item.get("session_status") == "terlaksana" or
            (item.get("attendance_status") == "hadir" and item.get("mentor_status") != "tidak_hadir")
        )

        if is_conducted:
            if item.get("meeting_number") and item.get("period_number"):
                # Data sudah tersedia lengkap di attendance
                pass
            else:
                # Sesi terlaksana tapi belum tercatat di kolom meeting_number (data historis/awal)
                s_id = item.get("student_id")
                p_id = item.get("program_id")
                if s_id and p_id:
                    cache_key = (s_id, p_id)
                    if cache_key not in stats_cache:
                        try:
                            from services.meeting_service import get_student_program_meeting_stats
                            stats_cache[cache_key] = get_student_program_meeting_stats(s_id, p_id, db_path=db_path)
                        except Exception:
                            stats_cache[cache_key] = None
                    st_stats = stats_cache.get(cache_key)
                    if st_stats and st_stats.get("total_completed", 0) > 0:
                        try:
                            from services.meeting_service import calculate_period_and_meeting
                            p_num, m_num, _ = calculate_period_and_meeting(st_stats["total_completed"])
                            item["period_number"] = p_num
                            item["meeting_number"] = m_num
                            item["cumulative_meeting"] = st_stats["total_completed"]
                        except Exception:
                            pass
        else:
            # Sesi tidak terlaksana (siswa berhalangan, mentor tidak hadir, atau belum terlaksana)
            item["meeting_number"] = None
            item["period_number"] = None
            item["cumulative_meeting"] = None

        results.append(item)
    return results

def get_schedules_report(start_date=None, end_date=None, student_id=None, mentor_id=None, program_id=None, status=None, db_path=None):
    """Laporan rekap jadwal dengan filter multi-dimensi."""
    conditions = []
    args = []
    if start_date:
        conditions.append("s.schedule_date >= ?")
        args.append(start_date)
    if end_date:
        conditions.append("s.schedule_date <= ?")
        args.append(end_date)
    if student_id:
        conditions.append("s.student_id = ?")
        args.append(student_id)
    if mentor_id:
        conditions.append("s.mentor_id = ?")
        args.append(mentor_id)
    if program_id:
        conditions.append("s.program_id = ?")
        args.append(program_id)
    if status:
        conditions.append("s.status = ?")
        args.append(status)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT s.id, s.title, s.schedule_date, s.start_time, s.end_time, s.duration_minutes,
               s.status, s.student_confirmation_status, s.mentor_response_status,
               s.mentor_response_notes, s.session_notes,
               st.id as student_id,
               st.full_name as student_name,
               m.id as mentor_id,
               m.full_name as mentor_name,
               pr.id as program_id,
               pr.name as program_name,
               att.id as attendance_id,
               att.status as attendance_status,
               att.mentor_status,
               att.session_status,
               att.documentation_status,
               att.documentation_photo,
               att.documentation_pending_reason,
               att.meeting_number,
               att.period_number,
               att.cumulative_meeting
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN mentors m ON s.mentor_id = m.id
        JOIN programs pr ON s.program_id = pr.id
        LEFT JOIN attendance att ON s.id = att.schedule_id
        {where_clause}
        ORDER BY s.schedule_date DESC, s.start_time DESC
    """
    rows = query_db(query, args, db_path=db_path)
    return _enrich_schedule_meeting_info(rows, db_path=db_path)

def get_attendance_report(start_date=None, end_date=None, student_id=None, mentor_id=None, db_path=None):
    """Laporan rekap kehadiran siswa."""
    conditions = []
    args = []
    if start_date:
        conditions.append("s.schedule_date >= ?")
        args.append(start_date)
    if end_date:
        conditions.append("s.schedule_date <= ?")
        args.append(end_date)
    if student_id:
        conditions.append("a.student_id = ?")
        args.append(student_id)
    if mentor_id:
        conditions.append("a.mentor_id = ?")
        args.append(mentor_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT a.id, a.status as attendance_status, a.mentor_status, a.session_status,
               a.documentation_status, a.documentation_photo, a.documentation_pending_reason,
               a.meeting_number, a.period_number, a.cumulative_meeting,
               a.recorded_at, a.notes,
               s.schedule_date, s.start_time, s.end_time,
               st.id as student_id,
               st.full_name as student_name,
               m.id as mentor_id,
               m.full_name as mentor_name,
               pr.id as program_id,
               pr.name as program_name
        FROM attendance a
        JOIN schedules s ON a.schedule_id = s.id
        JOIN students st ON a.student_id = st.id
        JOIN mentors m ON a.mentor_id = m.id
        JOIN programs pr ON s.program_id = pr.id
        {where_clause}
        ORDER BY s.schedule_date DESC, a.recorded_at DESC
    """
    rows = query_db(query, args, db_path=db_path)
    return _enrich_schedule_meeting_info(rows, db_path=db_path)

def get_progress_report(student_id=None, mentor_id=None, program_id=None):
    """Laporan riwayat perkembangan belajar siswa."""
    conditions = []
    args = []
    if student_id:
        conditions.append("sp.student_id = ?")
        args.append(student_id)
    if mentor_id:
        conditions.append("sp.mentor_id = ?")
        args.append(mentor_id)
    if program_id:
        conditions.append("sp.program_id = ?")
        args.append(program_id)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT sp.id, sp.session_date, sp.topics_covered, sp.skills_mastered,
               sp.difficulties, sp.recommendations, sp.additional_notes, sp.created_at,
               st.full_name as student_name,
               m.full_name as mentor_name,
               pr.name as program_name
        FROM student_progress sp
        JOIN students st ON sp.student_id = st.id
        JOIN mentors m ON sp.mentor_id = m.id
        JOIN programs pr ON sp.program_id = pr.id
        {where_clause}
        ORDER BY sp.session_date DESC, sp.created_at DESC
    """
    return query_db(query, args)

def get_mentor_replacements_report():
    """Laporan riwayat pergantian mentor."""
    query = """
        SELECT r.id, r.reason, r.created_at,
               s.schedule_date, s.start_time, s.end_time, s.title as schedule_title,
               st.full_name as student_name,
               m_old.full_name as original_mentor,
               m_new.full_name as replacement_mentor,
               u.username as changed_by_username
        FROM mentor_replacements r
        JOIN schedules s ON r.schedule_id = s.id
        JOIN students st ON s.student_id = st.id
        JOIN mentors m_old ON r.original_mentor_id = m_old.id
        JOIN mentors m_new ON r.replacement_mentor_id = m_new.id
        LEFT JOIN users u ON r.changed_by = u.id
        ORDER BY r.created_at DESC
    """
    return query_db(query)

def generate_csv_string(headers, rows_dict_list, key_map):
    """
    Membuat string CSV dari daftar dictionary.
    key_map adalah list tuple: (header_name, dict_key)
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows_dict_list:
        line = []
        for _, key in key_map:
            val = row[key] if key in row.keys() else ""
            line.append(val if val is not None else "")
        writer.writerow(line)
    return output.getvalue()
