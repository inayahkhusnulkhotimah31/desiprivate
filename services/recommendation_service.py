"""
DESI PRIVAT - Recommendation Service (Langkah 4)
Layanan sistem rekomendasi mentor untuk membantu Admin menentukan mentor terbaik
berdasarkan tiga prioritas berjenjang:
1. Ketersediaan waktu & deteksi bentrokan jadwal (Prioritas Utama)
2. Kesesuaian mata pelajaran / program les dengan keahlian mentor
3. Jarak lokasi tempuh garis lurus (Haversine formula)

Sistem ini hanya memberikan rekomendasi dan kalkulasi kesesuaian.
Keputusan akhir pemilihan mentor tetap 100% manual di tangan Admin.
"""
import math
import re
from config import Config
from services.database_service import query_db

DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Menghitung jarak garis lurus (great-circle distance) dalam kilometer
    menggunakan rumus Haversine murni tanpa API eksternal.
    Mengembalikan None jika salah satu koordinat tidak tersedia / None.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    try:
        lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    except (ValueError, TypeError):
        return None

    # Radius bumi rata-rata dalam kilometer
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = R * c
    return round(distance, 2)


# Pemetaan sinonim kata kunci mata pelajaran umum untuk pencocokan semantik dasar
SUBJECT_KEYWORDS = {
    "matematika": ["math", "matematika", "hitung", "kalkulus", "aljabar", "geometri", "olimpiade"],
    "math": ["math", "matematika", "hitung", "aljabar", "olimpiade"],
    "english": ["english", "inggris", "bahasa inggris", "toefl", "conversation", "grammar"],
    "inggris": ["english", "inggris", "bahasa inggris", "grammar"],
    "ipa": ["ipa", "sains", "science", "biologi", "fisika", "kimia"],
    "biologi": ["biologi", "biology", "ipa", "sains"],
    "fisika": ["fisika", "physics", "ipa", "sains"],
    "kimia": ["kimia", "chemistry", "ipa", "sains"],
    "calistung": ["calistung", "baca", "tulis", "hitung", "sd", "dasar", "anak"],
    "mengaji": ["mengaji", "quran", "al-quran", "tajwid", "iqra", "islam", "tahsin", "tahfidz"],
}

def evaluate_expertise_match(mentor_expertise, program_name, program_desc=""):
    """
    Mencocokkan keahlian mentor dengan nama dan deskripsi program belajar.
    Pencocokan dilakukan secara wajar tanpa mengarang keahlian mentor.
    
    Skor:
    3: Kecocokan langsung pada nama program
    2: Kecocokan sinonim / rumpun mata pelajaran
    1: Kecocokan pada deskripsi program
    0: Keahlian belum teridentifikasi / tidak cocok
    """
    if not mentor_expertise or not mentor_expertise.strip():
        return {
            "score": 0,
            "matched": False,
            "label": "Keahlian Belum Teridentifikasi",
            "matched_keyword": None
        }

    exp_clean = mentor_expertise.lower()
    prog_name_clean = (program_name or "").lower()
    prog_desc_clean = (program_desc or "").lower()

    # Ekstrak token keahlian mentor (dipisahkan koma, slash, atau titik koma)
    raw_tokens = re.split(r"[,;/]+", exp_clean)
    mentor_tokens = [t.strip() for t in raw_tokens if t.strip()]

    # 1. Cek kecocokan langsung substring kata kunci
    for token in mentor_tokens:
        if token in prog_name_clean or prog_name_clean in token:
            return {
                "score": 3,
                "matched": True,
                "label": f"Keahlian Sesuai: {mentor_expertise.strip()}",
                "matched_keyword": token
            }

    # 2. Cek kecocokan melalui kamus sinonim rumpun ilmu
    for token in mentor_tokens:
        for root_key, synonyms in SUBJECT_KEYWORDS.items():
            if root_key in token or any(syn in token for syn in synonyms):
                # Periksa apakah ada sinonim yang cocok dengan nama program
                for syn in synonyms:
                    if syn in prog_name_clean:
                        return {
                            "score": 2,
                            "matched": True,
                            "label": f"Keahlian Relevan: {mentor_expertise.strip()}",
                            "matched_keyword": syn
                        }

    # 3. Cek kecocokan pada deskripsi program
    for token in mentor_tokens:
        if token in prog_desc_clean:
            return {
                "score": 1,
                "matched": True,
                "label": f"Keahlian Terkait Deskripsi: {mentor_expertise.strip()}",
                "matched_keyword": token
            }

    return {
        "score": 0,
        "matched": False,
        "label": "Keahlian Belum Teridentifikasi",
        "matched_keyword": None
    }


