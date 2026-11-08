-- DESI PRIVAT: Skema Database SQLite
-- Sistem Informasi Manajemen Tempat Les Privat

PRAGMA foreign_keys = ON;

-- 1. Tabel Pengguna (Users - Khusus Admin, Owner, Mentor)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'owner', 'mentor')),
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    is_active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabel Data Administratif Orang Tua / Wali (Parents - Tanpa Akun Pengguna)
CREATE TABLE IF NOT EXISTS parents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabel Siswa (Students)
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER NOT NULL REFERENCES parents(id) ON DELETE RESTRICT,
    full_name TEXT NOT NULL,
    school TEXT,
    grade TEXT,
    birth_date TEXT,
    address TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif', 'berhenti')),
    initial_meeting_offset INTEGER NOT NULL DEFAULT 0,
    initial_offset_notes TEXT,
    initial_offset_set_at DATETIME,
    initial_offset_set_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. Tabel Mentor (Mentors)
CREATE TABLE IF NOT EXISTS mentors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    expertise TEXT,
    bio TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. Tabel Program Les (Programs)
CREATE TABLE IF NOT EXISTS programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    description TEXT,
    level TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif', 'diarsipkan')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. Tabel Relasi Siswa - Program - Mentor (Student Programs)
CREATE TABLE IF NOT EXISTS student_programs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    mentor_id INTEGER REFERENCES mentors(id) ON DELETE SET NULL,
    start_date TEXT,
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'selesai', 'dibatalkan')),
    notes TEXT,
    initial_periods_completed INTEGER NOT NULL DEFAULT 0,
    initial_last_meeting INTEGER NOT NULL DEFAULT 0,
    initial_offset_total INTEGER NOT NULL DEFAULT 0,
    initial_offset_notes TEXT,
    initial_offset_set_at DATETIME,
    initial_offset_set_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 7. Ketersediaan Waktu Mentor (Mentor Availability)
