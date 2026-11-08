"""
DESI PRIVAT - Audit Service
Mencatat riwayat aktivitas penting (audit trail) untuk Admin, Pemilik, dan Developer.
Mendukung pelacakan perubahan data siswa tingkat field (field-level diffs: old vs new values),
pencatatan modul, status kode, dan siaran real-time untuk developer monitoring.
Catatan audit bersifat append-only dan tidak dapat diubah/dihapus via antarmuka.
"""
import json
import threading
import queue
from datetime import datetime
from services.database_service import execute_db, query_db

# Antrean pesan real-time (Pub/Sub) untuk Developer Live Monitoring Feed
_dev_subscribers = []
_dev_sub_lock = threading.Lock()

def register_dev_subscriber():
    """Mendaftarkan subscriber baru untuk Server-Sent Events (SSE) developer feed."""
    q = queue.Queue(maxsize=100)
    with _dev_sub_lock:
        _dev_subscribers.append(q)
    return q

def unregister_dev_subscriber(q):
    """Menghapus subscriber SSE developer feed."""
    with _dev_sub_lock:
        if q in _dev_subscribers:
            _dev_subscribers.remove(q)

def _broadcast_to_devs(event_data):
    """Menyiarkan aktivitas terbaru ke seluruh subscriber dashboard developer yang sedang online."""
    with _dev_sub_lock:
        dead = []
        for q in _dev_subscribers:
            try:
                q.put_nowait(event_data)
            except (queue.Full, Exception):
                dead.append(q)
        for d in dead:
            if d in _dev_subscribers:
                _dev_subscribers.remove(d)

def infer_module_name(action_type, target_entity):
    """Menentukan modul aktivitas secara otomatis berdasarkan action_type dan target_entity."""
    act = (action_type or "").upper()
    ent = (target_entity or "").lower()

    if "LOGIN" in act or "LOGOUT" in act or ent == "users":
        return "Autentikasi"
    elif "PROGRAM" in act or ent in ("student_programs", "programs"):
        return "Program Siswa"
    elif "SISWA" in act or ent in ("students", "parents"):
        return "Siswa"
    elif "JADWAL" in act or "SCHEDULE" in act or ent in ("schedules", "routine_schedules"):
        return "Jadwal"
    elif "ABSENSI" in act or "ATTENDANCE" in act or ent in ("attendance", "student_progress"):
        return "Absensi"
    elif "MENTOR" in act or ent in ("mentors", "mentor_availability"):
        return "Mentor"
    elif "BACKUP" in act or ent == "backups":
        return "Backup"
    elif "DEVELOPER" in act:
        return "Developer"
    return "Operasional"

def compute_field_diff(old_data, new_data, ignored_keys=("created_at", "updated_at", "csrf_token")):
    """
    Membandingkan dictionary data lama dengan data baru.
    Mengembalikan (fields_changed, old_values_dict, new_values_dict).
    """
    if not old_data or not new_data:
        return [], {}, {}

    changed_fields = []
    old_diff = {}
    new_diff = {}

    for key, new_val in new_data.items():
        if key in ignored_keys:
            continue
        if key in old_data:
            old_val = old_data[key]
            # Normalisasi perbandingan string vs None vs int
            str_old = "" if old_val is None else str(old_val).strip()
            str_new = "" if new_val is None else str(new_val).strip()
            if str_old != str_new:
                changed_fields.append(key)
                old_diff[key] = old_val
                new_diff[key] = new_val

    return changed_fields, old_diff, new_diff

def log_audit(
    user_id, user_name, action_type, target_entity, target_id, details,
    ip_address="127.0.0.1", module_name=None, old_values=None, new_values=None,
    fields_changed=None, status_code=200
):
    """
    Mencatat aktivitas ke tabel audit_logs dengan dukungan pelacakan diff field-level.
    Menyiarkan event secara real-time ke Developer Live Feed.
    """
    if not module_name:
        module_name = infer_module_name(action_type, target_entity)

    # Serialisasi diff jika berupa dictionary / list
    old_str = json.dumps(old_values, ensure_ascii=False) if isinstance(old_values, (dict, list)) else (str(old_values) if old_values else None)
    new_str = json.dumps(new_values, ensure_ascii=False) if isinstance(new_values, (dict, list)) else (str(new_values) if new_values else None)
    fields_str = json.dumps(fields_changed, ensure_ascii=False) if isinstance(fields_changed, (list, tuple)) else (str(fields_changed) if fields_changed else None)

    query = """
        INSERT INTO audit_logs (
            user_id, user_name, action_type, module_name, target_entity, target_id,
            details, old_values, new_values, fields_changed, status_code, ip_address
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    row_id = execute_db(query, (
        user_id, user_name, action_type, module_name, target_entity,
        str(target_id) if target_id else None, details,
        old_str, new_str, fields_str, status_code, ip_address
    ))

    # Kirim ke real-time subscriber jika ada
    event_payload = {
        "id": row_id,
        "user_id": user_id,
        "user_name": user_name,
        "action_type": action_type,
        "module_name": module_name,
        "target_entity": target_entity,
        "target_id": str(target_id) if target_id else None,
        "details": details,
        "old_values": old_str,
        "new_values": new_str,
        "fields_changed": fields_str,
        "status_code": status_code,
        "ip_address": ip_address,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    _broadcast_to_devs(event_payload)

    return row_id

def get_audit_logs(
    limit=100, action_type=None, target_entity=None, module_name=None,
    user_name=None, start_date=None, end_date=None, since_id=None
):
    """Mengambil daftar riwayat audit dengan berbagai filter interaktif."""
    conditions = []
    args = []

    if since_id:
        conditions.append("id > ?")
        args.append(int(since_id))
    if action_type:
        conditions.append("action_type = ?")
        args.append(action_type)
    if module_name:
        conditions.append("module_name = ?")
        args.append(module_name)
    if user_name:
        conditions.append("user_name LIKE ?")
        args.append(f"%{user_name}%")
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
        SELECT id, user_id, user_name, action_type, module_name, target_entity,
               target_id, details, old_values, new_values, fields_changed,
               status_code, ip_address, created_at
        FROM audit_logs
        {where_clause}
        ORDER BY id DESC
        LIMIT ?
    """
    args.append(limit)
    return query_db(query, args)

def get_student_change_logs(student_id=None, limit=50):
    """Mengambil riwayat khusus perubahan field-level data siswa."""
    query = """
        SELECT id, user_id, user_name, action_type, module_name, target_entity,
               target_id, details, old_values, new_values, fields_changed,
               status_code, ip_address, created_at
        FROM audit_logs
        WHERE (target_entity = 'students' OR target_entity = 'student_programs')
          AND fields_changed IS NOT NULL AND fields_changed != ''
    """
    args = []
    if student_id:
        query += " AND target_id = ?"
        args.append(str(student_id))

    query += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    return query_db(query, args)
