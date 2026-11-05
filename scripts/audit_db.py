import sqlite3

conn = sqlite3.connect('database/desi_privat.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== USERS ===")
for u in c.execute("SELECT id, username, full_name, role, is_active, created_at FROM users").fetchall():
    print(dict(u))

print("\n=== STUDENTS ===")
for s in c.execute("SELECT id, full_name, parent_id, school, grade, status FROM students").fetchall():
    print(dict(s))

print("\n=== PARENTS ===")
for p in c.execute("SELECT id, full_name, phone, user_id FROM parents").fetchall():
    print(dict(p))

print("\n=== MENTORS ===")
for m in c.execute("SELECT id, user_id, full_name, phone, status FROM mentors").fetchall():
    print(dict(m))

print("\n=== PROGRAMS ===")
for pr in c.execute("SELECT id, name, code, status FROM programs").fetchall():
    print(dict(pr))

print("\n=== STUDENT PROGRAMS ===")
for sp in c.execute("SELECT * FROM student_programs").fetchall():
    print(dict(sp))

print("\n=== RECURRING SCHEDULE RULES ===")
for r in c.execute("SELECT * FROM recurring_schedule_rules").fetchall():
    print(dict(r))

print("\n=== SCHEDULES ===")
for sc in c.execute("SELECT id, title, student_id, mentor_id, schedule_date, start_time, end_time, status FROM schedules").fetchall():
    print(dict(sc))

print("\n=== ATTENDANCE ===")
for a in c.execute("SELECT id, schedule_id, student_id, mentor_id, status, meeting_number, period_number, recorded_at FROM attendance").fetchall():
    print(dict(a))
