"""
DESI PRIVAT - Owner Routes & Controller
Dashboard Pengawasan Eksekutif untuk Pemilik DESI PRIVAT.
Pemilik hanya memiliki akses baca (READ-ONLY) yang ditegakkan secara ketat di sisi backend.
Pemilik tidak dapat menambah, mengubah, menghapus, mengarsipkan, atau memulihkan data.
"""
from datetime import datetime
from flask import (
    Blueprint, render_template, request, session,
    Response, abort, flash, redirect, url_for
)
from routes.auth import login_required, role_required, validate_csrf
from services.database_service import query_db, execute_db
from services.audit_service import get_audit_logs, log_audit
from services.report_service import (
    get_dashboard_summary, get_students_report, get_mentors_report,
    get_schedules_report, get_attendance_report, get_progress_report,
    get_mentor_replacements_report, generate_csv_string
)
from services.finance_service import (
    get_financial_overview, get_all_payments, get_mentor_honor_summary, get_student_bills,
    get_pending_new_students, validate_new_student_payment, update_mentor_fee_rate,
    sync_and_get_mentor_period_honors, mark_mentor_honor_as_transferred, get_billing_alerts_summary,
    record_bill_payment, record_owner_custom_payment, get_monthly_finance_report, generate_finance_excel_report,
    update_mentor_period_honor_meetings, get_mentor_student_program_fees,
    save_mentor_student_program_fee, delete_mentor_student_program_fee,
    record_operational_cash_transaction, delete_operational_cash_transaction
)

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")

@owner_bp.before_request
@login_required
@role_required("owner")
def check_owner_access():
    # Pemilik memiliki hak akses pengawasan eksekutif (Read-Only) untuk data umum,
    # namun memiliki wewenang eksekutif khusus pada:
    # 1. Validasi pembayaran murid baru sebelum pembelajaran dimulai
    # 2. Pengaturan tarif fee honor tentor per pertemuan (umum & detail per murid/program)
    # 3. Konfirmasi pencairan/transfer fee tentor per 8 pertemuan
    # 4. Pencatatan pembayaran tagihan & cicilan murid
    # 5. Pencatatan dan penghapusan kas operasional mandiri (uang masuk / keluar non-otomatis)
    allowed_executive_endpoints = [
        "owner.validate_student_payment",
        "owner.update_mentor_fee",
        "owner.save_mentor_student_fee",
        "owner.delete_mentor_student_fee",
        "owner.confirm_honor_transfer",
        "owner.update_honor_meetings",
        "owner.record_owner_payment",
        "owner.owner_correct_payment",
        "owner.owner_cancel_payment",
        "owner.create_operational_cash",
        "owner.delete_operational_cash",
    ]
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.endpoint not in allowed_executive_endpoints:
            abort(403, description="Akses ditolak. Akun Pemilik hanya memiliki hak eksekutif pada validasi pembayaran dan pencairan fee honor.")

@owner_bp.route("/dashboard")
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

    # Rekap data validasi eksekutif dan honor
    pending_new_students = get_pending_new_students()
    honor_data = sync_and_get_mentor_period_honors()
    ready_honor_count = honor_data["ready_count"]
    ready_honors = [h for h in honor_data["honors"] if h["status"] == "siap_ditransfer"]
    billing_alerts = get_billing_alerts_summary()

    return render_template(
        "owner/dashboard.html",
        summary=summary,
        recent_schedules=recent_schedules,
        recent_attendance=recent_attendance,
        recent_progress=recent_progress,
        pending_new_students=pending_new_students,
        ready_honor_count=ready_honor_count,
        ready_honors=ready_honors,
        billing_alerts=billing_alerts
    )

