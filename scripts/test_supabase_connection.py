"""
DESI PRIVAT - Script Pengujian Koneksi Database Supabase Cloud & Sinkronisasi
Mengecek konektivitas REST API dan PostgreSQL (jika DATABASE_URL diatur).
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import Config
import requests

def test_rest_api():
    print("=" * 60)
    print("1. PENGUJIAN SUPABASE REST API")
    print("=" * 60)
    url = f"{Config.SUPABASE_URL.rstrip('/')}/rest/v1/users?select=id,username,role,full_name"
    headers = {
        "apikey": Config.SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {Config.SUPABASE_SECRET_KEY}"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            users = res.json()
            print(f"[OK] Berhasil terhubung ke Supabase REST API! (Status: {res.status_code})")
            print(f"[OK] Ditemukan {len(users)} pengguna terdaftar di Cloud Database:")
            for u in users:
                print(f"     - User ID {u.get('id')}: {u.get('username')} ({u.get('role')}) - {u.get('full_name')}")
            return True
        else:
            print(f"[GAGAL] HTTP {res.status_code}: {res.text}")
            return False
    except Exception as e:
        print(f"[GAGAL] Error koneksi: {e}")
        return False

def test_postgres_connection():
    print("\n" + "=" * 60)
    print("2. PENGUJIAN DIRECT POSTGRESQL / TRANSACTION POOLER")
    print("=" * 60)
    db_url = Config.DATABASE_URL
    if not db_url:
        print("[INFO] DATABASE_URL belum diatur di .env.")
        print("       Untuk menghubungkan PostgreSQL langsung, tambahkan DATABASE_URL di .env atau Vercel:")
        print("       DATABASE_URL=postgresql://postgres.kzefvgtrcurbdrfujfcy:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require")
        return None

    try:
        import psycopg
        from psycopg.rows import dict_row
        print(f"[...] Menghubungkan ke PostgreSQL Supabase...")
        with psycopg.connect(db_url, row_factory=dict_row, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), current_user, version();")
                info = cur.fetchone()
                print(f"[OK] Sukses terhubung ke PostgreSQL!")
                print(f"     - Database: {info.get('current_database') if isinstance(info, dict) else info[0]}")
                print(f"     - User    : {info.get('current_user') if isinstance(info, dict) else info[1]}")
                
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                tables = [r['table_name'] if isinstance(r, dict) else r[0] for r in cur.fetchall()]
                print(f"[OK] Total {len(tables)} tabel public tersedia di Supabase.")
                return True
    except Exception as e:
        print(f"[GAGAL] Gagal menghubungkan ke PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    rest_ok = test_rest_api()
    pg_ok = test_postgres_connection()
    print("\n" + "=" * 60)
    print("RINGKASAN STATUS KONEKTIVITAS:")
    print(f"- Supabase REST API : {'AKTIF & TERHUBUNG' if rest_ok else 'GAGAL'}")
    print(f"- PostgreSQL Pooler : {'TERHUBUNG' if pg_ok else ('BELUM DIKONFIGURASI' if pg_ok is None else 'GAGAL')}")
    print("=" * 60)

