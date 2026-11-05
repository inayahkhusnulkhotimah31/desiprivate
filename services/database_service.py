"""
DESI PRIVAT - Database Service
Layanan koneksi Dual-Engine (Supabase PostgreSQL / Cloud & SQLite Lokal),
inisialisasi tabel, dan seeding data pengujian.
"""
import sqlite3
import os
import re
from pathlib import Path
from config import Config
from flask import g
from werkzeug.security import generate_password_hash

class RowDict(dict):
    """Dictionary hasil query yang juga mendukung akses indeks numerik seperti sqlite3.Row."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)

_pg_connection_failed = False

def is_postgres(db_path=None):
    """Mengecek apakah database yang aktif adalah PostgreSQL (Supabase)."""
    global _pg_connection_failed
    if db_path is not None:
        return False
    if getattr(Config, "TESTING", False):
        return False
    db_url = getattr(Config, "DATABASE_URL", None)
    if not (db_url and str(db_url).strip().startswith("postgres")):
        return False
    if _pg_connection_failed:
        return False
    return True

def _handle_pg_error(e):
    """Menangani kegagalan PostgreSQL Supabase secara anggun dan otomatis fallback ke database lokal."""
    global _pg_connection_failed
    _pg_connection_failed = True
    import sys
    print(f"[DATABASE AUTO-FALLBACK] Supabase PostgreSQL tidak dapat diakses ({e}). Beralih otomatis ke database lokal agar sistem tetap online 100%.", file=sys.stderr)

def _prepare_postgres_sql(query):
    """Menyesuaikan sintaks query SQLite agar kompatibel dengan PostgreSQL / psycopg."""
    sql = query
    # Ganti placeholder parameter ? menjadi %s
    sql = sql.replace("?", "%s")

    # Normalisasi fungsi tanggal SQLite -> PostgreSQL
    sql = re.sub(r"date\(\s*'now'\s*,\s*'\+1 day'\s*\)", "(CURRENT_DATE + INTERVAL '1 day')", sql, flags=re.IGNORECASE)
    sql = re.sub(r"date\(\s*'now'\s*\)", "CURRENT_DATE", sql, flags=re.IGNORECASE)
    sql = re.sub(r"strftime\(\s*'%Y-%m'\s*,\s*'now'\s*\)", "to_char(CURRENT_TIMESTAMP, 'YYYY-MM')", sql, flags=re.IGNORECASE)
    sql = re.sub(r"strftime\(\s*'%Y-%m'\s*,\s*([a-zA-Z0-9_\.]+)\s*\)", r"to_char(\1, 'YYYY-MM')", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bdate\(([a-zA-Z0-9_\.]+)\)", r"(\1)::date", sql, flags=re.IGNORECASE)
    return sql

def _ensure_vercel_db(path):
    """Menjamin database di temp directory selalu tersedia dan tersinkronisasi dari Cloud."""
    if getattr(Config, "IS_VERCEL", False) and not getattr(Config, "TESTING", False) and not is_postgres():
        p = Path(path)
        # 1. Coba sinkronisasi dari Supabase Cloud terlebih dahulu
        try:
            from services.cloud_sync_service import sync_from_cloud
            synced = sync_from_cloud(force=not p.exists())
            if synced:
                return
        except Exception:
            pass

        # 2. Fallback jika belum ada di cloud
        if not p.exists():
            seed = Path(__file__).resolve().parent.parent / "database" / "desi_privat.db"
            if seed.exists():
                import shutil
                try:
                    os.makedirs(p.parent, exist_ok=True)
                    shutil.copyfile(seed, p)
                    os.chmod(p, 0o666)
                except Exception:
                    pass

def get_db(db_path=None):
    """Membuka koneksi ke database (PostgreSQL jika DATABASE_URL tersedia, fallback otomatis SQLite jika gagal)."""
    if is_postgres(db_path):
        if 'db' not in g or g.get('is_pg') is not True or getattr(g.get('db'), 'closed', True):
            try:
                import psycopg
                from psycopg.rows import dict_row
                conn = psycopg.connect(Config.DATABASE_URL, row_factory=dict_row, connect_timeout=4)
                g.db = conn
                g.is_pg = True
                return g.db
            except Exception as e:
                _handle_pg_error(e)
                # Lanjut fallback ke SQLite di bawah

    path = db_path or Config.DATABASE_PATH
    _ensure_vercel_db(path)
    # Pastikan folder database ada
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    if 'db' not in g or g.get('db_path') != path or g.get('is_pg') is True:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
        g.db_path = path
        g.is_pg = False
    return g.db

def get_direct_connection(db_path=None):
    """Membuka koneksi langsung di luar konteks request Flask (misalnya untuk CLI/script)."""
    if is_postgres(db_path):
        try:
            import psycopg
            from psycopg.rows import dict_row
            return psycopg.connect(Config.DATABASE_URL, row_factory=dict_row, connect_timeout=4)
        except Exception as e:
            _handle_pg_error(e)
            # Lanjut fallback ke SQLite di bawah

    path = db_path or Config.DATABASE_PATH
    _ensure_vercel_db(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def close_db(e=None):
    """Menutup koneksi database pada akhir request."""
    db = g.pop('db', None)
    g.pop('is_pg', None)
    g.pop('db_path', None)
    if db is not None:
        try:
            db.close()
        except Exception:
            pass

def query_db(query, args=(), one=False, db_path=None):
    """Menjalankan query SELECT dan mengembalikan hasil (kompatibel SQLite & PostgreSQL)."""
    if is_postgres(db_path):
        try:
            pg_query = _prepare_postgres_sql(query)
            is_direct = False
            try:
                db = get_db(db_path)
                if not g.get('is_pg'):
                    raise RuntimeError("Beralih ke SQLite")
                cur = db.cursor()
                cur.execute(pg_query, args)
                raw_rows = cur.fetchall()
                cur.close()
            except RuntimeError:
                db = get_direct_connection(db_path)
                if not is_postgres():
                    raise RuntimeError("Beralih ke SQLite")
                cur = db.cursor()
                cur.execute(pg_query, args)
                raw_rows = cur.fetchall()
                cur.close()
                db.close()

            rows = [RowDict(r) for r in raw_rows]
            return (rows[0] if rows else None) if one else rows
        except Exception as e:
            _handle_pg_error(e)
            # Lanjut eksekusi SQLite di bawah

    # Fallback SQLite
    try:
        db = get_db(db_path)
    except RuntimeError:
        db = get_direct_connection(db_path)
        cur = db.execute(query, args)
        rv = cur.fetchall()
        db.close()
        return (rv[0] if rv else None) if one else rv

    cur = db.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=(), commit=True, db_path=None):
    """Menjalankan query INSERT/UPDATE/DELETE dan mengembalikan lastrowid atau affected rows."""
    if is_postgres(db_path):
        try:
            pg_query = _prepare_postgres_sql(query)
            is_insert = pg_query.strip().upper().startswith("INSERT INTO")
            if is_insert and "RETURNING" not in pg_query.upper():
                pg_query = pg_query.rstrip("; ") + " RETURNING id"

            is_direct = False
            try:
                db = get_db(db_path)
                if not g.get('is_pg'):
                    raise RuntimeError("Beralih ke SQLite")
            except RuntimeError:
                db = get_direct_connection(db_path)
                if not is_postgres():
                    raise RuntimeError("Beralih ke SQLite")
                is_direct = True

            cur = db.cursor()
            cur.execute(pg_query, args)
            last_id = None
            if is_insert:
                try:
                    ret = cur.fetchone()
                    if ret:
                        last_id = ret.get("id") if isinstance(ret, dict) else ret[0]
                except Exception:
                    pass
            row_count = cur.rowcount
            if commit:
                db.commit()
            cur.close()
            if is_direct:
                db.close()
            return last_id if last_id is not None else row_count
        except Exception as e:
            _handle_pg_error(e)
            # Lanjut eksekusi SQLite di bawah

    # Fallback SQLite
    is_direct = False
    try:
        db = get_db(db_path)
    except RuntimeError:
        db = get_direct_connection(db_path)
        is_direct = True

    cur = db.execute(query, args)
    last_id = cur.lastrowid
    row_count = cur.rowcount
    if commit:
        db.commit()
        if getattr(Config, "IS_VERCEL", False) and not getattr(Config, "TESTING", False):
            try:
                from services.cloud_sync_service import mark_db_dirty, sync_to_cloud
                mark_db_dirty()
                sync_to_cloud()
            except Exception:
                pass
    cur.close()
    if is_direct:
        db.close()
    return last_id if last_id else row_count

    # Fallback SQLite
    is_direct = False
    try:
        db = get_db(db_path)
    except RuntimeError:
        db = get_direct_connection(db_path)
        is_direct = True

    cur = db.execute(query, args)
    last_id = cur.lastrowid
    row_count = cur.rowcount
    if commit:
        db.commit()
        if getattr(Config, "IS_VERCEL", False) and not getattr(Config, "TESTING", False):
            try:
                from services.cloud_sync_service import mark_db_dirty, sync_to_cloud
                mark_db_dirty()
                sync_to_cloud()
            except Exception:
                pass
    cur.close()
    if is_direct:
        db.close()
    return last_id if last_id else row_count

def init_db(db_path=None, schema_path=None):
    """Menginisialisasi tabel-tabel database."""
    if is_postgres(db_path):
        # Pada PostgreSQL Supabase, skema dikelola melalui supabase_schema.sql
        return True

    target_db = db_path or Config.DATABASE_PATH
    s_path = schema_path or (Path(__file__).resolve().parent.parent / "database" / "schema.sql")

    conn = get_direct_connection(target_db)
    with open(s_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)

    # Migrasi otomatis kolom status pada tabel parents jika belum ada
    try:
        cur = conn.cursor()
        parent_cols = [col[1] for col in cur.execute("PRAGMA table_info(parents)").fetchall()]
        if "status" not in parent_cols:
            cur.execute("ALTER TABLE parents ADD COLUMN status TEXT NOT NULL DEFAULT 'aktif'")

        # Migrasi kolom riwayat awal pertemuan pada tabel students
        student_cols = [col[1] for col in cur.execute("PRAGMA table_info(students)").fetchall()]
        if "initial_meeting_offset" not in student_cols:
            cur.execute("ALTER TABLE students ADD COLUMN initial_meeting_offset INTEGER NOT NULL DEFAULT 0")
        if "initial_offset_notes" not in student_cols:
            cur.execute("ALTER TABLE students ADD COLUMN initial_offset_notes TEXT")
        if "initial_offset_set_at" not in student_cols:
            cur.execute("ALTER TABLE students ADD COLUMN initial_offset_set_at DATETIME")
        if "initial_offset_set_by" not in student_cols:
            cur.execute("ALTER TABLE students ADD COLUMN initial_offset_set_by INTEGER")

        # Migrasi kolom penomoran pertemuan, periode & dokumentasi belajar pada tabel attendance
        att_cols = [col[1] for col in cur.execute("PRAGMA table_info(attendance)").fetchall()]
        if "topics_covered" not in att_cols:
            cur.execute("ALTER TABLE attendance ADD COLUMN topics_covered TEXT")
        if "progress_notes" not in att_cols:
            cur.execute("ALTER TABLE attendance ADD COLUMN progress_notes TEXT")
        if "meeting_number" not in att_cols:
            cur.execute("ALTER TABLE attendance ADD COLUMN meeting_number INTEGER")
        if "period_number" not in att_cols:
            cur.execute("ALTER TABLE attendance ADD COLUMN period_number INTEGER")
        if "cumulative_meeting" not in att_cols:
            cur.execute("ALTER TABLE attendance ADD COLUMN cumulative_meeting INTEGER")

        # Nonaktifkan akses login untuk semua akun orang tua lama per ketentuan
        cur.execute("UPDATE users SET is_active = 0 WHERE role = 'parent'")
    except Exception:
        pass

    conn.commit()
    conn.close()

def seed_initial_data(db_path=None):
    """Menginisialisasi data dasar sistem (akun admin & owner, program) tanpa data fiktif."""
    if is_postgres(db_path):
        # Cek apakah akun admin sudah ada di Supabase
        admin = query_db("SELECT id FROM users WHERE username = ?", ("admin",), one=True)
        if not admin:
            execute_db("""
                INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
                VALUES (?, ?, 'admin', 'Admin Pengelola DESI', 'admin@desiprivat.id', '081234567801', 1)
            """, ("admin", generate_password_hash("admin123")))

        owner = query_db("SELECT id FROM users WHERE username = ?", ("owner",), one=True)
        if not owner:
            execute_db("""
                INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
                VALUES (?, ?, 'owner', 'Ibu Desi (Pemilik)', 'owner@desiprivat.id', '081234567802', 1)
            """, ("owner", generate_password_hash("owner123")))

        programs = query_db("SELECT COUNT(*) as count FROM programs", one=True)
        count = programs["count"] if programs else 0
        if count == 0:
            default_programs = [
                ("Matematika", "MAT-01", "Bimbingan konsep matematika dan pemecahan soal", "Semua Jenjang", "aktif"),
                ("Bahasa Inggris", "ENG-01", "Conversation, grammar, and vocabulary", "Semua Jenjang", "aktif"),
                ("Sains & IPA", "IPA-01", "Pendalaman materi IPA fisika dan biologi", "SD & SMP", "aktif"),
                ("Calistung", "CLS-01", "Membaca, menulis, dan berhitung dasar ramah anak", "TK B & SD 1-3", "aktif"),
            ]
            for p in default_programs:
                execute_db("""
                    INSERT INTO programs (name, code, description, level, status)
                    VALUES (?, ?, ?, ?, ?)
                """, p)
        return True

    # Fallback SQLite
    conn = get_direct_connection(db_path or Config.DATABASE_PATH)
    cur = conn.cursor()

    # Pastikan akun admin ada
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
            VALUES (?, ?, 'admin', 'Admin Pengelola DESI', 'admin@desiprivat.id', '081234567801', 1)
        """, ("admin", generate_password_hash("admin123")))

    # Pastikan akun owner ada
    cur.execute("SELECT id FROM users WHERE username = 'owner'")
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
            VALUES (?, ?, 'owner', 'Ibu Desi (Pemilik)', 'owner@desiprivat.id', '081234567802', 1)
        """, ("owner", generate_password_hash("owner123")))

    # Pastikan program les ada default jika belum ada satupun
    cur.execute("SELECT COUNT(*) FROM programs")
    if cur.fetchone()[0] == 0:
        default_programs = [
            ("Matematika", "MAT-01", "Bimbingan konsep matematika dan pemecahan soal", "Semua Jenjang", "aktif"),
            ("Bahasa Inggris", "ENG-01", "Conversation, grammar, and vocabulary", "Semua Jenjang", "aktif"),
            ("Sains & IPA", "IPA-01", "Pendalaman materi IPA fisika dan biologi", "SD & SMP", "aktif"),
            ("Calistung", "CLS-01", "Membaca, menulis, dan berhitung dasar ramah anak", "TK B & SD 1-3", "aktif"),
        ]
        cur.executemany("""
            INSERT INTO programs (name, code, description, level, status)
            VALUES (?, ?, ?, ?, ?)
        """, default_programs)

    conn.commit()
    conn.close()
    return True

def seed_test_data(db_path=None):
    """Mengisi data awal pengujian untuk sistem DESI PRIVAT."""
    conn = get_direct_connection(db_path or Config.DATABASE_PATH)
    cur = conn.cursor()

    # Periksa apakah sudah ada data admin
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if cur.fetchone():
        conn.close()
        return False

    # 1. Buat Pengguna Utama (Hanya role admin, owner, dan mentor)
    # Password default:
    # admin: admin123 | owner: owner123 | mentor*: mentor123
    users = [
        ("admin", generate_password_hash("admin123"), "admin", "Admin Pengelola DESI", "admin@desiprivat.id", "081234567801"),
        ("owner", generate_password_hash("owner123"), "owner", "Ibu Desi (Pemilik)", "owner@desiprivat.id", "081234567802"),
        ("mentor1", generate_password_hash("mentor123"), "mentor", "Sarah Nurhaliza, S.Pd.", "sarah@desiprivat.id", "081234567803"),
        ("mentor2", generate_password_hash("mentor123"), "mentor", "Budi Santoso, M.Sc.", "budi@desiprivat.id", "081234567804"),
        ("mentor3", generate_password_hash("mentor123"), "mentor", "Dian Sastro, B.Ed.", "dian@desiprivat.id", "081234567805"),
    ]

    cur.executemany("""
        INSERT INTO users (username, password_hash, role, full_name, email, phone, is_active)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, users)

    # Ambil ID Pengguna
    cur.execute("SELECT id, username FROM users")
    user_map = {row["username"]: row["id"] for row in cur.fetchall()}

    # 2. Data Orang Tua / Wali (Data administratif langsung tanpa user role)
    parents = [
        ("Ibu Ratna Kumalasari", "081298765401", "ratna@gmail.com", "Jl. Melati No. 45, Sleman, Yogyakarta", "Ibu dari Naufal Pratama dan Alisha Putri"),
        ("Bapak Hendra Wijaya", "081298765402", "hendra@gmail.com", "Jl. Mawar No. 12, Kota Yogyakarta", "Ayah dari Kevin Ardiansyah"),
    ]
    cur.executemany("""
        INSERT INTO parents (full_name, phone, email, address, notes)
        VALUES (?, ?, ?, ?, ?)
    """, parents)

    # 3. Data Siswa (Parent 1 memiliki 2 anak: Naufal & Alisha)
    students = [
        (1, "Naufal Pratama", "SMP Negeri 1 Sleman", "Kelas 8 SMP", "2012-05-14", "Jl. Melati No. 45, Sleman", "Perlu penguatan aljabar & persiapan PTS", "aktif"),
        (1, "Alisha Putri", "SD Percobaan 2 Yogyakarta", "Kelas 5 SD", "2015-09-22", "Jl. Melati No. 45, Sleman", "Fokus Bahasa Inggris dasar dan sains seru", "aktif"),
        (2, "Kevin Ardiansyah", "SMP Negeri 5 Yogyakarta", "Kelas 9 SMP", "2011-03-10", "Jl. Mawar No. 12, Yogyakarta", "Persiapan Asesmen Standarisasi Pendidikan Daerah (ASPD)", "aktif"),
        (2, "Rina Wijaya (Arsip)", "SMA Negeri 3 Yogyakarta", "Kelas 12 SMA", "2008-01-18", "Jl. Mawar No. 12, Yogyakarta", "Sudah lulus dan diterima PTN", "berhenti"),
    ]
    cur.executemany("""
        INSERT INTO students (parent_id, full_name, school, grade, birth_date, address, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, students)

    # 4. Data Mentor
    mentors = [
        (user_map["mentor1"], "Sarah Nurhaliza, S.Pd.", "081234567803", "sarah@desiprivat.id", "Matematika SD/SMP, IPA Terpadu", "Lulusan Pendidikan Matematika UNY. Pengalaman mengajar privat 4 tahun.", "aktif"),
        (user_map["mentor2"], "Budi Santoso, M.Sc.", "081234567804", "budi@desiprivat.id", "Bahasa Inggris, Fisika SMP", "Lulusan S2 ITB, TOEFL 610. Spesialis persiapan ujian & speaking.", "aktif"),
        (user_map["mentor3"], "Dian Sastro, B.Ed.", "081234567805", "dian@desiprivat.id", "Calistung, Tematik SD", "Pakar pendekatan belajar ramah anak usia dini dan SD kelas rendah.", "aktif"),
    ]
    cur.executemany("""
        INSERT INTO mentors (user_id, full_name, phone, email, expertise, bio, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, mentors)

    # 5. Data Program Les
    programs = [
        ("Matematika Hebat SMP", "MAT-SMP", "Pendampingan privat matematika konsep & trik pemecahan soal", "SMP Kelas 7-9", "aktif"),
        ("Sains & IPA Terpadu SMP", "IPA-SMP", "Pembahasan materi fisika dan biologi disertai eksperimen konseptual", "SMP Kelas 7-9", "aktif"),
        ("English Smart Active", "ENG-SD-SMP", "Grammar praktis, vocabulary booster, dan percakapan percaya diri", "SD & SMP", "aktif"),
        ("Calistung & Pendampingan SD", "CLS-SD", "Membaca lancar, menulis rapi, dan berhitung dasar menyenangkan", "TK B & SD Kelas 1-3", "aktif"),
        ("Persiapan Olimpiade Sains 2025", "OLM-2025", "Program intensif persiapan OSN tahun lalu", "SMP", "diarsipkan"),
    ]
    cur.executemany("""
        INSERT INTO programs (name, code, description, level, status)
        VALUES (?, ?, ?, ?, ?)
    """, programs)

    # 6. Relasi Siswa - Program - Mentor
    student_programs = [
        (1, 1, 1, "2026-10-01", "2026-12-31", "aktif", "Fokus matematika 2 sesi seminggu"),
        (2, 3, 2, "2026-10-01", "2026-12-31", "aktif", "Bahasa Inggris 1 sesi seminggu"),
        (3, 1, 1, "2026-10-05", "2026-12-31", "aktif", "Matematika intensif persiapan ASPD"),
    ]
    cur.executemany("""
        INSERT INTO student_programs (student_id, program_id, mentor_id, start_date, end_date, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, student_programs)

    # 7. Ketersediaan Waktu Mentor
    # Sarah (mentor 1): Senin & Rabu 15:30 - 18:00
    # Budi (mentor 2): Selasa & Kamis 15:00 - 18:00
    availabilities = [
        (1, 0, "15:00", "18:00", "Senin sore siap mengajar matematika"),
        (1, 2, "15:00", "18:00", "Rabu sore siap mengajar matematika/IPA"),
        (2, 1, "15:30", "18:30", "Selasa sore English speaking"),
        (2, 3, "15:30", "18:30", "Kamis sore IPA/Fisika"),
        (3, 4, "14:00", "17:00", "Jumat sore calistung ramah anak"),
    ]
    cur.executemany("""
        INSERT INTO mentor_availability (mentor_id, day_of_week, start_time, end_time, notes)
        VALUES (?, ?, ?, ?, ?)
    """, availabilities)

    # 8. Ketersediaan Waktu Siswa
    student_avails = [
        (1, 0, "16:00", "18:00", 1, "Senin sepulang sekolah"),
        (1, 2, "16:00", "18:00", 1, "Rabu sepulang ekstrakurikuler"),
        (2, 5, "09:00", "11:30", 1, "Sabtu pagi setelah les renang"),
        (3, 1, "16:00", "17:30", 1, "Selasa sore kosong"),
    ]
    cur.executemany("""
        INSERT INTO student_availability (student_id, day_of_week, start_time, end_time, is_confirmed, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, student_avails)

    # 9. Jadwal Pengujian
    schedules = [
        ("Sesi Matematika - Aljabar Dasar", 1, 1, 1, "2026-10-19", "16:00", "17:30", 90, "disetujui", "bersedia", None, "dikonfirmasi", None, "2026-10-18 10:00:00", 0, "Sesi tatap muka di rumah siswa", user_map["mentor1"], user_map["admin"]),
        ("Sesi Bahasa Inggris - Daily Conversation", 3, 2, 2, "2026-10-24", "16:00", "17:30", 90, "disetujui", "bersedia", None, "dikonfirmasi", None, "2026-10-23 09:00:00", 0, "Materi listening & simple dialogue", user_map["mentor2"], user_map["admin"]),
        ("Sesi Sains - Hukum Newton", 2, 1, 1, "2026-10-26", "16:00", "17:30", 90, "menunggu_persetujuan_admin", "bersedia", None, "menunggu_konfirmasi", None, None, 0, "Usulan rutin hari Senin sore", user_map["mentor1"], None),
        ("Sesi Matematika - Geometri Bangun Ruang", 1, 3, 1, "2026-10-28", "16:00", "17:30", 90, "menunggu_konfirmasi_siswa", "menunggu", None, "menunggu_konfirmasi", None, None, 0, "Koordinasi via WhatsApp dengan Ibu/Bapak", user_map["mentor1"], None),
        ("Sesi Matematika - Persiapan Kuis", 1, 1, 1, "2026-10-29", "16:00", "17:30", 90, "disetujui", "bersedia", None, "perlu_mentor_pengganti", "Mohon maaf sedang ada dinas PPG luar kota mendadak.", "2026-10-23 14:00:00", 0, "Memerlukan pengganti segera", user_map["mentor1"], user_map["admin"]),
    ]
    cur.executemany("""
        INSERT INTO schedules (
            title, program_id, student_id, mentor_id, schedule_date, start_time, end_time,
            duration_minutes, status, student_confirmation_status, student_confirmation_notes,
            mentor_response_status, mentor_response_notes, mentor_response_at, is_recurring,
            session_notes, created_by, approved_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, schedules)

    # 10. Data Absensi & Perkembangan Siswa Sesi 1
    cur.execute("""
        INSERT INTO attendance (schedule_id, student_id, mentor_id, status, notes)
        VALUES (1, 1, 1, 'hadir', 'Siswa hadir tepat waktu dan sangat fokus.')
    """)

    cur.execute("""
        INSERT INTO student_progress (
            schedule_id, student_id, mentor_id, program_id, session_date,
            topics_covered, skills_mastered, difficulties, recommendations, additional_notes
        ) VALUES (
            1, 1, 1, 1, '2026-10-19',
            'Operasi Aljabar, Penyederhanaan Suku Sejenis, dan Persamaan Linier Satu Variabel',
            'Mampu menyelesaikan perkalian bentuk aljabar dan mengelompokkan variabel sejenis dengan tepat.',
            'Masih sedikit ragu pada pemindahan ruas tanda negatif/positif.',
            'Perlu latihan tambahan 5 soal tentang pecahan bentuk aljabar sebelum sesi berikutnya.',
            'Naufal memiliki antusiasme belajar yang sangat baik.'
        )
    """)

    # 11. Notifikasi In-App
    notifications = [
        (user_map["admin"], "Usulan Jadwal Baru", "Mentor Sarah mengusulkan jadwal Sains Hukum Newton untuk Naufal Pratama.", "jadwal", 0, "/admin/schedules"),
        (user_map["admin"], "Perlu Mentor Pengganti", "Mentor Sarah tidak dapat mengajar pada 29 Okt 2026. Alasan: dinas PPG.", "penggantian", 0, "/admin/schedules"),
        (user_map["admin"], "Laporan Perkembangan Tersedia", "Laporan perkembangan sesi Matematika Naufal Pratama tanggal 19 Okt 2026 telah ditambahkan oleh Mentor Sarah.", "perkembangan", 0, "/admin/reports"),
        (user_map["mentor1"], "Jadwal Disetujui", "Jadwal sesi 19 Okt 2026 telah disetujui oleh Admin.", "jadwal", 1, "/mentor/schedules"),
    ]
    cur.executemany("""
        INSERT INTO notifications (user_id, title, message, type, is_read, reference_url)
        VALUES (?, ?, ?, ?, ?, ?)
    """, notifications)

    # 12. Audit Logs
    audit_logs = [
        (user_map["admin"], "admin", "INIT_SYSTEM", "system", "1", "Inisialisasi sistem informasi DESI PRIVAT dan data awal.", "127.0.0.1"),
        (user_map["admin"], "admin", "TAMBAH_SISWA", "students", "1", "Pendaftaran siswa baru Naufal Pratama (Wali: Ibu Ratna Kumalasari).", "127.0.0.1"),
        (user_map["admin"], "admin", "SETUJUI_JADWAL", "schedules", "1", "Persetujuan jadwal sesi Matematika Naufal Pratama tgl 2026-10-19.", "127.0.0.1"),
    ]
    cur.executemany("""
        INSERT INTO audit_logs (user_id, user_name, action_type, target_entity, target_id, details, ip_address)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, audit_logs)

    conn.commit()
    conn.close()
    return True
