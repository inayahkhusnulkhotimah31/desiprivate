"""
DESI PRIVAT - Admin Routes & Controller
Pusat kendali operasional DESI PRIVAT:
- Manajemen Data Siswa (CRUD, Filter, Arsip, Riwayat)
- Manajemen Orang Tua/Wali (1 Wali -> Banyak Siswa)
- Manajemen Mentor (Keahlian, Waktu Luang, Beban Jadwal)
- Manajemen Program Les (CRUD, Arsip)
- Manajemen Akun & Keamanan (Reset Password, Aktivasi, Cegah Duplikat)
- Penjadwalan & Persetujuan (Deteksi Bentrokan, Jadwal Berulang, Konfirmasi Siswa/Wali)
- Pergantian Mentor & Peringatan Keterlambatan Respons
- Pencadangan & Pemulihan Database (Backup & Restore)
- Notifikasi & WhatsApp Testing
- Riwayat Audit Log & Laporan / Ekspor
"""
from datetime import datetime, date
import os
import uuid
import time
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify, Response, current_app
)
from werkzeug.security import generate_password_hash
from routes.auth import login_required, role_required, validate_csrf
from services.database_service import query_db, execute_db
from services.audit_service import log_audit, get_audit_logs
from services.notification_service import (
    create_notification, get_user_notifications, mark_as_read, mark_all_as_read
)
from services.whatsapp_service import (
    send_whatsapp_message, get_delivery_logs, run_test_scenario,
    create_whatsapp_link, format_schedule_notification,
    format_schedule_reschedule, format_operational_announcement
)
from services.meeting_service import (
    calculate_period_and_meeting, calculate_total_from_period_and_meeting,
    get_student_meeting_stats, get_student_program_meeting_stats,
    set_student_initial_history, set_student_program_initial_history,
    resequence_student_attendances, resequence_student_program_attendances,
    format_meeting_label
)
from services.audit_service import compute_field_diff
from services.schedule_service import (
    check_schedule_conflict, create_schedule_proposal, generate_recurring_schedules,
    approve_schedule, mentor_respond_schedule, check_overdue_mentor_responses,
    get_eligible_replacement_mentors, execute_mentor_replacement, calculate_end_time,
    get_routine_schedules, create_routine_schedule, update_routine_schedule,
    delete_routine_schedule, check_routine_schedule_conflict, DAY_NAMES
)
from services.backup_service import create_backup, list_backups, restore_backup
from services.report_service import (
    get_dashboard_summary, get_students_report, get_mentors_report,
    get_schedules_report, get_attendance_report, get_progress_report,
    get_mentor_replacements_report, generate_csv_string
)
from services.finance_service import (
    get_student_bills, create_student_bill, record_bill_payment,
    get_student_bill_detail, get_bill_payment_receipt, get_all_payments,
    get_financial_overview, get_mentor_honor_summary
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Semua rute admin dilindungi oleh login_required dan role_required('admin')
@admin_bp.before_request
@login_required
@role_required("admin")
def check_admin_access():
    pass

# ==========================================
# 1. DASHBOARD ADMIN
# ==========================================
@admin_bp.route("/dashboard")
def dashboard():
    summary = get_dashboard_summary()
    overdue_responses = check_overdue_mentor_responses()
    recent_notifs = get_user_notifications(session["user_id"], limit=5)
    today_date = date.today()
    today_str = today_date.strftime("%Y-%m-%d")
    today_dow = today_date.weekday()

    # Gabungkan sesi tanggal spesifik hari ini dan jadwal rutin mingguan yang jatuh hari ini
    today_schedules_list = query_db("""
        SELECT s.id, s.title, s.start_time, s.end_time, s.status, s.mentor_response_status,
               st.full_name as student_name, m.full_name as mentor_name, pr.name as program_name,
               'sesi_spesifik' as schedule_type
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN mentors m ON s.mentor_id = m.id
        JOIN programs pr ON s.program_id = pr.id
        WHERE s.schedule_date = ? AND s.status NOT IN ('dibatalkan', 'ditolak')

        UNION ALL

        SELECT rs.id, 'Jadwal Rutin Mingguan' as title, rs.start_time, rs.end_time, 'aktif' as status,
               'rutin' as mentor_response_status, st.full_name as student_name, m.full_name as mentor_name,
               pr.name as program_name, 'jadwal_rutin' as schedule_type
        FROM routine_schedules rs
        JOIN students st ON rs.student_id = st.id AND st.status = 'aktif'
        JOIN mentors m ON rs.mentor_id = m.id AND m.status = 'aktif'
        JOIN programs pr ON rs.program_id = pr.id AND pr.status = 'aktif'
        WHERE rs.day_of_week = ? AND rs.status = 'aktif'
        ORDER BY start_time ASC
    """, (today_str, today_dow))

    # Hitung total jadwal yang memerlukan perhatian (tidak dibatasi LIMIT 10)
    action_count_row = query_db("""
        SELECT COUNT(s.id) as total
        FROM schedules s
        LEFT JOIN mentors m ON s.mentor_id = m.id
        WHERE s.status NOT IN ('dibatalkan', 'ditolak', 'selesai')
          AND (s.mentor_id IS NULL
               OR s.status IN ('menunggu_persetujuan_admin', 'menunggu_konfirmasi_siswa')
               OR s.mentor_response_status = 'perlu_mentor_pengganti')
    """, one=True)
    action_count = action_count_row["total"] if action_count_row else 0

    # Jadwal yang butuh tindakan (menunggu persetujuan atau perlu pengganti)
    action_required_schedules = query_db("""
        SELECT s.id, s.title, s.schedule_date, s.start_time, s.status, s.mentor_response_status,
               s.mentor_response_notes, st.full_name as student_name,
               COALESCE(m.full_name, 'Belum Ditentukan') as mentor_name,
               pr.name as program_name
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        LEFT JOIN mentors m ON s.mentor_id = m.id
        JOIN programs pr ON s.program_id = pr.id
        WHERE s.status NOT IN ('dibatalkan', 'ditolak', 'selesai')
          AND (s.mentor_id IS NULL
               OR s.status IN ('menunggu_persetujuan_admin', 'menunggu_konfirmasi_siswa')
               OR s.mentor_response_status = 'perlu_mentor_pengganti')
        ORDER BY s.schedule_date ASC
        LIMIT 10
    """)

    recent_audits = get_audit_logs(limit=5)

    # Riwayat absensi terkini beserta rincian pertemuan, periode, dokumentasi foto, dan laporan perkembangan
    recent_attendances = query_db("""
        SELECT att.id as attendance_id, att.schedule_id, att.status, att.mentor_status, att.session_status,
               att.meeting_number, att.period_number, att.cumulative_meeting,
               att.topics_covered, att.progress_notes,
               prog.skills_mastered, prog.difficulties, prog.recommendations,
               att.documentation_status, att.documentation_photo, att.documentation_pending_reason,
               att.recorded_at,
               s.schedule_date as session_date,
               s.start_time, s.end_time,
               st.id as student_id, st.full_name as student_name, st.grade as student_grade, st.school as student_school,
               m.id as mentor_id, m.full_name as mentor_name,
               pr.id as program_id, pr.name as program_name
        FROM attendance att
        JOIN schedules s ON att.schedule_id = s.id
        JOIN students st ON att.student_id = st.id
        JOIN mentors m ON att.mentor_id = m.id
        JOIN programs pr ON s.program_id = pr.id
        LEFT JOIN student_progress prog ON att.schedule_id = prog.schedule_id
        ORDER BY s.schedule_date DESC, att.recorded_at DESC
        LIMIT 10
    """)

    return render_template(
        "admin/dashboard.html",
        summary=summary,
        overdue_responses=overdue_responses,
        recent_notifs=recent_notifs,
        recent_audits=recent_audits,
        recent_attendances=recent_attendances,
        today_schedules=today_schedules_list,
        action_schedules=action_required_schedules,
        action_count=action_count,
        today_str=today_str,
        today_dow=today_dow
    )

# ==========================================
# 2. DATA SISWA
# ==========================================
@admin_bp.route("/students")
def students():
    status_filter = request.args.get("status")
    program_filter = request.args.get("program_id")
    search = request.args.get("q", "").strip()

    students_list = get_students_report(status_filter, program_filter, search)
    enriched_students = []
    for st in students_list:
        st_d = dict(st)
        st_d["meeting_stats"] = get_student_meeting_stats(st["id"])
        enriched_students.append(st_d)

    parents_list = query_db("SELECT id, full_name, phone FROM parents ORDER BY full_name ASC")
    programs_list = query_db("SELECT id, name FROM programs WHERE status = 'aktif' ORDER BY name ASC")
    mentors_list = query_db("SELECT id, full_name FROM mentors WHERE status = 'aktif' ORDER BY full_name ASC")

    return render_template(
        "admin/students.html",
        students=enriched_students,
        parents=parents_list,
        programs=programs_list,
        mentors=mentors_list,
        status_filter=status_filter,
        program_filter=program_filter,
        search=search
    )

@admin_bp.route("/students/create", methods=["POST"])
def create_student():
    validate_csrf()
    parent_id = request.form.get("parent_id")
    new_parent_name = request.form.get("new_parent_name", "").strip()
    new_parent_phone = request.form.get("new_parent_phone", "").strip()
    full_name = request.form.get("full_name", "").strip()
    school = request.form.get("school", "").strip()
    grade = request.form.get("grade", "").strip()
    birth_date = request.form.get("birth_date", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    program_id = request.form.get("program_id")
    subject_info = request.form.get("subject_info", "").strip()

    # Ekstraksi riwayat periode & pertemuan awal (untuk siswa lama)
    init_p_raw = request.form.get("initial_periods_completed", 1)
    init_m_raw = request.form.get("initial_last_meeting", 0)
    try:
        init_p = max(1, int(init_p_raw or 1))
        init_m = max(0, min(8, int(init_m_raw or 0)))
    except (TypeError, ValueError):
        init_p, init_m = 1, 0

    from services.meeting_service import calculate_total_from_period_and_meeting
    total_offset = calculate_total_from_period_and_meeting(init_p, init_m) if (init_p > 1 or init_m > 0) else 0

    # 1. Buat data orang tua baru jika diisi di formulir
    if new_parent_name and new_parent_phone:
        parent_id = execute_db("""
            INSERT INTO parents (full_name, phone, address, notes)
            VALUES (?, ?, ?, 'Didaftarkan bersamaan dengan siswa baru')
        """, (new_parent_name, new_parent_phone, address))

    if not parent_id or not full_name:
        flash("Nama lengkap siswa dan data orang tua/wali murid wajib diisi.", "danger")
        return redirect(url_for("admin.students"))

    # Backend Guard: Pencegahan Duplikasi Siswa (1 Siswa Multi-Program)
    confirm_duplicate = request.form.get("confirm_duplicate", "0").strip()
    existing_student = None
    if parent_id:
        existing_student = query_db(
            "SELECT id, full_name, school, grade FROM students WHERE LOWER(TRIM(full_name)) = LOWER(TRIM(?)) AND parent_id = ?",
            (full_name, parent_id),
            one=True
        )
    if not existing_student:
        existing_student = query_db(
            "SELECT id, full_name, school, grade FROM students WHERE LOWER(TRIM(full_name)) = LOWER(TRIM(?))",
            (full_name,),
            one=True
        )

    if existing_student and confirm_duplicate != "1":
        target_student_id = existing_student["id"]
        if program_id:
            already_enrolled = query_db(
                "SELECT id FROM student_programs WHERE student_id = ? AND program_id = ?",
                (target_student_id, program_id),
                one=True
            )
            if already_enrolled:
                flash(f"Pemberitahuan Sistem: Siswa '{existing_student['full_name']}' sudah terdaftar (ID #{target_student_id}) dan telah mengambil program ini.", "warning")
                return redirect(url_for("admin.student_detail", student_id=target_student_id))

            execute_db("""
                INSERT INTO student_programs (
                    student_id, program_id, mentor_id, start_date, notes, status,
                    initial_periods_completed, initial_last_meeting, initial_offset_total,
                    initial_offset_notes, initial_offset_set_at, initial_offset_set_by, meetings_per_period
                )
                VALUES (?, ?, NULL, date('now'), ?, 'aktif', ?, ?, ?, 'Baseline pendaftaran program', CURRENT_TIMESTAMP, ?, 8)
            """, (target_student_id, program_id, notes or subject_info, init_p, init_m, total_offset, session["user_id"]))

            # Buat tagihan awal Periode 1 untuk program yang baru ditambahkan
            from services.finance_service import create_student_bill
            from services.pricing_service import calculate_package_tuition_fee
            pr_info = query_db("SELECT name, level, service_type, price_per_session FROM programs WHERE id = ?", (program_id,), one=True)
            pr_name = pr_info["name"] if pr_info else "Les Privat"
            pr_level = pr_info["level"] if pr_info else (existing_student["grade"] or "SD")
            pr_service = pr_info["service_type"] if (pr_info and "service_type" in pr_info.keys() and pr_info["service_type"]) else "Private Tutoring"

            prog_fee, rate_session, _ = calculate_package_tuition_fee(
                service_type=pr_service,
                level=pr_level,
                meetings_per_period=8,
                student_grade=existing_student["grade"],
                program_name=pr_name,
                custom_fee=None
            )

            existing_bill = query_db("SELECT id FROM student_bills WHERE student_id = ? AND program_id = ? AND period_number = 1", (target_student_id, program_id), one=True)
            if not existing_bill:
                create_student_bill(
                    student_id=target_student_id,
                    program_id=program_id,
                    period_number=1,
                    title=f"Tagihan {pr_name} - Periode 1 (8 Pertemuan)",
                    total_amount=prog_fee,
                    notes=f"Tagihan penambahan program les baru {pr_name} (8 sesi). Menunggu pembayaran sebelum pembelajaran dimulai."
                )

            log_audit(session["user_id"], session["username"], "TAMBAH_PROGRAM_SISWA", "student_programs", target_student_id,
                      f"Menambahkan program baru (ID {program_id}) ke profil siswa yang sudah ada ({existing_student['full_name']})")

            flash(f"Pemberitahuan Sistem: Siswa '{existing_student['full_name']}' sudah terdaftar (ID #{target_student_id}). Program les {pr_name} berhasil ditambahkan dan tagihan SPP telah terbit.", "success")
            return redirect(url_for("admin.student_detail", student_id=target_student_id))
        else:
            flash(f"Pemberitahuan Sistem: Siswa '{existing_student['full_name']}' sudah terdaftar (ID #{target_student_id}).", "info")
            return redirect(url_for("admin.student_detail", student_id=target_student_id))

    try:
        meetings_per_period = int(request.form.get("meetings_per_period", 8))
        if meetings_per_period not in (4, 8, 12):
            meetings_per_period = 8
    except (ValueError, TypeError):
        meetings_per_period = 8

    try:
        initial_offset = max(0, int(request.form.get("initial_meeting_offset", 0)))
    except (TypeError, ValueError):
        initial_offset = total_offset

    lat_val = request.form.get("latitude", "").strip()
    lng_val = request.form.get("longitude", "").strip()
    try:
        latitude = float(lat_val) if lat_val else None
    except (ValueError, TypeError):
        latitude = None
    try:
        longitude = float(lng_val) if lng_val else None
    except (ValueError, TypeError):
        longitude = None

    student_id = execute_db("""
        INSERT INTO students (
            parent_id, full_name, school, grade, birth_date, address, latitude, longitude, notes, status, payment_status,
            initial_meeting_offset, initial_offset_notes, initial_offset_set_at, initial_offset_set_by, meetings_per_period
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'nonaktif', 'menunggu_validasi', ?, 'Pendaftaran murid baru (menunggu validasi pembayaran)', CURRENT_TIMESTAMP, ?, ?)
    """, (parent_id, full_name, school, grade, birth_date, address, latitude, longitude, notes, initial_offset, session["user_id"], meetings_per_period))

    if program_id:
        execute_db("""
            INSERT INTO student_programs (
                student_id, program_id, mentor_id, start_date, notes, status,
                initial_periods_completed, initial_last_meeting, initial_offset_total,
                initial_offset_notes, initial_offset_set_at, initial_offset_set_by, meetings_per_period
            )
            VALUES (?, ?, NULL, date('now'), ?, 'aktif', ?, ?, ?, 'Baseline pendaftaran awal', CURRENT_TIMESTAMP, ?, ?)
        """, (student_id, program_id, notes or subject_info, init_p, init_m, total_offset, session["user_id"], meetings_per_period))

        # Buat tagihan awal Periode 1 sesuai biaya yang diinput atau kalkulasi dari kategori layanan & jenjang
        from services.finance_service import create_student_bill
        from services.pricing_service import calculate_package_tuition_fee
        pr_info = query_db("SELECT name, level, service_type, price_per_session FROM programs WHERE id = ?", (program_id,), one=True)
        pr_name = pr_info["name"] if pr_info else "Les Privat"
        pr_level = pr_info["level"] if pr_info else grade
        pr_service = pr_info["service_type"] if (pr_info and "service_type" in pr_info.keys() and pr_info["service_type"]) else "Private Tutoring"

        initial_fee, rate_session, is_custom = calculate_package_tuition_fee(
            service_type=pr_service,
            level=pr_level,
            meetings_per_period=meetings_per_period,
            student_grade=grade,
            program_name=pr_name,
            custom_fee=None
        )

        create_student_bill(
            student_id=student_id,
            program_id=program_id,
            period_number=1,
            title=f"Tagihan {pr_name} - Periode 1 ({meetings_per_period} Pertemuan)",
            total_amount=initial_fee,
            notes=f"Tagihan pendaftaran awal murid baru ({meetings_per_period} sesi). Menunggu validasi pembayaran oleh Pemilik sebelum pembelajaran dimulai."
        )

    log_audit(session["user_id"], session["username"], "TAMBAH_SISWA", "students", student_id, f"Menambahkan siswa baru: {full_name} (Menunggu Validasi Pembayaran Pemilik)")

    flash(f"Siswa {full_name} berhasil didaftarkan dengan status 'Menunggu Validasi Pembayaran oleh Pemilik'. Pembelajaran dan penjadwalan akan dibuka setelah Pemilik memvalidasi pembayaran awal.", "info")
    return redirect(url_for("admin.students"))

@admin_bp.route("/students/<int:student_id>")
def student_detail(student_id):
    student = query_db("""
        SELECT s.*, p.full_name as parent_name, p.phone as parent_phone, p.email as parent_email, p.address as parent_address
        FROM students s
        JOIN parents p ON s.parent_id = p.id
        WHERE s.id = ?
    """, (student_id,), one=True)

    if not student:
        flash("Siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.students"))

    # Program yang diikuti beserta statistik periode independen masing-masing
    raw_programs = query_db("""
        SELECT sp.*, pr.name as program_name, m.full_name as mentor_name
        FROM student_programs sp
        JOIN programs pr ON sp.program_id = pr.id
        LEFT JOIN mentors m ON sp.mentor_id = m.id
        WHERE sp.student_id = ?
        ORDER BY sp.created_at DESC
    """, (student_id,))

    programs = []
    for pr in raw_programs:
        pr_d = dict(pr)
        pr_d["meeting_stats"] = get_student_program_meeting_stats(student_id, pr["program_id"])
        programs.append(pr_d)

    # Riwayat jadwal
    schedules = query_db("""
        SELECT s.*, m.full_name as mentor_name, pr.name as program_name,
               att.status as attendance_status, att.meeting_number, att.period_number,
               att.cumulative_meeting, att.topics_covered as att_topics
        FROM schedules s
        JOIN mentors m ON s.mentor_id = m.id
        JOIN programs pr ON s.program_id = pr.id
        LEFT JOIN attendance att ON s.id = att.schedule_id
        WHERE s.student_id = ?
        ORDER BY s.schedule_date DESC, s.start_time DESC
        LIMIT 30
    """, (student_id,))

    # Riwayat perkembangan belajar
    progress_list = query_db("""
        SELECT sp.*, m.full_name as mentor_name, pr.name as program_name,
               att.documentation_photo, att.documentation_status
        FROM student_progress sp
        JOIN mentors m ON sp.mentor_id = m.id
        JOIN programs pr ON sp.program_id = pr.id
        LEFT JOIN attendance att ON sp.schedule_id = att.schedule_id
        WHERE sp.student_id = ?
        ORDER BY sp.session_date DESC
        LIMIT 30
    """, (student_id,))

    meeting_stats = get_student_meeting_stats(student_id)
    routine_schedules = get_routine_schedules(student_id=student_id)
    parents_list = query_db("SELECT id, full_name FROM parents ORDER BY full_name ASC")
    all_programs = query_db("SELECT id, name, code, level, default_fee_8, default_fee_4 FROM programs WHERE status = 'aktif' ORDER BY name ASC")
    all_mentors = query_db("SELECT id, full_name, expertise FROM mentors WHERE status = 'aktif' ORDER BY full_name ASC")

    return render_template(
        "admin/student_detail.html",
        student=student,
        programs=programs,
        routine_schedules=routine_schedules,
        schedules=schedules,
        progress_list=progress_list,
        parents=parents_list,
        all_programs=all_programs,
        all_mentors=all_mentors,
        meeting_stats=meeting_stats,
        day_names=DAY_NAMES
    )

@admin_bp.route("/students/<int:student_id>/edit", methods=["POST"])
def edit_student(student_id):
    validate_csrf()
    old_st = query_db("SELECT parent_id, full_name, school, grade, birth_date, address, latitude, longitude, notes, status FROM students WHERE id = ?", (student_id,), one=True)
    if not old_st:
        flash("Siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.students"))

    parent_id = request.form.get("parent_id")
    full_name = request.form.get("full_name", "").strip()
    school = request.form.get("school", "").strip()
    grade = request.form.get("grade", "").strip()
    birth_date = request.form.get("birth_date", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    status = request.form.get("status", "aktif")

    lat_val = request.form.get("latitude", "").strip()
    lng_val = request.form.get("longitude", "").strip()
    try:
        latitude = float(lat_val) if lat_val else None
    except (ValueError, TypeError):
        latitude = None
    try:
        longitude = float(lng_val) if lng_val else None
    except (ValueError, TypeError):
        longitude = None

    new_data = {
        "parent_id": int(parent_id) if parent_id else None,
        "full_name": full_name,
        "school": school,
        "grade": grade,
        "birth_date": birth_date,
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
        "notes": notes,
        "status": status
    }
    old_data = dict(old_st)
    changed_fields, old_diff, new_diff = compute_field_diff(old_data, new_data)

    execute_db("""
        UPDATE students
        SET parent_id = ?, full_name = ?, school = ?, grade = ?, birth_date = ?,
            address = ?, latitude = ?, longitude = ?, notes = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (parent_id, full_name, school, grade, birth_date, address, latitude, longitude, notes, status, student_id))

    detail_msg = f"Mengubah data siswa ID {student_id} ({full_name})"
    if changed_fields:
        detail_msg += f". Field diubah: {', '.join(changed_fields)}"

    log_audit(
        session["user_id"], session["username"], "UBAH_SISWA", "students", student_id,
        detail_msg,
        module_name="Siswa",
        old_values=old_diff,
        new_values=new_diff,
        fields_changed=changed_fields,
        ip_address=request.remote_addr
    )
    flash(f"Data siswa {full_name} berhasil diperbarui.", "success")
    return redirect(url_for("admin.student_detail", student_id=student_id))

@admin_bp.route("/students/<int:student_id>/archive", methods=["POST"])
def archive_student(student_id):
    validate_csrf()
    action = request.form.get("action", "berhenti") # 'berhenti' atau 'aktif'
    execute_db("UPDATE students SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (action, student_id))
    log_audit(session["user_id"], session["username"], "ARSIP_SISWA", "students", student_id, f"Mengubah status siswa ID {student_id} menjadi {action}")
    flash(f"Status siswa berhasil diubah menjadi '{action}'. Riwayat data tetap aman tersimpan.", "info")
    return redirect(url_for("admin.students"))

@admin_bp.route("/students/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    validate_csrf()
    student = query_db("SELECT id, full_name, status FROM students WHERE id = ?", (student_id,), one=True)
    if not student:
        flash("Siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.students"))

    action_type = request.form.get("action_type", "auto_delete")

    if action_type in ("archive", "arsip", "nonaktif"):
        # Pilihan 1: Hanya Arsip / Nonaktifkan
        execute_db("UPDATE students SET status = 'berhenti', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (student_id,))
        log_audit(session["user_id"], session["username"], "ARSIP_SISWA", "students", student_id,
                  f"Mengarsipkan data siswa ID {student_id} ({student['full_name']}). Riwayat jadwal tetap tersimpan.")
        flash(f"Siswa {student['full_name']} berhasil diarsipkan. Seluruh data dan riwayat belajar tetap tersimpan aman.", "info")
        return redirect(url_for("admin.students"))

    # Pilihan 2: Hapus Otomatis (Membersihkan seluruh relasi terkait secara tuntas)
    # 1. Hapus absensi dan perkembangan terkait jadwal siswa ini
    execute_db("DELETE FROM attendance WHERE student_id = ? OR schedule_id IN (SELECT id FROM schedules WHERE student_id = ?)", (student_id, student_id))
    execute_db("DELETE FROM student_progress WHERE student_id = ? OR schedule_id IN (SELECT id FROM schedules WHERE student_id = ?)", (student_id, student_id))
    # 2. Hapus log penggantian mentor terkait jadwal siswa ini
    execute_db("DELETE FROM mentor_replacements WHERE schedule_id IN (SELECT id FROM schedules WHERE student_id = ?)", (student_id,))
    # 3. Hapus seluruh jadwal les
    execute_db("DELETE FROM schedules WHERE student_id = ?", (student_id,))
    # 4. Hapus aturan jadwal berulang
    execute_db("DELETE FROM recurring_schedule_rules WHERE student_id = ?", (student_id,))
    # 5. Hapus pendaftaran program dan ketersediaan waktu
    execute_db("DELETE FROM student_programs WHERE student_id = ?", (student_id,))
    execute_db("DELETE FROM student_availability WHERE student_id = ?", (student_id,))
    # 6. Hapus data siswa
    execute_db("DELETE FROM students WHERE id = ?", (student_id,))

    log_audit(session["user_id"], session["username"], "HAPUS_SISWA_OTOMATIS", "students", student_id,
              f"Menghapus data siswa ID {student_id} ({student['full_name']}) beserta seluruh riwayat terkait secara otomatis.")
    flash(f"Data siswa {student['full_name']} beserta seluruh riwayat terkait berhasil dihapus secara otomatis dari sistem.", "success")
    return redirect(url_for("admin.students"))

# ==========================================
# 2B. PENGATURAN RIWAYAT AWAL PERTEMUAN (SISWA LAMA)
# ==========================================
@admin_bp.route("/students/<int:student_id>/initial-meetings", methods=["POST"])
def set_student_initial_meetings(student_id):
    validate_csrf()
    student = query_db("SELECT id, full_name FROM students WHERE id = ?", (student_id,), one=True)
    if not student:
        flash("Data siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.students"))

    input_mode = request.form.get("input_mode", "total")
    if input_mode == "period_meeting":
        period_val = request.form.get("last_period", 1)
        meeting_val = request.form.get("last_meeting", 0)
        total_offset = calculate_total_from_period_and_meeting(period_val, meeting_val)
    else:
        total_offset = request.form.get("initial_offset", 0)

    notes = request.form.get("notes", "").strip()

    res = set_student_initial_history(
        student_id=student_id,
        initial_offset=total_offset,
        notes=notes,
        admin_user_id=session["user_id"]
    )

    if res["success"]:
        flash(
            f"Pengaturan riwayat awal pertemuan untuk {student['full_name']} berhasil disimpan! "
            f"Baseline: {res['new_offset']} pertemuan diselesaikan. "
            f"Sesi berikutnya: {res['stats']['next_meeting_str']}.",
            "success"
        )
    else:
        flash(f"Gagal mengatur riwayat: {res.get('message')}", "danger")

    return redirect(request.referrer or url_for("admin.student_detail", student_id=student_id))

@admin_bp.route("/api/preview-meeting-calc", methods=["POST"])
def api_preview_meeting_calc():
    data = request.get_json() or {}
    mode = data.get("mode", "total")
    if mode == "period_meeting":
        p = data.get("period", 1)
        m = data.get("meeting", 0)
        total = calculate_total_from_period_and_meeting(p, m)
    else:
        try:
            total = int(data.get("total", 0))
        except (TypeError, ValueError):
            total = 0

    if total > 0:
        last_p, last_m, last_str = calculate_period_and_meeting(total)
    else:
        last_p, last_m, last_str = 0, 0, "Belum ada"

    next_p, next_m, next_str = calculate_period_and_meeting(total + 1)
    return jsonify({
        "total": total,
        "last_period": last_p,
        "last_meeting": last_m,
        "last_meeting_str": last_str,
        "next_period": next_p,
        "next_meeting": next_m,
        "next_meeting_str": next_str
    })

@admin_bp.route("/api/check-duplicate-student")
def api_check_duplicate_student():
    """
    Memeriksa potensi duplikasi siswa berdasarkan kemiripan nama siswa atau kontak wali / parent_id.
    Menghindari pembuatan profil ganda ketika siswa mendaftar program kedua.
    """
    name = request.args.get("name", "").strip()
    phone = request.args.get("phone", "").strip()
    parent_id = request.args.get("parent_id", "").strip()
    
    if not name and not phone and not parent_id:
        return jsonify({"matches": []})

    conditions = []
    args = []
    if name and len(name) >= 2:
        conditions.append("(LOWER(s.full_name) LIKE ? OR LOWER(?) LIKE '%' || LOWER(s.full_name) || '%')")
        args.extend([f"%{name.lower()}%", name.lower()])
    if phone and len(phone) >= 6:
        conditions.append("p.phone LIKE ?")
        args.append(f"%{phone}%")
    if parent_id:
        try:
            pid_int = int(parent_id)
            conditions.append("s.parent_id = ?")
            args.append(pid_int)
        except (TypeError, ValueError):
            pass

    if not conditions:
        return jsonify({"matches": []})

    query = f"""
        SELECT s.id, s.full_name, s.school, s.grade, s.status, s.parent_id,
               p.full_name as parent_name, p.phone as parent_phone
        FROM students s
        JOIN parents p ON s.parent_id = p.id
        WHERE {' OR '.join(conditions)}
        LIMIT 10
    """
    rows = query_db(query, args)
    matches = []
    seen_ids = set()
    for r in rows:
        if r["id"] in seen_ids:
            continue
        seen_ids.add(r["id"])
        progs = query_db(
            "SELECT pr.name FROM student_programs sp JOIN programs pr ON sp.program_id = pr.id WHERE sp.student_id = ?",
            (r["id"],)
        )
        prog_names = [p["name"] for p in progs]
        is_exact = bool(name and r["full_name"] and r["full_name"].strip().lower() == name.lower())
        is_parent = bool(parent_id and str(r["parent_id"]) == str(parent_id))
        matches.append({
            "id": r["id"],
            "full_name": r["full_name"],
            "school": r["school"] or "-",
            "grade": r["grade"] or "-",
            "status": r["status"],
            "parent_id": r["parent_id"],
            "parent_name": r["parent_name"],
            "parent_phone": r["parent_phone"] or "-",
            "programs": prog_names,
            "is_exact_name": is_exact,
            "is_same_parent": is_parent
        })
    return jsonify({"matches": matches})

@admin_bp.route("/students/<int:student_id>/programs/add", methods=["POST"])
def add_student_program(student_id):
    validate_csrf()
    student = query_db("SELECT id, full_name, grade FROM students WHERE id = ?", (student_id,), one=True)
    if not student:
        flash("Siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.students"))

    program_id = request.form.get("program_id")
    mentor_id = request.form.get("mentor_id") or None
    start_date = request.form.get("start_date") or None
    notes = request.form.get("notes", "").strip()

    # Opsi riwayat awal jika siswa sudah pernah les program ini sebelumnya
    init_period = request.form.get("initial_periods_completed", 1)
    init_meeting = request.form.get("initial_last_meeting", 0)
    init_notes = request.form.get("initial_offset_notes", "").strip()
    try:
        p_val = max(1, int(init_period))
        m_val = max(0, min(8, int(init_meeting)))
    except (TypeError, ValueError):
        p_val = 1
        m_val = 0
    total_offset = calculate_total_from_period_and_meeting(p_val, m_val) if (p_val > 1 or m_val > 0) else 0

    if not program_id:
        flash("Silakan pilih program les yang ingin didaftarkan.", "danger")
        return redirect(url_for("admin.student_detail", student_id=student_id))

    existing = query_db(
        "SELECT id, status FROM student_programs WHERE student_id = ? AND program_id = ?",
        (student_id, program_id),
        one=True
    )
    if existing:
        flash("Siswa sudah terdaftar pada program les ini. Anda dapat mengubah mentor atau statusnya melalui tombol '✏️ Ganti / Edit'.", "warning")
        return redirect(url_for("admin.student_detail", student_id=student_id))

    try:
        meetings_per_period = int(request.form.get("meetings_per_period", 8))
        if meetings_per_period not in (4, 8, 12):
            meetings_per_period = 8
    except (ValueError, TypeError):
        meetings_per_period = 8

    execute_db("""
        INSERT INTO student_programs (
            student_id, program_id, mentor_id, start_date, status, notes,
            initial_periods_completed, initial_last_meeting, initial_offset_total,
            initial_offset_notes, initial_offset_set_at, initial_offset_set_by, meetings_per_period
        )
        VALUES (?, ?, ?, COALESCE(?, date('now')), 'aktif', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
    """, (student_id, program_id, mentor_id, start_date, notes,
          p_val if total_offset > 0 else 0, m_val if total_offset > 0 else 0,
          total_offset, init_notes, session["user_id"], meetings_per_period))

    p = query_db("SELECT name, level, service_type, price_per_session FROM programs WHERE id = ?", (program_id,), one=True)
    p_name = p["name"] if p else f"ID {program_id}"
    p_level = p["level"] if p else student["grade"]
    p_service = p["service_type"] if (p and "service_type" in p.keys() and p["service_type"]) else "Private Tutoring"

    # Buat tagihan awal Periode 1 untuk program baru jika siswa belum memiliki tagihan pada program ini
    from services.finance_service import create_student_bill
    from services.pricing_service import calculate_package_tuition_fee
    existing_bill = query_db("SELECT id FROM student_bills WHERE student_id = ? AND program_id = ? AND period_number = 1", (student_id, program_id), one=True)
    if not existing_bill:
        prog_fee, rate_session, is_custom = calculate_package_tuition_fee(
            service_type=p_service,
            level=p_level,
            meetings_per_period=meetings_per_period,
            student_grade=student["grade"],
            program_name=p_name,
            custom_fee=None
        )

        create_student_bill(
            student_id=student_id,
            program_id=program_id,
            period_number=1,
            title=f"Tagihan {p_name} - Periode 1 ({meetings_per_period} Pertemuan)",
            total_amount=prog_fee,
            notes=f"Tagihan penambahan program les baru {p_name} ({meetings_per_period} sesi)."
        )
    log_audit(
        session["user_id"], session["username"], "TAMBAH_PROGRAM_SISWA", "student_programs", student_id,
        f"Mendaftarkan program {p_name} ke siswa {student['full_name']}" + (f" (Riwayat awal: Periode {p_val}, Pertemuan {m_val})" if total_offset > 0 else ""),
        module_name="Program Siswa",
        new_values={"program_id": program_id, "program_name": p_name, "mentor_id": mentor_id, "initial_offset": total_offset},
        fields_changed=["pendaftaran_program_baru"]
    )
    flash(f"Program les {p_name} berhasil didaftarkan untuk siswa {student['full_name']}.", "success")
    return redirect(url_for("admin.student_detail", student_id=student_id))

@admin_bp.route("/students/<int:student_id>/programs/<int:sp_id>/initial-history", methods=["POST"])
def set_student_program_initial_history_route(student_id, sp_id):
    """Mengatur riwayat awal pertemuan siswa lama pada program tertentu."""
    validate_csrf()
    student = query_db("SELECT id, full_name FROM students WHERE id = ?", (student_id,), one=True)
    if not student:
        flash("Siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.students"))

    sp = query_db("""
        SELECT sp.*, pr.name as program_name
        FROM student_programs sp
        JOIN programs pr ON sp.program_id = pr.id
        WHERE sp.id = ? AND sp.student_id = ?
    """, (sp_id, student_id), one=True)
    if not sp:
        flash("Data program siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.student_detail", student_id=student_id))

    last_period = request.form.get("last_period", 1)
    last_meeting = request.form.get("last_meeting", 0)
    notes = request.form.get("notes", "").strip()

    res = set_student_program_initial_history(
        student_id=student_id,
        program_id=sp["program_id"],
        last_period=last_period,
        last_meeting=last_meeting,
        notes=notes,
        admin_user_id=session["user_id"]
    )

    if res["success"]:
        flash(
            f"Riwayat awal untuk program {res['program_name']} ({student['full_name']}) berhasil disimpan! "
            f"Posisi awal: Periode {res['period']}, Pertemuan {res['meeting']} (Total: {res['total_offset']} sesi). "
            f"Sesi berikutnya di sistem: {res['stats']['next_meeting_bracket']}.",
            "success"
        )
    else:
        flash(f"Gagal mengatur riwayat: {res.get('message')}", "danger")

    return redirect(url_for("admin.student_detail", student_id=student_id))

@admin_bp.route("/students/<int:student_id>/programs/<int:sp_id>/edit", methods=["POST"])
def edit_student_program(student_id, sp_id):
    validate_csrf()
    student = query_db("SELECT id, full_name, grade FROM students WHERE id = ?", (student_id,), one=True)
    if not student:
        flash("Siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.students"))

    program_id = request.form.get("program_id")
    mentor_id = request.form.get("mentor_id") or None
    status = request.form.get("status", "aktif")
    start_date = request.form.get("start_date") or None
    end_date = request.form.get("end_date") or None
    notes = request.form.get("notes", "").strip()

    if status not in ("aktif", "selesai", "dibatalkan"):
        status = "aktif"

    sp = query_db("SELECT * FROM student_programs WHERE id = ? AND student_id = ?", (sp_id, student_id), one=True)
    if not sp:
        flash("Data program les siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.student_detail", student_id=student_id))

    if not program_id:
        flash("Program les wajib dipilih.", "danger")
        return redirect(url_for("admin.student_detail", student_id=student_id))

    # Cek duplikasi jika program_id diubah
    if str(program_id) != str(sp["program_id"]):
        conflict = query_db(
            "SELECT id FROM student_programs WHERE student_id = ? AND program_id = ? AND id != ?",
            (student_id, program_id, sp_id),
            one=True
        )
        if conflict:
            flash("Siswa sudah terdaftar di program les tersebut. Silakan pilih program lain atau kelola program tersebut secara langsung.", "warning")
            return redirect(url_for("admin.student_detail", student_id=student_id))

    try:
        meetings_per_period = int(request.form.get("meetings_per_period", 8))
        if meetings_per_period not in (4, 8, 12):
            meetings_per_period = 8
    except (ValueError, TypeError):
        meetings_per_period = 8

    execute_db("""
        UPDATE student_programs
        SET program_id = ?, mentor_id = ?, status = ?, start_date = ?, end_date = ?, notes = ?, meetings_per_period = ?
        WHERE id = ? AND student_id = ?
    """, (program_id, mentor_id, status, start_date, end_date, notes, meetings_per_period, sp_id, student_id))

    from services.meeting_service import resequence_student_program_attendances
    resequence_student_program_attendances(student_id, program_id)

    p = query_db("SELECT name, level, service_type, price_per_session FROM programs WHERE id = ?", (program_id,), one=True)
    p_name = p["name"] if p else f"ID {program_id}"
    p_level = p["level"] if p else student["grade"]
    p_service = p["service_type"] if (p and "service_type" in p.keys() and p["service_type"]) else "Private Tutoring"

    # Buat tagihan awal Periode 1 untuk program baru jika siswa belum memiliki tagihan pada program ini
    from services.finance_service import create_student_bill
    from services.pricing_service import calculate_package_tuition_fee
    existing_bill = query_db("SELECT id FROM student_bills WHERE student_id = ? AND program_id = ? AND period_number = 1", (student_id, program_id), one=True)
    if not existing_bill:
        prog_fee, rate_session, is_custom = calculate_package_tuition_fee(
            service_type=p_service,
            level=p_level,
            meetings_per_period=meetings_per_period,
            student_grade=student["grade"],
            program_name=p_name,
            custom_fee=None
        )

        create_student_bill(
            student_id=student_id,
            program_id=program_id,
            period_number=1,
            title=f"Tagihan {p_name} - Periode 1 ({meetings_per_period} Pertemuan)",
            total_amount=prog_fee,
            notes=f"Tagihan penambahan program les baru {p_name} ({meetings_per_period} sesi)."
        )
    log_audit(session["user_id"], session["username"], "UBAH_PROGRAM_SISWA", "student_programs", sp_id, f"Mengubah program les siswa {student['full_name']} menjadi {p_name} (Status: {status})")
    flash(f"Data program les {p_name} untuk siswa {student['full_name']} berhasil diperbarui.", "success")
    return redirect(url_for("admin.student_detail", student_id=student_id))

@admin_bp.route("/students/<int:student_id>/programs/<int:sp_id>/delete", methods=["POST"])
def delete_student_program(student_id, sp_id):
    validate_csrf()
    student = query_db("SELECT id, full_name FROM students WHERE id = ?", (student_id,), one=True)
    if not student:
        flash("Siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.students"))

    sp = query_db("""
        SELECT sp.*, pr.name as program_name
        FROM student_programs sp
        JOIN programs pr ON sp.program_id = pr.id
        WHERE sp.id = ? AND sp.student_id = ?
    """, (sp_id, student_id), one=True)

    if not sp:
        flash("Data program les siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.student_detail", student_id=student_id))

    p_name = sp["program_name"]
    execute_db("DELETE FROM student_programs WHERE id = ? AND student_id = ?", (sp_id, student_id))

    log_audit(session["user_id"], session["username"], "HAPUS_PROGRAM_SISWA", "student_programs", sp_id, f"Menghapus program {p_name} dari siswa {student['full_name']}")
    flash(f"Program les {p_name} berhasil dihapus dari daftar les siswa {student['full_name']}.", "info")
    return redirect(url_for("admin.student_detail", student_id=student_id))


# ==========================================
# 3. DATA ORANG TUA / WALI
# ==========================================
@admin_bp.route("/parents")
def parents():
    status_filter = request.args.get("status")
    search = request.args.get("q", "").strip()
    query = """
        SELECT p.*,
               u.username as parent_username, u.is_active as user_is_active,
               COUNT(s.id) as children_count,
               GROUP_CONCAT(s.full_name, ', ') as children_names
        FROM parents p
        LEFT JOIN users u ON p.user_id = u.id
        LEFT JOIN students s ON p.id = s.parent_id
    """
    conditions = []
    args = []
    if status_filter:
        conditions.append("p.status = ?")
        args.append(status_filter)
    if search:
        conditions.append("(p.full_name LIKE ? OR p.phone LIKE ? OR p.email LIKE ? OR u.username LIKE ?)")
        term = f"%{search}%"
        args.extend([term, term, term, term])

    if conditions:
        query += f" WHERE {' AND '.join(conditions)}"

    query += " GROUP BY p.id ORDER BY p.full_name ASC"
    parents_list = query_db(query, args)
    return render_template("admin/parents.html", parents=parents_list, status_filter=status_filter, search=search)

@admin_bp.route("/parents/create", methods=["POST"])
def create_parent():
    validate_csrf()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    create_account = request.form.get("create_account")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not full_name or not phone:
        flash("Nama lengkap dan nomor telepon wali wajib diisi.", "danger")
        return redirect(url_for("admin.parents"))

    user_id = None
    if create_account and username and password:
        existing = query_db("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,), one=True)
        if existing:
            flash(f"ID Pengguna / Username '{username}' sudah digunakan. Silakan gunakan username lain.", "danger")
            return redirect(url_for("admin.parents"))
        user_id = execute_db("""
            INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
            VALUES (?, ?, 'parent', ?, ?, ?, 1)
        """, (username, generate_password_hash(password), full_name, email, phone))

    parent_id = execute_db("""
        INSERT INTO parents (user_id, full_name, phone, email, address, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, 'aktif')
    """, (user_id, full_name, phone, email, address, notes))

    log_audit(session["user_id"], session["username"], "TAMBAH_WALI", "parents", parent_id, f"Menambahkan wali murid baru: {full_name}")
    flash(f"Data wali {full_name} berhasil disimpan." + (f" Akun login '{username}' aktif." if user_id else ""), "success")
    return redirect(url_for("admin.parents"))

@admin_bp.route("/parents/<int:parent_id>/create-account", methods=["POST"])
def create_parent_account(parent_id):
    validate_csrf()
    parent = query_db("SELECT * FROM parents WHERE id = ?", (parent_id,), one=True)
    if not parent:
        flash("Orang tua/wali tidak ditemukan.", "danger")
        return redirect(url_for("admin.parents"))

    if parent["user_id"]:
        flash("Wali murid ini sudah memiliki akun login.", "warning")
        return redirect(url_for("admin.parents"))

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password or len(password) < 6:
        flash("Username dan password (minimal 6 karakter) wajib diisi.", "danger")
        return redirect(url_for("admin.parents"))

    existing = query_db("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,), one=True)
    if existing:
        flash(f"ID Pengguna / Username '{username}' sudah digunakan. Silakan gunakan username lain.", "danger")
        return redirect(url_for("admin.parents"))

    user_id = execute_db("""
        INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
        VALUES (?, ?, 'parent', ?, ?, ?, 1)
    """, (username, generate_password_hash(password), parent["full_name"], parent["email"], parent["phone"]))

    execute_db("UPDATE parents SET user_id = ? WHERE id = ?", (user_id, parent_id))

    log_audit(session["user_id"], session["username"], "BUAT_AKUN_WALI", "parents", parent_id,
              f"Membuat akun login orang tua untuk {parent['full_name']} (Username: {username})")
    flash(f"Akun login untuk wali {parent['full_name']} berhasil dibuat dengan username '{username}'.", "success")
    return redirect(url_for("admin.parents"))

@admin_bp.route("/parents/<int:parent_id>/edit", methods=["POST"])
def edit_parent(parent_id):
    validate_csrf()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    status = request.form.get("status", "aktif")

    execute_db("""
        UPDATE parents
        SET full_name = ?, phone = ?, email = ?, address = ?, notes = ?, status = ?
        WHERE id = ?
    """, (full_name, phone, email, address, notes, status, parent_id))

    log_audit(session["user_id"], session["username"], "EDIT_WALI", "parents", parent_id, f"Memperbarui data wali {full_name}")
    flash(f"Data wali {full_name} berhasil diperbarui.", "success")
    return redirect(url_for("admin.parents"))

    log_audit(session["user_id"], session["username"], "UBAH_WALI", "parents", parent_id, f"Mengubah data wali ID {parent_id} ({full_name})")
    flash(f"Data wali {full_name} berhasil diperbarui.", "success")
    return redirect(url_for("admin.parents"))

@admin_bp.route("/parents/<int:parent_id>/toggle-status", methods=["POST"])
def toggle_parent_status(parent_id):
    validate_csrf()
    p = query_db("SELECT * FROM parents WHERE id = ?", (parent_id,), one=True)
    if not p:
        flash("Orang tua/wali tidak ditemukan.", "danger")
        return redirect(url_for("admin.parents"))

    current_status = p["status"] if "status" in p.keys() and p["status"] else "aktif"
    new_status = "nonaktif" if current_status == "aktif" else "aktif"
    execute_db("UPDATE parents SET status = ? WHERE id = ?", (new_status, parent_id))
    if p["user_id"]:
        execute_db("UPDATE users SET is_active = ? WHERE id = ?", (1 if new_status == "aktif" else 0, p["user_id"]))

    log_audit(session["user_id"], session["username"], "STATUS_WALI", "parents", parent_id,
              f"Mengubah status wali ID {parent_id} ({p['full_name']}) menjadi {new_status}")
    flash(f"Status orang tua/wali {p['full_name']} berhasil diubah menjadi '{new_status}'.", "info")
    return redirect(url_for("admin.parents"))

@admin_bp.route("/parents/<int:parent_id>/delete", methods=["POST"])
def delete_parent(parent_id):
    validate_csrf()
    parent = query_db("SELECT * FROM parents WHERE id = ?", (parent_id,), one=True)
    if not parent:
        flash("Orang tua/wali tidak ditemukan.", "danger")
        return redirect(url_for("admin.parents"))

    action_type = request.form.get("action_type", "auto_delete")

    if action_type in ("archive", "arsip", "nonaktif"):
        # Pilihan 1: Hanya Arsip / Nonaktifkan
        execute_db("UPDATE parents SET status = 'nonaktif' WHERE id = ?", (parent_id,))
        if parent["user_id"]:
            execute_db("UPDATE users SET is_active = 0 WHERE id = ?", (parent["user_id"],))
        log_audit(session["user_id"], session["username"], "ARSIP_WALI", "parents", parent_id,
                  f"Menonaktifkan status wali ID {parent_id} ({parent['full_name']}). Data riwayat tetap tersimpan aman.")
        flash(f"Data orang tua/wali {parent['full_name']} berhasil dinonaktifkan/diarsipkan. Seluruh data tetap aman tersimpan.", "info")
        return redirect(url_for("admin.parents"))

    # Pilihan 2: Hapus Otomatis (Membersihkan seluruh relasi terkait anak, jadwal, dan akun secara otomatis)
    children = query_db("SELECT id, full_name FROM students WHERE parent_id = ?", (parent_id,))
    for ch in children:
        ch_id = ch["id"]
        execute_db("DELETE FROM attendance WHERE student_id = ? OR schedule_id IN (SELECT id FROM schedules WHERE student_id = ?)", (ch_id, ch_id))
        execute_db("DELETE FROM student_progress WHERE student_id = ? OR schedule_id IN (SELECT id FROM schedules WHERE student_id = ?)", (ch_id, ch_id))
        execute_db("DELETE FROM mentor_replacements WHERE schedule_id IN (SELECT id FROM schedules WHERE student_id = ?)", (ch_id,))
        execute_db("DELETE FROM schedules WHERE student_id = ?", (ch_id,))
        execute_db("DELETE FROM recurring_schedule_rules WHERE student_id = ?", (ch_id,))
        execute_db("DELETE FROM student_programs WHERE student_id = ?", (ch_id,))
        execute_db("DELETE FROM student_availability WHERE student_id = ?", (ch_id,))
        execute_db("DELETE FROM students WHERE id = ?", (ch_id,))

    parent_user_id = parent["user_id"]
    execute_db("DELETE FROM parents WHERE id = ?", (parent_id,))

    if parent_user_id:
        execute_db("DELETE FROM notifications WHERE user_id = ?", (parent_user_id,))
        execute_db("DELETE FROM users WHERE id = ?", (parent_user_id,))

    log_audit(session["user_id"], session["username"], "HAPUS_WALI_OTOMATIS", "parents", parent_id,
              f"Menghapus wali ID {parent_id} ({parent['full_name']}) beserta data siswa dan riwayat terkait secara otomatis.")
    flash(f"Data orang tua/wali {parent['full_name']} beserta data siswa dan riwayat terkait berhasil dihapus secara otomatis.", "success")
    return redirect(url_for("admin.parents"))

# ==========================================
# 4. DATA MENTOR
# ==========================================
@admin_bp.route("/mentors")
def mentors():
    status_filter = request.args.get("status")
    search = request.args.get("q", "").strip()
    mentors_list = get_mentors_report(status_filter, search)

    # Ambil ketersediaan waktu untuk setiap mentor
    mentor_data = []
    days_name = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    for m in mentors_list:
        avails = query_db("SELECT * FROM mentor_availability WHERE mentor_id = ? ORDER BY day_of_week ASC", (m["id"],))
        avail_list = []
        for av in avails:
            day_str = days_name[av["day_of_week"]] if 0 <= av["day_of_week"] <= 6 else str(av["day_of_week"])
            avail_list.append(f"{day_str} ({av['start_time']}-{av['end_time']})")
        m_dict = dict(m)
        m_dict["availability_summary"] = ", ".join(avail_list) if avail_list else "Belum diatur"
        mentor_data.append(m_dict)

    return render_template("admin/mentors.html", mentors=mentor_data, status_filter=status_filter, search=search)

@admin_bp.route("/mentors/create", methods=["POST"])
def create_mentor():
    validate_csrf()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    address = request.form.get("address", "").strip()
    expertise = request.form.get("expertise", "").strip()
    bio = request.form.get("bio", "").strip()
    create_account = request.form.get("create_account")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    lat_val = request.form.get("latitude", "").strip()
    lng_val = request.form.get("longitude", "").strip()
    try:
        latitude = float(lat_val) if lat_val else None
    except (ValueError, TypeError):
        latitude = None
    try:
        longitude = float(lng_val) if lng_val else None
    except (ValueError, TypeError):
        longitude = None

    if not full_name or not phone:
        flash("Nama lengkap dan nomor telepon mentor wajib diisi.", "danger")
        return redirect(url_for("admin.mentors"))

    user_id = None
    if create_account and username and password:
        existing = query_db("SELECT id FROM users WHERE username = ?", (username,), one=True)
        if existing:
            flash("ID Pengguna / Username sudah digunakan. Silakan gunakan ID lain.", "danger")
            return redirect(url_for("admin.mentors"))
        user_id = execute_db("""
            INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
            VALUES (?, ?, 'mentor', ?, ?, ?, 1)
        """, (username, generate_password_hash(password), full_name, email, phone))

    mentor_id = execute_db("""
        INSERT INTO mentors (user_id, full_name, phone, email, expertise, bio, status, address, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?, 'aktif', ?, ?, ?)
    """, (user_id, full_name, phone, email, expertise, bio, address, latitude, longitude))

    log_audit(session["user_id"], session["username"], "TAMBAH_MENTOR", "mentors", mentor_id, f"Menambahkan mentor baru: {full_name}")
    flash(f"Mentor {full_name} berhasil ditambahkan.", "success")
    return redirect(url_for("admin.mentors"))

@admin_bp.route("/mentors/<int:mentor_id>/edit", methods=["POST"])
def edit_mentor(mentor_id):
    validate_csrf()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    address = request.form.get("address", "").strip()
    expertise = request.form.get("expertise", "").strip()
    bio = request.form.get("bio", "").strip()
    status = request.form.get("status", "aktif")

    lat_val = request.form.get("latitude", "").strip()
    lng_val = request.form.get("longitude", "").strip()
    try:
        latitude = float(lat_val) if lat_val else None
    except (ValueError, TypeError):
        latitude = None
    try:
        longitude = float(lng_val) if lng_val else None
    except (ValueError, TypeError):
        longitude = None

    execute_db("""
        UPDATE mentors
        SET full_name = ?, phone = ?, email = ?, expertise = ?, bio = ?, status = ?,
            address = ?, latitude = ?, longitude = ?
        WHERE id = ?
    """, (full_name, phone, email, expertise, bio, status, address, latitude, longitude, mentor_id))

    # Perbarui data user jika ada
    m = query_db("SELECT user_id FROM mentors WHERE id = ?", (mentor_id,), one=True)
    if m and m["user_id"]:
        execute_db("UPDATE users SET full_name = ?, phone = ?, email = ?, is_active = ? WHERE id = ?",
                   (full_name, phone, email, 1 if status == 'aktif' else 0, m["user_id"]))

    log_audit(session["user_id"], session["username"], "UBAH_MENTOR", "mentors", mentor_id, f"Mengubah data mentor ID {mentor_id} ({full_name})")
    flash(f"Data mentor {full_name} berhasil diperbarui.", "success")
    return redirect(url_for("admin.mentors"))

@admin_bp.route("/mentors/<int:mentor_id>/availability/add", methods=["POST"])
def add_mentor_availability(mentor_id):
    validate_csrf()
    flash("Admin tidak diperkenankan mengatur ketersediaan waktu mentor. Ketersediaan waktu hanya dapat diatur secara mandiri oleh mentor melalui akun login mentor masing-masing.", "warning")
    return redirect(url_for("admin.mentors"))

@admin_bp.route("/mentors/<int:mentor_id>/availability/<int:avail_id>/delete", methods=["POST"])
def delete_mentor_availability(mentor_id, avail_id):
    validate_csrf()
    flash("Admin tidak diperkenankan menghapus ketersediaan waktu mentor. Ketersediaan waktu hanya dapat dikelola secara mandiri oleh mentor.", "warning")
    return redirect(url_for("admin.mentors"))

@admin_bp.route("/api/mentors/<int:mentor_id>/availability")
def api_mentor_availability(mentor_id):
    mentor = query_db("SELECT id, full_name FROM mentors WHERE id = ?", (mentor_id,), one=True)
    if not mentor:
        return jsonify({"error": "Mentor tidak ditemukan"}), 404
    avails = query_db("SELECT * FROM mentor_availability WHERE mentor_id = ? ORDER BY day_of_week ASC, start_time ASC", (mentor_id,))
    days_name = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    data = []
    for av in avails:
        dow = av["day_of_week"]
        data.append({
            "id": av["id"],
            "day_of_week": dow,
            "day_name": days_name[dow] if 0 <= dow <= 6 else str(dow),
            "start_time": av["start_time"],
            "end_time": av["end_time"],
            "notes": av["notes"] or ""
        })
    return jsonify({
        "mentor_id": mentor["id"],
        "mentor_name": mentor["full_name"],
        "availabilities": data
    })

@admin_bp.route("/mentors/<int:mentor_id>/toggle-status", methods=["POST"])
def toggle_mentor_status(mentor_id):
    validate_csrf()
    m = query_db("SELECT * FROM mentors WHERE id = ?", (mentor_id,), one=True)
    if not m:
        flash("Mentor tidak ditemukan.", "danger")
        return redirect(url_for("admin.mentors"))

    new_status = "nonaktif" if m["status"] == "aktif" else "aktif"
    execute_db("UPDATE mentors SET status = ? WHERE id = ?", (new_status, mentor_id))
    if m["user_id"]:
        execute_db("UPDATE users SET is_active = ? WHERE id = ?", (1 if new_status == 'aktif' else 0, m["user_id"]))

    log_audit(session["user_id"], session["username"], "STATUS_MENTOR", "mentors", mentor_id, f"Mengubah status mentor ID {mentor_id} menjadi {new_status}")
    flash(f"Status mentor {m['full_name']} diubah menjadi {new_status}.", "info")
    return redirect(url_for("admin.mentors"))

@admin_bp.route("/mentors/<int:mentor_id>/delete", methods=["POST"])
def delete_mentor(mentor_id):
    validate_csrf()
    mentor = query_db("SELECT * FROM mentors WHERE id = ?", (mentor_id,), one=True)
    if not mentor:
        flash("Mentor tidak ditemukan.", "danger")
        return redirect(url_for("admin.mentors"))

    action_type = request.form.get("action_type", "auto_delete")

    if action_type in ("archive", "arsip", "nonaktif"):
        # Pilihan 1: Hanya Arsip / Nonaktifkan
        execute_db("UPDATE mentors SET status = 'nonaktif' WHERE id = ?", (mentor_id,))
        if mentor["user_id"]:
            execute_db("UPDATE users SET is_active = 0 WHERE id = ?", (mentor["user_id"],))
        log_audit(session["user_id"], session["username"], "ARSIP_MENTOR", "mentors", mentor_id,
                  f"Menonaktifkan status mentor ID {mentor_id} ({mentor['full_name']}). Riwayat jadwal tetap tersimpan.")
        flash(f"Mentor {mentor['full_name']} berhasil dinonaktifkan/diarsipkan. Riwayat mengajar tetap aman tersimpan.", "info")
        return redirect(url_for("admin.mentors"))

    # Pilihan 2: Hapus Otomatis (Membersihkan seluruh relasi terkait secara tuntas)
    # 1. Hapus ketersediaan waktu mentor
    execute_db("DELETE FROM mentor_availability WHERE mentor_id = ?", (mentor_id,))
    # 2. Hapus aturan jadwal berulang mentor
    execute_db("DELETE FROM recurring_schedule_rules WHERE mentor_id = ?", (mentor_id,))
    # 3. Hapus catatan riwayat pergantian mentor
    execute_db("DELETE FROM mentor_replacements WHERE original_mentor_id = ? OR replacement_mentor_id = ?", (mentor_id, mentor_id))
    # 4. Hapus absensi dan progress terkait sesi mengajar mentor ini
    execute_db("DELETE FROM attendance WHERE mentor_id = ? OR schedule_id IN (SELECT id FROM schedules WHERE mentor_id = ?)", (mentor_id, mentor_id))
    execute_db("DELETE FROM student_progress WHERE mentor_id = ? OR schedule_id IN (SELECT id FROM schedules WHERE mentor_id = ?)", (mentor_id, mentor_id))
    # 5. Hapus jadwal les yang dipegang mentor ini
    execute_db("DELETE FROM schedules WHERE mentor_id = ?", (mentor_id,))
    # 6. Lepaskan penugasan mentor pada program siswa (set mentor_id = NULL)
    execute_db("UPDATE student_programs SET mentor_id = NULL WHERE mentor_id = ?", (mentor_id,))
    # 7. Hapus profil mentor
    mentor_user_id = mentor["user_id"]
    execute_db("DELETE FROM mentors WHERE id = ?", (mentor_id,))
    # 8. Hapus notifikasi & akun pengguna jika ada
    if mentor_user_id:
        execute_db("DELETE FROM notifications WHERE user_id = ?", (mentor_user_id,))
        execute_db("DELETE FROM users WHERE id = ?", (mentor_user_id,))

    log_audit(session["user_id"], session["username"], "HAPUS_MENTOR_OTOMATIS", "mentors", mentor_id,
              f"Menghapus mentor ID {mentor_id} ({mentor['full_name']}) beserta akun dan seluruh riwayat terkait secara otomatis.")
    flash(f"Data mentor {mentor['full_name']} beserta akun dan seluruh data terkait berhasil dihapus secara otomatis dari sistem.", "success")
    return redirect(url_for("admin.mentors"))

# ==========================================
# 5. DATA PROGRAM LES
# ==========================================
@admin_bp.route("/programs")
def programs():
    programs_list = query_db("""
        SELECT p.*,
               COUNT(sp.id) as active_students_count
        FROM programs p
        LEFT JOIN student_programs sp ON p.id = sp.program_id AND sp.status = 'aktif'
        GROUP BY p.id
        ORDER BY p.status ASC, p.name ASC
    """)
    return render_template("admin/programs.html", programs=programs_list)

@admin_bp.route("/programs/create", methods=["POST"])
def create_program():
    validate_csrf()
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    description = request.form.get("description", "").strip()
    level = request.form.get("level", "Semua Jenjang").strip()
    service_type = request.form.get("service_type", "Private Tutoring").strip()

    if not name or not code:
        flash("Nama dan kode program wajib diisi.", "danger")
        return redirect(url_for("admin.programs"))

    existing = query_db("SELECT id FROM programs WHERE code = ?", (code,), one=True)
    if existing:
        flash(f"Kode program '{code}' sudah digunakan. Gunakan kode unik lain.", "danger")
        return redirect(url_for("admin.programs"))

    from services.pricing_service import get_tuition_rate_per_session
    rate = get_tuition_rate_per_session(service_type=service_type, level=level, program_name=name)

    program_id = execute_db("""
        INSERT INTO programs (name, code, description, level, service_type, status, price_per_session, default_fee_4, default_fee_8, default_fee_12)
        VALUES (?, ?, ?, ?, ?, 'aktif', ?, ?, ?, ?)
    """, (name, code, description, level, service_type, rate, rate * 4, rate * 8, rate * 12))

    log_audit(session["user_id"], session["username"], "TAMBAH_PROGRAM", "programs", program_id,
              f"Menambahkan program les: {name} ({code}) - Jenjang: {level}, Layanan: {service_type}")
    flash(f"Program {name} ({level} - {service_type}) berhasil ditambahkan ke daftar program les.", "success")
    return redirect(url_for("admin.programs"))

@admin_bp.route("/programs/<int:program_id>/edit", methods=["POST"])
def edit_program(program_id):
    validate_csrf()
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    description = request.form.get("description", "").strip()
    level = request.form.get("level", "Semua Jenjang").strip()
    service_type = request.form.get("service_type", "Private Tutoring").strip()
    status = request.form.get("status", "aktif")

    from services.pricing_service import get_tuition_rate_per_session
    rate = get_tuition_rate_per_session(service_type=service_type, level=level, program_name=name)

    execute_db("""
        UPDATE programs
        SET name = ?, code = COALESCE(NULLIF(?, ''), code), description = ?, level = ?, service_type = ?, status = ?,
            price_per_session = ?, default_fee_4 = ?, default_fee_8 = ?, default_fee_12 = ?
        WHERE id = ?
    """, (name, code, description, level, service_type, status, rate, rate * 4, rate * 8, rate * 12, program_id))

    log_audit(session["user_id"], session["username"], "UBAH_PROGRAM", "programs", program_id,
              f"Mengubah program les ID {program_id}: {name} - Jenjang: {level}, Layanan: {service_type} (Status: {status})")
    flash(f"Data program {name} berhasil diperbarui.", "success")
    return redirect(url_for("admin.programs"))

@admin_bp.route("/programs/<int:program_id>/archive", methods=["POST"])
def archive_program(program_id):
    validate_csrf()
    p = query_db("SELECT * FROM programs WHERE id = ?", (program_id,), one=True)
    if not p:
        flash("Program tidak ditemukan.", "danger")
        return redirect(url_for("admin.programs"))

    new_status = "diarsipkan" if p["status"] != "diarsipkan" else "aktif"
    execute_db("UPDATE programs SET status = ? WHERE id = ?", (new_status, program_id))
    log_audit(session["user_id"], session["username"], "ARSIP_PROGRAM", "programs", program_id, f"Mengubah status program ID {program_id} menjadi {new_status}")
    flash(f"Status program {p['name']} diubah menjadi {new_status}. Riwayat jadwal dan laporan tetap aman.", "info")
    return redirect(url_for("admin.programs"))

# ==========================================
# 6. MANAJEMEN AKUN & PENGGUNA
# ==========================================
@admin_bp.route("/accounts")
def accounts():
    role_filter = request.args.get("role")
    search = request.args.get("q", "").strip()

    conditions = []
    args = []
    if role_filter:
        conditions.append("role = ?")
        args.append(role_filter)
    if search:
        conditions.append("(username LIKE ? OR full_name LIKE ? OR email LIKE ?)")
        term = f"%{search}%"
        args.extend([term, term, term])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    accounts_list = query_db(f"""
        SELECT id, username, role, full_name, email, phone, is_active, created_at, updated_at
        FROM users
        {where_clause}
        ORDER BY created_at DESC
    """, args)

    return render_template("admin/accounts.html", accounts=accounts_list, role_filter=role_filter, search=search)

@admin_bp.route("/accounts/create", methods=["POST"])
def create_account():
    validate_csrf()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "").strip()
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()

    if not username or not password or not role or not full_name:
        flash("Username, password, role, dan nama lengkap wajib diisi.", "danger")
        return redirect(url_for("admin.accounts"))

    if role not in ("admin", "owner", "mentor", "parent"):
        flash("Role yang dipilih tidak valid. Role yang diizinkan: Admin, Pemilik, Mentor, Orang Tua.", "danger")
        return redirect(url_for("admin.accounts"))

    existing = query_db("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username,), one=True)
    if existing:
        flash(f"ID Pengguna / Username '{username}' sudah digunakan. Cegah duplikasi ID pengguna.", "danger")
        return redirect(url_for("admin.accounts"))

    user_id = execute_db("""
        INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (username, generate_password_hash(password), role, full_name, email, phone))

    parent_id = request.form.get("parent_id")
    if role == "parent" and parent_id:
        execute_db("UPDATE parents SET user_id = ? WHERE id = ?", (user_id, parent_id))

    log_audit(session["user_id"], session["username"], "BUAT_AKUN", "users", user_id, f"Membuat akun pengguna baru: {username} (Role: {role})")
    flash(f"Akun pengguna {username} ({role}) berhasil dibuat.", "success")
    return redirect(url_for("admin.accounts"))

@admin_bp.route("/accounts/<int:user_id>/toggle-status", methods=["POST"])
def toggle_account_status(user_id):
    validate_csrf()
    if user_id == session["user_id"]:
        flash("Anda tidak dapat menonaktifkan akun yang sedang Anda gunakan sendiri.", "warning")
        return redirect(url_for("admin.accounts"))

    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if not user:
        flash("Pengguna tidak ditemukan.", "danger")
        return redirect(url_for("admin.accounts"))

    new_active = 0 if user["is_active"] else 1
    execute_db("UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_active, user_id))
    action_str = "diaktifkan" if new_active else "dinonaktifkan"
    log_audit(session["user_id"], session["username"], "STATUS_AKUN", "users", user_id, f"Akun {user['username']} {action_str}.")
    flash(f"Akun {user['username']} berhasil {action_str}.", "info")
    return redirect(url_for("admin.accounts"))

@admin_bp.route("/accounts/<int:user_id>/reset-password", methods=["POST"])
def reset_password(user_id):
    validate_csrf()
    new_password = request.form.get("new_password", "").strip()
    if not new_password or len(new_password) < 6:
        flash("Password baru minimal harus 6 karakter.", "danger")
        return redirect(url_for("admin.accounts"))

    user = query_db("SELECT username FROM users WHERE id = ?", (user_id,), one=True)
    if not user:
        flash("Pengguna tidak ditemukan.", "danger")
        return redirect(url_for("admin.accounts"))

    execute_db("UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (generate_password_hash(new_password), user_id))
    log_audit(session["user_id"], session["username"], "RESET_PASSWORD", "users", user_id, f"Reset password akun {user['username']}")
    flash(f"Password untuk akun {user['username']} berhasil direset.", "success")
    return redirect(url_for("admin.accounts"))

# ==========================================
# 7. PENJADWALAN RUTIN & PELAKSANAAN SESI
# ==========================================
@admin_bp.route("/schedules")
def schedules():
    day_filter = request.args.get("day")
    student_filter = request.args.get("student_id")
    mentor_filter = request.args.get("mentor_id")
    date_filter = request.args.get("date")
    status_filter = request.args.get("status")

    # 1. Daftar Jadwal Rutin Mingguan (Jadwal Utama)
    routine_list = get_routine_schedules(
        student_id=student_filter,
        mentor_id=mentor_filter,
        day_of_week=day_filter
    )

    # 2. Riwayat Pelaksanaan Sesi
    schedules_list = get_schedules_report(
        start_date=date_filter,
        end_date=date_filter,
        student_id=student_filter,
        mentor_id=mentor_filter,
        status=status_filter
    )

    students_list = query_db("SELECT id, full_name FROM students WHERE status = 'aktif' ORDER BY full_name ASC")
    mentors_list = query_db("SELECT id, full_name FROM mentors WHERE status = 'aktif' ORDER BY full_name ASC")
    programs_list = query_db("SELECT id, name FROM programs WHERE status = 'aktif' ORDER BY name ASC")

    return render_template(
        "admin/schedules.html",
        routine_schedules=routine_list,
        schedules=schedules_list,
        students=students_list,
        mentors=mentors_list,
        programs=programs_list,
        day_names=DAY_NAMES,
        day_filter=day_filter,
        date_filter=date_filter,
        student_filter=student_filter,
        mentor_filter=mentor_filter,
        status_filter=status_filter
    )

@admin_bp.route("/schedules/routine/create", methods=["POST"])
def admin_create_routine_schedule():
    validate_csrf()
    student_id = request.form.get("student_id")
    program_id = request.form.get("program_id")
    subject_info = request.form.get("subject_info", "").strip()
    notes = request.form.get("notes", "").strip()

    # Pengecekan validasi: Siswa baru tidak boleh mulai belajar sebelum divalidasi pembayarannya oleh Pemilik
    st_check = query_db("SELECT full_name, status, payment_status FROM students WHERE id = ?", (student_id,), one=True)
    if st_check and (st_check["payment_status"] == "menunggu_validasi" or st_check["status"] == "menunggu_validasi"):
        flash(f"Pembelajaran belum dapat dimulai untuk {st_check['full_name']}. Siswa masih berstatus 'Menunggu Validasi Pembayaran oleh Pemilik'. Silakan tunggu validasi dari Pemilik terlebih dahulu.", "warning")
        return redirect(url_for("admin.schedules"))

    # Ambil daftar mentor: mentor_ids[] atau fallback ke mentor_id
    raw_mentors = request.form.getlist("mentor_ids[]") or request.form.getlist("mentor_ids")
    if not raw_mentors:
        single_m = request.form.get("mentor_id")
        if single_m:
            raw_mentors = [single_m]
    # Fallback jika ada slot_mentor_id (backward compat)
    slot_mentors = request.form.getlist("slot_mentor_id[]")

    # Bersihkan duplikat & nilai kosong dengan tetap menjaga urutan
    mentor_ids = []
    for m in raw_mentors:
        m_str = str(m).strip()
        if m_str and m_str not in mentor_ids:
            mentor_ids.append(m_str)

    # Ambil seluruh baris jadwal (mendukung opsi multi-hari dalam 1 kali input)
    days = request.form.getlist("day_of_week[]") or request.form.getlist("day_of_week")
    start_times = request.form.getlist("start_time[]") or request.form.getlist("start_time")
    end_times = request.form.getlist("end_time[]") or request.form.getlist("end_time")

    if not (student_id and program_id and (mentor_ids or slot_mentors) and days):
        flash("Informasi siswa, program les, mentor pengampu, dan minimal 1 jadwal hari les wajib diisi.", "danger")
        return redirect(request.referrer or url_for("admin.schedules"))

    # Validasi: Siswa harus terdaftar aktif dalam program les yang dipilih
    enrolled = query_db(
        "SELECT id FROM student_programs WHERE student_id = ? AND program_id = ? AND status = 'aktif'",
        (student_id, program_id),
        one=True
    )
    if not enrolled:
        flash("Siswa yang dipilih belum terdaftar aktif dalam program les tersebut. Tambahkan program ke profil siswa terlebih dahulu.", "danger")
        return redirect(request.referrer or url_for("admin.schedules"))

    # Update paket pertemuan per periode jika dipilih saat membuat jadwal rutin
    mpp_input = request.form.get("meetings_per_period")
    if mpp_input:
        try:
            mpp_val = int(mpp_input)
            if mpp_val in (4, 8, 12):
                execute_db("UPDATE student_programs SET meetings_per_period = ? WHERE student_id = ? AND program_id = ?", (mpp_val, student_id, program_id))
                from services.meeting_service import resequence_student_program_attendances
                resequence_student_program_attendances(student_id, program_id)
        except (ValueError, TypeError):
            pass

    # Update riwayat awal belajar (khusus siswa lama) jika diisi saat membuat jadwal rutin
    init_period = request.form.get("initial_periods_completed")
    init_meeting = request.form.get("initial_last_meeting")
    init_notes = request.form.get("initial_offset_notes", "").strip()
    if init_period or init_meeting:
        try:
            p_val = max(1, int(init_period or 1))
            m_val = max(0, min(12, int(init_meeting or 0)))
            if p_val > 1 or m_val > 0:
                from services.meeting_service import calculate_total_from_period_and_meeting, resequence_student_program_attendances
                eff_mpp = mpp_val if ('mpp_val' in locals() and mpp_val in (4, 8, 12)) else 8
                tot_offset = calculate_total_from_period_and_meeting(p_val, m_val, eff_mpp)
                execute_db("""
                    UPDATE student_programs
                    SET initial_periods_completed = ?, initial_last_meeting = ?, initial_offset_total = ?,
                        initial_offset_notes = ?, initial_offset_set_at = CURRENT_TIMESTAMP, initial_offset_set_by = ?
                    WHERE student_id = ? AND program_id = ?
                """, (p_val, m_val, tot_offset, init_notes or "Riwayat awal saat penetapan jadwal", session["user_id"], student_id, program_id))
                execute_db("""
                    UPDATE students
                    SET initial_meeting_offset = ?, initial_offset_notes = ?,
                        initial_offset_set_at = CURRENT_TIMESTAMP, initial_offset_set_by = ?
                    WHERE id = ?
                """, (tot_offset, init_notes or "Riwayat awal saat penetapan jadwal", session["user_id"], student_id))
                resequence_student_program_attendances(student_id, program_id)
        except (ValueError, TypeError):
            pass

    slots_to_add = []
    conflict_errors = []

    for idx, d_raw in enumerate(days):
        if d_raw is None or d_raw == "":
            continue
        try:
            dow = int(d_raw)
        except (ValueError, TypeError):
            continue

        st = start_times[idx].strip() if idx < len(start_times) else ""
        et = end_times[idx].strip() if idx < len(end_times) else ""

        if not (st and et):
            flash(f"Jam mulai dan jam selesai untuk baris jadwal ke-{idx+1} wajib diisi.", "danger")
            return redirect(request.referrer or url_for("admin.schedules"))

        # Tentukan mentor untuk slot ini: jika ada slot_mentor_id spesifik, gunakan itu;
        # jika tidak, gunakan seluruh mentor_ids yang didaftarkan untuk program ini
        target_mentors = []
        if idx < len(slot_mentors) and slot_mentors[idx].strip():
            target_mentors = [slot_mentors[idx].strip()]
        else:
            target_mentors = mentor_ids

        # Cek bentrokan untuk setiap mentor pada slot ini
        for m_id in target_mentors:
            conflict = check_routine_schedule_conflict(m_id, dow, st, et, student_id=student_id, program_id=program_id)
            if conflict.get("has_conflict"):
                conflict_errors.append(conflict["message"])

        slots_to_add.append({
            "mentors": target_mentors,
            "day_of_week": dow,
            "start_time": st,
            "end_time": et
        })

    if conflict_errors:
        flash("Gagal menyimpan jadwal: " + " | ".join(conflict_errors), "danger")
        return redirect(request.referrer or url_for("admin.schedules"))

    if not slots_to_add:
        flash("Tidak ada jadwal valid yang dimasukkan.", "warning")
        return redirect(request.referrer or url_for("admin.schedules"))

    # Update primary mentor di student_programs jika belum ada
    if mentor_ids:
        execute_db(
            "UPDATE student_programs SET mentor_id = ? WHERE student_id = ? AND program_id = ? AND (mentor_id IS NULL OR mentor_id = '')",
            (mentor_ids[0], student_id, program_id)
        )

    # Simpan seluruh slot jadwal yang telah tervalidasi
    created_messages = []
    for s in slots_to_add:
        for m_id in s["mentors"]:
            res = create_routine_schedule(
                student_id, program_id, m_id,
                s["day_of_week"], s["start_time"], s["end_time"],
                subject_info, notes
            )
            if res["success"]:
                log_audit(session["user_id"], session["username"], "BUAT_JADWAL_RUTIN", "routine_schedules", res["id"], f"Membuat jadwal rutin ID {res['id']}")
        created_messages.append(f"Hari {DAY_NAMES[s['day_of_week']]} ({s['start_time']} - {s['end_time']})")

    flash(f"Berhasil menetapkan {len(created_messages)} jadwal les rutin: {', '.join(created_messages)}.", "success")
    return redirect(request.referrer or url_for("admin.schedules"))

@admin_bp.route("/schedules/routine/<int:routine_id>/edit", methods=["POST"])
def admin_edit_routine_schedule(routine_id):
    validate_csrf()
    day_of_week = request.form.get("day_of_week")
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()
    mentor_id = request.form.get("mentor_id")
    subject_info = request.form.get("subject_info", "").strip()
    notes = request.form.get("notes", "").strip()

    res = update_routine_schedule(routine_id, day_of_week, start_time, end_time, mentor_id, subject_info, notes)
    if res["success"]:
        flash(res["message"], "success")
        log_audit(session["user_id"], session["username"], "EDIT_JADWAL_RUTIN", "routine_schedules", routine_id, f"Memperbarui jadwal rutin ID {routine_id}")
    else:
        flash(res["message"], "danger")

    return redirect(request.referrer or url_for("admin.schedules"))

@admin_bp.route("/schedules/routine/<int:routine_id>/delete", methods=["POST"])
def admin_delete_routine_schedule(routine_id):
    validate_csrf()
    res = delete_routine_schedule(routine_id)
    if res["success"]:
        flash(res["message"], "info")
        log_audit(session["user_id"], session["username"], "HAPUS_JADWAL_RUTIN", "routine_schedules", routine_id, f"Menghapus jadwal rutin ID {routine_id}")
    else:
        flash(res["message"], "danger")

    return redirect(request.referrer or url_for("admin.schedules"))

@admin_bp.route("/schedules/create", methods=["POST"])
def create_schedule():
    validate_csrf()
    is_recurring = request.form.get("is_recurring") == "1"
    title = request.form.get("title", "").strip()
    program_id = request.form.get("program_id")
    student_id = request.form.get("student_id")
    mentor_id = request.form.get("mentor_id")
    start_time = request.form.get("start_time", "").strip()
    duration_minutes = int(request.form.get("duration_minutes", 90))
    session_notes = request.form.get("session_notes", "").strip()

    if not program_id or not student_id or not mentor_id or not start_time:
        flash("Program, siswa, mentor, dan jam mulai wajib diisi.", "danger")
        return redirect(url_for("admin.schedules"))

    # Pengecekan validasi: Siswa baru tidak boleh mulai belajar sebelum divalidasi pembayarannya oleh Pemilik
    st_check = query_db("SELECT full_name, status, payment_status FROM students WHERE id = ?", (student_id,), one=True)
    if st_check and (st_check["payment_status"] == "menunggu_validasi" or st_check["status"] == "menunggu_validasi"):
        flash(f"Pembelajaran belum dapat dimulai untuk {st_check['full_name']}. Siswa masih berstatus 'Menunggu Validasi Pembayaran oleh Pemilik'. Silakan tunggu validasi dari Pemilik terlebih dahulu.", "warning")
        return redirect(url_for("admin.schedules"))

    end_time = calculate_end_time(start_time, duration_minutes)

    if is_recurring:
        # Menambahkan jadwal rutin mingguan
        days_of_week = request.form.getlist("days_of_week")
        if not days_of_week:
            flash("Untuk jadwal rutin, pilih minimal satu hari belajar mingguan.", "danger")
            return redirect(url_for("admin.schedules"))

        added = 0
        conflicts = []
        for dow in days_of_week:
            try:
                d_int = int(dow)
            except ValueError:
                continue
            res_rs = create_routine_schedule(
                student_id=student_id,
                program_id=program_id,
                mentor_id=mentor_id,
                day_of_week=d_int,
                start_time=start_time,
                end_time=end_time,
                subject_info=title,
                notes=session_notes
            )
            if res_rs["success"]:
                added += 1
            else:
                conflicts.append(res_rs["message"])

        if added > 0:
            msg = f"{added} slot jadwal rutin berhasil ditetapkan."
            if conflicts:
                flash(f"{msg} Namun ada bentrokan: {'; '.join(conflicts)}", "warning")
            else:
                flash(msg, "success")
        else:
            flash(f"Gagal menetapkan jadwal rutin: {'; '.join(conflicts)}", "danger")

        return redirect(url_for("admin.schedules"))
    else:
        # Jadwal Satuan Langsung Fix
        schedule_date = request.form.get("schedule_date")
        if not schedule_date:
            flash("Tanggal jadwal wajib diisi.", "danger")
            return redirect(url_for("admin.schedules"))

        res = create_schedule_proposal(
            title, program_id, student_id, mentor_id, schedule_date,
            start_time, duration_minutes, session_notes, session["user_id"],
            status="disetujui" # Langsung fix disetujui
        )
        if res["success"]:
            flash("Jadwal sesi les fix berhasil diterbitkan dan langsung aktif.", "success")
        else:
            flash(res["message"], "danger")

    return redirect(url_for("admin.schedules"))

@admin_bp.route("/schedules/<int:schedule_id>/approve", methods=["POST"])
def admin_approve_schedule(schedule_id):
    validate_csrf()
    res = approve_schedule(schedule_id, session["user_id"])
    if res["success"]:
        flash(res["message"], "success")
    else:
        flash(res["message"], "danger")
    return redirect(url_for("admin.schedules"))

@admin_bp.route("/schedules/<int:schedule_id>/reject", methods=["POST"])
def admin_reject_schedule(schedule_id):
    validate_csrf()
    reason = request.form.get("reason", "").strip()
    execute_db("""
        UPDATE schedules
        SET status = 'ditolak', session_notes = COALESCE(session_notes, '') || ' [Ditolak Admin: ' || ? || ']',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (reason, schedule_id))
    log_audit(session["user_id"], session["username"], "TOLAK_JADWAL", "schedules", schedule_id, f"Menolak jadwal ID {schedule_id}. Alasan: {reason}")
    flash("Jadwal telah ditolak.", "info")
    return redirect(url_for("admin.schedules"))

@admin_bp.route("/schedules/<int:schedule_id>/student-confirmation", methods=["POST"])
def update_student_confirmation(schedule_id):
    validate_csrf()
    status_choice = request.form.get("confirmation_status") # 'bersedia' atau 'tidak_bisa'
    notes = request.form.get("notes", "").strip()

    schedule = query_db("SELECT * FROM schedules WHERE id = ?", (schedule_id,), one=True)
    if not schedule:
        flash("Jadwal tidak ditemukan.", "danger")
        return redirect(url_for("admin.schedules"))

    new_sched_status = schedule["status"]
    if status_choice == "bersedia" and schedule["status"] == "menunggu_konfirmasi_siswa":
        new_sched_status = "menunggu_persetujuan_admin"
    elif status_choice == "tidak_bisa":
        new_sched_status = "perlu_dijadwalkan_ulang"

    execute_db("""
        UPDATE schedules
        SET student_confirmation_status = ?,
            student_confirmation_notes = ?,
            status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status_choice, notes, new_sched_status, schedule_id))

    log_audit(session["user_id"], session["username"], "KONFIRMASI_SISWA", "schedules", schedule_id,
              f"Pencatatan konfirmasi siswa ID {schedule_id}: status={status_choice}, catatan={notes}")
    flash("Hasil koordinasi konfirmasi siswa/wali berhasil dicatat.", "success")
    return redirect(url_for("admin.schedules"))

@admin_bp.route("/schedules/<int:schedule_id>/replace-mentor", methods=["POST"])
def admin_replace_mentor(schedule_id):
    validate_csrf()
    replacement_mentor_id = request.form.get("replacement_mentor_id")
    reason = request.form.get("reason", "").strip()

    if not replacement_mentor_id or not reason:
        flash("Mentor pengganti dan alasan pergantian wajib diisi.", "danger")
        return redirect(url_for("admin.schedules"))

    res = execute_mentor_replacement(schedule_id, int(replacement_mentor_id), reason, session["user_id"])
    if res["success"]:
        flash(res["message"], "success")
    else:
        flash(res["message"], "danger")
    return redirect(url_for("admin.schedules"))

@admin_bp.route("/schedules/<int:schedule_id>/reschedule", methods=["POST"])
def admin_reschedule_schedule(schedule_id):
    """
    Penjadwalan ulang (reschedule) sesi sementara tanpa mengubah jadwal rutin mingguan.
    """
    validate_csrf()
    sched = query_db("""
        SELECT s.*, st.full_name as student_name, m.full_name as mentor_name
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN mentors m ON s.mentor_id = m.id
        WHERE s.id = ?
    """, (schedule_id,), one=True)
    if not sched:
        flash("Sesi jadwal tidak ditemukan.", "danger")
        return redirect(url_for("admin.schedules"))

    new_date = request.form.get("schedule_date", "").strip()
    new_start = request.form.get("start_time", "").strip()
    duration = int(sched["duration_minutes"] or 90)
    new_end = request.form.get("end_time", "").strip() or calculate_end_time(new_start, duration)
    reason = request.form.get("reason", "").strip()

    if not new_date or not new_start:
        flash("Tanggal baru dan jam mulai wajib diisi untuk reschedule.", "danger")
        return redirect(url_for("admin.schedules"))

    # Cek bentrokan jadwal untuk mentor dan siswa pada waktu baru
    conf = check_schedule_conflict(sched["mentor_id"], sched["student_id"], new_date, new_start, new_end, exclude_schedule_id=schedule_id)
    if conf["has_conflict"]:
        flash(f"Tidak dapat reschedule ke waktu tersebut: {conf['message']}", "danger")
        return redirect(url_for("admin.schedules"))

    old_date = sched["schedule_date"]
    old_time = f"{sched['start_time']} - {sched['end_time']}"
    reschedule_note = f"Reschedule sementara dari {old_date} ({old_time}). Alasan: {reason}" if reason else f"Reschedule sementara dari {old_date} ({old_time})"

    execute_db("""
        UPDATE schedules
        SET schedule_date = ?, start_time = ?, end_time = ?,
            session_notes = CASE WHEN session_notes IS NULL OR session_notes = '' THEN ? ELSE session_notes || ' | ' || ? END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_date, new_start, new_end, reschedule_note, reschedule_note, schedule_id))

    log_audit(
        session["user_id"], session["username"], "RESCHEDULE_SESI", "schedules", schedule_id,
        f"Reschedule sesi siswa {sched['student_name']} dari {old_date} ({old_time}) menjadi {new_date} ({new_start}-{new_end}). Alasan: {reason}",
        module_name="Jadwal & Sesi"
    )

    flash(f"Sesi bimbingan {sched['student_name']} berhasil di-reschedule sementara ke tanggal {new_date} pukul {new_start} - {new_end} WIB.", "success")
    return redirect(url_for("admin.schedules"))

@admin_bp.route("/routine-schedules/<int:routine_id>/assign-temporary-mentor", methods=["POST"])
def admin_assign_routine_temporary_mentor(routine_id):
    """
    Menugaskan mentor pengganti sementara untuk sesi tertentu dari jadwal rutin.
    Membuat rekaman sesi di schedules (jika belum ada) dan langsung mengganti mentornya.
    """
    validate_csrf()
    rs = query_db("""
        SELECT rs.*, st.full_name as student_name, pr.name as program_name, m.full_name as original_mentor_name
        FROM routine_schedules rs
        JOIN students st ON rs.student_id = st.id
        JOIN programs pr ON rs.program_id = pr.id
        JOIN mentors m ON rs.mentor_id = m.id
        WHERE rs.id = ?
    """, (routine_id,), one=True)
    if not rs:
        flash("Jadwal rutin tidak ditemukan.", "danger")
        return redirect(url_for("admin.schedules"))

    target_date = request.form.get("target_date", "").strip()
    replacement_mentor_id = request.form.get("replacement_mentor_id")
    reason = request.form.get("reason", "").strip()

    if not target_date or not replacement_mentor_id or not reason:
        flash("Tanggal sesi, mentor pengganti, dan alasan pergantian wajib diisi.", "danger")
        return redirect(url_for("admin.schedules"))

    # Cari apakah sudah ada schedule pada tanggal ini
    existing_sched = query_db("""
        SELECT id FROM schedules
        WHERE student_id = ? AND program_id = ? AND schedule_date = ?
    """, (rs["student_id"], rs["program_id"], target_date), one=True)

    if existing_sched:
        sched_id = existing_sched["id"]
    else:
        # Buat schedule untuk tanggal tersebut
        sched_id = execute_db("""
            INSERT INTO schedules (
                title, program_id, student_id, mentor_id,
                schedule_date, start_time, end_time, duration_minutes,
                status, student_confirmation_status, mentor_response_status,
                is_recurring, session_notes,
                created_by, approved_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 90, 'disetujui', 'bersedia', 'dikonfirmasi', 1, ?, ?, ?)
        """, (
            f"Sesi {rs['program_name']} - {rs['student_name']}",
            rs["program_id"], rs["student_id"], rs["mentor_id"],
            target_date, rs["start_time"], rs["end_time"],
            f"Penugasan mentor pengganti: {reason}",
            session["user_id"], session["user_id"]
        ))

    # Eksekusi penggantian mentor
    res = execute_mentor_replacement(sched_id, int(replacement_mentor_id), reason, session["user_id"])
    if res["success"]:
        flash(f"Berhasil menugaskan mentor pengganti untuk sesi {target_date}: {res['message']}", "success")
    else:
        flash(res["message"], "danger")
    return redirect(url_for("admin.schedules"))

# API deteksi bentrokan untuk frontend (fetch / AJAX)
@admin_bp.route("/api/check-conflict", methods=["POST"])
def api_check_conflict():
    data = request.get_json() or {}
    mentor_id = data.get("mentor_id")
    student_id = data.get("student_id")
    schedule_date = data.get("schedule_date")
    start_time = data.get("start_time")
    duration = data.get("duration", 90)
    exclude_id = data.get("exclude_schedule_id")

    if not (mentor_id and student_id and schedule_date and start_time):
        return jsonify({"has_conflict": False, "message": "Data tidak lengkap untuk deteksi bentrokan."})

    end_time = calculate_end_time(start_time, duration)
    conf = check_schedule_conflict(mentor_id, student_id, schedule_date, start_time, end_time, exclude_id)
    return jsonify(conf)

@admin_bp.route("/api/eligible-replacements/<int:schedule_id>")
def api_eligible_replacements(schedule_id):
    replacements = get_eligible_replacement_mentors(schedule_id)
    return jsonify(replacements)

# Sistem Rekomendasi Mentor (Langkah 4)
@admin_bp.route("/api/mentor-recommendations")
def api_mentor_recommendations():
    student_id = request.args.get("student_id")
    program_id = request.args.get("program_id")
    day_of_week = request.args.get("day_of_week")
    start_time = request.args.get("start_time", "").strip()
    end_time = request.args.get("end_time", "").strip()
    schedule_date = request.args.get("schedule_date", "").strip() or None

    if not (student_id and program_id and day_of_week is not None and start_time and end_time):
        return jsonify({
            "success": False,
            "message": "Parameter student_id, program_id, day_of_week, start_time, dan end_time wajib diisi."
        }), 400

    try:
        student_id_int = int(student_id)
        program_id_int = int(program_id)
        day_of_week_int = int(day_of_week)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Format parameter numerik tidak valid."}), 400

    from services.recommendation_service import get_mentor_recommendations
    res = get_mentor_recommendations(
        student_id=student_id_int,
        program_id=program_id_int,
        day_of_week=day_of_week_int,
        start_time=start_time,
        end_time=end_time,
        schedule_date=schedule_date
    )
    return jsonify(res)

# API Program yang Diambil Siswa (Untuk Filter Dinamis Penjadwalan Rutin)
@admin_bp.route("/api/students/<int:student_id>/programs")
def api_student_enrolled_programs(student_id):
    """Mengembalikan daftar program aktif yang diambil oleh siswa tertentu."""
    progs = query_db("""
        SELECT sp.id as student_program_id, pr.id, pr.name, pr.level, pr.code,
               sp.mentor_id, m.full_name as mentor_name,
               COALESCE(sp.meetings_per_period, 8) as meetings_per_period
        FROM student_programs sp
        JOIN programs pr ON sp.program_id = pr.id
        LEFT JOIN mentors m ON sp.mentor_id = m.id
        WHERE sp.student_id = ? AND sp.status = 'aktif'
        ORDER BY pr.name ASC
    """, (student_id,))
    return jsonify([dict(p) for p in progs])

# Pelengkapan Dokumentasi Foto Tertunda oleh Admin (Langkah 3)
@admin_bp.route("/attendance/<int:attendance_id>/complete-documentation", methods=["POST"])
def complete_documentation(attendance_id):
    validate_csrf()
    att = query_db("SELECT * FROM attendance WHERE id = ?", (attendance_id,), one=True)
    if not att:
        flash("Data absensi tidak ditemukan.", "danger")
        return redirect(request.referrer or url_for("admin.schedules"))

    if att["documentation_status"] != "menunggu":
        flash("Hanya sesi dengan status dokumentasi menunggu yang dapat dilengkapi.", "warning")
        return redirect(request.referrer or url_for("admin.schedules"))

    photo_file = request.files.get("session_photo")
    if not photo_file or not photo_file.filename:
        flash("Mohon pilih file foto dokumentasi yang valid.", "danger")
        return redirect(request.referrer or url_for("admin.schedules"))

    ext = photo_file.filename.rsplit(".", 1)[-1].lower() if "." in photo_file.filename else ""
    if ext not in ("jpg", "jpeg", "png", "webp"):
        flash("Format file foto tidak didukung. Mohon gunakan format JPG, PNG, atau WebP.", "danger")
        return redirect(request.referrer or url_for("admin.schedules"))

    photo_file.seek(0, os.SEEK_END)
    file_size = photo_file.tell()
    photo_file.seek(0)
    if file_size > 5 * 1024 * 1024:
        flash("Ukuran file foto melebihi batas 5MB. Silakan pilih foto dengan resolusi lebih kecil.", "danger")
        return redirect(request.referrer or url_for("admin.schedules"))

    upload_folder = os.path.join(current_app.root_path, "uploads", "session_photos")
    os.makedirs(upload_folder, exist_ok=True)
    saved_filename = f"session_{att['schedule_id']}_{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}"
    saved_file_path = os.path.join(upload_folder, saved_filename)

    try:
        photo_file.save(saved_file_path)
        execute_db("""
            UPDATE attendance
            SET documentation_status = 'lengkap',
                documentation_photo = ?,
                documentation_pending_reason = NULL
            WHERE id = ?
        """, (saved_filename, attendance_id))

        log_audit(
            session["user_id"], session["username"], "COMPLETE_SESSION_DOCUMENTATION",
            "attendance", attendance_id,
            f"Admin melengkapi dokumentasi foto sesi belajar tertunda untuk jadwal #{att['schedule_id']} (File: {saved_filename})",
            old_values={"documentation_status": "menunggu", "documentation_photo": None},
            new_values={"documentation_status": "lengkap", "documentation_photo": saved_filename}
        )
        flash("Foto dokumentasi belajar berhasil dilengkapi dan status diverifikasi LENGKAP.", "success")
    except Exception as e:
        if saved_file_path and os.path.exists(saved_file_path):
            try:
                os.remove(saved_file_path)
            except OSError:
                pass
        flash(f"Terjadi kesalahan saat menyimpan foto: {str(e)}", "danger")

    return redirect(request.referrer or url_for("admin.schedules"))

# ==========================================
# 8. BACKUP & RESTORE DATABASE
# ==========================================
@admin_bp.route("/backups")
def backups():
    backups_list = list_backups()
    return render_template("admin/backups.html", backups=backups_list)

@admin_bp.route("/backups/create", methods=["POST"])
def create_backup_route():
    validate_csrf()
    notes = request.form.get("notes", "Pencadangan manual dari dashboard Admin").strip()
    res = create_backup(created_by=session["username"], notes=notes)
    if res["success"]:
        flash(res["message"], "success")
    else:
        flash(f"Gagal membuat backup: {res.get('message')}", "danger")
    return redirect(url_for("admin.backups"))

@admin_bp.route("/backups/<int:backup_id>/restore", methods=["POST"])
def restore_backup_route():
    validate_csrf()
    confirm_text = request.form.get("confirm_text", "").strip()
    if confirm_text != "PULIHKAN":
        flash("Konfirmasi tidak sesuai. Harap ketik 'PULIHKAN' untuk menjalankan pemulihan database.", "danger")
        return redirect(url_for("admin.backups"))

    res = restore_backup(backup_id, requested_by=session["username"])
    if res["success"]:
        flash(res["message"], "success")
    else:
        flash(res["message"], "danger")
    return redirect(url_for("admin.backups"))

# ==========================================
# 9. AUDIT LOGS & LAPORAN
# ==========================================
@admin_bp.route("/audit-logs")
def audit_logs():
    action_type = request.args.get("action_type")
    target_entity = request.args.get("target_entity")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    logs = get_audit_logs(limit=200, action_type=action_type, target_entity=target_entity, start_date=start_date, end_date=end_date)
    return render_template(
        "admin/audit_logs.html",
        logs=logs,
        action_type=action_type,
        target_entity=target_entity,
        start_date=start_date,
        end_date=end_date
    )

@admin_bp.route("/reports")
def reports():
    report_type = request.args.get("type", "schedules")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    student_id = request.args.get("student_id")
    mentor_id = request.args.get("mentor_id")
    program_id = request.args.get("program_id")
    status = request.args.get("status")

    data = []
    if report_type == "schedules":
        data = get_schedules_report(start_date, end_date, student_id, mentor_id, program_id, status)
    elif report_type == "students":
        data = get_students_report(status, program_id)
    elif report_type == "mentors":
        data = get_mentors_report(status)
    elif report_type == "attendance":
        data = get_attendance_report(start_date, end_date, student_id, mentor_id)
    elif report_type == "progress":
        data = get_progress_report(student_id, mentor_id, program_id)
    elif report_type == "replacements":
        data = get_mentor_replacements_report()

    students_list = query_db("SELECT id, full_name FROM students ORDER BY full_name ASC")
    mentors_list = query_db("SELECT id, full_name FROM mentors ORDER BY full_name ASC")
    programs_list = query_db("SELECT id, name FROM programs ORDER BY name ASC")

    return render_template(
        "admin/reports.html",
        report_type=report_type,
        report_data=data,
        students=students_list,
        mentors=mentors_list,
        programs=programs_list,
        start_date=start_date,
        end_date=end_date,
        student_id=student_id,
        mentor_id=mentor_id,
        program_id=program_id,
        status=status
    )

@admin_bp.route("/reports/export")
def export_report_csv():
    report_type = request.args.get("type", "schedules")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    student_id = request.args.get("student_id")
    mentor_id = request.args.get("mentor_id")
    program_id = request.args.get("program_id")
    status = request.args.get("status")

    if report_type == "schedules":
        data = get_schedules_report(start_date, end_date, student_id, mentor_id, program_id, status)
        headers = ["ID", "Judul", "Tanggal", "Mulai", "Selesai", "Durasi (menit)", "Status", "Siswa", "Mentor", "Program", "Kehadiran"]
        key_map = [
            ("ID", "id"), ("Judul", "title"), ("Tanggal", "schedule_date"),
            ("Mulai", "start_time"), ("Selesai", "end_time"), ("Durasi", "duration_minutes"),
            ("Status", "status"), ("Siswa", "student_name"), ("Mentor", "mentor_name"),
            ("Program", "program_name"), ("Kehadiran", "attendance_status")
        ]
    elif report_type == "attendance":
        data = get_attendance_report(start_date, end_date, student_id, mentor_id)
        headers = ["ID", "Tanggal Sesi", "Waktu", "Siswa", "Mentor", "Program", "Status Kehadiran", "Waktu Dicatat", "Catatan"]
        key_map = [
            ("ID", "id"), ("Tanggal Sesi", "schedule_date"), ("Waktu", "start_time"),
            ("Siswa", "student_name"), ("Mentor", "mentor_name"), ("Program", "program_name"),
            ("Status", "attendance_status"), ("Dicatat", "recorded_at"), ("Catatan", "notes")
        ]
    elif report_type == "progress":
        data = get_progress_report(student_id, mentor_id, program_id)
        headers = ["ID", "Tanggal Sesi", "Siswa", "Mentor", "Program", "Materi Dipelajari", "Kemampuan Dikuasai", "Kesulitan", "Rekomendasi"]
        key_map = [
            ("ID", "id"), ("Tanggal", "session_date"), ("Siswa", "student_name"),
            ("Mentor", "mentor_name"), ("Program", "program_name"), ("Materi", "topics_covered"),
            ("Dikuasai", "skills_mastered"), ("Kesulitan", "difficulties"), ("Rekomendasi", "recommendations")
        ]
    elif report_type == "replacements":
        data = get_mentor_replacements_report()
        headers = ["ID", "Tanggal Sesi", "Siswa", "Mentor Awal", "Mentor Pengganti", "Alasan Pergantian", "Waktu Diubah", "Diubah Oleh"]
        key_map = [
            ("ID", "id"), ("Tanggal Sesi", "schedule_date"), ("Siswa", "student_name"),
            ("Mentor Awal", "original_mentor"), ("Mentor Pengganti", "replacement_mentor"),
            ("Alasan", "reason"), ("Waktu", "created_at"), ("Petugas", "changed_by_username")
        ]
    else:
        data = get_students_report(status, program_id)
        headers = ["ID", "Nama Lengkap", "Sekolah", "Tingkat/Kelas", "Nama Wali", "No. Telepon Wali", "Program Terdaftar", "Status"]
        key_map = [
            ("ID", "id"), ("Nama Lengkap", "full_name"), ("Sekolah", "school"),
            ("Kelas", "grade"), ("Wali", "parent_name"), ("Telepon", "parent_phone"),
            ("Program", "enrolled_programs"), ("Status", "status")
        ]

    csv_content = generate_csv_string(headers, data, key_map)
    filename = f"laporan_desi_privat_{report_type}_{datetime.now().strftime('%Y%m%d')}.csv"

    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==========================================
# 10. NOTIFIKASI & WHATSAPP CENTER
# ==========================================
@admin_bp.route("/notifications")
def notifications_center():
    notifs = get_user_notifications(session["user_id"], limit=50)
    delivery_logs = get_delivery_logs(limit=30)
    return render_template("admin/notifications.html", notifications=notifs, delivery_logs=delivery_logs)

@admin_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
def read_notification(notification_id):
    validate_csrf()
    mark_as_read(notification_id, session["user_id"])
    return jsonify({"success": True})

@admin_bp.route("/notifications/mark-all-read", methods=["POST"])
def read_all_notifications():
    validate_csrf()
    mark_all_as_read(session["user_id"])
    flash("Semua notifikasi telah ditandai sebagai dibaca.", "info")
    return redirect(url_for("admin.notifications_center"))

@admin_bp.route("/notifications/test-whatsapp", methods=["POST"])
def test_whatsapp_send():
    validate_csrf()
    phone = request.form.get("phone", "").strip()
    message = request.form.get("message", "").strip()
    scenario = request.form.get("scenario", "custom")

    if scenario != "custom":
        res = run_test_scenario(scenario, phone=phone, custom_msg=message if message else None)
    else:
        if not phone or not message:
            flash("Nomor telepon tujuan dan isi pesan wajib diisi untuk uji pesan kustom.", "danger")
            return redirect(url_for("admin.notifications_center"))
        res = send_whatsapp_message(phone, message, template_name="pengujian_kustom_admin")

    if res["success"]:
        status_txt = "Simulasi Berhasil (WhatsApp Test Mode)" if res["status"] == "simulasi" else "Berhasil Terkirim via Cloud API"
        flash(f"[{status_txt}] {res['message']}", "success" if res["status"] == "sukses" else "info")
    else:
        flash(f"[Gagal Kirim WhatsApp] {res['message']}", "danger")

    return redirect(url_for("admin.notifications_center"))

# ==========================================
# 11. TAGIHAN, PEMBAYARAN, & KUITANSI SISWA
# ==========================================
@admin_bp.route("/bills")
def bills():
    # Admin dan Pemilik memiliki akses pengelolaan tagihan dan pencatatan cicilan
    from services.finance_service import get_billing_alerts_summary, get_pending_new_students
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
    overview = get_financial_overview()
    billing_alerts = get_billing_alerts_summary()
    pending_new_students = get_pending_new_students()
    students_list = query_db("SELECT id, full_name FROM students WHERE status != 'berhenti' ORDER BY full_name ASC")
    programs_list = query_db("SELECT id, name FROM programs WHERE status = 'aktif' ORDER BY name ASC")

    return render_template(
        "admin/bills.html",
        bills=bills_list,
        overview=overview,
        billing_alerts=billing_alerts,
        pending_new_students=pending_new_students,
        students=students_list,
        programs=programs_list,
        status_filter=status_filter,
        student_filter=student_filter,
        program_filter=program_filter,
        search=search
    )

@admin_bp.route("/bills/create", methods=["POST"])
def create_bill():
    validate_csrf()
    student_id = request.form.get("student_id")
    program_id = request.form.get("program_id")
    period_number = request.form.get("period_number", 1)
    title = request.form.get("title", "").strip()
    total_amount = request.form.get("total_amount", 0)
    due_date = request.form.get("due_date", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    if not student_id or not program_id or not title or not total_amount:
        flash("Siswa, program, judul tagihan, dan nominal wajib diisi.", "danger")
        return redirect(url_for("admin.bills"))

    try:
        bill_id = create_student_bill(
            student_id=student_id,
            program_id=program_id,
            period_number=period_number,
            title=title,
            total_amount=total_amount,
            due_date=due_date,
            notes=notes
        )
        st = query_db("SELECT full_name FROM students WHERE id = ?", (student_id,), one=True)
        st_name = st["full_name"] if st else f"ID {student_id}"
        log_audit(session["user_id"], session["username"], "BUAT_TAGIHAN", "student_bills", bill_id,
                  f"Membuat tagihan {title} untuk siswa {st_name} (Rp {float(total_amount):,.0f})")
        flash(f"Tagihan untuk siswa {st_name} berhasil dibuat.", "success")
    except Exception as e:
        flash(f"Gagal membuat tagihan: {e}", "danger")

    return redirect(url_for("admin.bills"))

@admin_bp.route("/bills/<int:bill_id>/pay", methods=["POST"])
def pay_bill(bill_id):
    validate_csrf()
    amount = request.form.get("amount", 0)
    payment_date = request.form.get("payment_date", date.today().strftime("%Y-%m-%d"))
    payment_method = request.form.get("payment_method", "Transfer Bank")
    notes = request.form.get("notes", "").strip() or None

    try:
        payment_id, receipt_num = record_bill_payment(
            bill_id=bill_id,
            amount=amount,
            payment_date=payment_date,
            payment_method=payment_method,
            recorded_by=session["user_id"],
            notes=notes
        )
        bill, _ = get_student_bill_detail(bill_id)
        log_audit(session["user_id"], session["username"], "BAYAR_TAGIHAN", "bill_payments", payment_id,
                  f"Mencatat pembayaran Rp {float(amount):,.0f} untuk tagihan {bill['bill_code']} (Kuitansi: {receipt_num})")
        flash(f"Pembayaran sebesar Rp {float(amount):,.0f} berhasil dicatat. Nomor Kuitansi: {receipt_num}", "success")
    except Exception as e:
        flash(f"Gagal mencatat pembayaran: {e}", "danger")

    return redirect(url_for("admin.bills"))

@admin_bp.route("/payments")
def payments():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    student_id = request.args.get("student_id")
    bill_id = request.args.get("bill_id")

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
        selected_bill=selected_bill
    )

@admin_bp.route("/payments/<int:payment_id>/correct", methods=["POST"])
def admin_correct_payment(payment_id):
    validate_csrf()
    new_amount = request.form.get("new_amount")
    reason = request.form.get("reason", "").strip()

    if not new_amount or not reason:
        flash("Nominal baru dan alasan koreksi wajib diisi.", "danger")
        return redirect(request.referrer or url_for("admin.payments"))

    from services.finance_service import correct_bill_payment
    res = correct_bill_payment(payment_id, new_amount, reason=reason, user_id=session["user_id"])
    if res["success"]:
        flash(res["message"], "success")
    else:
        flash(res["message"], "danger")
    return redirect(request.referrer or url_for("admin.payments"))

@admin_bp.route("/payments/<int:payment_id>/cancel", methods=["POST"])
def admin_cancel_payment(payment_id):
    validate_csrf()
    reason = request.form.get("reason", "").strip()

    if not reason:
        flash("Alasan pembatalan pembayaran wajib diisi.", "danger")
        return redirect(request.referrer or url_for("admin.payments"))

    from services.finance_service import cancel_bill_payment
    res = cancel_bill_payment(payment_id, reason=reason, user_id=session["user_id"])
    if res["success"]:
        flash(res["message"], "success")
    else:
        flash(res["message"], "danger")
    return redirect(request.referrer or url_for("admin.payments"))

@admin_bp.route("/receipts/<int:payment_id>/print")
def print_receipt(payment_id):
    receipt = get_bill_payment_receipt(payment_id)
    if not receipt:
        flash("Kuitansi pembayaran tidak ditemukan.", "danger")
        return redirect(url_for("admin.bills"))

    return render_template("admin/receipt_print.html", receipt=receipt)

# ==========================================
# 12. MONITORING & REKAP HONOR MENTOR
# ==========================================
@admin_bp.route("/mentor-honor")
def mentor_honor():
    if session.get("role") != "owner":
        flash("Halaman Rekap Honor Mentor hanya dapat diakses oleh akun Pemilik (Owner).", "warning")
        return redirect(url_for("admin.dashboard"))
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    mentor_id = request.args.get("mentor_id")
    rate_per_session = request.args.get("rate_per_session")

    honor_list = get_mentor_honor_summary(
        mentor_id=mentor_id,
        start_date=start_date,
        end_date=end_date,
        rate_per_session=rate_per_session
    )
    mentors_list = query_db("SELECT id, full_name FROM mentors ORDER BY full_name ASC")

    return render_template(
        "admin/mentor_honor.html",
        honor_list=honor_list,
        mentors=mentors_list,
        mentor_id=mentor_id,
        start_date=start_date,
        end_date=end_date,
        rate_per_session=rate_per_session
    )
