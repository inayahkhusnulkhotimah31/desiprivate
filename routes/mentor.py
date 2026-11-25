"""
DESI PRIVAT - Mentor Routes & Controller
Dashboard Mentor:
- Melihat ringkasan jadwal mengajar
- Kalender dan ketersediaan waktu
- Mengusulkan jadwal untuk siswa yang diajar (dengan deteksi bentrokan otomatis)
- Mengonfirmasi jadwal atau menolak dengan alasan wajib
- Melihat daftar siswa bimbingan dalam mode baca
- Mengisi absensi sesi les (mencegah duplikasi ganda)
- Mengisi dan melihat riwayat laporan perkembangan siswa
"""
from datetime import datetime, date
import os
import uuid
import time
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify, abort, current_app
)
from routes.auth import login_required, role_required, validate_csrf
from services.database_service import query_db, execute_db
from services.audit_service import log_audit
from services.notification_service import create_notification, get_user_notifications
from services.schedule_service import (
    check_schedule_conflict, create_schedule_proposal, generate_recurring_schedules,
    mentor_respond_schedule, calculate_end_time,
    get_routine_schedules, get_mentor_today_routine, DAY_NAMES
)
from services.meeting_service import (
    record_or_update_attendance, get_student_meeting_stats, get_student_program_meeting_stats,
    calculate_period_and_meeting
)
from services.finance_service import sync_and_get_mentor_period_honors

mentor_bp = Blueprint("mentor", __name__, url_prefix="/mentor")

@mentor_bp.before_request
@login_required
@role_required("mentor")
def check_mentor_access():
    pass

def get_current_mentor_id():
    """Mengambil ID rekaman mentor berdasarkan user_id dalam session."""
    user_id = session.get("user_id")
    row = query_db("SELECT id FROM mentors WHERE user_id = ?", (user_id,), one=True)
    if not row:
        abort(403, description="Data profil mentor Anda tidak ditemukan di sistem.")
    return row["id"]

@mentor_bp.route("/dashboard")
def dashboard():
    mentor_id = get_current_mentor_id()
    today_str = date.today().strftime("%Y-%m-%d")

    # Jadwal hari ini
    today_schedules = query_db("""
        SELECT s.*, st.full_name as student_name, pr.name as program_name,
               att.status as attendance_status, sp.id as progress_id
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN programs pr ON s.program_id = pr.id
        LEFT JOIN attendance att ON s.id = att.schedule_id
        LEFT JOIN student_progress sp ON s.id = sp.schedule_id
        WHERE s.mentor_id = ? AND s.schedule_date = ?
        ORDER BY s.start_time ASC
    """, (mentor_id, today_str))

    # Jadwal yang memerlukan konfirmasi mentor
    pending_confirmations = query_db("""
        SELECT s.*, st.full_name as student_name, pr.name as program_name
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN programs pr ON s.program_id = pr.id
        WHERE s.mentor_id = ?
          AND s.status = 'disetujui'
          AND s.mentor_response_status = 'menunggu_konfirmasi'
        ORDER BY s.schedule_date ASC
    """, (mentor_id,))

    # Statistik ringkas mentor
    total_assigned_students = query_db("""
        SELECT COUNT(DISTINCT st.id) as c
        FROM students st
        JOIN student_programs sp ON st.id = sp.student_id AND sp.status = 'aktif'
        LEFT JOIN routine_schedules rs ON st.id = rs.student_id AND sp.program_id = rs.program_id AND rs.status = 'aktif'
        WHERE (sp.mentor_id = ? OR rs.mentor_id = ?) AND st.status = 'aktif'
    """, (mentor_id, mentor_id), one=True)["c"]

    total_sessions_taught = query_db("""
        SELECT COUNT(*) as c
        FROM attendance
        WHERE mentor_id = ?
    """, (mentor_id,), one=True)["c"]

    active_schedules_count = query_db("""
        SELECT COUNT(*) as c
        FROM schedules
        WHERE mentor_id = ? AND status = 'disetujui' AND schedule_date >= ?
    """, (mentor_id, today_str), one=True)["c"]

    # Jadwal mendatang
    upcoming_schedules = query_db("""
        SELECT s.*, st.full_name as student_name, pr.name as program_name,
               att.status as attendance_status
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN programs pr ON s.program_id = pr.id
        LEFT JOIN attendance att ON s.id = att.schedule_id
        WHERE s.mentor_id = ? AND s.schedule_date > ? AND s.status = 'disetujui'
        ORDER BY s.schedule_date ASC, s.start_time ASC
        LIMIT 5
    """, (mentor_id, today_str))

    # Siswa bimbingan mentor ini (bisa melalui penugasan utama maupun co-mentor jadwal rutin)
    raw_students = query_db("""
        SELECT DISTINCT st.id, st.full_name, st.grade, st.school, pr.id as program_id, pr.name as program_name
        FROM students st
        JOIN student_programs sp ON st.id = sp.student_id AND sp.status = 'aktif'
        JOIN programs pr ON sp.program_id = pr.id
        LEFT JOIN routine_schedules rs ON st.id = rs.student_id AND pr.id = rs.program_id AND rs.status = 'aktif'
        WHERE (sp.mentor_id = ? OR rs.mentor_id = ?) AND st.status = 'aktif'
        LIMIT 6
    """, (mentor_id, mentor_id))
    assigned_students = []
    for st in raw_students:
        s_d = dict(st)
        s_d["meeting_stats"] = get_student_program_meeting_stats(st["id"], st["program_id"])
        assigned_students.append(s_d)

    # Riwayat pertemuan terbaru
    recent_history = query_db("""
        SELECT a.*, s.schedule_date, st.full_name as student_name, pr.name as program_name
        FROM attendance a
        JOIN schedules s ON a.schedule_id = s.id
        JOIN students st ON a.student_id = st.id
        JOIN programs pr ON s.program_id = pr.id
        WHERE a.mentor_id = ?
        ORDER BY a.recorded_at DESC
        LIMIT 5
    """, (mentor_id,))

    recent_notifs = get_user_notifications(session["user_id"], limit=5)
    today_routines = get_mentor_today_routine(mentor_id)
    routine_schedules = get_routine_schedules(mentor_id=mentor_id)

    return render_template(
        "mentor/dashboard.html",
        today_schedules=today_schedules,
        today_routines=today_routines,
        routine_schedules=routine_schedules,
        upcoming_schedules=upcoming_schedules,
        assigned_students=assigned_students,
        recent_history=recent_history,
        pending_confirmations=pending_confirmations,
        total_students=total_assigned_students,
        total_sessions=total_sessions_taught,
        active_schedules_count=len(routine_schedules),
        recent_notifs=recent_notifs,
        day_names=DAY_NAMES
    )

