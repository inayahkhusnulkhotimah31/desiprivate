"""
DESI PRIVAT - Notification Service
Layanan pengelolaan notifikasi in-app untuk pengguna (Admin, Pemilik, Mentor, Orang Tua).
"""
from services.database_service import execute_db, query_db

def create_notification(user_id, title, message, notif_type="info", reference_url=None):
    """Membuat notifikasi baru untuk pengguna tertentu."""
    query = """
        INSERT INTO notifications (user_id, title, message, type, is_read, reference_url)
        VALUES (?, ?, ?, ?, 0, ?)
    """
    return execute_db(query, (user_id, title, message, notif_type, reference_url))

def notify_admins(title, message, notif_type="info", reference_url=None):
    """Mengirim notifikasi ke semua pengguna dengan role admin."""
    admins = query_db("SELECT id FROM users WHERE role = 'admin' AND is_active = 1")
    for adm in admins:
        create_notification(adm["id"], title, message, notif_type, reference_url)

def get_user_notifications(user_id, limit=30, unread_only=False):
    """Mengambil daftar notifikasi milik pengguna."""
    if unread_only:
        query = """
            SELECT id, user_id, title, message, type, is_read, reference_url, created_at
            FROM notifications
            WHERE user_id = ? AND is_read = 0
            ORDER BY created_at DESC
            LIMIT ?
        """
    else:
        query = """
            SELECT id, user_id, title, message, type, is_read, reference_url, created_at
            FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
    return query_db(query, (user_id, limit))

def get_unread_count(user_id):
    """Menghitung jumlah notifikasi yang belum dibaca."""
    row = query_db(
        "SELECT COUNT(*) as unread_count FROM notifications WHERE user_id = ? AND is_read = 0",
        (user_id,),
        one=True
    )
    return row["unread_count"] if row else 0

def mark_as_read(notification_id, user_id=None):
    """Menandai satu notifikasi sebagai sudah dibaca."""
    if user_id:
        query = "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?"
        return execute_db(query, (notification_id, user_id))
    else:
        query = "UPDATE notifications SET is_read = 1 WHERE id = ?"
        return execute_db(query, (notification_id,))

def mark_all_as_read(user_id):
    """Menandai semua notifikasi pengguna sebagai sudah dibaca."""
    query = "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0"
    return execute_db(query, (user_id,))
