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
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify, Response
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
    get_student_meeting_stats, set_student_initial_history,
    resequence_student_attendances
)
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
    today_str = date.today().strftime("%Y-%m-%d")

    today_schedules_list = query_db("""
        SELECT s.id, s.title, s.start_time, s.end_time, s.status, s.mentor_response_status,
               st.full_name as student_name, m.full_name as mentor_name, pr.name as program_name
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN mentors m ON s.mentor_id = m.id
        JOIN programs pr ON s.program_id = pr.id
        WHERE s.schedule_date = ?
        ORDER BY s.start_time ASC
    """, (today_str,))

    # Jadwal yang butuh tindakan (menunggu persetujuan atau perlu pengganti)
    action_required_schedules = query_db("""
        SELECT s.id, s.title, s.schedule_date, s.start_time, s.status, s.mentor_response_status,
               s.mentor_response_notes, st.full_name as student_name, m.full_name as mentor_name,
               pr.name as program_name
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN mentors m ON s.mentor_id = m.id
        JOIN programs pr ON s.program_id = pr.id
        WHERE s.status IN ('menunggu_persetujuan_admin', 'menunggu_konfirmasi_siswa')
           OR s.mentor_response_status = 'perlu_mentor_pengganti'
        ORDER BY s.schedule_date ASC
        LIMIT 10
    """)

    recent_audits = get_audit_logs(limit=5)

    return render_template(
        "admin/dashboard.html",
        summary=summary,
        overdue_responses=overdue_responses,
        recent_notifs=recent_notifs,
        recent_audits=recent_audits,
        today_schedules=today_schedules_list,
        action_schedules=action_required_schedules
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
    mentor_id = request.form.get("mentor_id")
    subject_info = request.form.get("subject_info", "").strip()
    
    # 1. Buat data orang tua baru jika diisi di formulir
    if new_parent_name and new_parent_phone:
        parent_id = execute_db("""
            INSERT INTO parents (full_name, phone, address, notes)
            VALUES (?, ?, ?, 'Didaftarkan bersamaan dengan siswa baru')
        """, (new_parent_name, new_parent_phone, address))

    if not parent_id or not full_name:
        flash("Nama lengkap siswa dan data orang tua/wali murid wajib diisi.", "danger")
        return redirect(url_for("admin.students"))

    try:
        initial_offset = max(0, int(request.form.get("initial_meeting_offset", 0)))
    except (TypeError, ValueError):
        initial_offset = 0

    student_id = execute_db("""
        INSERT INTO students (
            parent_id, full_name, school, grade, birth_date, address, notes, status,
            initial_meeting_offset, initial_offset_notes, initial_offset_set_at, initial_offset_set_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'aktif', ?, 'Baseline pendaftaran awal', CURRENT_TIMESTAMP, ?)
    """, (parent_id, full_name, school, grade, birth_date, address, notes, initial_offset, session["user_id"]))

    if program_id:
        execute_db("""
            INSERT INTO student_programs (student_id, program_id, mentor_id, start_date, notes, status)
            VALUES (?, ?, ?, date('now'), ?, 'aktif')
        """, (student_id, program_id, mentor_id if mentor_id else None, subject_info))

    log_audit(session["user_id"], session["username"], "TAMBAH_SISWA", "students", student_id, f"Menambahkan siswa baru: {full_name}")

    # 2. Pengaturan Jadwal Rutin Mingguan Siswa (Dapat lebih dari 1 hari dengan jam berbeda)
    routine_days = request.form.getlist("routine_day[]")
    routine_starts = request.form.getlist("routine_start[]")
    routine_ends = request.form.getlist("routine_end[]")

    # Fallback jika formulir menggunakan format checkbox hari
    if not routine_days:
        cb_days = request.form.getlist("recurring_days")
        st_time = request.form.get("schedule_start_time", "16:00").strip() or "16:00"
        dur = int(request.form.get("schedule_duration", 90))
        ed_time = calculate_end_time(st_time, dur)
        for d in cb_days:
            routine_days.append(d)
            routine_starts.append(st_time)
            routine_ends.append(ed_time)

    slots_added = 0
    conflict_warnings = []

    if program_id and mentor_id and routine_days:
        for idx_slot, r_day in enumerate(routine_days):
            try:
                dow = int(r_day)
            except (TypeError, ValueError):
                continue
            r_start = routine_starts[idx_slot].strip() if idx_slot < len(routine_starts) else "16:00"
            r_end = routine_ends[idx_slot].strip() if idx_slot < len(routine_ends) else calculate_end_time(r_start, 90)

            # Cek bentrokan jadwal rutin mentor
            conflict = check_routine_schedule_conflict(mentor_id, dow, r_start, r_end, student_id=student_id)
            if conflict["has_conflict"]:
                conflict_warnings.append(conflict["message"])
            else:
                res_rs = create_routine_schedule(
                    student_id=student_id,
                    program_id=program_id,
                    mentor_id=mentor_id,
                    day_of_week=dow,
                    start_time=r_start,
                    end_time=r_end,
                    subject_info=subject_info,
                    notes=notes or "Jadwal rutin mingguan pendaftaran siswa"
                )
                if res_rs["success"]:
                    slots_added += 1

    success_msg = f"Siswa {full_name} berhasil didaftarkan."
    if slots_added > 0:
        success_msg += f" {slots_added} slot jadwal rutin mingguan berhasil ditetapkan dan langsung aktif."
    if conflict_warnings:
        flash(f"{success_msg} Peringatan bentrokan jadwal: {'; '.join(conflict_warnings)}", "warning")
    else:
        flash(success_msg, "success")

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

    # Program yang diikuti
    programs = query_db("""
        SELECT sp.*, pr.name as program_name, m.full_name as mentor_name
        FROM student_programs sp
        JOIN programs pr ON sp.program_id = pr.id
        LEFT JOIN mentors m ON sp.mentor_id = m.id
        WHERE sp.student_id = ?
        ORDER BY sp.created_at DESC
    """, (student_id,))

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
        SELECT sp.*, m.full_name as mentor_name, pr.name as program_name
        FROM student_progress sp
        JOIN mentors m ON sp.mentor_id = m.id
        JOIN programs pr ON sp.program_id = pr.id
        WHERE sp.student_id = ?
        ORDER BY sp.session_date DESC
        LIMIT 30
    """, (student_id,))

    meeting_stats = get_student_meeting_stats(student_id)
    routine_schedules = get_routine_schedules(student_id=student_id)
    parents_list = query_db("SELECT id, full_name FROM parents ORDER BY full_name ASC")
    all_programs = query_db("SELECT id, name, code, level FROM programs WHERE status = 'aktif' ORDER BY name ASC")
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
    parent_id = request.form.get("parent_id")
    full_name = request.form.get("full_name", "").strip()
    school = request.form.get("school", "").strip()
    grade = request.form.get("grade", "").strip()
    birth_date = request.form.get("birth_date", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    status = request.form.get("status", "aktif")

    execute_db("""
        UPDATE students
        SET parent_id = ?, full_name = ?, school = ?, grade = ?, birth_date = ?,
            address = ?, notes = ?, status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (parent_id, full_name, school, grade, birth_date, address, notes, status, student_id))

    log_audit(session["user_id"], session["username"], "UBAH_SISWA", "students", student_id, f"Mengubah data siswa ID {student_id} ({full_name})")
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

