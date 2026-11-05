"""
DESI PRIVAT - Owner Routes & Controller
Dashboard Pengawasan Eksekutif untuk Pemilik DESI PRIVAT.
Pemilik hanya memiliki akses baca (READ-ONLY) yang ditegakkan secara ketat di sisi backend.
Pemilik tidak dapat menambah, mengubah, menghapus, mengarsipkan, atau memulihkan data.
"""
from datetime import datetime
from flask import (
    Blueprint, render_template, request, session,
    Response, abort
)
from routes.auth import login_required, role_required
from services.database_service import query_db
from services.audit_service import get_audit_logs
from services.report_service import (
    get_dashboard_summary, get_students_report, get_mentors_report,
    get_schedules_report, get_attendance_report, get_progress_report,
    get_mentor_replacements_report, generate_csv_string
)

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")

@owner_bp.before_request
@login_required
@role_required("owner")
def check_owner_access():
    # Perlindungan backend: pemilik sama sekali tidak diizinkan mengirim request modifikasi (POST/PUT/DELETE)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        abort(403, description="Akses ditolak. Akun Pemilik hanya memiliki hak akses baca (Read-Only) dan tidak dapat memodifikasi data operasional.")

@owner_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    summary = get_dashboard_summary()

    # Rekap jadwal terbaru
    recent_schedules = query_db("""
        SELECT s.id, s.title, s.schedule_date, s.start_time, s.end_time, s.status,
               s.mentor_response_status, st.full_name as student_name,
               m.full_name as mentor_name, pr.name as program_name
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN mentors m ON s.mentor_id = m.id
        JOIN programs pr ON s.program_id = pr.id
        ORDER BY s.schedule_date DESC, s.start_time DESC
        LIMIT 10
    """)

    # Rekap kehadiran terbaru
    recent_attendance = query_db("""
        SELECT a.*, s.schedule_date, st.full_name as student_name,
               m.full_name as mentor_name, pr.name as program_name
        FROM attendance a
        JOIN schedules s ON a.schedule_id = s.id
        JOIN students st ON a.student_id = st.id
        JOIN mentors m ON a.mentor_id = m.id
        JOIN programs pr ON s.program_id = pr.id
        ORDER BY a.recorded_at DESC
        LIMIT 8
    """)

    # Rekap pergantian mentor terbaru
    recent_replacements = query_db("""
        SELECT r.*, s.schedule_date, st.full_name as student_name,
               m_old.full_name as old_mentor, m_new.full_name as new_mentor
        FROM mentor_replacements r
        JOIN schedules s ON r.schedule_id = s.id
        JOIN students st ON s.student_id = st.id
        JOIN mentors m_old ON r.original_mentor_id = m_old.id
        JOIN mentors m_new ON r.replacement_mentor_id = m_new.id
        ORDER BY r.created_at DESC
        LIMIT 5
    """)

    # Rekap perkembangan belajar siswa terbaru
    recent_progress = query_db("""
        SELECT sp.*, st.full_name as student_name, m.full_name as mentor_name, pr.name as program_name
        FROM student_progress sp
        JOIN students st ON sp.student_id = st.id
        JOIN mentors m ON sp.mentor_id = m.id
        JOIN programs pr ON sp.program_id = pr.id
        ORDER BY sp.session_date DESC, sp.created_at DESC
        LIMIT 6
    """)

    return render_template(
        "owner/dashboard.html",
        summary=summary,
        recent_schedules=recent_schedules,
        recent_attendance=recent_attendance,
        recent_replacements=recent_replacements,
        recent_progress=recent_progress
    )

@owner_bp.route("/students")
def students():
    status_filter = request.args.get("status")
    program_filter = request.args.get("program_id")
    search = request.args.get("q", "").strip()

    students_list = get_students_report(status_filter, program_filter, search)
    programs_list = query_db("SELECT id, name FROM programs ORDER BY name ASC")

    return render_template(
        "owner/students.html",
        students=students_list,
        programs=programs_list,
        status_filter=status_filter,
        program_filter=program_filter,
        search=search
    )

@owner_bp.route("/mentors")
def mentors():
    status_filter = request.args.get("status")
    search = request.args.get("q", "").strip()
    mentors_list = get_mentors_report(status_filter, search)
    return render_template("owner/mentors.html", mentors=mentors_list, status_filter=status_filter, search=search)

@owner_bp.route("/schedules")
def schedules():
    date_filter = request.args.get("date")
    student_filter = request.args.get("student_id")
    mentor_filter = request.args.get("mentor_id")
    status_filter = request.args.get("status")

    schedules_list = get_schedules_report(
        start_date=date_filter,
        end_date=date_filter,
        student_id=student_filter,
        mentor_id=mentor_filter,
        status=status_filter
    )
    students_list = query_db("SELECT id, full_name FROM students ORDER BY full_name ASC")
    mentors_list = query_db("SELECT id, full_name FROM mentors ORDER BY full_name ASC")

    return render_template(
        "owner/schedules.html",
        schedules=schedules_list,
        students=students_list,
        mentors=mentors_list,
        date_filter=date_filter,
        student_filter=student_filter,
        mentor_filter=mentor_filter,
        status_filter=status_filter
    )

