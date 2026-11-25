"""
DESI PRIVAT - Parent Routes & Controller
Dashboard Orang Tua / Wali:
- Akses terbatas HANYA untuk anak yang terhubung dengan akun wali
- Pemilih anak (Child Selector) jika wali memiliki lebih dari 1 anak
- Profil anak, program les, mentor pendamping
- Jadwal les, status konfirmasi, dan informasi pergantian mentor
- Riwayat absensi kehadiran
- Laporan perkembangan siswa lengkap (Materi, Kemampuan Dikuasai, Kesulitan, Rekomendasi)
- Notifikasi terbaru
"""
from flask import (
    Blueprint, render_template, request, session, abort
)
from routes.auth import login_required, role_required
from services.database_service import query_db
from services.notification_service import get_user_notifications

parent_bp = Blueprint("parent", __name__, url_prefix="/parent")

@parent_bp.before_request
def check_parent_access():
    if "user_id" not in session or session.get("role") != "parent":
        abort(403, description="Akses khusus untuk akun Orang Tua/Wali murid terdaftar.")

def get_parent_and_children():
    """
    Mengambil data wali dan daftar anak yang terhubung dengan akun login saat ini.
    Mencegah akses ke data siswa milik orang tua lain di sisi backend.
    """
    user_id = session.get("user_id")
    parent = query_db("SELECT * FROM parents WHERE user_id = ?", (user_id,), one=True)
    if not parent:
        abort(403, description="Profil orang tua/wali tidak ditemukan untuk akun ini.")

    children = query_db("""
        SELECT * FROM students
        WHERE parent_id = ?
        ORDER BY status ASC, full_name ASC
    """, (parent["id"],))

    if not children:
        return parent, [], None

    # Tentukan anak yang sedang dipilih (dari parameter ?student_id= atau default ke anak pertama)
    selected_id = request.args.get("student_id")
    selected_child = None
    if selected_id:
        try:
            sel_id_int = int(selected_id)
            for c in children:
                if c["id"] == sel_id_int:
                    selected_child = c
                    break
        except ValueError:
            pass

    if not selected_child:
        selected_child = children[0]

    return parent, children, selected_child