@owner_bp.route("/attendance")
def attendance():
    from services.meeting_service import get_student_program_meeting_stats
    search = request.args.get("q", "").strip()

    conditions = []
    args = []
    if search:
        conditions.append("(st.full_name LIKE ? OR st.school LIKE ?)")
        term = f"%{search}%"
        args.extend([term, term])
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    students_raw = query_db(f"""
        SELECT st.*, p.full_name as parent_name, p.phone as parent_phone
        FROM students st
        LEFT JOIN parents p ON st.parent_id = p.id
        {where_clause}
        ORDER BY st.full_name ASC
    """, args)

    students_list = []
    for st in students_raw:
        std = dict(st)
        programs = query_db("""
            SELECT pr.id, pr.name as program_name
            FROM student_programs sp
            JOIN programs pr ON sp.program_id = pr.id
            WHERE sp.student_id = ? AND sp.status = 'aktif'
            ORDER BY pr.name ASC
        """, (std["id"],))

        prog_stats = []
        for pr in programs:
            stats = get_student_program_meeting_stats(std["id"], pr["id"])
            if stats:
                prog_stats.append({
                    "program_id": pr["id"],
                    "program_name": pr["program_name"],
                    "last_period": stats.get("last_period", 1),
                    "last_meeting": stats.get("last_meeting", 0),
                    "total_meetings": stats.get("total_meetings", 0),
                    "next_meeting_str": stats.get("next_meeting_str", "Pertemuan 1")
                })
        std["program_stats"] = prog_stats
        students_list.append(std)

    total_completed_sessions = query_db("SELECT COUNT(*) as c FROM attendance WHERE status = 'hadir'", one=True)["c"]
    total_documented_sessions = query_db("SELECT COUNT(*) as c FROM attendance WHERE documentation_photo IS NOT NULL AND documentation_photo != ''", one=True)["c"]
    total_mentors = query_db("SELECT COUNT(*) as c FROM mentors WHERE status = 'aktif'", one=True)["c"]

    return render_template(
        "owner/attendance.html",
        students=students_list,
        total_completed_sessions=total_completed_sessions,
        total_documented_sessions=total_documented_sessions,
        total_mentors=total_mentors,
        search=search
    )

@owner_bp.route("/attendance/<int:student_id>")
def student_attendance_detail(student_id):
    student = query_db("""
        SELECT st.*, p.full_name as parent_name, p.phone as parent_phone
        FROM students st
        LEFT JOIN parents p ON st.parent_id = p.id
        WHERE st.id = ?
    """, (student_id,), one=True)

    if not student:
        abort(404, description="Data siswa tidak ditemukan.")

    student_programs = query_db("""
        SELECT DISTINCT pr.id, pr.name
        FROM student_programs sp
        JOIN programs pr ON sp.program_id = pr.id
        WHERE sp.student_id = ?
        ORDER BY pr.name ASC
    """, (student_id,))

    program_filter = request.args.get("program_id")
    selected_program_id = None
    if program_filter:
        try:
            selected_program_id = int(program_filter)
        except ValueError:
            pass

    conditions = ["a.student_id = ?"]
    args = [student_id]
    if selected_program_id:
        conditions.append("s.program_id = ?")
        args.append(selected_program_id)

    attendance_list = query_db(f"""
        SELECT a.*, s.schedule_date, s.start_time, s.end_time,
               pr.name as program_name, m.full_name as mentor_name,
               prog.topics_covered as prog_topics, prog.skills_mastered, prog.difficulties, prog.recommendations
        FROM attendance a
        JOIN schedules s ON a.schedule_id = s.id
        JOIN programs pr ON s.program_id = pr.id
        JOIN mentors m ON a.mentor_id = m.id
        LEFT JOIN student_progress prog ON a.schedule_id = prog.schedule_id
        WHERE {' AND '.join(conditions)}
        ORDER BY s.schedule_date DESC, a.recorded_at DESC
    """, args)

    all_attendance_count = query_db("SELECT COUNT(*) as c FROM attendance WHERE student_id = ?", (student_id,), one=True)["c"]

    return render_template(
        "owner/attendance_detail.html",
        student=student,
        student_programs=student_programs,
        attendance_list=attendance_list,
        selected_program_id=selected_program_id,
        all_attendance_count=all_attendance_count
    )