@mentor_bp.route("/schedules")
def schedules():
    mentor_id = get_current_mentor_id()
    date_filter = request.args.get("date")
    status_filter = request.args.get("status")

    conditions = ["s.mentor_id = ?"]
    args = [mentor_id]

    if date_filter:
        conditions.append("s.schedule_date = ?")
        args.append(date_filter)
    if status_filter:
        conditions.append("s.status = ?")
        args.append(status_filter)

    query = f"""
        SELECT s.*, st.full_name as student_name, pr.name as program_name,
               att.id as attendance_id, att.status as attendance_status,
               prog.id as progress_id
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN programs pr ON s.program_id = pr.id
        LEFT JOIN attendance att ON s.id = att.schedule_id
        LEFT JOIN student_progress prog ON s.id = prog.schedule_id
        WHERE {' AND '.join(conditions)}
        ORDER BY s.schedule_date DESC, s.start_time DESC
    """
    schedules_list = query_db(query, args)

    # Siswa dan program yang diajar mentor ini (untuk usulan jadwal baru)
    # Mencakup penugasan di student_programs, routine_schedules, maupun schedules langsung
    my_students = query_db("""
        SELECT DISTINCT s.id as student_id, s.full_name as student_name,
                        p.id as program_id, p.name as program_name
        FROM students s
        JOIN student_programs sp ON s.id = sp.student_id AND sp.status = 'aktif'
        JOIN programs p ON sp.program_id = p.id
        LEFT JOIN routine_schedules rs ON s.id = rs.student_id AND p.id = rs.program_id AND rs.status = 'aktif'
        LEFT JOIN schedules sc ON s.id = sc.student_id AND p.id = sc.program_id
        WHERE (sp.mentor_id = ? OR rs.mentor_id = ? OR sc.mentor_id = ?) AND s.status = 'aktif'
        ORDER BY s.full_name ASC
    """, (mentor_id, mentor_id, mentor_id))

    routine_schedules = get_routine_schedules(mentor_id=mentor_id)

    pending_confirmations = query_db("""
        SELECT s.*, st.full_name as student_name, pr.name as program_name
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN programs pr ON s.program_id = pr.id
        WHERE s.mentor_id = ?
          AND s.status = 'disetujui'
          AND s.mentor_response_status = 'menunggu_konfirmasi'
        ORDER BY s.schedule_date ASC
    """, (mentor_id,))

    return render_template(
        "mentor/schedules.html",
        routine_schedules=routine_schedules,
        schedules=schedules_list,
        pending_confirmations=pending_confirmations,
        my_students=my_students,
        date_filter=date_filter,
        status_filter=status_filter,
        day_names=DAY_NAMES
    )

