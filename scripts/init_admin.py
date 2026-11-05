"""
DESI PRIVAT - Inisialisasi Akun Admin Produksi
Script CLI untuk inisialisasi / reset kredensial akun admin di lingkungan hosting.
"""
import sys
import getpass
from pathlib import Path
from werkzeug.security import generate_password_hash

# Tambahkan root direktori ke path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config
from services.database_service import get_direct_connection, init_db

def init_admin():
    print("=== DESI PRIVAT - SETUP AKUN ADMINISTRATOR ===")
    init_db()

    username = input("Masukkan username admin [admin]: ").strip() or "admin"
    full_name = input("Masukkan nama lengkap [Administrator DESI]: ").strip() or "Administrator DESI"
    email = input("Masukkan email [admin@desiprivat.id]: ").strip() or "admin@desiprivat.id"
    phone = input("Masukkan no. telepon [081234567801]: ").strip() or "081234567801"

    password = getpass.getpass("Masukkan password admin (min 6 karakter): ").strip()
    if not password:
        password = "admin123"
        print("Menggunakan password default: admin123")
    elif len(password) < 6:
        print("Error: Password minimal 6 karakter.")
        return

    password_hash = generate_password_hash(password)

    conn = get_direct_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    existing = cur.fetchone()

    if existing:
        cur.execute("""
            UPDATE users
            SET password_hash = ?, full_name = ?, email = ?, phone = ?, role = 'admin', is_active = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (password_hash, full_name, email, phone, existing[0]))
        print(f"Berhasil: Akun admin '{username}' telah diperbarui!")
    else:
        cur.execute("""
            INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
            VALUES (?, ?, 'admin', ?, ?, ?, 1)
        """, (username, password_hash, full_name, email, phone))
        print(f"Berhasil: Akun admin '{username}' telah dibuat!")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_admin()

