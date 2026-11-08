"""
DESI PRIVAT - Additive Migration Script
Multi-Program Siswa, Riwayat Periode Independen & Developer Monitoring Audit Fields
Dijalankan secara aman, idempoten, dan zero-data-loss.
"""
import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path):
    print(f"[*] Menjalankan migrasi additive pada database: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Tabel student_programs: Tambahkan kolom riwayat periode awal per program
    sp_cols = [c[1] for c in cur.execute("PRAGMA table_info(student_programs)").fetchall()]
    print(f"    Kolom student_programs saat ini: {sp_cols}")

    if "initial_periods_completed" not in sp_cols:
        cur.execute("ALTER TABLE student_programs ADD COLUMN initial_periods_completed INTEGER NOT NULL DEFAULT 0")
        print("    [+] Added student_programs.initial_periods_completed")
    if "initial_last_meeting" not in sp_cols:
        cur.execute("ALTER TABLE student_programs ADD COLUMN initial_last_meeting INTEGER NOT NULL DEFAULT 0")
        print("    [+] Added student_programs.initial_last_meeting")
    if "initial_offset_total" not in sp_cols:
        cur.execute("ALTER TABLE student_programs ADD COLUMN initial_offset_total INTEGER NOT NULL DEFAULT 0")
        print("    [+] Added student_programs.initial_offset_total")
    if "initial_offset_notes" not in sp_cols:
        cur.execute("ALTER TABLE student_programs ADD COLUMN initial_offset_notes TEXT")
        print("    [+] Added student_programs.initial_offset_notes")
    if "initial_offset_set_at" not in sp_cols:
        cur.execute("ALTER TABLE student_programs ADD COLUMN initial_offset_set_at DATETIME")
        print("    [+] Added student_programs.initial_offset_set_at")
    if "initial_offset_set_by" not in sp_cols:
        cur.execute("ALTER TABLE student_programs ADD COLUMN initial_offset_set_by INTEGER")
        print("    [+] Added student_programs.initial_offset_set_by")

    # Migrasi data offset lama dari tabel students ke student_programs
    cur.execute("""
        SELECT s.id, s.full_name, s.initial_meeting_offset, s.initial_offset_notes,
               s.initial_offset_set_at, s.initial_offset_set_by
        FROM students s
        WHERE s.initial_meeting_offset > 0
    """)
    students_with_offset = cur.fetchall()
    for s_id, s_name, off, notes, s_at, s_by in students_with_offset:
        # Cek apakah student_program aktif untuk siswa ini sudah memiliki initial_offset_total
        cur.execute("""
            SELECT id, initial_offset_total
            FROM student_programs
            WHERE student_id = ? AND status = 'aktif'
            ORDER BY id ASC
            LIMIT 1
        """, (s_id,))
        sp_row = cur.fetchone()
        if sp_row and (sp_row[1] == 0 or sp_row[1] is None):
            p = ((off - 1) // 8) + 1 if off > 0 else 0
            m = ((off - 1) % 8) + 1 if off > 0 else 0
            cur.execute("""
                UPDATE student_programs
                SET initial_periods_completed = ?,
                    initial_last_meeting = ?,
                    initial_offset_total = ?,
                    initial_offset_notes = ?,
                    initial_offset_set_at = ?,
                    initial_offset_set_by = ?
                WHERE id = ?
            """, (p, m, off, notes or "Migrasi otomatis dari baseline siswa", s_at, s_by, sp_row[0]))
            print(f"    [Migrasi Offset] Siswa {s_name} (ID {s_id}) -> Program SP ID {sp_row[0]}: Total {off} (Periode {p}, Pertemuan {m})")

    # 2. Tabel attendance: Tambahkan kolom program_id untuk kemudahan relasi per program
    att_cols = [c[1] for c in cur.execute("PRAGMA table_info(attendance)").fetchall()]
    if "program_id" not in att_cols:
        cur.execute("ALTER TABLE attendance ADD COLUMN program_id INTEGER REFERENCES programs(id)")
        print("    [+] Added attendance.program_id")

    # Backfill program_id dari schedules jika ada yang masih NULL
    cur.execute("""
        UPDATE attendance
        SET program_id = (SELECT program_id FROM schedules WHERE schedules.id = attendance.schedule_id)
        WHERE program_id IS NULL AND EXISTS (SELECT 1 FROM schedules WHERE schedules.id = attendance.schedule_id)
    """)

    # 3. Tabel audit_logs: Tambahkan kolom detail diff dan modul
    audit_cols = [c[1] for c in cur.execute("PRAGMA table_info(audit_logs)").fetchall()]
    if "module_name" not in audit_cols:
        cur.execute("ALTER TABLE audit_logs ADD COLUMN module_name TEXT")
        print("    [+] Added audit_logs.module_name")
    if "old_values" not in audit_cols:
        cur.execute("ALTER TABLE audit_logs ADD COLUMN old_values TEXT")
        print("    [+] Added audit_logs.old_values")
    if "new_values" not in audit_cols:
        cur.execute("ALTER TABLE audit_logs ADD COLUMN new_values TEXT")
        print("    [+] Added audit_logs.new_values")
    if "fields_changed" not in audit_cols:
        cur.execute("ALTER TABLE audit_logs ADD COLUMN fields_changed TEXT")
        print("    [+] Added audit_logs.fields_changed")
    if "status_code" not in audit_cols:
        cur.execute("ALTER TABLE audit_logs ADD COLUMN status_code INTEGER DEFAULT 200")
        print("    [+] Added audit_logs.status_code")

    # Backfill module_name pada audit_logs yang sudah ada
    cur.execute("""
        UPDATE audit_logs
        SET module_name = CASE
            WHEN action_type LIKE '%SISWA%' THEN 'Siswa'
            WHEN action_type LIKE '%PROGRAM%' THEN 'Program Siswa'
            WHEN action_type LIKE '%JADWAL%' OR action_type LIKE '%SCHEDULE%' THEN 'Jadwal'
            WHEN action_type LIKE '%ABSENSI%' OR action_type LIKE '%ATTENDANCE%' THEN 'Absensi'
            WHEN action_type LIKE '%MENTOR%' THEN 'Mentor'
            WHEN action_type LIKE '%LOGIN%' OR action_type LIKE '%LOGOUT%' THEN 'Autentikasi'
            WHEN action_type LIKE '%BACKUP%' THEN 'Backup'
            ELSE 'Operasional'
        END
        WHERE module_name IS NULL
    """)

    conn.commit()

    # Verifikasi integritas database
    integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"[*] Status integritas database: {integrity}")
    conn.close()
    return integrity == "ok"

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "database/desi_privat.db"
    if Path(target).exists():
        ok = migrate_database(target)
        if ok:
            print("[SUCCESS] Migrasi additive selesai dengan aman.")
        else:
            print("[ERROR] Integritas database bermasalah!")
            sys.exit(1)
    else:
        print(f"[!] File database {target} tidak ditemukan.")