@mentor_bp.route("/schedules/propose", methods=["POST"])
def propose_schedule():
    validate_csrf()
    mentor_id = get_current_mentor_id()
    student_id = request.form.get("student_id")
    program_id = request.form.get("program_id")
    schedule_date = request.form.get("schedule_date")
    start_time = request.form.get("start_time")
    duration_minutes = int(request.form.get("duration_minutes", 90))
    session_notes = request.form.get("session_notes", "").strip()
    title = request.form.get("title", "Sesi Les Privat").strip()

    if not (student_id and program_id and schedule_date and start_time):
        flash("Siswa, program, tanggal, dan jam mulai wajib diisi.", "danger")
        return redirect(url_for("mentor.schedules"))

    # Pastikan siswa tersebut memang menjadi tanggung jawab mentor ini (di student_programs atau routine_schedules)
    assigned = query_db("""
        SELECT sp.id FROM student_programs sp
        LEFT JOIN routine_schedules rs ON sp.student_id = rs.student_id AND sp.program_id = rs.program_id AND rs.status = 'aktif'
        WHERE (sp.mentor_id = ? OR rs.mentor_id = ?)
          AND sp.student_id = ? AND sp.program_id = ? AND sp.status = 'aktif'
    """, (mentor_id, mentor_id, student_id, program_id), one=True)
    if not assigned:
        flash("Anda hanya dapat mengusulkan jadwal untuk siswa dan program yang ditugaskan kepada Anda.", "danger")
        return redirect(url_for("mentor.schedules"))

    res = create_schedule_proposal(
        title, program_id, student_id, mentor_id, schedule_date,
        start_time, duration_minutes, session_notes, session["user_id"],
        status="disetujui"
    )

    if res["success"]:
        flash(f"Jadwal sesi les {title} ({schedule_date}) berhasil dibuat dan langsung aktif (Fix).", "success")
    else:
        flash(res["message"], "danger")

    return redirect(url_for("mentor.schedules"))

@mentor_bp.route("/schedules/<int:schedule_id>/respond", methods=["POST"])
def respond_schedule(schedule_id):
    validate_csrf()
    choice = request.form.get("response_choice") # 'dikonfirmasi' atau 'tidak_bisa'
    reason = request.form.get("reason", "").strip()

    res = mentor_respond_schedule(schedule_id, session["user_id"], choice, reason)
    if res["success"]:
        flash(res["message"], "success" if choice == "dikonfirmasi" else "info")
    else:
        flash(res["message"], "danger")

    return redirect(url_for("mentor.schedules"))

@mentor_bp.route("/students")
def students():
    mentor_id = get_current_mentor_id()
    students_list = query_db("""
        SELECT DISTINCT s.id, s.full_name, s.school, s.grade, s.notes,
                        pr.id as program_id, pr.name as program_name, sp.start_date,
                        (SELECT COUNT(*) FROM schedules sc WHERE sc.student_id = s.id AND sc.mentor_id = ? AND sc.status = 'disetujui') as total_sessions
        FROM student_programs sp
        JOIN students s ON sp.student_id = s.id
        JOIN programs pr ON sp.program_id = pr.id
        LEFT JOIN routine_schedules rs ON s.id = rs.student_id AND pr.id = rs.program_id AND rs.status = 'aktif'
        WHERE (sp.mentor_id = ? OR rs.mentor_id = ?) AND sp.status = 'aktif' AND s.status = 'aktif'
        ORDER BY s.full_name ASC
    """, (mentor_id, mentor_id, mentor_id))

    students_data = []
    for s in students_list:
        sd = dict(s)
        sd["meeting_stats"] = get_student_program_meeting_stats(sd["id"], sd["program_id"]) if sd.get("program_id") else get_student_meeting_stats(sd["id"])
        students_data.append(sd)

    return render_template("mentor/students.html", students=students_data)

