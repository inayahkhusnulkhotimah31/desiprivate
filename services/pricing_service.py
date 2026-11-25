"""
DESI PRIVAT - Centralized Pricing Service
Layanan perhitungan dan penetapan tarif les terpusat berdasarkan:
1. Jenis Layanan: Private Tutoring (Tatap Muka), Kelas Online, atau Program Khusus
2. Jenjang Pendidikan: SD, SMP, SMA, atau Program Khusus
Tarif ditentukan berdasarkan jenis layanan dan jenjang pendidikan, bukan nama mata pelajaran.
"""
from services.database_service import query_db, execute_db

# Matriks tarif resmi brosur DESI PRIVAT
OFFICIAL_RATE_MATRIX = {
    # 1. Private Tutoring (Tatap Muka)
    ("Private Tutoring", "SD"): 75000.0,
    ("Private Tutoring", "SMP"): 90000.0,
    ("Private Tutoring", "SMA"): 120000.0,
    ("Private Tutoring", "Semua Jenjang"): 90000.0,
    ("Private Tutoring", "Umum"): 90000.0,

    # 2. Paket Kelas Online
    ("Kelas Online", "SD"): 50000.0,
    ("Kelas Online", "SMP"): 65000.0,
    ("Kelas Online", "SMA"): 75000.0,
    ("Kelas Online", "Semua Jenjang"): 65000.0,
    ("Kelas Online", "Umum"): 65000.0,

    # 3. Program Khusus
    ("Program Khusus", "SD"): 100000.0,
    ("Program Khusus", "SMP"): 120000.0,
    ("Program Khusus", "SMA"): 150000.0,
    ("Program Khusus", "Semua Jenjang"): 150000.0,
    ("Program Khusus", "Umum"): 150000.0,
    ("Program Khusus", "Kedinasan / CPNS / SNBT"): 200000.0,
    ("Program Khusus", "Psikotes / Akademik Polisi"): 150000.0,
    ("Program Khusus", "Bimbingan KTI"): 100000.0,
}

def normalize_education_level(level_str=None, student_grade=None):
    """Mendeteksi dan menormalkan jenjang pendidikan (SD, SMP, SMA, atau Umum) dari string level atau kelas siswa."""
    combined = f"{level_str or ''} {student_grade or ''}".upper()
    if any(k in combined for k in ("SMA", "SMK", "MA ", "KELAS 10", "KELAS 11", "KELAS 12")):
        return "SMA"
    elif any(k in combined for k in ("SMP", "MTS", "KELAS 7", "KELAS 8", "KELAS 9")):
        return "SMP"
    elif any(k in combined for k in ("SD", "MI ", "KELAS 1", "KELAS 2", "KELAS 3", "KELAS 4", "KELAS 5", "KELAS 6", "TK", "PAUD", "CALISTUNG")):
        return "SD"
    return "Semua Jenjang"

def get_tuition_rate_per_session(service_type="Private Tutoring", level="SD", student_grade=None, program_name=None, db_path=None):
    """
    Mengambil tarif resmi les per sesi berdasarkan Jenis Layanan dan Jenjang Pendidikan.
    """
    st = (service_type or "Private Tutoring").strip()
    lvl = normalize_education_level(level, student_grade)

    # Deteksi program khusus berdasarkan nama program jika ada
    p_name = (program_name or "").upper()
    if any(k in p_name for k in ("SNBT", "UTBK", "CPNS", "KEDINASAN")):
        st = "Program Khusus"
        lvl = "Kedinasan / CPNS / SNBT"
    elif any(k in p_name for k in ("POLISI", "PSIKOTES", "AKADEMIK POLISI")):
        st = "Program Khusus"
        lvl = "Psikotes / Akademik Polisi"
    elif any(k in p_name for k in ("KTI", "KARYA TULIS")):
        st = "Program Khusus"
        lvl = "Bimbingan KTI"

    # 1. Cari dari tabel service_pricing_rules di database jika ada
    try:
        rule = query_db("""
            SELECT rate_per_session FROM service_pricing_rules
            WHERE service_type = ? AND education_level = ?
        """, (st, lvl), one=True, db_path=db_path)
        if rule and rule["rate_per_session"]:
            return float(rule["rate_per_session"])
    except Exception:
        pass

    # 2. Fallback ke matriks resmi brosur
    return OFFICIAL_RATE_MATRIX.get((st, lvl), OFFICIAL_RATE_MATRIX.get((st, "SD"), 75000.0))

def calculate_package_tuition_fee(service_type, level, meetings_per_period=8, student_grade=None, program_name=None, custom_fee=None, db_path=None):
    """
    Menghitung total biaya paket les untuk periode bimbingan:
    - Jika custom_fee diberikan dan bernilai > 0, gunakan tarif khusus hasil kesepakatan.
    - Jika tidak, hitung otomatis: (tarif per sesi) × (jumlah pertemuan: 4, 8, atau 12 sesi).
    Mengembalikan: (total_amount, rate_per_session, is_custom)
    """
    mpp = int(meetings_per_period or 8)
    if custom_fee is not None and str(custom_fee).strip() != "":
        try:
            val = float(custom_fee)
            if val > 0:
                return val, val / mpp, True
        except (ValueError, TypeError):
            pass

    rate = get_tuition_rate_per_session(service_type, level, student_grade=student_grade, program_name=program_name, db_path=db_path)
    total = rate * mpp
    return total, rate, False