@parent_bp.route("/dashboard")
def dashboard():
    parent, children, selected_child = get_parent_and_children()

    if not selected_child:
        return render_template("parent/no_children.html", parent=parent)

    child_id = selected_child["id"]

    # Program yang diikuti anak yang dipilih
    raw_programs = query_db("""
        SELECT sp.*, pr.name as program_name, pr.description as program_desc,
               m.full_name as mentor_name
        FROM student_programs sp
        JOIN programs pr ON sp.program_id = pr.id
        LEFT JOIN mentors m ON sp.mentor_id = m.id
        WHERE sp.student_id = ? AND sp.status = 'aktif'
    """, (child_id,))

    programs = []
    for pr in raw_programs:
        prd = dict(pr)
        bill = query_db("""
            SELECT id, bill_code, total_amount, paid_amount, remaining_amount, status
            FROM student_bills
            WHERE student_id = ? AND program_id = ?
            ORDER BY period_number DESC, id DESC LIMIT 1
        """, (child_id, prd["program_id"]), one=True)
        prd["bill"] = bill
        programs.append(prd)

    # Seluruh Jadwal Belajar Siswa (Rutin dari routine_schedules)
    DAY_NAMES = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    from datetime import datetime
    today_dow = datetime.now().weekday() # 0 = Senin, ..., 5 = Sabtu, 6 = Minggu

    raw_routine_schedules = query_db("""
        SELECT rs.*, pr.name as program_name, m.full_name as mentor_name
        FROM routine_schedules rs
        JOIN programs pr ON rs.program_id = pr.id
        JOIN mentors m ON rs.mentor_id = m.id
        WHERE rs.student_id = ? AND rs.status = 'aktif'
        ORDER BY rs.day_of_week ASC, rs.start_time ASC
    """, (child_id,))

    student_schedules = []
    for rs in raw_routine_schedules:
        rs_dict = dict(rs)
        dow = rs_dict.get("day_of_week", 0)
        rs_dict["day_name"] = DAY_NAMES[dow] if 0 <= dow < 7 else "Hari Lain"
        rs_dict["is_today"] = (dow == today_dow)
        student_schedules.append(rs_dict)

    # Laporan perkembangan terbaru
    latest_progress = query_db("""
        SELECT sp.*, pr.name as program_name, m.full_name as mentor_name
        FROM student_progress sp
        JOIN programs pr ON sp.program_id = pr.id
        JOIN mentors m ON sp.mentor_id = m.id
        WHERE sp.student_id = ?
        ORDER BY sp.session_date DESC, sp.created_at DESC
        LIMIT 1
    """, (child_id,), one=True)

    # Riwayat kehadiran sesuai yang diabsenkan mentor
    recent_attendance = query_db("""
        SELECT a.*, s.schedule_date, s.start_time, s.end_time,
               pr.name as program_name, m.full_name as mentor_name,
               prog.skills_mastered, prog.difficulties, prog.recommendations
        FROM attendance a
        JOIN schedules s ON a.schedule_id = s.id
        JOIN programs pr ON s.program_id = pr.id
        JOIN mentors m ON a.mentor_id = m.id
        LEFT JOIN student_progress prog ON a.schedule_id = prog.schedule_id
        WHERE a.student_id = ?
        ORDER BY s.schedule_date DESC, a.recorded_at DESC
        LIMIT 5
    """, (child_id,))

    notifications = get_user_notifications(session["user_id"], limit=5)

    # Tagihan aktif, sisa tunggakan, dan notifikasi periode 8 pertemuan selesai
    from services.finance_service import get_student_bills
    child_bills = get_student_bills(student_id=child_id)
    unpaid_bills = [b for b in child_bills if b["status"] in ("belum_lunas", "sebagian", "tunggakan")]
    total_unpaid = sum(float(b["remaining_amount"] or 0) for b in unpaid_bills)

    period_completion_alerts = query_db("""
        SELECT h.*, pr.name as program_name, m.full_name as mentor_name
        FROM mentor_period_honor h
        JOIN programs pr ON h.program_id = pr.id
        JOIN mentors m ON h.mentor_id = m.id
        WHERE h.student_id = ? AND h.status = 'sudah_ditransfer' AND h.billing_alert_active = 1
        ORDER BY h.period_number DESC
    """, (child_id,))

    return render_template(
        "parent/dashboard.html",
        parent=parent,
        children=children,
        selected_child=selected_child,
        programs=programs,
        student_schedules=student_schedules,
        today_dow=today_dow,
        latest_progress=latest_progress,
        recent_attendance=recent_attendance,
        notifications=notifications,
        child_bills=child_bills,
        unpaid_bills=unpaid_bills,
        total_unpaid=total_unpaid,
        period_completion_alerts=period_completion_alerts
    )

@parent_bp.route("/schedules")
def schedules():
    parent, children, selected_child = get_parent_and_children()
    if not selected_child:
        return render_template("parent/no_children.html", parent=parent)

    child_id = selected_child["id"]
    DAY_NAMES = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
    from datetime import datetime
    today_dow = datetime.now().weekday()

    raw_routine_schedules = query_db("""
        SELECT rs.*, pr.name as program_name, m.full_name as mentor_name
        FROM routine_schedules rs
        JOIN programs pr ON rs.program_id = pr.id
        JOIN mentors m ON rs.mentor_id = m.id
        WHERE rs.student_id = ? AND rs.status = 'aktif'
        ORDER BY rs.day_of_week ASC, rs.start_time ASC
    """, (child_id,))

    student_schedules = []
    for rs in raw_routine_schedules:
        rs_dict = dict(rs)
        dow = rs_dict.get("day_of_week", 0)
        rs_dict["day_name"] = DAY_NAMES[dow] if 0 <= dow < 7 else "Hari Lain"
        rs_dict["is_today"] = (dow == today_dow)
        student_schedules.append(rs_dict)

    schedules_list = query_db("""
        SELECT s.*, pr.name as program_name, m.full_name as mentor_name,
               r.id as replacement_id, r.reason as replacement_reason,
               m_old.full_name as old_mentor_name
        FROM schedules s
        JOIN programs pr ON s.program_id = pr.id
        JOIN mentors m ON s.mentor_id = m.id
        LEFT JOIN mentor_replacements r ON s.id = r.schedule_id
        LEFT JOIN mentors m_old ON r.original_mentor_id = m_old.id
        WHERE s.student_id = ?
        ORDER BY s.schedule_date DESC, s.start_time DESC
    """, (child_id,))

    return render_template(
        "parent/schedules.html",
        parent=parent,
        children=children,
        selected_child=selected_child,
        student_schedules=student_schedules,
        today_dow=today_dow,
        schedules=schedules_list
    )