@owner_bp.route("/parents")
def parents():
    search = request.args.get("q", "").strip()
    conditions = []
    args = []
    if search:
        conditions.append("(p.full_name LIKE ? OR p.phone LIKE ? OR st.full_name LIKE ?)")
        term = f"%{search}%"
        args.extend([term, term, term])
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    parents_rows = query_db(f"""
        SELECT p.*, u.username
        FROM parents p
        LEFT JOIN users u ON p.user_id = u.id
        LEFT JOIN students st ON p.id = st.parent_id
        {where_clause}
        GROUP BY p.id
        ORDER BY p.full_name ASC
    """, args)

    parents_list = []
    for p in parents_rows:
        pd = dict(p)
        children = query_db("""
            SELECT id, full_name, school, grade, status
            FROM students
            WHERE parent_id = ?
            ORDER BY full_name ASC
        """, (pd["id"],))
        pd["children_list"] = children
        parents_list.append(pd)

    return render_template("owner/parents.html", parents=parents_list, search=search)

@owner_bp.route("/admins")
def admins():
    admins_list = query_db("""
        SELECT id, username, full_name, email, phone, is_active, created_at
        FROM users
        WHERE role = 'admin'
        ORDER BY full_name ASC
    """)
    return render_template("owner/admins.html", admins=admins_list)

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
    from flask import redirect, url_for
    return redirect(url_for("owner.dashboard"))

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
    elif report_type == "payments":
        data = get_all_payments(start_date, end_date, student_id)
        headers = ["No Kuitansi", "Tanggal", "Siswa", "Program", "Periode", "Metode", "Nominal", "Dicatat Oleh", "Catatan"]
        key_map = [
            ("No Kuitansi", "receipt_number"), ("Tanggal", "payment_date"),
            ("Siswa", "student_name"), ("Program", "program_name"),
            ("Periode", "period_number"), ("Metode", "payment_method"),
            ("Nominal", "amount"), ("Dicatat Oleh", "recorder_name"),
            ("Catatan", "notes")
        ]
    elif report_type == "bills":
        data = get_student_bills(student_id=student_id, status=status)
        headers = ["Kode Tagihan", "Siswa", "Wali", "Program", "Periode", "Total Tagihan", "Terbayar", "Sisa", "Status"]
        key_map = [
            ("Kode Tagihan", "bill_code"), ("Siswa", "student_name"),
            ("Wali", "parent_name"), ("Program", "program_name"),
            ("Periode", "period_number"), ("Total Tagihan", "total_amount"),
            ("Terbayar", "paid_amount"), ("Sisa", "remaining_amount"),
            ("Status", "status")
        ]
    elif report_type == "honor":
        rate_per_session = request.args.get("rate_per_session")
        data = get_mentor_honor_summary(mentor_id=mentor_id, start_date=start_date, end_date=end_date, rate_per_session=rate_per_session)
        headers = ["Mentor", "Keahlian", "Total Sesi", "Sesi Terlaksana", "Siswa Berhalangan", "Mentor Berhalangan", "Periode Selesai", "Estimasi Honor"]
        key_map = [
            ("Mentor", "mentor_name"), ("Keahlian", "expertise"),
            ("Total Sesi", "total_recorded_sessions"), ("Sesi Terlaksana", "completed_sessions"),
            ("Siswa Berhalangan", "student_absent_sessions"), ("Mentor Berhalangan", "mentor_absent_sessions"),
            ("Periode Selesai", "periods_completed"), ("Estimasi Honor", "estimated_honor")
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

@owner_bp.route("/students/<int:student_id>/validate-payment", methods=["POST"])
def validate_student_payment(student_id):
    validate_csrf()
    try:
        student = validate_new_student_payment(student_id, session["user_id"])
        log_audit(session["user_id"], session["username"], "VALIDASI_PEMBAYARAN_SISWA", "students", student_id,
                  f"Owner memvalidasi pembayaran awal siswa {student['full_name']}. Akses belajar dibuka.")
        flash(f"Pembayaran siswa {student['full_name']} berhasil divalidasi! Status siswa kini AKTIF dan pembelajaran dapat dimulai.", "success")
    except Exception as e:
        flash(f"Gagal memvalidasi pembayaran siswa: {e}", "danger")
    return redirect(request.referrer or url_for("owner.dashboard"))

@owner_bp.route("/mentors/<int:mentor_id>/update-fee", methods=["POST"])
def update_mentor_fee(mentor_id):
    validate_csrf()
    fee_val = request.form.get("fee_per_session", 35000)
    fee_4_raw = request.form.get("fee_per_session_4", "").strip()
    fee_4_val = float(fee_4_raw) if fee_4_raw else None
    try:
        updated_fee, updated_fee_4 = update_mentor_fee_rate(mentor_id, fee_val, fee_4_val)
        m = query_db("SELECT full_name FROM mentors WHERE id = ?", (mentor_id,), one=True)
        m_name = m["full_name"] if m else f"ID {mentor_id}"
        fee_4_str = f", Paket 4: Rp {updated_fee_4:,.0f}" if updated_fee_4 else " (Paket 4: sama dg paket 8)"
        log_audit(session["user_id"], session["username"], "UPDATE_FEE_MENTOR", "mentors", mentor_id,
                  f"Owner menetapkan fee mengajar {m_name}: Paket 8 = Rp {updated_fee:,.0f}{fee_4_str}")
        flash(f"Tarif fee mengajar {m_name} berhasil diatur: Paket 8 Sesi = Rp {updated_fee:,.0f}{fee_4_str}.", "success")
    except Exception as e:
        flash(f"Gagal mengatur tarif fee mentor: {e}", "danger")
    return redirect(request.referrer or url_for("owner.mentors"))

@owner_bp.route("/mentors/<int:mentor_id>/student-fees-data")
def mentor_student_fees_data(mentor_id):
    """API JSON yang mengembalikan daftar murid, program, dan fee per sesi untuk mentor tertentu."""
    mentor = query_db("SELECT id, full_name, fee_per_session, fee_per_session_4 FROM mentors WHERE id = ?", (mentor_id,), one=True)
    if not mentor:
        return {"error": "Mentor tidak ditemukan"}, 404

    items = get_mentor_student_program_fees(mentor_id)
    all_students = query_db("SELECT id, full_name, grade FROM students WHERE status = 'aktif' ORDER BY full_name ASC")
    all_programs = query_db("SELECT id, name FROM programs WHERE status = 'aktif' ORDER BY name ASC")

    return {
        "mentor": dict(mentor),
        "items": items,
        "all_students": [dict(s) for s in all_students],
        "all_programs": [dict(p) for p in all_programs]
    }

@owner_bp.route("/mentors/<int:mentor_id>/save-student-fee", methods=["POST"])
def save_mentor_student_fee(mentor_id):
    validate_csrf()
    student_id = int(request.form.get("student_id", 0))
    program_id = int(request.form.get("program_id", 0))
    fee_per_session = request.form.get("fee_per_session", 0)
    notes = request.form.get("notes", "").strip() or None

    try:
        updated_fee = save_mentor_student_program_fee(mentor_id, student_id, program_id, fee_per_session, notes=notes)
        m = query_db("SELECT full_name FROM mentors WHERE id = ?", (mentor_id,), one=True)
        st = query_db("SELECT full_name FROM students WHERE id = ?", (student_id,), one=True)
        pr = query_db("SELECT name FROM programs WHERE id = ?", (program_id,), one=True)
        m_name = m["full_name"] if m else f"Mentor #{mentor_id}"
        st_name = st["full_name"] if st else f"Siswa #{student_id}"
        pr_name = pr["name"] if pr else f"Program #{program_id}"

        log_audit(session["user_id"], session["username"], "SAVE_MENTOR_STUDENT_FEE", "mentor_student_program_fees",
                  f"{mentor_id}-{student_id}-{program_id}",
                  f"Owner menetapkan tarif fee khusus {m_name} untuk siswa {st_name} (Program {pr_name}): Rp {updated_fee:,.0f} / sesi")
        msg = f"Tarif fee {m_name} untuk siswa {st_name} ({pr_name}) berhasil disimpan: Rp {updated_fee:,.0f} / sesi."
        flash(msg, "success")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
            return {"success": True, "fee": updated_fee, "message": msg}
    except Exception as e:
        err_msg = str(e)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
            return {"success": False, "error": err_msg}, 400
        flash(f"Gagal menyimpan tarif fee: {err_msg}", "danger")

    return redirect(request.referrer or url_for("owner.mentors"))

@owner_bp.route("/mentors/<int:mentor_id>/delete-student-fee", methods=["POST"])
def delete_mentor_student_fee(mentor_id):
    validate_csrf()
    student_id = int(request.form.get("student_id", 0))
    program_id = int(request.form.get("program_id", 0))

    try:
        delete_mentor_student_program_fee(mentor_id, student_id, program_id)
        m = query_db("SELECT full_name FROM mentors WHERE id = ?", (mentor_id,), one=True)
        st = query_db("SELECT full_name FROM students WHERE id = ?", (student_id,), one=True)
        pr = query_db("SELECT name FROM programs WHERE id = ?", (program_id,), one=True)
        m_name = m["full_name"] if m else f"Mentor #{mentor_id}"
        st_name = st["full_name"] if st else f"Siswa #{student_id}"
        pr_name = pr["name"] if pr else f"Program #{program_id}"

        log_audit(session["user_id"], session["username"], "DELETE_MENTOR_STUDENT_FEE", "mentor_student_program_fees",
                  f"{mentor_id}-{student_id}-{program_id}",
                  f"Owner menghapus tarif khusus mentor {m_name} untuk siswa {st_name} (Program {pr_name}) -> kembali ke default")
        msg = f"Tarif khusus {m_name} untuk siswa {st_name} ({pr_name}) dihapus. Menggunakan tarif fee default mentor."
        flash(msg, "success")

        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
            return {"success": True, "message": msg}
    except Exception as e:
        err_msg = str(e)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.accept_mimetypes.best == "application/json":
            return {"success": False, "error": err_msg}, 400
        flash(f"Gagal menghapus tarif fee khusus: {err_msg}", "danger")

    return redirect(request.referrer or url_for("owner.mentors"))

@owner_bp.route("/honor")
def honor():
    honor_data = sync_and_get_mentor_period_honors()
    return render_template(
        "owner/honor.html",
        honors=honor_data["honors"],
        ready_count=honor_data["ready_count"],
        transferred_count=honor_data["transferred_count"]
    )

@owner_bp.route("/honor/<int:honor_id>/confirm-transfer", methods=["POST"])
def confirm_honor_transfer(honor_id):
    validate_csrf()
    notes = request.form.get("transfer_notes", "").strip() or None
    try:
        honor = mark_mentor_honor_as_transferred(honor_id, session["user_id"], notes=notes)
        m = query_db("SELECT full_name FROM mentors WHERE id = ?", (honor["mentor_id"],), one=True)
        st = query_db("SELECT full_name FROM students WHERE id = ?", (honor["student_id"],), one=True)
        m_name = m["full_name"] if m else "Mentor"
        st_name = st["full_name"] if st else "Siswa"
        log_audit(session["user_id"], session["username"], "TRANSFER_FEE_MENTOR", "mentor_period_honor", honor_id,
                  f"Owner mengonfirmasi transfer fee 8 pertemuan untuk {m_name} (Siswa: {st_name}, Periode {honor['period_number']}, Rp {float(honor['total_fee']):,.0f})")
        flash(f"Fee honor 8 pertemuan untuk {m_name} berhasil ditandai SUDAH DITRANSFER. Peringatan penagihan ke wali murid otomatis diaktifkan untuk periode berikutnya!", "success")
    except Exception as e:
        flash(f"Gagal mengonfirmasi transfer fee: {e}", "danger")
    return redirect(request.referrer or url_for("owner.honor"))

@owner_bp.route("/honor/<int:honor_id>/update-meetings", methods=["POST"])
def update_honor_meetings(honor_id):
    validate_csrf()
    try:
        meetings_count = int(request.form.get("completed_meetings", 8))
        res = update_mentor_period_honor_meetings(honor_id, meetings_count)
        log_audit(session["user_id"], session["username"], "UPDATE_HONOR_MEETINGS", "mentor_period_honor", honor_id,
                  f"Owner menyesuaikan jumlah pertemuan honor ID {honor_id} menjadi {meetings_count} sesi (Total: Rp {res['total_fee']:,.0f})")
        flash(f"Jumlah sesi pertemuan honor berhasil disesuaikan menjadi {meetings_count} sesi (Total: Rp {res['total_fee']:,.0f}).", "success")
    except Exception as e:
        flash(f"Gagal memperbarui jumlah sesi honor: {e}", "danger")
    return redirect(request.referrer or url_for("owner.honor"))

@owner_bp.route("/bills")
def bills():
    status_filter = request.args.get("status")
    student_filter = request.args.get("student_id")
    program_filter = request.args.get("program_id")
    search = request.args.get("q", "").strip()

    bills_list = get_student_bills(
        student_id=student_filter,
        program_id=program_filter,
        status=status_filter,
        search=search
    )
    pending_new_students = get_pending_new_students()
    billing_alerts = get_billing_alerts_summary()
    students_list = query_db("SELECT id, full_name FROM students ORDER BY full_name ASC")
    programs_list = query_db("SELECT id, name FROM programs WHERE status = 'aktif' ORDER BY name ASC")

    return render_template(
        "owner/bills.html",
        bills=bills_list,
        pending_new_students=pending_new_students,
        billing_alerts=billing_alerts,
        students=students_list,
        programs=programs_list,
        status_filter=status_filter,
        student_filter=student_filter,
        program_filter=program_filter,
        search=search
    )

@owner_bp.route("/bills/record-payment", methods=["POST"])
def record_owner_payment():
    validate_csrf()
    try:
        bill_id = int(request.form.get("bill_id", 0))
        amount = float(request.form.get("amount", 0))
        payment_option = request.form.get("payment_option", "lunas")
        target_total_raw = request.form.get("target_total_amount")
        target_total = float(target_total_raw) if target_total_raw and target_total_raw.strip() else None
        payment_method = request.form.get("payment_method", "Transfer Bank")
        notes = request.form.get("notes", "").strip()

        user_id = session.get("user_id")
        user_name = session.get("username", "owner")
        payment_id, receipt_num, remaining = record_owner_custom_payment(
            bill_id=bill_id,
            amount=amount,
            payment_option=payment_option,
            target_total_amount=target_total,
            payment_method=payment_method,
            notes=notes,
            recorded_by=user_id
        )

        status_text = "LUNAS (Tidak ada sisa tunggakan)" if remaining == 0 else f"Cicilan Diterima (Sisa Tunggakan: Rp {remaining:,.0f})"
        flash(f"Pembayaran Rp {amount:,.0f} ({receipt_num}) berhasil dicatat oleh Pemilik. Status: {status_text}.", "success")
        log_audit(user_id, user_name, "RECORD_PAYMENT", "student_bills", bill_id, f"Owner mencatat pembayaran Rp {amount:,.0f} ({payment_option}) - No. Kwitansi: {receipt_num}")
    except Exception as e:
        flash(f"Gagal mencatat pembayaran: {e}", "danger")
    return redirect(request.referrer or url_for("owner.bills"))

@owner_bp.route("/payments")
def payments():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    student_id = request.args.get("student_id")
    bill_id = request.args.get("bill_id")

    from services.finance_service import get_all_payments
    payments_list = get_all_payments(start_date=start_date, end_date=end_date, student_id=student_id, bill_id=bill_id)
    students_list = query_db("SELECT id, full_name FROM students ORDER BY full_name ASC")

    selected_bill = None
    if bill_id:
        selected_bill = query_db("SELECT * FROM student_bills WHERE id = ?", (bill_id,), one=True)

    return render_template(
        "admin/payments.html",
        payments=payments_list,
        students=students_list,
        start_date=start_date,
        end_date=end_date,
        student_id=student_id,
        bill_id=bill_id,
        selected_bill=selected_bill,
        is_owner_view=True
    )

@owner_bp.route("/payments/<int:payment_id>/correct", methods=["POST"])
def owner_correct_payment(payment_id):
    validate_csrf()
    new_amount = request.form.get("new_amount")
    reason = request.form.get("reason", "").strip()

    if not new_amount or not reason:
        flash("Nominal baru dan alasan koreksi wajib diisi.", "danger")
        return redirect(request.referrer or url_for("owner.payments"))

    from services.finance_service import correct_bill_payment
    res = correct_bill_payment(payment_id, new_amount, reason=reason, user_id=session["user_id"])
    if res["success"]:
        flash(res["message"], "success")
    else:
        flash(res["message"], "danger")
    return redirect(request.referrer or url_for("owner.payments"))

@owner_bp.route("/payments/<int:payment_id>/cancel", methods=["POST"])
def owner_cancel_payment(payment_id):
    validate_csrf()
    reason = request.form.get("reason", "").strip()

    if not reason:
        flash("Alasan pembatalan pembayaran wajib diisi.", "danger")
        return redirect(request.referrer or url_for("owner.payments"))

    from services.finance_service import cancel_bill_payment
    res = cancel_bill_payment(payment_id, reason=reason, user_id=session["user_id"])
    if res["success"]:
        flash(res["message"], "success")
    else:
        flash(res["message"], "danger")
    return redirect(request.referrer or url_for("owner.payments"))

@owner_bp.route("/finance-report")
def finance_report():
    month = request.args.get("month", "").strip()
    if not month:
        month = datetime.now().strftime("%Y-%m")

    report_data = get_monthly_finance_report(month_str=month)
    return render_template(
        "owner/finance_report.html",
        report=report_data,
        selected_month=report_data["selected_month"],
        available_months=report_data["available_months"]
    )

@owner_bp.route("/finance-report/export-excel")
def export_finance_excel():
    month = request.args.get("month", "").strip()
    if not month:
        month = datetime.now().strftime("%Y-%m")

    excel_file = generate_finance_excel_report(month_str=month)
    filename = f"Laporan_Keuangan_Desi_Privat_{month}.xlsx" if month != "all" else "Laporan_Keuangan_Desi_Privat_Semua.xlsx"
    return Response(
        excel_file.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@owner_bp.route("/operational-cash/create", methods=["POST"])
def create_operational_cash():
    """Mencatat uang masuk atau uang keluar operasional secara mandiri oleh Owner."""
    validate_csrf()
    tx_type = request.form.get("transaction_type", "keluar").strip().lower()
    category = request.form.get("category", "").strip() or ("Biaya Operasional" if tx_type == "keluar" else "Pemasukan Lainnya")
    amount = request.form.get("amount", 0)
    tx_date = request.form.get("transaction_date", date.today().strftime("%Y-%m-%d")).strip()
    description = request.form.get("description", "").strip()
    payment_method = request.form.get("payment_method", "Tunai").strip()
    receipt_ref = request.form.get("receipt_ref", "").strip() or None

    if not description:
        flash("Keterangan transaksi kas wajib diisi.", "danger")
        return redirect(request.referrer or url_for("owner.finance_report"))

    try:
        amt = float(amount)
        if amt <= 0:
            flash("Nominal transaksi harus lebih besar dari 0.", "danger")
            return redirect(request.referrer or url_for("owner.finance_report"))

        tx_id = record_operational_cash_transaction(
            transaction_type=tx_type,
            category=category,
            amount=amt,
            transaction_date=tx_date,
            description=description,
            payment_method=payment_method,
            receipt_ref=receipt_ref,
            recorded_by=session.get("user_id")
        )
        log_audit(
            session.get("user_id"),
            session.get("username", "owner"),
            "CATAT_KAS_OPERASIONAL",
            "operational_cash_transactions",
            str(tx_id),
            f"Mencatat kas {tx_type}: {category} Rp {amt:,.0f} - {description}",
            module_name="Keuangan Owner"
        )
        flash(f"Transaksi kas {tx_type} ({category}) sebesar Rp {amt:,.0f} berhasil dicatat.", "success")
    except Exception as e:
        flash(f"Gagal mencatat transaksi kas operasional: {e}", "danger")

    return redirect(request.referrer or url_for("owner.finance_report"))

@owner_bp.route("/operational-cash/<int:tx_id>/delete", methods=["POST"])
def delete_operational_cash(tx_id):
    """Menghapus transaksi kas operasional yang pernah dicatat oleh Owner."""
    validate_csrf()
    res = delete_operational_cash_transaction(tx_id, user_id=session.get("user_id"))
    if res["success"]:
        log_audit(
            session.get("user_id"),
            session.get("username", "owner"),
            "HAPUS_KAS_OPERASIONAL",
            "operational_cash_transactions",
            str(tx_id),
            f"Menghapus transaksi kas operasional #{tx_id}",
            module_name="Keuangan Owner"
        )
        flash(res["message"], "success")
    else:
        flash(res["message"], "danger")
    return redirect(request.referrer or url_for("owner.finance_report"))


