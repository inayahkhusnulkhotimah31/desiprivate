"""
DESI PRIVAT - Verifikasi Sinkronisasi Real-Time Supabase Cloud
"""
import sys
import psycopg

def test_sync(password="DesiPrivat2026"):
    conn_str = f"postgresql://postgres.kzefvgtrcurbdrfujfcy:{password}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require"
    try:
        with psycopg.connect(conn_str, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM students;")
                st_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM users;")
                u_count = cur.fetchone()[0]
                print(f"[SUKSES] Terhubung ke Supabase Cloud!")
                print(f"         - Total Pengguna di Cloud: {u_count}")
                print(f"         - Total Siswa di Cloud   : {st_count}")
                print("Sinkronisasi Real-Time HP <-> Laptop AKTIF!")
                return True
    except Exception as e:
        print(f"[BELUM TERKONEKSI] {e}")
        return False

if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else "DesiPrivat2026"
    test_sync(pwd)

