"""
DESI PRIVAT - Aplikasi Utama Flask
Sistem Informasi Manajemen Tempat Les Privat
"""
import os
import sys
from pathlib import Path

# Deteksi otomatis virtual environment lokal (.venv) jika ada
_local_venv = Path(__file__).resolve().parent / ".venv" / "Lib" / "site-packages"
if _local_venv.exists() and str(_local_venv) not in sys.path:
    sys.path.insert(0, str(_local_venv))

# Fallback path jika dependensi terpasang di Python 3.11 pengguna
_py311_site = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python311" / "Lib" / "site-packages"
if _py311_site.exists() and str(_py311_site) not in sys.path:
    sys.path.append(str(_py311_site))

from datetime import datetime
from flask import Flask, render_template, session, g
from config import Config, config_by_name
from services.database_service import close_db, init_db, seed_initial_data, query_db
from services.notification_service import get_unread_count
from routes.auth import auth_bp, generate_csrf_token
from routes.admin import admin_bp
from routes.owner import owner_bp
from routes.mentor import mentor_bp

def create_app(config_class=None):
    """Application factory untuk DESI PRIVAT."""
    if config_class is None:
        env = os.getenv("FLASK_ENV", "production" if os.getenv("ENV") == "production" else "development")
        config_class = config_by_name.get(env, Config)

    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inisialisasi Database dan Data Utama secara otomatis jika belum ada
    with app.app_context():
        init_db()
        seed_initial_data()

    # Daftarkan teardown database
    app.teardown_appcontext(close_db)

    # Daftarkan Blueprint Routes
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(owner_bp)
    app.register_blueprint(mentor_bp)

    # Context Processor untuk Template Jinja2
    @app.context_processor
    def inject_global_data():
        user = None
        unread_count = 0
        if "user_id" in session:
            user = {
                "id": session.get("user_id"),
                "username": session.get("username"),
                "role": session.get("role"),
                "full_name": session.get("full_name")
            }
            try:
                unread_count = get_unread_count(session["user_id"])
            except Exception:
                unread_count = 0

        return {
            "current_user": user,
            "unread_count": unread_count,
            "csrf_token": generate_csrf_token,
            "app_name": "DESI PRIVAT",
            "current_year": datetime.now().year
        }

    # Filter Jinja kustom dalam Bahasa Indonesia
    @app.template_filter("date_indo")
    def date_indo_filter(date_str):
        if not date_str:
            return "-"
        try:
            if isinstance(date_str, datetime):
                dt = date_str
            else:
                date_str = str(date_str).split(" ")[0]
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            months = [
                "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
                "Juli", "Agustus", "September", "Oktober", "November", "Desember"
            ]
            days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            day_name = days[dt.weekday()]
            return f"{day_name}, {dt.day} {months[dt.month]} {dt.year}"
        except Exception:
            return str(date_str)

    @app.template_filter("status_badge")
    def status_badge_filter(status_code):
        labels = {
            "aktif": ("Aktif", "badge-success"),
            "nonaktif": ("Nonaktif", "badge-secondary"),
            "berhenti": ("Berhenti (Arsip)", "badge-warning"),
            "diarsipkan": ("Diarsipkan", "badge-warning"),
            "selesai": ("Selesai", "badge-info"),
            "draft": ("Draft", "badge-secondary"),
            "menunggu_konfirmasi_siswa": ("Menunggu Konfirmasi Siswa/Wali", "badge-warning"),
            "menunggu_persetujuan_admin": ("Menunggu Persetujuan Admin", "badge-info"),
            "disetujui": ("Resmi Disetujui", "badge-success"),
            "ditolak": ("Ditolak", "badge-danger"),
            "perlu_dijadwalkan_ulang": ("Perlu Dijadwalkan Ulang", "badge-warning"),
            "dibatalkan": ("Dibatalkan", "badge-danger"),
            "menunggu_konfirmasi": ("Menunggu Konfirmasi Mentor", "badge-warning"),
            "dikonfirmasi": ("Mentor Siap Mengajar", "badge-success"),
            "tidak_bisa": ("Mentor Berhalangan", "badge-danger"),
            "perlu_mentor_pengganti": ("Perlu Mentor Pengganti", "badge-danger"),
            "hadir": ("Hadir", "badge-success"),
            "izin": ("Izin", "badge-warning"),
            "tidak_hadir": ("Tidak Hadir (Alpa)", "badge-danger"),
            "bersedia": ("Bersedia", "badge-success"),
            "menunggu": ("Menunggu Koordinasi", "badge-warning")
        }
        text, css_class = labels.get(str(status_code).lower(), (str(status_code), "badge-secondary"))
        return f'<span class="badge {css_class}">{text}</span>'

    # Penanganan Error
    @app.errorhandler(400)
    def bad_request(error):
        return render_template("errors/400.html", description=error.description), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("errors/403.html", description=error.description), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        return render_template("errors/500.html"), 500

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
