"""
DESI PRIVAT - Cloud Database Synchronization Service
Menyinkronkan database secara otomatis dan real-time ke Supabase Storage Cloud,
sehingga data tersinkronisasi 100% antara HP, Laptop, dan semua perangkat
secara instan tanpa perlu konfigurasi password manual dari pengguna.
"""
import os
import sys
import time
from pathlib import Path
import requests
from config import Config

SUPABASE_URL = Config.SUPABASE_URL
SUPABASE_KEY = Config.SUPABASE_SECRET_KEY
BUCKET_NAME = "database_sync"
FILE_NAME = "desi_privat.db"

_last_synced_etag = None
_last_check_time = 0
_db_dirty = False

def get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }

def mark_db_dirty():
    """Menandai bahwa ada perubahan data baru (INSERT/UPDATE/DELETE) yang perlu diunggah ke cloud."""
    global _db_dirty
    _db_dirty = True

def sync_from_cloud(force=False):
    """
    Mengunduh database terbaru dari Supabase Cloud jika ada perubahan dari perangkat lain.
    """
    global _last_synced_etag, _last_check_time
    if getattr(Config, "TESTING", False):
        return False

    now = time.time()
    # Batasi pemeriksaan maksimal 1 kali per 1.5 detik agar respon web sangat kencang
    if not force and (now - _last_check_time) < 1.5:
        return False
    _last_check_time = now

    target_path = Path(Config.DATABASE_PATH)

    try:
        info_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/info/{BUCKET_NAME}/{FILE_NAME}"
        r = requests.get(info_url, headers=get_headers(), timeout=3)
        if r.status_code == 200:
            remote_etag = r.json().get("etag")
            if remote_etag and (remote_etag != _last_synced_etag or not target_path.exists()):
                download_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/{BUCKET_NAME}/{FILE_NAME}"
                res = requests.get(download_url, headers=get_headers(), timeout=5)
                if res.status_code == 200 and len(res.content) > 1000:
                    os.makedirs(target_path.parent, exist_ok=True)
                    with open(target_path, "wb") as f:
                        f.write(res.content)
                    try:
                        os.chmod(target_path, 0o666)
                    except Exception:
                        pass
                    _last_synced_etag = remote_etag
                    return True
        return False
    except Exception as e:
        print(f"[CLOUD SYNC] Catatan sinkronisasi masuk: {e}", file=sys.stderr)
        return False

def sync_to_cloud():
    """
    Mengunggah database lokal ke Supabase Cloud jika ada data yang baru diubah.
    """
    global _db_dirty, _last_synced_etag
    if getattr(Config, "TESTING", False):
        return False

    if not _db_dirty:
        return False

    target_path = Path(Config.DATABASE_PATH)
    if not target_path.exists():
        return False

    try:
        upload_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/{BUCKET_NAME}/{FILE_NAME}"
        headers = {
            **get_headers(),
            "Content-Type": "application/x-sqlite3",
            "x-upsert": "true"
        }
        with open(target_path, "rb") as f:
            content = f.read()

        res = requests.post(upload_url, headers=headers, data=content, timeout=5)
        if res.status_code == 200:
            _db_dirty = False
            info_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/info/{BUCKET_NAME}/{FILE_NAME}"
            info_r = requests.get(info_url, headers=get_headers(), timeout=3)
            if info_r.status_code == 200:
                _last_synced_etag = info_r.json().get("etag")
            return True
        return False
    except Exception as e:
        print(f"[CLOUD SYNC] Catatan sinkronisasi keluar: {e}", file=sys.stderr)
        return False