def evaluate_mentor_availability(mentor_id, day_of_week, start_time, end_time, schedule_date=None, db_path=None):
    """
    Memeriksa ketersediaan waktu mentor dan mendeteksi bentrokan jadwal.
    
    Terapkan 4 Status Sesuai Arahan:
    1. Tersedia (Hijau): Sudah isi ketersediaan, jam cocok, tidak bentrok.
    2. Bebas Bentrok — Belum Ada Info Ketersediaan (Abu-abu): Belum isi ketersediaan, tidak bentrok.
    3. Di Luar Preferensi Waktu (Kuning): Sudah isi ketersediaan, jam di luar slot, tidak bentrok.
    4. Bentrok Jadwal (Merah): Ada jadwal aktif bertabrakan (tampilkan nama siswa yang bentrok).
    
    Perhatikan batas waktu: jadwal bersinggungan di batas (e.g. 10:00-11:00 vs 11:00-12:00)
    TIDAK dianggap bentrok karena tidak ada durasi tumpang tindih (overlap).
    """
    # 1. Periksa bentrokan dengan jadwal rutin mingguan lain (routine_schedules)
    # Aturan overlap: (start_time < existing.end_time AND end_time > existing.start_time)
    conflict_routine = query_db("""
        SELECT rs.id, rs.student_id, rs.start_time, rs.end_time, st.full_name as student_name
        FROM routine_schedules rs
        JOIN students st ON rs.student_id = st.id
        WHERE rs.mentor_id = ?
          AND rs.day_of_week = ?
          AND (rs.start_time < ? AND rs.end_time > ?)
        LIMIT 1
    """, (mentor_id, day_of_week, end_time, start_time), one=True, db_path=db_path)

    # 2. Periksa bentrokan dengan jadwal sesi tanggal spesifik jika ada schedule_date
    conflict_session = None
    if schedule_date:
        conflict_session = query_db("""
            SELECT s.id, s.student_id, s.start_time, s.end_time, st.full_name as student_name
            FROM schedules s
            JOIN students st ON s.student_id = st.id
            WHERE s.mentor_id = ?
              AND s.schedule_date = ?
              AND s.status NOT IN ('ditolak', 'dibatalkan')
              AND (s.start_time < ? AND s.end_time > ?)
            LIMIT 1
        """, (mentor_id, schedule_date, end_time, start_time), one=True, db_path=db_path)

    active_conflict = conflict_routine or conflict_session

    if active_conflict:
        conf_student = active_conflict["student_name"]
        conf_start = active_conflict["start_time"]
        conf_end = active_conflict["end_time"]
        return {
            "status": "bentrok",
            "time_tier": 5, # Prioritas paling bawah
            "badge": "danger",
            "label": "Bentrok Jadwal",
            "has_conflict": True,
            "conflict_info": {
                "student_name": conf_student,
                "start_time": conf_start,
                "end_time": conf_end,
                "message": f"Bentrok dengan sesi siswa {conf_student} ({conf_start} - {conf_end})"
            }
        }

    # 3. Tidak ada bentrokan, periksa tabel ketersediaan mingguan mentor (mentor_availability)
    all_avails = query_db(
        "SELECT * FROM mentor_availability WHERE mentor_id = ?",
        (mentor_id,),
        db_path=db_path
    )

    if not all_avails:
        # Mentor belum mengisi data ketersediaan sama sekali
        return {
            "status": "bebas_tanpa_info",
            "time_tier": 3,
            "badge": "secondary",
            "label": "Bebas Bentrok (Belum Ada Info Ketersediaan)",
            "has_conflict": False,
            "conflict_info": None
        }

    # Mentor sudah mengisi ketersediaan, cek apakah slot hari dan jam cocok
    matching_slot = None
    for av in all_avails:
        if av["day_of_week"] == day_of_week:
            # Slot mencakup jam yang diminta: slot.start_time <= start_time AND slot.end_time >= end_time
            if av["start_time"] <= start_time and av["end_time"] >= end_time:
                matching_slot = av
                break

    if matching_slot:
        return {
            "status": "tersedia",
            "time_tier": 1, # Prioritas tertinggi
            "badge": "success",
            "label": "Tersedia (Sesuai Ketersediaan)",
            "has_conflict": False,
            "conflict_info": None
        }
    else:
        # Sudah ada data ketersediaan, tetapi hari/jam ini di luar slot
        return {
            "status": "luar_preferensi",
            "time_tier": 4,
            "badge": "warning",
            "label": "Di Luar Preferensi Waktu",
            "has_conflict": False,
            "conflict_info": None
        }


