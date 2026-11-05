"""
Migrasi skema database untuk Jadwal Rutin Mingguan (routine_schedules).
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "desi_privat.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Buat tabel routine_schedules jika belum ada
    c.execute("""
    CREATE TABLE IF NOT EXISTS routine_schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
        mentor_id INTEGER NOT NULL REFERENCES mentors(id) ON DELETE CASCADE,
        day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        subject_info TEXT,
        notes TEXT,
        status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif')),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_routine_mentor ON routine_schedules(mentor_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_routine_student ON routine_schedules(student_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_routine_day ON routine_schedules(day_of_week)")

    # 2. Cek apakah ada jadwal rutin untuk Muzayyan (student_id = 32)
    c.execute("SELECT COUNT(*) FROM routine_schedules WHERE student_id = 32")
    if c.fetchone()[0] == 0:
        # Tambahkan jadwal rutin resmi Muzayyan: Kamis & Jumat 16:00 - 17:30
        c.execute("""
        INSERT INTO routine_schedules (student_id, program_id, mentor_id, day_of_week, start_time, end_time, subject_info, notes)
        VALUES (32, 1, 6, 3, '16:00', '17:30', 'Math Olimpiade - Aljabar & Geometri', 'Jadwal rutin Kamis sore')
        """)
        c.execute("""
        INSERT INTO routine_schedules (student_id, program_id, mentor_id, day_of_week, start_time, end_time, subject_info, notes)
        VALUES (32, 1, 6, 4, '16:00', '17:30', 'Math Olimpiade - Pemecahan Soal OSN', 'Jadwal rutin Jumat sore')
        """)
        print("Jadwal rutin Muzayyan berhasil ditambahkan.")

    conn.commit()
    conn.close()
    print("Migrasi routine_schedules berhasil.")

if __name__ == "__main__":
    migrate()

