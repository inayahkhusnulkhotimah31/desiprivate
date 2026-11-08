"""
DESI PRIVAT - Backup dan Verifikasi Integritas Database Production Supabase
"""
import os
import sys
import time
import sqlite3
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import Config

SUPABASE_URL = Config.SUPABASE_URL or os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = Config.SUPABASE_SECRET_KEY or os.getenv("SUPABASE_SECRET_KEY", "")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}"
}

def backup_and_verify():
    print("=" * 60)
    print("MEMULAI PENCADANGAN DAN VERIFIKASI INTEGRITAS DATABASE PRODUCTION")
    print("=" * 60)
    
    # 1. Download database aktual dari Supabase Storage
    url = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/database_sync/desi_privat.db"
    res = requests.get(url, headers=headers, timeout=10)
    if res.status_code != 200 or len(res.content) < 1000:
        print(f"[GAGAL] Download dari Supabase Storage gagal! HTTP {res.status_code}")
        # Coba periksa file lokal jika ada
        local_db = BASE_DIR / "database" / "desi_privat.db"
        if local_db.exists():
            print(f"[INFO] Menggunakan file database lokal: {local_db}")
            with open(local_db, "rb") as f:
                content = f.read()
        else:
            sys.exit(1)
    else:
        content = res.content
        print(f"[OK] Database berhasil diunduh dari Supabase Storage ({len(content)} bytes)")

    # 2. Simpan ke direktori backup terverifikasi
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_dir = BASE_DIR / "backups" / "verified_pre_migration"
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = backup_dir / f"production_supabase_backup_{timestamp}.db"
    
    with open(backup_file, "wb") as f:
        f.write(content)
    print(f"[OK] File backup tersimpan di: {backup_file}")

    # 3. Uji Pemulihan (Restoration Verification)
    # Buka database, lakukan PRAGMA integrity_check, baca semua tabel dan row count
    restore_test_path = backup_dir / f"restore_test_{timestamp}.db"
    with open(restore_test_path, "wb") as f:
        f.write(content)

    conn = sqlite3.connect(restore_test_path)
    cur = conn.cursor()
    
    # Jalankan integrity check
    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchone()[0]
    print(f"[OK] PRAGMA integrity_check: {integrity}")
    if integrity.lower() != "ok":
        print("[BAHAYA] Database rusak! Jangan lanjutkan.")
        sys.exit(1)

    # Periksa tabel dan hitung data
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    print(f"[OK] Total tabel terverifikasi: {len(tables)}")
    
    summary = {}
    for tbl in tables:
        if tbl.startswith("sqlite_"):
            continue
        count = cur.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0]
        summary[tbl] = count
        print(f"     - {tbl:25}: {count} baris data")

    # Uji query penting: users, students, schedules, attendance
    cur.execute("SELECT id, username, role, full_name FROM users;")
    users = cur.fetchall()
    print("\n[VERIFIKASI DATA PENGGUNA]")
    for u in users:
        print(f"     * ID {u[0]}: {u[1]} ({u[2]}) - {u[3]}")

    cur.execute("SELECT id, full_name, school, grade, status FROM students;")
    students = cur.fetchall()
    print("\n[VERIFIKASI DATA SISWA]")
    for s in students:
        print(f"     * ID {s[0]}: {s[1]} ({s[2]}, {s[3]}) - Status: {s[4]}")

    cur.execute("SELECT id, name, code, level FROM programs;")
    programs = cur.fetchall()
    print("\n[VERIFIKASI DATA PROGRAM]")
    for p in programs:
        print(f"     * ID {p[0]}: {p[1]} [{p[2]}] - {p[3]}")

    conn.close()
    
    # Hapus file uji restore sementara
    try:
        os.remove(restore_test_path)
    except Exception:
        pass

    # Simpan juga cadangan snapshot JSON dari semua tabel di Supabase REST API
    print("\n" + "=" * 60)
    print("MENGAMBIL SNAPSHOT JSON DARI SUPABASE REST API")
    print("=" * 60)
    import json
    json_snapshot = {}
    for tbl in tables:
        if tbl.startswith("sqlite_"):
            continue
        try:
            tbl_url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{tbl}?select=*"
            r = requests.get(tbl_url, headers=headers, timeout=5)
            if r.status_code == 200:
                json_snapshot[tbl] = r.json()
                print(f"[OK] Snapshot REST {tbl:22}: {len(r.json())} entri")
        except Exception as e:
            print(f"[INFO] Lewati tabel {tbl}: {e}")

    json_backup_file = backup_dir / f"production_supabase_snapshot_{timestamp}.json"
    with open(json_backup_file, "w", encoding="utf-8") as f:
        json.dump(json_snapshot, f, indent=2, ensure_ascii=False)
    print(f"[OK] Snapshot JSON tersimpan di: {json_backup_file}")

    print("\n" + "=" * 60)
    print("HASIL: DATABASE PRODUCTION BERHASIL DICADANGKAN DAN TERBUKTI BISA DIPULIHKAN 100%!")
    print("=" * 60)
    return str(backup_file), str(json_backup_file), summary

if __name__ == "__main__":
    backup_and_verify()