-- day_of_week: 0=Senin, 1=Selasa, 2=Rabu, 3=Kamis, 4=Jumat, 5=Sabtu, 6=Minggu
CREATE TABLE IF NOT EXISTS mentor_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mentor_id INTEGER NOT NULL REFERENCES mentors(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
    start_time TEXT NOT NULL, -- Format HH:MM (24 jam)
    end_time TEXT NOT NULL,   -- Format HH:MM (24 jam)
    valid_from TEXT,
    valid_until TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 8. Ketersediaan / Waktu Kosong Siswa (Student Availability)
CREATE TABLE IF NOT EXISTS student_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    is_confirmed INTEGER DEFAULT 1,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 9. Tabel Jadwal Rutin Mingguan Siswa (Routine Schedules - Langsung Ditetapkan Admin)
-- day_of_week: 0=Senin, 1=Selasa, 2=Rabu, 3=Kamis, 4=Jumat, 5=Sabtu, 6=Minggu
CREATE TABLE IF NOT EXISTS routine_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    mentor_id INTEGER NOT NULL REFERENCES mentors(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
    start_time TEXT NOT NULL, -- Format HH:MM
    end_time TEXT NOT NULL,   -- Format HH:MM
    subject_info TEXT,        -- Informasi mata pelajaran atau jenis les sesuai program
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'aktif' CHECK(status IN ('aktif', 'nonaktif')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Aturan Jadwal Berulang (Legacy kompatibilitas)
CREATE TABLE IF NOT EXISTS recurring_schedule_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    mentor_id INTEGER NOT NULL REFERENCES mentors(id) ON DELETE CASCADE,
    days_of_week TEXT NOT NULL, -- Contoh "0,2" untuk Senin dan Rabu
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 10. Tabel Jadwal Sesi Les (Schedules)
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    program_id INTEGER NOT NULL REFERENCES programs(id) ON DELETE RESTRICT,
    student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE RESTRICT,
    mentor_id INTEGER NOT NULL REFERENCES mentors(id) ON DELETE RESTRICT,
    schedule_date TEXT NOT NULL, -- Format YYYY-MM-DD
    start_time TEXT NOT NULL,    -- Format HH:MM
    end_time TEXT NOT NULL,      -- Format HH:MM
    duration_minutes INTEGER NOT NULL DEFAULT 90,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN (
        'draft',
        'menunggu_konfirmasi_siswa',
        'menunggu_persetujuan_admin',
        'disetujui',
        'ditolak',
        'perlu_dijadwalkan_ulang',
        'dibatalkan'
    )),
    student_confirmation_status TEXT NOT NULL DEFAULT 'menunggu' CHECK(student_confirmation_status IN ('menunggu', 'bersedia', 'tidak_bisa')),
    student_confirmation_notes TEXT,
    mentor_response_status TEXT NOT NULL DEFAULT 'menunggu_konfirmasi' CHECK(mentor_response_status IN ('menunggu_konfirmasi', 'dikonfirmasi', 'tidak_bisa', 'perlu_mentor_pengganti')),
    mentor_response_notes TEXT,
    mentor_response_at DATETIME,
    is_recurring INTEGER DEFAULT 0,
    recurring_rule_id INTEGER REFERENCES recurring_schedule_rules(id) ON DELETE SET NULL,
    session_notes TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 11. Riwayat Pergantian Mentor (Mentor Replacements)
CREATE TABLE IF NOT EXISTS mentor_replacements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    original_mentor_id INTEGER NOT NULL REFERENCES mentors(id),
    replacement_mentor_id INTEGER NOT NULL REFERENCES mentors(id),
    reason TEXT NOT NULL,
    changed_by INTEGER NOT NULL REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 12. Tabel Absensi (Attendance)
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER UNIQUE NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id),
    mentor_id INTEGER NOT NULL REFERENCES mentors(id),
    program_id INTEGER REFERENCES programs(id),
    status TEXT NOT NULL CHECK(status IN ('hadir', 'izin', 'tidak_hadir')),
    topics_covered TEXT,
    progress_notes TEXT,
    meeting_number INTEGER,
    period_number INTEGER,
    cumulative_meeting INTEGER,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 13. Tabel Laporan Perkembangan Siswa (Student Progress)
CREATE TABLE IF NOT EXISTS student_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER UNIQUE NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES students(id),
    mentor_id INTEGER NOT NULL REFERENCES mentors(id),
    program_id INTEGER NOT NULL REFERENCES programs(id),
    session_date TEXT NOT NULL,
    topics_covered TEXT NOT NULL,
    skills_mastered TEXT,
    difficulties TEXT,
    recommendations TEXT,
    additional_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 14. Tabel Notifikasi In-App (Notifications)
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'info' CHECK(type IN ('info', 'jadwal', 'penggantian', 'absensi', 'perkembangan', 'peringatan')),
    is_read INTEGER DEFAULT 0,
    reference_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 15. Tabel Log Pengiriman Notifikasi WhatsApp & Saluran Lain (Notification Delivery Logs)
CREATE TABLE IF NOT EXISTS notification_delivery_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id INTEGER REFERENCES notifications(id) ON DELETE SET NULL,
    recipient_phone TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'whatsapp' CHECK(channel IN ('whatsapp', 'in_app')),
    template_name TEXT,
    payload TEXT,
    status TEXT NOT NULL CHECK(status IN ('sukses', 'gagal', 'simulasi')),
    response_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 16. Tabel Audit Log Aktivitas Admin & Sistem (Audit Logs)
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    user_name TEXT,
    action_type TEXT NOT NULL,
    module_name TEXT,
    target_entity TEXT NOT NULL,
    target_id TEXT,
    details TEXT,
    old_values TEXT,
    new_values TEXT,
    fields_changed TEXT,
    status_code INTEGER DEFAULT 200,
    ip_address TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 17. Tabel Riwayat Backup (Backups)
CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    created_by TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indeks Tambahan untuk Optimalisasi Performa Pencarian dan Kalender
CREATE INDEX IF NOT EXISTS idx_schedules_date ON schedules(schedule_date);
CREATE INDEX IF NOT EXISTS idx_schedules_mentor ON schedules(mentor_id);
CREATE INDEX IF NOT EXISTS idx_schedules_student ON schedules(student_id);
CREATE INDEX IF NOT EXISTS idx_schedules_status ON schedules(status);
CREATE INDEX IF NOT EXISTS idx_attendance_schedule ON attendance(schedule_id);
CREATE INDEX IF NOT EXISTS idx_student_progress_schedule ON student_progress(schedule_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