def get_mentor_recommendations(student_id, program_id, day_of_week, start_time, end_time, schedule_date=None, db_path=None, filter_strictly_available=True):
    """
    Menghasilkan daftar rekomendasi mentor berjenjang berdasarkan:
    1. Ketersediaan Waktu (Tersedia > Bebas Tanpa Info > Di Luar Preferensi > Bentrok)
    2. Kesesuaian Mata Pelajaran (Keahlian Sesuai > Belum Teridentifikasi)
    3. Jarak Tempuh Garis Lurus (Haversine km, jarak terdekat)

    Semua mentor aktif ditampilkan dengan transparansi status.
    Admin tetap menjadi pengambil keputusan akhir.
    """
    # 1. Validasi keberadaan siswa
    student = query_db(
        "SELECT id, full_name, address, latitude, longitude FROM students WHERE id = ?",
        (student_id,),
        one=True,
        db_path=db_path
    )
    if not student:
        return {"success": False, "message": "Data siswa tidak ditemukan.", "recommendations": []}

    # 2. Validasi program belajar
    program = query_db(
        "SELECT id, name, code, description FROM programs WHERE id = ?",
        (program_id,),
        one=True,
        db_path=db_path
    )
    if not program:
        return {"success": False, "message": "Data program belajar tidak ditemukan.", "recommendations": []}

    # Pastikan day_of_week integer 0-6
    try:
        dow_int = int(day_of_week)
    except (ValueError, TypeError):
        return {"success": False, "message": "Format hari tidak valid.", "recommendations": []}

    if not (0 <= dow_int <= 6):
        return {"success": False, "message": "Hari harus bernilai antara 0 (Senin) hingga 6 (Minggu).", "recommendations": []}

    if not start_time or not end_time or start_time >= end_time:
        return {"success": False, "message": "Jam mulai harus lebih awal dari jam selesai.", "recommendations": []}

    # 3. Ambil seluruh mentor aktif
    mentors = query_db(
        "SELECT id, full_name, phone, email, expertise, bio, address, latitude, longitude FROM mentors WHERE status = 'aktif' ORDER BY full_name ASC",
        db_path=db_path
    )

    student_lat = student["latitude"]
    student_lon = student["longitude"]

    scored_mentors = []

    for m in mentors:
        # A. Evaluasi Waktu & Bentrokan (Prioritas 1)
        avail = evaluate_mentor_availability(
            mentor_id=m["id"],
            day_of_week=dow_int,
            start_time=start_time,
            end_time=end_time,
            schedule_date=schedule_date,
            db_path=db_path
        )

        # B. Evaluasi Keahlian Mata Pelajaran (Prioritas 2)
        exp = evaluate_expertise_match(
            mentor_expertise=m["expertise"],
            program_name=program["name"],
            program_desc=program["description"]
        )

        # C. Evaluasi Jarak Lokasi (Prioritas 3 - Haversine)
        dist_km = calculate_haversine_distance(student_lat, student_lon, m["latitude"], m["longitude"])
        dist_label = f"{dist_km} km" if dist_km is not None else "Belum ada koordinat"

        # D. Penentuan Kelompok Peringkat (Tier Group):
        # 1: Tersedia & Keahlian Sesuai (High/Med Match)
        # 2: Tersedia & Keahlian Belum Teridentifikasi
        # 3: Bebas Bentrok — Belum Ada Info Ketersediaan
        # 4: Di Luar Preferensi Waktu
        # 5: Bentrok Jadwal (Paling Bawah)
        if avail["status"] == "tersedia":
            tier_group = 1 if exp["score"] > 0 else 2
        elif avail["status"] == "bebas_tanpa_info":
            tier_group = 3
        elif avail["status"] == "luar_preferensi":
            tier_group = 4
        else: # 'bentrok'
            tier_group = 5

        # Rangkuman ringkas rekomendasi
        summary_parts = []
        if tier_group == 1:
            summary_parts.append("Sangat Direkomendasikan: Jadwal cocok & keahlian sesuai")
        elif tier_group == 2:
            summary_parts.append("Jadwal cocok (keahlian belum terkonfirmasi)")
        elif tier_group == 3:
            summary_parts.append("Bebas bentrok (belum ada info ketersediaan mingguan)")
        elif tier_group == 4:
            summary_parts.append("Di luar slot waktu ketersediaan mentor")
        elif tier_group == 5:
            summary_parts.append(f"Tidak disarankan: {avail['conflict_info']['message']}")

        if dist_km is not None:
            summary_parts.append(f"jarak {dist_km} km")

        scored_mentors.append({
            "mentor_id": m["id"],
            "mentor_name": m["full_name"],
            "phone": m["phone"],
            "expertise": m["expertise"] or "-",
            "tier_group": tier_group,
            "time_status": avail["status"],
            "time_badge": avail["badge"],
            "time_label": avail["label"],
            "has_conflict": avail["has_conflict"],
            "conflict_info": avail["conflict_info"],
            "expertise_matched": exp["matched"],
            "expertise_score": exp["score"],
            "expertise_label": exp["label"],
            "distance_km": dist_km,
            "distance_label": dist_label,
            "has_coordinates": bool(m["latitude"] is not None and m["longitude"] is not None),
            "recommendation_summary": " • ".join(summary_parts)
        })

    # E. Pengurutan Berjenjang:
    # 1. tier_group (1 -> 5)
    # 2. -expertise_score (skor keahlian tertinggi lebih dahulu)
    # 3. Jarak: jarak terdekat lebih dahulu (jarak diketahui didahulukan sebelum None)
    # 4. Nama mentor secara alfabetis
    def sort_key(item):
        tg = item["tier_group"]
        exp_score = -item["expertise_score"]
        # Jarak: (0, dist) jika ada, (1, 999999) jika None
        dist_tuple = (0, item["distance_km"]) if item["distance_km"] is not None else (1, 999999)
        name = item["mentor_name"]
        return (tg, exp_score, dist_tuple, name)

    scored_mentors.sort(key=sort_key)

    if filter_strictly_available:
        # Filter rekomendasi sesuai arahan pemilik:
        # "untuk rekomendasi tentor klo mmng tidak sesuai tidak usah di munculkan Namanya jadi yg betul-betul tersedia baru munculkan biar tidak banyak rekomendasi"
        
        # 1. Hapus SEMUA mentor yang bentrok jadwal (has_conflict == True)
        # 2. Hapus SEMUA mentor yang berada di luar preferensi waktu (time_status == 'luar_preferensi')
        viable_mentors = [
            m for m in scored_mentors
            if not m["has_conflict"] and m["time_status"] != "luar_preferensi"
        ]

        # 3. Jika ada mentor yang secara spesifik 'tersedia' (sudah mengisi ketersediaan di mentor_availability dan jamnya cocok):
        strictly_available = [m for m in viable_mentors if m["time_status"] == "tersedia"]
        if strictly_available:
            # Prioritaskan hanya yang betul-betul 'tersedia'
            final_list = strictly_available
        else:
            # Jika belum ada mentor yang mengisi ketersediaan spesifik:
            # Prioritaskan mentor yang keahliannya sesuai (expertise_matched)
            matched_exp = [m for m in viable_mentors if m["expertise_matched"]]
            if matched_exp:
                final_list = matched_exp
            else:
                # Batasi maksimal 2-3 mentor bebas bentrok agar daftar rekomendasi tetap ringkas dan relevan
                final_list = viable_mentors[:3]
    else:
        final_list = scored_mentors

    # Berikan nomor peringkat 1, 2, 3...
    for idx, item in enumerate(final_list, start=1):
        item["rank"] = idx

    day_name = DAY_NAMES[dow_int] if 0 <= dow_int < len(DAY_NAMES) else str(dow_int)

    return {
        "success": True,
        "student": {
            "id": student["id"],
            "name": student["full_name"],
            "address": student["address"] or "-",
            "has_coordinates": bool(student_lat is not None and student_lon is not None),
            "latitude": student_lat,
            "longitude": student_lon
        },
        "program": {
            "id": program["id"],
            "name": program["name"],
            "code": program["code"]
        },
        "requested_slot": {
            "day_of_week": dow_int,
            "day_name": day_name,
            "start_time": start_time,
            "end_time": end_time,
            "schedule_date": schedule_date
        },
        "recommendations": final_list
    }