@admin_bp.route("/students/<int:student_id>/programs/add", methods=["POST"])
def add_student_program(student_id):
    validate_csrf()
    student = query_db("SELECT id, full_name FROM students WHERE id = ?", (student_id,), one=True)
    if not student:
        flash("Siswa tidak ditemukan.", "danger")
        return redirect(url_for("admin.students"))

    program_id = request.form.get("program_id")
    mentor_id = request.form.get("mentor_id") or None
    start_date = request.form.get("start_date") or None
    notes = request.form.get("notes", "").strip()

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

    execute_db("""
        INSERT INTO student_programs (student_id, program_id, mentor_id, start_date, status, notes)
        VALUES (?, ?, ?, COALESCE(?, date('now')), 'aktif', ?)
    """, (student_id, program_id, mentor_id, start_date, notes))

    p = query_db("SELECT name FROM programs WHERE id = ?", (program_id,), one=True)
    p_name = p["name"] if p else f"ID {program_id}"
    log_audit(session["user_id"], session["username"], "TAMBAH_PROGRAM_SISWA", "student_programs", student_id, f"Mendaftarkan program {p_name} ke siswa {student['full_name']}")
    flash(f"Program les {p_name} berhasil didaftarkan untuk siswa {student['full_name']}.", "success")
    return redirect(url_for("admin.student_detail", student_id=student_id))

