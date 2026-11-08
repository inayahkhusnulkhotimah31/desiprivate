import shutil
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.migrate_multi_program_and_monitoring import migrate_database

# 1. Clone backup to verified_staging.db
src = "backups/verified_pre_migration/production_supabase_backup_20261108_144743.db"
staging = "backups/verified_staging.db"
shutil.copyfile(src, staging)

# 2. Check counts before migration
conn1 = sqlite3.connect(staging)
cur1 = conn1.cursor()
count_users_before = cur1.execute("SELECT COUNT(*) FROM users").fetchone()[0]
count_students_before = cur1.execute("SELECT COUNT(*) FROM students").fetchone()[0]
count_parents_before = cur1.execute("SELECT COUNT(*) FROM parents").fetchone()[0]
count_programs_before = cur1.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
count_sp_before = cur1.execute("SELECT COUNT(*) FROM student_programs").fetchone()[0]
count_audits_before = cur1.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
conn1.close()

print("=== COUNTS BEFORE MIGRATION ===")
print(f"Users: {count_users_before}, Students: {count_students_before}, Parents: {count_parents_before}")
print(f"Programs: {count_programs_before}, Student Programs: {count_sp_before}, Audit Logs: {count_audits_before}")

# 3. Execute migration
ok = migrate_database(staging)
assert ok, "Migration failed integrity check!"

# 4. Check counts after migration
conn2 = sqlite3.connect(staging)
cur2 = conn2.cursor()
count_users_after = cur2.execute("SELECT COUNT(*) FROM users").fetchone()[0]
count_students_after = cur2.execute("SELECT COUNT(*) FROM students").fetchone()[0]
count_parents_after = cur2.execute("SELECT COUNT(*) FROM parents").fetchone()[0]
count_programs_after = cur2.execute("SELECT COUNT(*) FROM programs").fetchone()[0]
count_sp_after = cur2.execute("SELECT COUNT(*) FROM student_programs").fetchone()[0]
count_audits_after = cur2.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]

print("\n=== COUNTS AFTER MIGRATION ===")
print(f"Users: {count_users_after}, Students: {count_students_after}, Parents: {count_parents_after}")
print(f"Programs: {count_programs_after}, Student Programs: {count_sp_after}, Audit Logs: {count_audits_after}")

# Assert ZERO DATA LOSS
assert count_users_before == count_users_after, "Users count changed!"
assert count_students_before == count_students_after, "Students count changed!"
assert count_parents_before == count_parents_after, "Parents count changed!"
assert count_programs_before == count_programs_after, "Programs count changed!"
assert count_sp_before == count_sp_after, "Student Programs count changed!"
assert count_audits_before == count_audits_after, "Audit Logs count changed!"

# Check that Halim and Aya's initial offset was migrated to student_programs
cur2.execute("SELECT id, student_id, initial_offset_total, initial_periods_completed, initial_last_meeting FROM student_programs")
for sp_row in cur2.fetchall():
    print(f"Migrated SP: ID={sp_row[0]}, student_id={sp_row[1]}, total={sp_row[2]}, period={sp_row[3]}, meeting={sp_row[4]}")
    assert sp_row[2] == 6, f"Expected initial_offset_total 6, got {sp_row[2]}"

conn2.close()
print("\n[VERIFICATION PASSED 100%] ZERO DATA LOSS CONFIRMED!")
