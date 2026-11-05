"""
DESI PRIVAT - Backup & Restore Service
Layanan pencadangan dan pemulihan database SQLite yang konsisten, aman, dan tervalidasi.
Menyediakan pembuatan cadangan otomatis sebelum pemulihan (pre-restore snapshot)
serta verifikasi integritas file.
"""
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from config import Config
from services.database_service import execute_db, query_db, get_direct_connection
from services.audit_service import log_audit

def ensure_backup_dir():
    """Memastikan folder backup tersedia."""
    os.makedirs(Config.BACKUP_DIR, exist_ok=True)
    return Config.BACKUP_DIR

def create_backup(created_by="admin", notes="Pencadangan rutin manual"):
    """
    Membuat backup database SQLite secara konsisten menggunakan backup API SQLite.
    Menyimpan file di folder backups/ dan mencatatnya ke tabel backups.
    """
    b_dir = ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"desi_privat_backup_{timestamp}.db"
    target_path = os.path.join(b_dir, filename)

    src_conn = get_direct_connection(Config.DATABASE_PATH)
    dest_conn = sqlite3.connect(target_path)
    try:
        # Gunakan backup API bawaan SQLite agar atomic dan konsisten
        with dest_conn:
            src_conn.backup(dest_conn, pages=100)
    finally:
        dest_conn.close()
        src_conn.close()

    # Periksa ukuran file
    file_size = os.path.getsize(target_path)

    # Catat ke tabel backups
    backup_id = execute_db("""
        INSERT INTO backups (filename, filepath, file_size, created_by, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (filename, target_path, file_size, created_by, notes))

    # Audit log
    log_audit(
        None,
        created_by,
        "BACKUP_DATABASE",
        "backups",
        backup_id,
        f"Membuat backup database: {filename} (Ukuran: {file_size} byte)"
    )

    return {
        "success": True,
        "backup_id": backup_id,
        "filename": filename,
        "filepath": target_path,
        "file_size": file_size,
        "message": f"Backup database berhasil dibuat: {filename}"
    }

def list_backups():
    """Mengambil daftar riwayat backup dari database dan folder."""
    rows = query_db("""
        SELECT id, filename, filepath, file_size, created_by, notes, created_at
        FROM backups
        ORDER BY created_at DESC
    """)
    backups = []
    for r in rows:
        d = dict(r)
        d["exists_on_disk"] = os.path.exists(d["filepath"])
        backups.append(d)
    return backups

def validate_backup_file(filepath):
    """
    Memvalidasi apakah file backup valid, bukan korup, dan memiliki tabel-tabel utama DESI PRIVAT.
    """
    if not os.path.exists(filepath):
        return {"valid": False, "message": "File backup tidak ditemukan pada media penyimpanan."}

    if os.path.getsize(filepath) < 1024:
        return {"valid": False, "message": "Ukuran file terlalu kecil atau tidak valid."}

    try:
        test_conn = sqlite3.connect(filepath)
        test_cur = test_conn.cursor()

        # 1. Cek integritas SQLite
        test_cur.execute("PRAGMA quick_check;")
        check_result = test_cur.fetchone()
        if not check_result or check_result[0] != "ok":
            test_conn.close()
            return {"valid": False, "message": "File database korup atau gagal uji integritas SQLite."}

        # 2. Cek keberadaan tabel-tabel esensial
        test_cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in test_cur.fetchall()]
        required_tables = ["users", "students", "mentors", "schedules", "attendance"]
        missing = [t for t in required_tables if t not in tables]

        test_conn.close()

        if missing:
            return {
                "valid": False,
                "message": f"File backup tidak memiliki tabel penting: {', '.join(missing)}."
            }

        return {"valid": True, "message": "File backup terverifikasi valid dan siap dipulihkan."}
    except Exception as e:
        return {"valid": False, "message": f"Kesalahan saat membaca file database: {str(e)}"}

def restore_backup(backup_id, requested_by="admin"):
    """
    Memulihkan database dari file backup yang dipilih.
    Langkah pengamanan:
    1. Validasi file backup tujuan
    2. Buat snapshot backup dari database aktif saat ini (pre-restore snapshot)
    3. Pulihkan database
    4. Tangani kegagalan tanpa merusak database aktif
    5. Catat audit log
    """
    backup_row = query_db("SELECT * FROM backups WHERE id = ?", (backup_id,), one=True)
    if not backup_row:
        return {"success": False, "message": "Catatan backup tidak ditemukan di sistem."}

    target_backup_file = backup_row["filepath"]

    # 1. Validasi file backup
    validation = validate_backup_file(target_backup_file)
    if not validation["valid"]:
        return {"success": False, "message": f"Restorasi dibatalkan: {validation['message']}"}

    # 2. Buat backup otomatis dari database aktif sekarang sebelum ditimpa
    pre_restore = create_backup(
        created_by=requested_by,
        notes=f"Pencadangan otomatis sebelum restore dari backup ID {backup_id} ({backup_row['filename']})"
    )
    if not pre_restore["success"]:
        return {"success": False, "message": "Gagal membuat snapshot database aktif sebelum restore. Operasi dibatalkan demi keamanan."}

    # 3. Proses pemulihan database
    active_db_path = Config.DATABASE_PATH
    temp_restored_db = active_db_path + ".restoring"

    try:
        # Salin file backup ke lokasi sementara terlebih dahulu
        shutil.copy2(target_backup_file, temp_restored_db)

        # Uji koneksi ke file hasil salinan
        val_temp = validate_backup_file(temp_restored_db)
        if not val_temp["valid"]:
            if os.path.exists(temp_restored_db):
                os.remove(temp_restored_db)
            return {"success": False, "message": "File hasil persiapan restore tidak valid."}

        # Ganti database aktif dengan file yang sudah dipulihkan
        # Di Windows, file yang sedang terbuka oleh process lain bisa terkunci,
        # sehingga kita gunakan copy2 langsung menimpa atau rename aman
        shutil.copy2(temp_restored_db, active_db_path)
        if os.path.exists(temp_restored_db):
            os.remove(temp_restored_db)

        # 4. Catat audit log pada database yang baru dipulihkan
        log_audit(
            None,
            requested_by,
            "RESTORE_DATABASE",
            "backups",
            backup_id,
            f"Database berhasil dipulihkan dari file {backup_row['filename']}. Snapshot pengaman tersimpan di {pre_restore['filename']}."
        )

        return {
            "success": True,
            "message": f"Database berhasil dipulihkan dari {backup_row['filename']}. Data sebelum restore telah dicadangkan aman ke {pre_restore['filename']}."
        }
    except Exception as e:
        if os.path.exists(temp_restored_db):
            os.remove(temp_restored_db)
        return {
            "success": False,
            "message": f"Terjadi kesalahan saat memulihkan database: {str(e)}. Database aktif tetap aman."
        }