@owner_bp.route("/progress")
def progress():
    student_filter = request.args.get("student_id")
    mentor_filter = request.args.get("mentor_id")
    progress_list = get_progress_report(student_id=student_filter, mentor_id=mentor_filter)
    students_list = query_db("SELECT id, full_name FROM students ORDER BY full_name ASC")
    mentors_list = query_db("SELECT id, full_name FROM mentors ORDER BY full_name ASC")

    return render_template(
        "owner/progress.html",
        progress_list=progress_list,
        students=students_list,
        mentors=mentors_list,
        student_filter=student_filter,
        mentor_filter=mentor_filter
    )

@owner_bp.route("/replacements")
def replacements():
    replacements_list = get_mentor_replacements_report()
    return render_template("owner/replacements.html", replacements=replacements_list)

@owner_bp.route("/audit-logs")
def audit_logs():
    logs = get_audit_logs(limit=200)
    return render_template("owner/audit_logs.html", logs=logs)

@owner_bp.route("/reports")
def reports():
    report_type = request.args.get("type", "schedules")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    student_id = request.args.get("student_id")
    mentor_id = request.args.get("mentor_id")
    status = request.args.get("status")

    data = []
    if report_type == "schedules":
        data = get_schedules_report(start_date, end_date, student_id, mentor_id, status=status)
    elif report_type == "students":
        data = get_students_report(status)
    elif report_type == "mentors":
        data = get_mentors_report(status)
    elif report_type == "attendance":
        data = get_attendance_report(start_date, end_date, student_id, mentor_id)
    elif report_type == "progress":
        data = get_progress_report(student_id, mentor_id)
    elif report_type == "replacements":
        data = get_mentor_replacements_report()

    students_list = query_db("SELECT id, full_name FROM students ORDER BY full_name ASC")
    mentors_list = query_db("SELECT id, full_name FROM mentors ORDER BY full_name ASC")

    return render_template(
        "owner/reports.html",
        report_type=report_type,
        report_data=data,
        students=students_list,
        mentors=mentors_list,
        start_date=start_date,
        end_date=end_date,
        student_id=student_id,
        mentor_id=mentor_id,
        status=status
    )

@owner_bp.route("/reports/export")
def export_report_csv():
    report_type = request.args.get("type", "schedules")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    student_id = request.args.get("student_id")
    mentor_id = request.args.get("mentor_id")
    status = request.args.get("status")

    if report_type == "schedules":
        data = get_schedules_report(start_date, end_date, student_id, mentor_id, status=status)
        headers = ["ID", "Judul", "Tanggal", "Mulai", "Selesai", "Status", "Siswa", "Mentor", "Program"]
        key_map = [
            ("ID", "id"), ("Judul", "title"), ("Tanggal", "schedule_date"),
            ("Mulai", "start_time"), ("Selesai", "end_time"), ("Status", "status"),
            ("Siswa", "student_name"), ("Mentor", "mentor_name"), ("Program", "program_name")
        ]
    elif report_type == "attendance":
        data = get_attendance_report(start_date, end_date, student_id, mentor_id)
        headers = ["ID", "Tanggal", "Waktu", "Siswa", "Mentor", "Status Kehadiran", "Catatan"]
        key_map = [
            ("ID", "id"), ("Tanggal", "schedule_date"), ("Waktu", "start_time"),
            ("Siswa", "student_name"), ("Mentor", "mentor_name"),
            ("Status Kehadiran", "attendance_status"), ("Catatan", "notes")
        ]
    elif report_type == "progress":
        data = get_progress_report(student_id, mentor_id)
        headers = ["ID", "Tanggal", "Siswa", "Mentor", "Materi", "Kemampuan Dikuasai", "Kesulitan", "Rekomendasi"]
        key_map = [
            ("ID", "id"), ("Tanggal", "session_date"), ("Siswa", "student_name"),
            ("Mentor", "mentor_name"), ("Materi", "topics_covered"),
            ("Dikuasai", "skills_mastered"), ("Kesulitan", "difficulties"), ("Rekomendasi", "recommendations")
        ]
    else:
        data = get_students_report(status)
        headers = ["ID", "Nama Lengkap", "Sekolah", "Tingkat", "Nama Wali", "Status"]
        key_map = [
            ("ID", "id"), ("Nama Lengkap", "full_name"), ("Sekolah", "school"),
            ("Tingkat", "grade"), ("Wali", "parent_name"), ("Status", "status")
        ]

    csv_content = generate_csv_string(headers, data, key_map)
    filename = f"laporan_pemilik_desi_privat_{report_type}_{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
