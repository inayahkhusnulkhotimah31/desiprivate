-- ========================================================================
-- DESI PRIVAT - Skema Database PostgreSQL / Supabase Cloud
-- Kompatibel penuh untuk hosting Vercel Serverless + Supabase Database
-- ========================================================================

-- 1. TABEL PENGGUNA (users)
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'owner', 'mentor')),
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. TABEL ORANG TUA / WALI (parents)
CREATE TABLE IF NOT EXISTS parents (
    id BIGSERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. TABEL SISWA (students)
CREATE TABLE IF NOT EXISTS students (
    id BIGSERIAL PRIMARY KEY,
    parent_id BIGINT NOT NULL REFERENCES parents(id) ON DELETE RESTRICT,
    full_name TEXT NOT NULL,
    school TEXT,
    grade TEXT,
    birth_date TEXT,
    address TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif', 'berhenti')),
    initial_meeting_offset INTEGER NOT NULL DEFAULT 0,
    initial_offset_notes TEXT,
    initial_offset_set_at TIMESTAMPTZ,
    initial_offset_set_by BIGINT REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. TABEL MENTOR (mentors)
CREATE TABLE IF NOT EXISTS mentors (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    expertise TEXT,
    bio TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 5. TABEL PROGRAM LES (programs)
CREATE TABLE IF NOT EXISTS programs (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    description TEXT,
    level TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif', 'diarsipkan')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 6. TABEL RELASI SISWA - PROGRAM (student_programs)
CREATE TABLE IF NOT EXISTS student_programs (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    program_id BIGINT NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    mentor_id BIGINT REFERENCES mentors(id) ON DELETE SET NULL,
    start_date TEXT,
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'selesai', 'dibatalkan')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 7. KETERSEDIAAN MENTOR (mentor_availability)
CREATE TABLE IF NOT EXISTS mentor_availability (
    id BIGSERIAL PRIMARY KEY,
    mentor_id BIGINT NOT NULL REFERENCES mentors(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    valid_from TEXT,
    valid_until TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 8. KETERSEDIAAN SISWA (student_availability)
CREATE TABLE IF NOT EXISTS student_availability (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    is_confirmed INTEGER DEFAULT 1,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 9. JADWAL RUTIN MINGGUAN (routine_schedules)
CREATE TABLE IF NOT EXISTS routine_schedules (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    program_id BIGINT NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    mentor_id BIGINT NOT NULL REFERENCES mentors(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    subject_info TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 10. JADWAL SESI LES (schedules)
CREATE TABLE IF NOT EXISTS schedules (
    id BIGSERIAL PRIMARY KEY,
    title TEXT,
    program_id BIGINT NOT NULL REFERENCES programs(id) ON DELETE RESTRICT,
    student_id BIGINT NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
    mentor_id BIGINT NOT NULL REFERENCES mentors(id) ON DELETE RESTRICT,
    schedule_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 90,
    status TEXT NOT NULL DEFAULT 'disetujui',
    student_confirmation_status TEXT NOT NULL DEFAULT 'bersedia',
    student_confirmation_notes TEXT,
    mentor_response_status TEXT NOT NULL DEFAULT 'dikonfirmasi',
    mentor_response_notes TEXT,
    mentor_response_at TIMESTAMPTZ,
    is_recurring INTEGER DEFAULT 0,
    recurring_rule_id BIGINT,
    session_notes TEXT,
    created_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    approved_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 11. RIWAYAT PERGANTIAN MENTOR (mentor_replacements)
CREATE TABLE IF NOT EXISTS mentor_replacements (
    id BIGSERIAL PRIMARY KEY,
    schedule_id BIGINT NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    original_mentor_id BIGINT NOT NULL REFERENCES mentors(id),
    replacement_mentor_id BIGINT NOT NULL REFERENCES mentors(id),
    reason TEXT NOT NULL,
    changed_by BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 12. TABEL ABSENSI (attendance)
CREATE TABLE IF NOT EXISTS attendance (
    id BIGSERIAL PRIMARY KEY,
    schedule_id BIGINT UNIQUE NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES students(id),
    mentor_id BIGINT NOT NULL REFERENCES mentors(id),
    status TEXT NOT NULL CHECK(status IN ('hadir', 'izin', 'tidak_hadir')),
    topics_covered TEXT,
    progress_notes TEXT,
    meeting_number INTEGER,
    period_number INTEGER,
    cumulative_meeting INTEGER,
    recorded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 13. TABEL PERKEMBANGAN SISWA (student_progress)
CREATE TABLE IF NOT EXISTS student_progress (
    id BIGSERIAL PRIMARY KEY,
    schedule_id BIGINT UNIQUE NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    student_id BIGINT NOT NULL REFERENCES students(id),
    mentor_id BIGINT NOT NULL REFERENCES mentors(id),
    program_id BIGINT NOT NULL REFERENCES programs(id),
    session_date TEXT NOT NULL,
    topics_covered TEXT NOT NULL,
    skills_mastered TEXT,
    difficulties TEXT,
    recommendations TEXT,
    additional_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 14. TABEL NOTIFIKASI (notifications)
CREATE TABLE IF NOT EXISTS notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'info',
    is_read INTEGER DEFAULT 0,
    reference_url TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 15. TABEL LOG PENGIRIMAN (notification_delivery_logs)
CREATE TABLE IF NOT EXISTS notification_delivery_logs (
    id BIGSERIAL PRIMARY KEY,
    notification_id BIGINT REFERENCES notifications(id) ON DELETE SET NULL,
    recipient_phone TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    template_name TEXT,
    payload TEXT,
    status TEXT NOT NULL,
    response_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 16. TABEL AUDIT LOG (audit_logs)
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    user_name TEXT,
    action_type TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    target_id TEXT,
    details TEXT,
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 17. TABEL BACKUP (backups)
CREATE TABLE IF NOT EXISTS backups (
    id BIGSERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    created_by TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- INDEKS EFISIENSI
CREATE INDEX IF NOT EXISTS idx_schedules_date ON schedules(schedule_date);
CREATE INDEX IF NOT EXISTS idx_schedules_mentor ON schedules(mentor_id);
CREATE INDEX IF NOT EXISTS idx_schedules_student ON schedules(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_schedule ON attendance(schedule_id);

-- ========================================================================
-- DATA AWAL SISTEM (TERVERIFIKASI & DATA NYATA)
-- ========================================================================

-- Akun Pengguna (Admin, Owner, Mentor Inayah)
INSERT INTO users (id, username, password_hash, role, full_name, email, phone, is_active)
VALUES
(1002, 'admin', 'scrypt:32768:8:1$qzk5Naqh8kHuuSAH$74781eb50e9bbc326974cd394edf16d8f88c877b6256f3a61162195f3f9f5b53341ebf53d6e501abf70e9e17047e23af16fb40bd1d5b7e925a148f9c3cc39cf4', 'admin', 'Admin Pengelola DESI', 'admin@desiprivat.id', '081234567801', 1),
(1003, 'owner', 'scrypt:32768:8:1$IpkE63i4MpqLLViZ$3a9732d3552b4b90158410dbc1e61a7e25986bbb84522ff7a02246394cb7e9d5533359214c667a4ca382ae2db8129f9ba51e6d92bffa444a1ff0f704b21d66e8', 'owner', 'Ibu Desi (Pemilik)', 'owner@desiprivat.id', '081234567802', 1),
(1004, 'inayah', 'scrypt:32768:8:1$ocy9VdjSKYw1Me7X$5b7441da37c1d5069a3d00e7399332bb38d4e5e485c1433b1e699c61219b100fa40832f4f6434e44fca727ab6ebfbb886cd54b00f57e9e4988abd46b9b7d75a0', 'mentor', 'inayah', '', '085820313260', 1)
ON CONFLICT (username) DO NOTHING;

-- Data Wali Murid
INSERT INTO parents (id, full_name, phone, email, address, notes, status)
VALUES
(17, 'satriana', '081244388891', '', 'jl tinumbu', '', 'aktif')
ON CONFLICT (id) DO NOTHING;

-- Data Siswa
INSERT INTO students (id, parent_id, full_name, school, grade, birth_date, address, notes, status, initial_meeting_offset)
VALUES
(37, 17, 'Muzayyan', 'SMP IT COBIG', 'Kelas 8 SMP', '2012-11-14', 'jln Tinummbu', '', 'aktif', 0)
ON CONFLICT (id) DO NOTHING;

-- Data Mentor
INSERT INTO mentors (id, user_id, full_name, phone, email, expertise, bio, status)
VALUES
(12, 1004, 'inayah', '085820313260', '', 'Matematika', '', 'aktif')
ON CONFLICT (id) DO NOTHING;

-- Program Les
INSERT INTO programs (id, name, code, description, level, status)
VALUES
(6, 'Math Olimpiade', 'MAT-SMP', 'Tips n Trick Menghadapi soal" olimpiade', 'SD - SMA', 'aktif'),
(7, 'Mengaji', 'IPA-SMP', 'mengaji, Tajwid, dan menghafal al-qur''an', 'TK - SMA', 'aktif'),
(8, 'English', 'ENG-SD-SMP', 'Grammar praktis, vocabulary booster, dan percakapan percaya diri', 'SD - SMA', 'aktif'),
(9, 'Calistung & Pendampingan SD', 'CLS-SD', 'Membaca lancar, menulis rapi, dan berhitung dasar menyenangkan', 'TK B & SD Kelas 1-3', 'aktif'),
(10, 'Math School', 'MATH', 'Belajar matematika dari dasar dan trik hitung cepat', 'SD - SMA', 'aktif')
ON CONFLICT (id) DO NOTHING;

-- Relasi Siswa Program
INSERT INTO student_programs (id, student_id, program_id, mentor_id, start_date, status, notes)
VALUES
(19, 37, 10, 12, '2026-11-05', 'aktif', 'Hitung cepat')
ON CONFLICT (id) DO NOTHING;

-- Jadwal Rutin Mingguan
INSERT INTO routine_schedules (id, student_id, program_id, mentor_id, day_of_week, start_time, end_time, subject_info, notes, status)
VALUES
(7, 37, 10, 12, 0, '10:00', '10:30', 'Hitung cepat', 'Jadwal rutin mingguan pendaftaran siswa', 'aktif'),
(8, 37, 10, 12, 5, '13:00', '14:30', 'Hitung cepat', 'Jadwal rutin mingguan pendaftaran siswa', 'aktif')
ON CONFLICT (id) DO NOTHING;

-- Sesi Jadwal
INSERT INTO schedules (id, title, program_id, student_id, mentor_id, schedule_date, start_time, end_time, duration_minutes, status, student_confirmation_status, mentor_response_status, created_by, approved_by)
VALUES
(102, 'Sesi Math School - Muzayyan (Senin)', 10, 37, 12, '2026-11-02', '22:00', '23:30', 90, 'disetujui', 'bersedia', 'dikonfirmasi', 1002, 1002)
ON CONFLICT (id) DO NOTHING;

-- Absensi Sesi
INSERT INTO attendance (id, schedule_id, student_id, mentor_id, status, topics_covered, progress_notes, meeting_number, period_number, cumulative_meeting)
VALUES
(21, 102, 37, 12, 'hadir', 'trik hitung', '', 1, 1, 1)
ON CONFLICT (id) DO NOTHING;

-- Reset Urutan Auto-Increment ID (agar penambahan data baru otomatis berlanjut dengan benar)
SELECT setval(pg_get_serial_sequence('users', 'id'), COALESCE((SELECT MAX(id) FROM users), 1005));
SELECT setval(pg_get_serial_sequence('parents', 'id'), COALESCE((SELECT MAX(id) FROM parents), 18));
SELECT setval(pg_get_serial_sequence('students', 'id'), COALESCE((SELECT MAX(id) FROM students), 38));
SELECT setval(pg_get_serial_sequence('mentors', 'id'), COALESCE((SELECT MAX(id) FROM mentors), 13));
SELECT setval(pg_get_serial_sequence('programs', 'id'), COALESCE((SELECT MAX(id) FROM programs), 11));
SELECT setval(pg_get_serial_sequence('student_programs', 'id'), COALESCE((SELECT MAX(id) FROM student_programs), 20));
SELECT setval(pg_get_serial_sequence('routine_schedules', 'id'), COALESCE((SELECT MAX(id) FROM routine_schedules), 9));
SELECT setval(pg_get_serial_sequence('schedules', 'id'), COALESCE((SELECT MAX(id) FROM schedules), 103));
SELECT setval(pg_get_serial_sequence('attendance', 'id'), COALESCE((SELECT MAX(id) FROM attendance), 22));