@admin_bp.route("/students/<int:student_id>/programs/<int:sp_id>/edit", methods=["POST"])
def edit_student_program(student_id, sp_id):
    validate_csrf()
    student = query_db("SELECT id, full_name FROM students WHERE id = ?", (student_id,), one=True)
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

    execute_db("""
        UPDATE student_programs
        SET program_id = ?, mentor_id = ?, status = ?, start_date = ?, end_date = ?, notes = ?
        WHERE id = ? AND student_id = ?
    """, (program_id, mentor_id, status, start_date, end_date, notes, sp_id, student_id))

    p = query_db("SELECT name FROM programs WHERE id = ?", (program_id,), one=True)
    p_name = p["name"] if p else f"ID {program_id}"
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
               COUNT(s.id) as children_count,
               GROUP_CONCAT(s.full_name, ', ') as children_names
        FROM parents p
        LEFT JOIN students s ON p.id = s.parent_id
    """
    conditions = []
    args = []
    if status_filter:
        conditions.append("p.status = ?")
        args.append(status_filter)
    if search:
        conditions.append("(p.full_name LIKE ? OR p.phone LIKE ? OR p.email LIKE ?)")
        term = f"%{search}%"
        args.extend([term, term, term])

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

    if not full_name or not phone:
        flash("Nama lengkap dan nomor telepon wali wajib diisi.", "danger")
        return redirect(url_for("admin.parents"))

    # Orang Tua/Wali tidak lagi memiliki akun login, data disimpan sebagai relasi wali
    parent_id = execute_db("""
        INSERT INTO parents (full_name, phone, email, address, notes, status)
        VALUES (?, ?, ?, ?, ?, 'aktif')
    """, (full_name, phone, email, address, notes))

    log_audit(session["user_id"], session["username"], "TAMBAH_WALI", "parents", parent_id, f"Menambahkan wali murid baru: {full_name}")
    flash(f"Data wali {full_name} berhasil disimpan.", "success")
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
    expertise = request.form.get("expertise", "").strip()
    bio = request.form.get("bio", "").strip()
    create_account = request.form.get("create_account")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

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
        INSERT INTO mentors (user_id, full_name, phone, email, expertise, bio, status)
        VALUES (?, ?, ?, ?, ?, ?, 'aktif')
    """, (user_id, full_name, phone, email, expertise, bio))

    log_audit(session["user_id"], session["username"], "TAMBAH_MENTOR", "mentors", mentor_id, f"Menambahkan mentor baru: {full_name}")
    flash(f"Mentor {full_name} berhasil ditambahkan.", "success")
    return redirect(url_for("admin.mentors"))

