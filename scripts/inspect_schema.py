import sqlite3

conn = sqlite3.connect('backups/verified_pre_migration/production_supabase_backup_20261108_144743.db')
cur = conn.cursor()
for table in ['students', 'student_programs', 'schedules', 'attendance', 'audit_logs']:
    for row in cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name = ?", (table,)):
        print('=== ' + table + ' ===')
        print(row[0])
        print()
conn.close()