@mentor_bp.route("/availability", methods=["GET", "POST"])
def availability():
    mentor_id = get_current_mentor_id()

    if request.method == "POST":
        validate_csrf()
        # Mendukung input satu persatu per hari, penambahan jam di hari yang sama, maupun hari berbeda
        days = request.form.getlist("day_of_week[]") or request.form.getlist("days[]") or request.form.getlist("day_of_week") or request.form.getlist("days")
        start_times = request.form.getlist("start_time[]") or request.form.getlist("start_time")
        end_times = request.form.getlist("end_time[]") or request.form.getlist("end_time")
        slot_notes = request.form.getlist("slot_notes[]") or request.form.getlist("notes[]") or request.form.getlist("notes")

        if not days:
            flash("Pilih minimal satu hari ketersediaan waktu.", "danger")
            return redirect(url_for("mentor.availability"))

        days_name = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        added_slots = []
        errors = []

        for idx, d_raw in enumerate(days):
            if d_raw is None or d_raw == "":
                continue
            try:
                dow = int(d_raw)
            except (ValueError, TypeError):
                continue
            if not (0 <= dow <= 6):
                continue

            st = start_times[idx].strip() if idx < len(start_times) else ""
            et = end_times[idx].strip() if idx < len(end_times) else ""
            n = slot_notes[idx].strip() if idx < len(slot_notes) else ""

            if not (st and et):
                errors.append(f"Jam mulai dan jam selesai untuk baris ke-{idx+1} wajib diisi.")
                continue

            if st >= et:
                errors.append(f"Pada baris ke-{idx+1} ({days_name[dow]}), jam mulai ({st}) harus lebih awal dari jam selesai ({et}).")
                continue

            # Cek apakah slot yang sama persis sudah ada di database
            existing = query_db("""
                SELECT id FROM mentor_availability
                WHERE mentor_id = ? AND day_of_week = ? AND start_time = ? AND end_time = ?
            """, (mentor_id, dow, st, et), one=True)
            if existing:
                continue

            execute_db("""
                INSERT INTO mentor_availability (mentor_id, day_of_week, start_time, end_time, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (mentor_id, dow, st, et, n))
            added_slots.append(f"{days_name[dow]} ({st} - {et} WIB)")

        if errors:
            flash("Beberapa slot gagal disimpan: " + " | ".join(errors), "danger")
            if not added_slots:
                return redirect(url_for("mentor.availability"))

        if added_slots:
            flash(f"Berhasil menyimpan {len(added_slots)} slot ketersediaan waktu mengajar: {', '.join(added_slots)}.", "success")
        elif not errors:
            flash("Slot ketersediaan waktu tersebut sudah pernah ditambahkan sebelumnya.", "info")

        return redirect(url_for("mentor.availability"))

    avails = query_db("""
        SELECT * FROM mentor_availability
        WHERE mentor_id = ?
        ORDER BY day_of_week ASC, start_time ASC
    """, (mentor_id,))
    return render_template("mentor/availability.html", availabilities=avails)

@mentor_bp.route("/availability/<int:avail_id>/delete", methods=["POST"])
def delete_availability(avail_id):
    validate_csrf()
    mentor_id = get_current_mentor_id()
    execute_db("DELETE FROM mentor_availability WHERE id = ? AND mentor_id = ?", (avail_id, mentor_id))
    flash("Jadwal ketersediaan berhasil dihapus.", "info")
    return redirect(url_for("mentor.availability"))

# ==========================================
# ABSENSI SESI LES
# ==========================================
@mentor_bp.route("/attendance", methods=["GET", "POST"])
def attendance():
    mentor_id = get_current_mentor_id()

    if request.method == "POST":
        validate_csrf()
        schedule_id = request.form.get("schedule_id", "").strip()
        student_id = request.form.get("student_id", "").strip()
        program_id = request.form.get("program_id", "").strip()
        schedule_date = request.form.get("schedule_date", "").strip() or date.today().strftime("%Y-%m-%d")
        day_name = request.form.get("day_name", "").strip()
        start_time = request.form.get("start_time", "16:00").strip() or "16:00"
        duration_minutes = request.form.get("duration_minutes", "90").strip() or "90"
        
        # Pemisahan status kehadiran mentor & status sesi belajar siswa (Langkah 3)
        mentor_status = request.form.get("mentor_status", "").strip() or "hadir"
        session_status = request.form.get("session_status", "").strip() or "terlaksana"
        has_tech_issue = bool(request.form.get("has_tech_issue"))
        documentation_pending_reason = request.form.get("documentation_pending_reason", "").strip()
        
        status = request.form.get("status", "hadir") # Fallback kompatibilitas
        notes = request.form.get("notes", "").strip()
        topics_covered = request.form.get("topics_covered", "").strip()
        progress_notes = request.form.get("progress_notes", "").strip()
        skills_mastered = request.form.get("skills_mastered", "").strip()
        difficulties = request.form.get("difficulties", "").strip()
        recommendations = request.form.get("recommendations", "").strip()

        is_session_conducted = (mentor_status == "hadir" and session_status == "terlaksana")

        if is_session_conducted and not topics_covered:
            flash("Materi yang diajarkan wajib diisi ketika sesi belajar terlaksana.", "danger")
            return redirect(url_for("mentor.attendance"))

        # Validasi dokumentasi foto (Opsi B: Wajib untuk sesi terlaksana)
        saved_filename = None
        doc_status = "tidak_ada"
        photo_file = request.files.get("session_photo")

        if is_session_conducted:
            if has_tech_issue:
                # Mekanisme Dokumentasi Tertunda karena kendala kamera/upload
                if len(documentation_pending_reason) < 10:
                    flash("Alasan kendala teknis kamera/unggahan wajib diisi minimal 10 karakter.", "danger")
                    return redirect(url_for("mentor.attendance"))
                doc_status = "menunggu"
                saved_filename = None
            else:
                # Foto wajib diunggah
                if not photo_file or not photo_file.filename:
                    flash("Foto dokumentasi belajar wajib diunggah untuk sesi yang terlaksana.", "danger")
                    return redirect(url_for("mentor.attendance"))

                ext = photo_file.filename.rsplit(".", 1)[-1].lower() if "." in photo_file.filename else ""
                if ext not in ("jpg", "jpeg", "png", "webp"):
                    flash("Format file foto tidak didukung. Mohon gunakan format JPG, PNG, atau WebP.", "danger")
                    return redirect(url_for("mentor.attendance"))

                # Periksa ukuran file (maksimal 5 MB)
                photo_file.seek(0, os.SEEK_END)
                file_size = photo_file.tell()
                photo_file.seek(0)
                if file_size > 5 * 1024 * 1024:
                    flash("Ukuran file foto melebihi batas 5MB. Silakan pilih foto dengan resolusi lebih kecil.", "danger")
                    return redirect(url_for("mentor.attendance"))

                doc_status = "lengkap"
        else:
            doc_status = "tidak_ada"
            saved_filename = None
            documentation_pending_reason = None

        # Jika schedule_id tidak dipilih (input langsung siswa & tanggal)
        if not schedule_id:
            if not student_id:
                flash("Mohon pilih siswa bimbingan yang diajar.", "danger")
                return redirect(url_for("mentor.attendance"))

            student = query_db("SELECT id, full_name FROM students WHERE id = ?", (student_id,), one=True)
            if not student:
                flash("Data siswa tidak ditemukan di sistem.", "danger")
                return redirect(url_for("mentor.attendance"))

            if not program_id:
                sp = query_db("SELECT program_id FROM student_programs WHERE student_id = ? AND status = 'aktif' LIMIT 1", (student_id,), one=True)
                if sp:
                    program_id = sp["program_id"]
                else:
                    first_p = query_db("SELECT id FROM programs WHERE status = 'aktif' LIMIT 1", one=True)
                    program_id = first_p["id"] if first_p else 1

            pr_row = query_db("SELECT name FROM programs WHERE id = ?", (program_id,), one=True)
            program_name = pr_row["name"] if pr_row else "Les Privat"

            # Cek apakah sudah ada sesi jadwal untuk siswa, mentor, dan tanggal ini
            existing_sched = query_db("""
                SELECT id FROM schedules
                WHERE student_id = ? AND mentor_id = ? AND schedule_date = ?
            """, (student_id, mentor_id, schedule_date), one=True)

            if existing_sched:
                schedule_id = existing_sched["id"]
            else:
                try:
                    dur = int(duration_minutes)
                except (ValueError, TypeError):
                    dur = 90
                end_time = calculate_end_time(start_time, dur)
                day_title = f" ({day_name})" if day_name else ""
                schedule_id = execute_db("""
                    INSERT INTO schedules (
                        title, program_id, student_id, mentor_id,
                        schedule_date, start_time, end_time, duration_minutes,
                        status, student_confirmation_status, mentor_response_status,
                        created_by, approved_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'disetujui', 'bersedia', 'dikonfirmasi', ?, ?)
                """, (
                    f"Sesi {program_name} - {student['full_name']}{day_title}",
                    program_id, student_id, mentor_id,
                    schedule_date, start_time, end_time, dur,
                    session["user_id"], session["user_id"]
                ))

            sched = {
                "id": schedule_id,
                "student_id": student_id,
                "student_name": student["full_name"],
                "program_id": program_id,
                "schedule_date": schedule_date
            }
        else:
            # Pastikan jadwal milik mentor ini
            sched = query_db("""
                SELECT s.*, st.full_name as student_name
                FROM schedules s
                JOIN students st ON s.student_id = st.id
                WHERE s.id = ? AND s.mentor_id = ?
            """, (schedule_id, mentor_id), one=True)

            if not sched:
                flash("Jadwal tidak ditemukan atau bukan wewenang Anda.", "danger")
                return redirect(url_for("mentor.attendance"))

        # Penanganan penyimpanan file atomik (mencegah orphan file jika database gagal)
        upload_folder = os.path.join(current_app.root_path, "uploads", "session_photos")
        os.makedirs(upload_folder, exist_ok=True)
        saved_file_path = None

        if doc_status == "lengkap" and photo_file:
            ext = photo_file.filename.rsplit(".", 1)[-1].lower() if "." in photo_file.filename else "jpg"
            saved_filename = f"session_{schedule_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}"
            saved_file_path = os.path.join(upload_folder, saved_filename)

        try:
            if saved_file_path and photo_file:
                photo_file.save(saved_file_path)

            # Simpan absensi dan hitung nomor periode & pertemuan otomatis
            res = record_or_update_attendance(
                schedule_id=schedule_id,
                student_id=sched["student_id"],
                mentor_id=mentor_id,
                status="hadir" if is_session_conducted else ("izin" if session_status == "siswa_berhalangan" else "tidak_hadir"),
                notes=notes,
                topics_covered=topics_covered,
                progress_notes=progress_notes,
                skills_mastered=skills_mastered,
                difficulties=difficulties,
                recommendations=recommendations,
                mentor_status=mentor_status,
                session_status=session_status,
                documentation_status=doc_status,
                documentation_photo=saved_filename,
                documentation_pending_reason=documentation_pending_reason,
                attendance_date=schedule_date
            )

            if not res.get("success"):
                if saved_file_path and os.path.exists(saved_file_path):
                    try:
                        os.remove(saved_file_path)
                    except OSError:
                        pass
                flash(f"Gagal mencatat absensi: {res.get('message')}", "danger")
                return redirect(url_for("mentor.attendance"))

            # Selaraskan siklus honor jika pertemuan ke-8 selesai terisi
            try:
                sync_and_get_mentor_period_honors()
            except Exception:
                pass

        except Exception as e:
            # Rollback pembersihan file fisik jika transaksi DB gagal
            if saved_file_path and os.path.exists(saved_file_path):
                try:
                    os.remove(saved_file_path)
                except OSError:
                    pass
            flash(f"Terjadi kesalahan saat memproses absensi: {str(e)}", "danger")
            return redirect(url_for("mentor.attendance"))

        day_str = f" ({day_name})" if day_name else ""
        if mentor_status == "hadir" and session_status == "terlaksana":
            pending_str = " (Dokumentasi foto tertunda, menunggu verifikasi Admin)" if doc_status == "menunggu" else ""
            msg = f"Absensi {sched['student_name']} tanggal {schedule_date}{day_str} berhasil dicatat sebagai {res['meeting_label']}!{pending_str}"
        elif mentor_status == "hadir" and session_status == "siswa_berhalangan":
            msg = f"Kehadiran mentor tanggal {schedule_date}{day_str} tercatat: HADIR / SIAP MENGAJAR. Sesi siswa dicatat SISWA BERHALANGAN dan tidak dihitung ke siklus periode."
        else:
            msg = f"Ketidakhadiran mentor tanggal {schedule_date}{day_str} berhasil dicatat: {mentor_status.upper()}. Sesi siswa tidak diselesaikan."

        flash(msg, "success")
        return redirect(url_for("mentor.attendance"))

    # Ambil sesi yang siap diabsensi (jadwal disetujui milik mentor ini)
    raw_schedules = query_db("""
        SELECT s.*, st.full_name as student_name, pr.name as program_name,
               att.id as attendance_id, att.status as attendance_status, att.notes as attendance_notes,
               att.topics_covered, att.progress_notes, att.meeting_number, att.period_number,
               att.mentor_status, att.session_status, att.documentation_status, att.documentation_photo,
               att.documentation_pending_reason
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN programs pr ON s.program_id = pr.id
        LEFT JOIN attendance att ON s.id = att.schedule_id
        WHERE s.mentor_id = ? AND s.status = 'disetujui'
        ORDER BY s.schedule_date DESC, s.start_time DESC
        LIMIT 30
    """, (mentor_id,))

    # Lengkapi dengan nomor pertemuan & periode yang dihitung otomatis
    ready_schedules = []
    for s in raw_schedules:
        s_dict = dict(s)
        prog_id = s_dict.get("program_id")
        st_stats = get_student_program_meeting_stats(s_dict["student_id"], prog_id) if prog_id else get_student_meeting_stats(s_dict["student_id"])
        if s_dict.get("attendance_status") == "hadir" and s_dict.get("meeting_number"):
            s_dict["calculated_meeting_label"] = f"Pertemuan {s_dict['meeting_number']} ({s_dict['period_number']})"
        else:
            s_dict["calculated_meeting_label"] = st_stats["next_meeting_str"] if st_stats else "Pertemuan 1 (1)"
        ready_schedules.append(s_dict)

    # Siswa bimbingan mentor ini (bisa diajar oleh lebih dari 1 mentor pada program yang sama)
    # Mencakup siswa yang terdaftar di student_programs, routine_schedules, atau schedules
    my_students_raw = query_db("""
        SELECT DISTINCT st.id, st.full_name, st.school, st.grade,
               pr.id as program_id, pr.name as program_name
        FROM students st
        JOIN student_programs sp ON st.id = sp.student_id AND sp.status = 'aktif'
        JOIN programs pr ON sp.program_id = pr.id
        LEFT JOIN routine_schedules rs ON st.id = rs.student_id AND pr.id = rs.program_id AND rs.status = 'aktif'
        LEFT JOIN schedules s ON st.id = s.student_id AND pr.id = s.program_id
        WHERE (sp.mentor_id = ? OR rs.mentor_id = ? OR s.mentor_id = ?)
          AND st.status = 'aktif'
        ORDER BY st.full_name ASC
    """, (mentor_id, mentor_id, mentor_id))

    # Jika belum ada siswa yang terkait khusus di student_programs mentor ini,
    # tampilkan semua siswa aktif agar mentor tidak mentok
    if not my_students_raw:
        my_students_raw = query_db("""
            SELECT DISTINCT st.id, st.full_name, st.school, st.grade,
                   pr.id as program_id, pr.name as program_name
            FROM students st
            LEFT JOIN student_programs sp ON st.id = sp.student_id
            LEFT JOIN programs pr ON sp.program_id = pr.id
            WHERE st.status = 'aktif'
            ORDER BY st.full_name ASC
        """)

    students_list = []
    for st in my_students_raw:
        st_d = dict(st)
        prog_id = st_d.get("program_id")
        stats = get_student_program_meeting_stats(st_d["id"], prog_id) if prog_id else get_student_meeting_stats(st_d["id"])
        st_d["meeting_stats"] = stats
        st_d["next_meeting_str"] = stats["next_meeting_str"] if stats else "Pertemuan 1 (1)"
        students_list.append(st_d)

    # Program aktif
    programs_list = query_db("SELECT id, name FROM programs WHERE status = 'aktif' ORDER BY name ASC")

    today_str = date.today().strftime("%Y-%m-%d")
    preselect_student_id = request.args.get("student_id")
    preselect_date = request.args.get("schedule_date")

    # Riwayat absensi terdahulu yang diampu mentor ini
    history = query_db("""
        SELECT a.*, s.schedule_date, s.start_time, s.end_time,
               st.full_name as student_name, pr.name as program_name
        FROM attendance a
        JOIN schedules s ON a.schedule_id = s.id
        JOIN students st ON a.student_id = st.id
        JOIN programs pr ON s.program_id = pr.id
        WHERE a.mentor_id = ?
        ORDER BY a.recorded_at DESC
        LIMIT 40
    """, (mentor_id,))

    return render_template(
        "mentor/attendance.html",
        schedules=ready_schedules,
        students=students_list,
        programs=programs_list,
        history=history,
        today_str=preselect_date or today_str,
        preselect_student_id=preselect_student_id
    )

# ==========================================
# LAPORAN PERKEMBANGAN SISWA
# ==========================================
@mentor_bp.route("/progress", methods=["GET", "POST"])
def progress():
    mentor_id = get_current_mentor_id()

    if request.method == "POST":
        validate_csrf()
        schedule_id = request.form.get("schedule_id")
        topics_covered = request.form.get("topics_covered", "").strip()
        skills_mastered = request.form.get("skills_mastered", "").strip()
        difficulties = request.form.get("difficulties", "").strip()
        recommendations = request.form.get("recommendations", "").strip()
        additional_notes = request.form.get("additional_notes", "").strip()

        if not schedule_id or not topics_covered:
            flash("Sesi jadwal dan materi yang dipelajari wajib diisi.", "danger")
            return redirect(url_for("mentor.progress"))

        sched = query_db("""
            SELECT s.*, st.full_name as student_name, p.user_id as parent_user_id
            FROM schedules s
            JOIN students st ON s.student_id = st.id
            JOIN parents p ON st.parent_id = p.id
            WHERE s.id = ? AND s.mentor_id = ?
        """, (schedule_id, mentor_id), one=True)

        if not sched:
            flash("Jadwal tidak ditemukan atau bukan tanggung jawab Anda.", "danger")
            return redirect(url_for("mentor.progress"))

        # Cek apakah laporan sudah ada (update atau insert)
        existing = query_db("SELECT id FROM student_progress WHERE schedule_id = ?", (schedule_id,), one=True)
        if existing:
            execute_db("""
                UPDATE student_progress
                SET topics_covered = ?, skills_mastered = ?, difficulties = ?,
                    recommendations = ?, additional_notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE schedule_id = ?
            """, (topics_covered, skills_mastered, difficulties, recommendations, additional_notes, schedule_id))
            flash(f"Laporan perkembangan belajar untuk {sched['student_name']} berhasil diperbarui.", "success")
        else:
            execute_db("""
                INSERT INTO student_progress (
                    schedule_id, student_id, mentor_id, program_id, session_date,
                    topics_covered, skills_mastered, difficulties, recommendations, additional_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                schedule_id, sched["student_id"], mentor_id, sched["program_id"],
                sched["schedule_date"], topics_covered, skills_mastered,
                difficulties, recommendations, additional_notes
            ))

            # Notifikasi ke Wali Murid: langsung tersedia di dashboard wali
            if sched["parent_user_id"]:
                create_notification(
                    sched["parent_user_id"],
                    "Laporan Perkembangan Siswa Baru",
                    f"Mentor telah mengirimkan laporan perkembangan belajar {sched['student_name']} untuk sesi tanggal {sched['schedule_date']}.",
                    "perkembangan",
                    "/parent/progress"
                )

            flash(f"Laporan perkembangan belajar untuk {sched['student_name']} berhasil disimpan dan langsung dapat dilihat oleh wali murid.", "success")

        return redirect(url_for("mentor.progress"))

    # Sesi les yang telah disetujui untuk diisi laporannya
    target_schedule_id = request.args.get("schedule_id")
    schedules_for_progress = query_db("""
        SELECT s.*, st.full_name as student_name, pr.name as program_name,
               sp.id as progress_id, sp.topics_covered, sp.skills_mastered,
               sp.difficulties, sp.recommendations, sp.additional_notes
        FROM schedules s
        JOIN students st ON s.student_id = st.id
        JOIN programs pr ON s.program_id = pr.id
        LEFT JOIN student_progress sp ON s.id = sp.schedule_id
        WHERE s.mentor_id = ? AND s.status = 'disetujui'
        ORDER BY s.schedule_date DESC
        LIMIT 25
    """, (mentor_id,))

    # Riwayat laporan perkembangan yang pernah dibuat oleh mentor ini
    history = query_db("""
        SELECT sp.*, st.full_name as student_name, pr.name as program_name
        FROM student_progress sp
        JOIN students st ON sp.student_id = st.id
        JOIN programs pr ON sp.program_id = pr.id
        WHERE sp.mentor_id = ?
        ORDER BY sp.session_date DESC, sp.created_at DESC
        LIMIT 30
    """, (mentor_id,))

    return render_template(
        "mentor/progress.html",
        schedules=schedules_for_progress,
        history=history,
        target_schedule_id=target_schedule_id
    )
