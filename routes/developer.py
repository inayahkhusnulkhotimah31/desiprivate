"""
DESI PRIVAT - Developer Monitoring Blueprint
Dashboard Pemantauan Khusus Pengembang (Real-Time Developer Monitoring)
- Autentikasi dan otorisasi terpisah untuk developer (@developer_required)
- Live Activity Feed dengan Server-Sent Events (SSE) & polling fallback
- Pelacakan perubahan data siswa tingkat field (field-level diffs)
- Analisis aktivitas admin dan log kesalahan
- Ekspor log aktivitas ke CSV / JSON
"""
import io
import csv
import json
import time
from datetime import datetime
from functools import wraps
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify, Response, abort
)
from werkzeug.security import check_password_hash
from config import Config
from services.database_service import query_db, get_direct_connection, is_postgres
from services.audit_service import (
    log_audit, get_audit_logs, get_student_change_logs,
    register_dev_subscriber, unregister_dev_subscriber
)

developer_bp = Blueprint("developer", __name__, url_prefix="/developer")

def developer_required(f):
    """Dekorator otorisasi ketat khusus akun developer."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_developer"):
            if request.path.startswith("/developer/api/"):
                return jsonify({"error": "Akses ditolak. Diperlukan sesi developer yang valid."}), 403
            flash("Silakan masuk dengan akun developer untuk mengakses dashboard pemantauan.", "warning")
            return redirect(url_for("developer.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# AUTENTIKASI DEVELOPER
# ==========================================
@developer_bp.route("/login", methods=["GET", "POST"])
def login():
    """Halaman login khusus Developer DESI PRIVAT."""
    if session.get("is_developer"):
        return redirect(url_for("developer.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        is_valid = False
        dev_identity = username

        # 1. Cek kredensial developer dari Config / Environment
        cfg_user = getattr(Config, "DEVELOPER_USERNAME", "developer")
        cfg_pass = getattr(Config, "DEVELOPER_PASSWORD", "DesiPrivat@Dev2026!")

        if username.lower() == cfg_user.lower() and password == cfg_pass:
            is_valid = True
            dev_identity = cfg_user
        else:
            # 2. Cek akun database ber-role developer atau username devlop
            user = query_db(
                "SELECT * FROM users WHERE LOWER(username) IN ('devlop', 'developer') AND is_active = 1",
                one=True
            )
            if user and check_password_hash(user["password_hash"], password):
                is_valid = True
                dev_identity = user["username"]

        if is_valid:
            session["is_developer"] = True
            session["developer_username"] = dev_identity
            session["developer_login_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            log_audit(
                user_id=None,
                user_name=f"dev:{dev_identity}",
                action_type="DEVELOPER_LOGIN",
                target_entity="developer_session",
                target_id=dev_identity,
                details=f"Developer {dev_identity} berhasil login ke Developer Monitoring Dashboard.",
                ip_address=request.remote_addr,
                module_name="Developer"
            )
            flash("Selamat datang di Developer Real-Time Monitoring DESI PRIVAT.", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/developer"):
                return redirect(next_url)
            return redirect(url_for("developer.dashboard"))

        flash("ID Pengguna atau Password Developer salah.", "danger")

    return render_template("developer/login.html")

@developer_bp.route("/logout")
def logout():
    """Mengakhiri sesi developer."""
    dev_user = session.get("developer_username", "developer")
    if session.get("is_developer"):
        log_audit(
            user_id=None,
            user_name=f"dev:{dev_user}",
            action_type="DEVELOPER_LOGOUT",
            target_entity="developer_session",
            target_id=dev_user,
            details=f"Developer {dev_user} keluar dari Developer Monitoring Dashboard.",
            ip_address=request.remote_addr,
            module_name="Developer"
        )
    session.pop("is_developer", None)
    session.pop("developer_username", None)
    session.pop("developer_login_at", None)
    flash("Sesi developer telah diakhiri dengan aman.", "info")
    return redirect(url_for("developer.login"))

# ==========================================
# DASHBOARD UTAMA MONITORING
# ==========================================
@developer_bp.route("/")
@developer_bp.route("/dashboard")
@developer_required
def dashboard():
    """Tampilan utama Dashboard Developer Real-Time."""
    # Ambil metrik ringkasan sistem
    st_count = query_db("SELECT COUNT(*) as c FROM students", one=True)["c"]
    st_active = query_db("SELECT COUNT(*) as c FROM students WHERE status = 'aktif'", one=True)["c"]
    parent_count = query_db("SELECT COUNT(*) as c FROM parents", one=True)["c"]
    prog_count = query_db("SELECT COUNT(*) as c FROM programs WHERE status = 'aktif'", one=True)["c"]
    sp_count = query_db("SELECT COUNT(*) as c FROM student_programs WHERE status = 'aktif'", one=True)["c"]
    sched_count = query_db("SELECT COUNT(*) as c FROM schedules", one=True)["c"]
    att_count = query_db("SELECT COUNT(*) as c FROM attendance", one=True)["c"]
    audit_count = query_db("SELECT COUNT(*) as c FROM audit_logs", one=True)["c"]

    # Cek integritas database
    integrity_status = "ok"
    try:
        conn = get_direct_connection()
        integrity_status = conn.execute("PRAGMA integrity_check").fetchone()[0]
        conn.close()
    except Exception as e:
        integrity_status = str(e)

    # Identifikasi engine database
    db_engine = "Supabase PostgreSQL" if is_postgres() else "Dual-Engine SQLite + Cloud Sync"

    # Daftar admin & user aktif untuk filter
    admins = query_db("SELECT DISTINCT user_name FROM audit_logs WHERE user_name IS NOT NULL AND user_name != '' ORDER BY user_name ASC")

    # Modul unik untuk filter
    modules = query_db("SELECT DISTINCT module_name FROM audit_logs WHERE module_name IS NOT NULL ORDER BY module_name ASC")

    # Ambil 50 aktivitas terbaru
    recent_activities = get_audit_logs(limit=50)

    # Ambil 25 perubahan data siswa (field-level diffs)
    student_diffs = get_student_change_logs(limit=25)

    system_metrics = {
        "students_total": st_count,
        "students_active": st_active,
        "parents_total": parent_count,
        "programs_active": prog_count,
        "student_programs_active": sp_count,
        "schedules_total": sched_count,
        "attendances_total": att_count,
        "audit_logs_total": audit_count,
        "db_engine": db_engine,
        "db_integrity": integrity_status,
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return render_template(
        "developer/dashboard.html",
        metrics=system_metrics,
        admins=admins,
        modules=modules,
        activities=recent_activities,
        student_diffs=student_diffs,
        dev_user=session.get("developer_username", "developer"),
        login_time=session.get("developer_login_at", "-")
    )

# ==========================================
# REAL-TIME APIS
# ==========================================
@developer_bp.route("/api/live-feed")
@developer_required
def api_live_feed():
    """
    Endpoint Server-Sent Events (SSE) untuk live streaming aktivitas secara instan.
    Mengirim event JSON setiap kali terdapat aktivitas audit baru di sistem.
    """
    def event_stream():
        q = register_dev_subscriber()
        try:
            # Kirim initial heartbeat untuk mengonfirmasi koneksi aktif
            yield f": connected\n\n"
            while True:
                try:
                    # Tunggu pesan dari audit service hingga 12 detik
                    event = q.get(timeout=12)
                    data_json = json.dumps(event, ensure_ascii=False)
                    yield f"event: activity\ndata: {data_json}\n\n"
                except Exception:
                    # Timeout heartbeat agar koneksi HTTP tetap hidup
                    yield f": heartbeat\n\n"
        finally:
            unregister_dev_subscriber(q)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

@developer_bp.route("/api/activities")
@developer_required
def api_activities():
    """
    Endpoint polling aktivitas dengan dukungan filter:
    since_id, module_name, user_name, action_type, start_date, end_date, limit.
    """
    since_id = request.args.get("since_id")
    module_name = request.args.get("module")
    user_name = request.args.get("admin")
    action_type = request.args.get("action_type")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    limit = int(request.args.get("limit", 50))

    logs = get_audit_logs(
        limit=limit,
        action_type=action_type,
        module_name=module_name,
        user_name=user_name,
        start_date=start_date,
        end_date=end_date,
        since_id=since_id
    )

    activities = []
    for l in logs:
        activities.append(dict(l))

    return jsonify({"success": True, "activities": activities, "count": len(activities)})

@developer_bp.route("/api/student-diffs")
@developer_required
def api_student_diffs():
    """Mengambil riwayat diff perubahan field-level siswa."""
    student_id = request.args.get("student_id")
    limit = int(request.args.get("limit", 30))
    diffs = get_student_change_logs(student_id=student_id, limit=limit)
    return jsonify({"success": True, "diffs": [dict(d) for d in diffs]})

@developer_bp.route("/api/system-health")
@developer_required
def api_system_health():
    """Diagnostik status sistem dan database secara langsung."""
    try:
        conn = get_direct_connection()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        tbl_counts = {}
        for tbl in ["students", "parents", "programs", "student_programs", "schedules", "attendance", "audit_logs"]:
            c = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            tbl_counts[tbl] = c
        conn.close()
        db_ok = (integrity == "ok")
    except Exception as e:
        integrity = str(e)
        tbl_counts = {}
        db_ok = False

    return jsonify({
        "status": "healthy" if db_ok else "warning",
        "database_ok": db_ok,
        "integrity": integrity,
        "engine": "Supabase PostgreSQL" if is_postgres() else "SQLite + Supabase Cloud Sync",
        "table_counts": tbl_counts,
        "timestamp": datetime.now().isoformat()
    })

# ==========================================
# EKSPOR DATA AKTIVITAS
# ==========================================
@developer_bp.route("/export")
@developer_required
def export_audit_logs():
    """Mengekspor seluruh riwayat audit log ke format CSV atau JSON."""
    fmt = request.args.get("format", "csv").lower()
    limit = int(request.args.get("limit", 1000))
    logs = get_audit_logs(limit=limit)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == "json":
        data = [dict(r) for r in logs]
        response = Response(
            json.dumps(data, indent=2, ensure_ascii=False),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename=desi_privat_audit_logs_{timestamp_str}.json"}
        )
        return response

    # Default: CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Waktu", "User / Admin", "Modul", "Jenis Aksi", "Target Entitas",
        "Target ID", "Detail Aktivitas", "Field Berubah", "Nilai Lama", "Nilai Baru", "IP Address"
    ])

    for r in logs:
        writer.writerow([
            r["id"],
            r["created_at"],
            r["user_name"] or "-",
            r["module_name"] or "-",
            r["action_type"] or "-",
            r["target_entity"] or "-",
            r["target_id"] or "-",
            r["details"] or "-",
            r["fields_changed"] or "-",
            r["old_values"] or "-",
            r["new_values"] or "-",
            r["ip_address"] or "-"
        ])

    response = Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=desi_privat_audit_logs_{timestamp_str}.csv"}
    )
    return response

