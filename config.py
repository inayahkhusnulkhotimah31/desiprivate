"""
DESI PRIVAT - Konfigurasi Aplikasi (Produksi & Pengembangan)
Sistem Informasi Manajemen Tempat Les Privat
"""
import os
import sys
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent

# Deteksi otomatis virtual environment lokal (.venv) jika ada
_local_venv = BASE_DIR / ".venv" / "Lib" / "site-packages"
if _local_venv.exists() and str(_local_venv) not in sys.path:
    sys.path.insert(0, str(_local_venv))

# Fallback path jika dependensi terpasang di Python 3.11 pengguna
_py311_site = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python311" / "Lib" / "site-packages"
if _py311_site.exists() and str(_py311_site) not in sys.path:
    sys.path.append(str(_py311_site))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v


class Config:
    """Konfigurasi dasar aplikasi Flask DESI PRIVAT."""
    DEBUG = False
    TESTING = False

    # Keamanan dan Session
    SECRET_KEY = os.getenv("SECRET_KEY", "kunci-default-pengembangan-desi-privat-2026")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)

    # Database dan Direktori Backup
    IS_VERCEL = bool(os.getenv("VERCEL"))
    if IS_VERCEL:
        import tempfile
        _temp_base = Path(tempfile.gettempdir())
        _tmp_db = _temp_base / "desi_privat.db"
        _seed_db = BASE_DIR / "database" / "desi_privat.db"
        if not _tmp_db.exists() and _seed_db.exists():
            import shutil
            try:
                shutil.copy2(_seed_db, _tmp_db)
            except Exception:
                pass
        DATABASE_PATH = str(_tmp_db)
        BACKUP_DIR = str(_temp_base / "backups")
    else:
        DB_NAME = os.getenv("DATABASE_PATH", "database/desi_privat.db")
        DATABASE_PATH = str(BASE_DIR / DB_NAME if not os.path.isabs(DB_NAME) else Path(DB_NAME))
        BACKUP_DIR = str(BASE_DIR / os.getenv("BACKUP_DIR", "backups"))

    # Batas Waktu Respons Mentor (dalam Jam)
    SCHEDULE_RESPONSE_TIMEOUT_HOURS = int(os.getenv("SCHEDULE_RESPONSE_TIMEOUT_HOURS", "24"))

    # Mode Uji WhatsApp
    WHATSAPP_TEST_MODE = True

    # Supabase Cloud Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
    SUPABASE_JWKS_URL = os.getenv("SUPABASE_JWKS_URL", "")


class DevelopmentConfig(Config):
    """Konfigurasi mode pengembangan lokal."""
    DEBUG = True


class ProductionConfig(Config):
    """Konfigurasi mode produksi dan hosting siap pakai."""
    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY", "prod-desi-privat-secret-change-in-env-key-2026")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1", "yes")


class TestingConfig(Config):
    """Konfigurasi untuk automated test suite."""
    TESTING = True
    DEBUG = False
    DATABASE_PATH = str(BASE_DIR / "database" / "test_desi_privat.db")


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": ProductionConfig if os.getenv("FLASK_ENV") == "production" else DevelopmentConfig
}
