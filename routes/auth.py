"""
DESI PRIVAT - Auth Blueprint & Access Control
Mengelola login, logout, session aman, proteksi CSRF,
serta pembatasan hak akses berbasis role (Admin, Pemilik, Mentor, Orang Tua).
"""
import secrets
from functools import wraps
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, abort, g
)
from werkzeug.security import check_password_hash
from services.database_service import query_db, execute_db
from services.audit_service import log_audit

auth_bp = Blueprint("auth", __name__)

def generate_csrf_token():
    """Membuat atau mengambil token CSRF dari session."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(24)
    return session["_csrf_token"]

def validate_csrf():
    """Memvalidasi token CSRF pada permintaan form POST."""
    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not token or token != session.get("_csrf_token"):
        abort(400, description="Token CSRF tidak valid atau telah kedaluwarsa. Silakan muat ulang halaman.")

def login_required(f):
    """Dekorator untuk memastikan pengguna telah login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Silakan masuk terlebih dahulu untuk mengakses halaman ini.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """Dekorator otorisasi ketat di sisi backend berdasarkan role pengguna."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Silakan masuk terlebih dahulu.", "warning")
                return redirect(url_for("auth.login"))
            user_role = session.get("role")
            if user_role not in allowed_roles:
                abort(403, description="Akses ditolak. Anda tidak memiliki izin untuk mengakses fitur ini.")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_role_dashboard_url(role):
    """Mengarahkan pengguna ke dashboard yang sesuai dengan rolenya."""
    mapping = {
        "admin": "admin.dashboard",
        "owner": "owner.dashboard",
        "mentor": "mentor.dashboard"
    }
    return url_for(mapping.get(role, "auth.login"))

@auth_bp.route("/")
def index():
    """Rute utama: arahkan pengguna yang sudah login ke dashboard, atau ke login."""
    if "user_id" in session:
        return redirect(get_role_dashboard_url(session.get("role")))
    return redirect(url_for("auth.login"))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Halaman login profesional DESI PRIVAT."""
    if "user_id" in session:
        return redirect(get_role_dashboard_url(session.get("role")))

    if request.method == "POST":
        # Validasi CSRF
        validate_csrf()

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Mohon masukkan ID pengguna dan password.", "danger")
            return render_template("login.html")

        # Ambil user dari database (case-insensitive)
        user = query_db("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username,), one=True)

        if not user:
            flash("ID Pengguna atau password salah. Silakan periksa kembali.", "danger")
            return render_template("login.html")

        # Cek kata sandi menggunakan hash yang aman
        if not check_password_hash(user["password_hash"], password):
            flash("ID Pengguna atau password salah. Silakan periksa kembali.", "danger")
            return render_template("login.html")

        if user["role"] not in ("admin", "owner", "mentor"):
            flash("Akses sistem hanya tersedia untuk Admin, Pemilik, dan Mentor. Silakan hubungi pengelola.", "warning")
            return render_template("login.html")

        if not user["is_active"]:
            flash("Akun Anda telah dinonaktifkan oleh administrator. Silakan hubungi pengelola DESI PRIVAT.", "danger")
            return render_template("login.html")

        # Inisialisasi session aman
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        session["full_name"] = user["full_name"]
        session["_csrf_token"] = secrets.token_hex(24)

        # Ambil referensi entitas spesifik sesuai role
        if user["role"] == "mentor":
            mentor_rec = query_db("SELECT id FROM mentors WHERE user_id = ?", (user["id"],), one=True)
            if mentor_rec:
                session["mentor_id"] = mentor_rec["id"]

        log_audit(
            user["id"],
            user["username"],
            "LOGIN",
            "users",
            user["id"],
            f"Pengguna {user['username']} ({user['role']}) berhasil masuk ke sistem.",
            request.remote_addr
        )

        flash(f"Selamat datang kembali, {user['full_name']}!", "success")
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(get_role_dashboard_url(user["role"]))

    return render_template("login.html")

@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Mengakhiri sesi pengguna."""
    u_id = session.get("user_id")
    u_name = session.get("username")
    if u_id:
        log_audit(u_id, u_name, "LOGOUT", "users", u_id, f"Pengguna {u_name} keluar dari sistem.", request.remote_addr)
    session.clear()
    flash("Anda telah berhasil keluar dari sistem DESI PRIVAT.", "info")
    return redirect(url_for("auth.login"))