@admin_bp.route("/mentors/<int:mentor_id>/edit", methods=["POST"])
def edit_mentor(mentor_id):
    validate_csrf()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    expertise = request.form.get("expertise", "").strip()
    bio = request.form.get("bio", "").strip()
    status = request.form.get("status", "aktif")

    execute_db("""
        UPDATE mentors
        SET full_name = ?, phone = ?, email = ?, expertise = ?, bio = ?, status = ?
        WHERE id = ?
    """, (full_name, phone, email, expertise, bio, status, mentor_id))

    # Perbarui data user jika ada
    m = query_db("SELECT user_id FROM mentors WHERE id = ?", (mentor_id,), one=True)
    if m and m["user_id"]:
        execute_db("UPDATE users SET full_name = ?, phone = ?, email = ?, is_active = ? WHERE id = ?",
                   (full_name, phone, email, 1 if status == 'aktif' else 0, m["user_id"]))

    log_audit(session["user_id"], session["username"], "UBAH_MENTOR", "mentors", mentor_id, f"Mengubah data mentor ID {mentor_id} ({full_name})")
    flash(f"Data mentor {full_name} berhasil diperbarui.", "success")
    return redirect(url_for("admin.mentors"))

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
    level = request.form.get("level", "").strip()

    if not name or not code:
        flash("Nama dan kode program wajib diisi.", "danger")
        return redirect(url_for("admin.programs"))

    existing = query_db("SELECT id FROM programs WHERE code = ?", (code,), one=True)
    if existing:
        flash(f"Kode program '{code}' sudah digunakan. Gunakan kode unik lain.", "danger")
        return redirect(url_for("admin.programs"))

    program_id = execute_db("""
        INSERT INTO programs (name, code, description, level, status)
        VALUES (?, ?, ?, ?, 'aktif')
    """, (name, code, description, level))

    log_audit(session["user_id"], session["username"], "TAMBAH_PROGRAM", "programs", program_id, f"Menambahkan program les: {name} ({code})")
    flash(f"Program {name} berhasil dibuat.", "success")
    return redirect(url_for("admin.programs"))

@admin_bp.route("/programs/<int:program_id>/edit", methods=["POST"])
def edit_program(program_id):
    validate_csrf()
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    level = request.form.get("level", "").strip()
    status = request.form.get("status", "aktif")

    execute_db("""
        UPDATE programs
        SET name = ?, description = ?, level = ?, status = ?
        WHERE id = ?
    """, (name, description, level, status, program_id))

    log_audit(session["user_id"], session["username"], "UBAH_PROGRAM", "programs", program_id, f"Mengubah program les ID {program_id} ({name})")
    flash(f"Program {name} berhasil diperbarui.", "success")
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

    if role not in ("admin", "owner", "mentor"):
        flash("Role yang dipilih tidak valid. Peran Orang Tua/Wali tidak lagi memiliki akses akun login.", "danger")
        return redirect(url_for("admin.accounts"))

    existing = query_db("SELECT id FROM users WHERE username = ?", (username,), one=True)
    if existing:
        flash(f"ID Pengguna / Username '{username}' sudah digunakan. Cegah duplikasi ID pengguna.", "danger")
        return redirect(url_for("admin.accounts"))

    user_id = execute_db("""
        INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (username, generate_password_hash(password), role, full_name, email, phone))

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
    mentor_id = request.form.get("mentor_id")
    day_of_week = request.form.get("day_of_week")
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()
    subject_info = request.form.get("subject_info", "").strip()
    notes = request.form.get("notes", "").strip()

    if not (student_id and program_id and mentor_id and day_of_week is not None and start_time and end_time):
        flash("Semua informasi jadwal rutin (siswa, program, mentor, hari, jam mulai & selesai) wajib diisi.", "danger")
        return redirect(request.referrer or url_for("admin.schedules"))

    res = create_routine_schedule(student_id, program_id, mentor_id, day_of_week, start_time, end_time, subject_info, notes)
    if res["success"]:
        flash(res["message"], "success")
        log_audit(session["user_id"], session["username"], "BUAT_JADWAL_RUTIN", "routine_schedules", res["id"], f"Membuat jadwal rutin ID {res['id']}")
    else:
        flash(res["message"], "danger")

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