@parent_bp.route("/attendance")
def attendance():
    parent, children, selected_child = get_parent_and_children()
    if not selected_child:
        return render_template("parent/no_children.html", parent=parent)

    child_id = selected_child["id"]
    attendance_list = query_db("""
        SELECT a.*, s.schedule_date, s.start_time, s.end_time,
               pr.name as program_name, m.full_name as mentor_name,
               prog.skills_mastered, prog.difficulties, prog.recommendations
        FROM attendance a
        JOIN schedules s ON a.schedule_id = s.id
        JOIN programs pr ON s.program_id = pr.id
        JOIN mentors m ON a.mentor_id = m.id
        LEFT JOIN student_progress prog ON a.schedule_id = prog.schedule_id
        WHERE a.student_id = ?
        ORDER BY s.schedule_date DESC, a.recorded_at DESC
    """, (child_id,))

    return render_template(
        "parent/attendance.html",
        parent=parent,
        children=children,
        selected_child=selected_child,
        attendance_list=attendance_list
    )

@parent_bp.route("/progress")
def progress():
    parent, children, selected_child = get_parent_and_children()
    if not selected_child:
        return render_template("parent/no_children.html", parent=parent)

    child_id = selected_child["id"]
    # Laporan diurutkan berdasarkan tanggal terbaru terlebih dahulu
    progress_list = query_db("""
        SELECT sp.*, pr.name as program_name, m.full_name as mentor_name
        FROM student_progress sp
        JOIN programs pr ON sp.program_id = pr.id
        JOIN mentors m ON sp.mentor_id = m.id
        WHERE sp.student_id = ?
        ORDER BY sp.session_date DESC, sp.created_at DESC
    """, (child_id,))

    return render_template(
        "parent/progress.html",
        parent=parent,
        children=children,
        selected_child=selected_child,
        progress_list=progress_list
    )

@parent_bp.route("/bills")
def bills():
    parent, children, selected_child = get_parent_and_children()
    if not selected_child:
        return render_template("parent/no_children.html", parent=parent)

    from services.finance_service import get_student_bills, get_all_payments
    bills_list = get_student_bills(student_id=selected_child["id"])
    payments_list = get_all_payments(student_id=selected_child["id"])
    unpaid_bills = [b for b in bills_list if b["status"] in ("belum_lunas", "sebagian", "tunggakan")]
    total_unpaid = sum(float(b["remaining_amount"] or 0) for b in unpaid_bills)

    period_completion_alerts = query_db("""
        SELECT h.*, pr.name as program_name, m.full_name as mentor_name
        FROM mentor_period_honor h
        JOIN programs pr ON h.program_id = pr.id
        JOIN mentors m ON h.mentor_id = m.id
        WHERE h.student_id = ? AND h.status = 'sudah_ditransfer' AND h.billing_alert_active = 1
        ORDER BY h.period_number DESC
    """, (selected_child["id"],))

    return render_template(
        "parent/bills.html",
        parent=parent,
        children=children,
        selected_child=selected_child,
        bills=bills_list,
        payments=payments_list,
        unpaid_bills=unpaid_bills,
        total_unpaid=total_unpaid,
        period_completion_alerts=period_completion_alerts
    )
