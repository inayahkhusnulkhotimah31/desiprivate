import sqlite3

conn = sqlite3.connect('backups/verified_pre_migration/production_supabase_backup_20261108_144743.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== STUDENTS ===")
for row in cur.execute("SELECT * FROM students"):
    print(dict(row))

print("\n=== STUDENT_PROGRAMS ===")
for row in cur.execute("SELECT * FROM student_programs"):
    print(dict(row))

print("\n=== SCHEDULES COUNT ===")
print(cur.execute("SELECT COUNT(*) FROM schedules").fetchone()[0])

print("\n=== ATTENDANCE COUNT ===")
print(cur.execute("SELECT COUNT(*) FROM attendance").fetchone()[0])

print("\n=== AUDIT LOGS COUNT ===")
print(cur.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0])

conn.close()

