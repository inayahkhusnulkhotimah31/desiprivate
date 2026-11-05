"""
DESI PRIVAT - Audit Service
Mencatat riwayat aktivitas penting (audit trail) untuk Admin dan Pemilik.
Catatan audit bersifat append-only dan tidak dapat diubah/dihapus via antarmuka.
"""
from services.database_service import execute_db, query_db

def log_audit(user_id, user_name, action_type, target_entity, target_id, details, ip_address="127.0.0.1"):
    """Mencatat aktivitas ke tabel audit_logs."""
    query = """
        INSERT INTO audit_logs (user_id, user_name, action_type, target_entity, target_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    return execute_db(query, (user_id, user_name, action_type, target_entity, str(target_id) if target_id else None, details, ip_address))

def get_audit_logs(limit=100, action_type=None, target_entity=None, start_date=None, end_date=None):
    """Mengambil daftar riwayat audit dengan filter."""
    conditions = []
    args = []

    if action_type:
        conditions.append("action_type = ?")
        args.append(action_type)
    if target_entity:
        conditions.append("target_entity = ?")
        args.append(target_entity)
    if start_date:
        conditions.append("date(created_at) >= ?")
        args.append(start_date)
    if end_date:
        conditions.append("date(created_at) <= ?")
        args.append(end_date)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
        SELECT id, user_id, user_name, action_type, target_entity, target_id, details, ip_address, created_at
        FROM audit_logs
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ?
    """
    args.append(limit)
    return query_db(query, args)
