import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
_local_venv = BASE_DIR / ".venv" / "Lib" / "site-packages"
if _local_venv.exists():
    sys.path.insert(0, str(_local_venv))
sys.path.insert(0, str(BASE_DIR))

import requests
from config import Config

SUPABASE_URL = Config.SUPABASE_URL
SUPABASE_KEY = Config.SUPABASE_SECRET_KEY
BUCKET_NAME = "database_sync"
FILE_NAME = "desi_privat.db"

db_file = BASE_DIR / "database" / "desi_privat.db"
print(f"Mengunggah {db_file} ({db_file.stat().st_size} bytes) ke Supabase Storage...")

upload_url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/{BUCKET_NAME}/{FILE_NAME}"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/x-sqlite3",
    "x-upsert": "true"
}

with open(db_file, "rb") as f:
    content = f.read()

res = requests.post(upload_url, headers=headers, data=content, timeout=10)
print(f"Status response: HTTP {res.status_code}")
if res.status_code == 200:
    print("[SUCCESS] Database produksi di Supabase Cloud Storage berhasil disinkronisasi!")
else:
    print(f"[RESPONSE] {res.text}")
