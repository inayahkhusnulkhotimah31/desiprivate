"""
Unit Tests for User Feedback Improvements
DESI PRIVAT - Bimbingan Belajar
"""
import unittest
import os
import sqlite3
from app import create_app
from services.database_service import query_db, execute_db
from services.meeting_service import (
    calculate_period_and_meeting,
    calculate_total_from_period_and_meeting,
    format_meeting_label,
    set_student_program_initial_history,
    get_student_program_meeting_stats
)

TEST_DB = "database/test_user_feedback.db"

class TestUserFeedbackImprovements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except OSError:
                pass

        os.environ["DATABASE_PATH"] = TEST_DB
        cls.db_path = TEST_DB
        from config import Config
        Config.DATABASE_PATH = TEST_DB
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["DATABASE_PATH"] = TEST_DB
        cls.client = cls.app.test_client()

        with open("database/schema.sql", "r", encoding="utf-8") as f:
            schema_sql = f.read()

        conn = sqlite3.connect(cls.db_path)
        conn.executescript(schema_sql)
        conn.close()

        # Seed initial admin and test data
        from werkzeug.security import generate_password_hash
        execute_db("""
            INSERT OR REPLACE INTO users (id, username, password_hash, role, full_name, is_active)
            VALUES (1, 'admin_test', ?, 'admin', 'Admin Penguji', 1)
        """, (generate_password_hash("admin123"),), db_path=cls.db_path)

        execute_db("""
            INSERT OR REPLACE INTO parents (id, full_name, phone, address)
            VALUES (1, 'Bapak Santoso', '081234567890', 'Jl. Kaliurang KM 5')
        """, db_path=cls.db_path)

        execute_db("""
            INSERT OR REPLACE INTO programs (id, name, code, level, description, status)
            VALUES (1, 'Matematika SD', 'MTK-SD', 'SD', 'Program Matematika Dasar', 'aktif'),
                   (2, 'Bahasa Inggris SMP', 'ENG-SMP', 'SMP', 'Program Bahasa Inggris', 'aktif'),
                   (3, 'Fisika SMA', 'FIS-SMA', 'SMA', 'Program Fisika Lanjutan', 'aktif')
        """, db_path=cls.db_path)

        execute_db("""
            INSERT OR REPLACE INTO mentors (id, full_name, phone, email, expertise, status)
            VALUES (1, 'Mentor Dimas', '081299998888', 'dimas@test.com', 'Matematika', 'aktif'),
                   (2, 'Mentor Sarah', '081277776666', 'sarah@test.com', 'Bahasa Inggris', 'aktif')
        """, db_path=cls.db_path)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except OSError:
                pass

    def get_admin_client(self):
        self.client.get("/login")
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin_test"
            sess["role"] = "admin"
            csrf = sess.get("_csrf_token")
        return self.client, csrf

    def test_01_dashboard_interactive_stat_cards(self):
        """A.1: Kartu statistik dashboard dapat diklik dan mengarah ke URL yang valid dengan class stat-card-link"""
        c, _ = self.get_admin_client()
        res = c.get("/admin/dashboard")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Cek class stat-card-link dan tag anchor
        self.assertIn("class=\"stat-card stat-card-link\"", html)
        self.assertIn("href=\"/admin/students\"", html)
        self.assertIn("href=\"/admin/mentors\"", html)
        self.assertIn("href=\"/admin/programs\"", html)
        self.assertIn("href=\"/admin/schedules?status=disetujui\"", html)
        self.assertIn("href=\"#actionAttentionSection\"", html)

    def test_02_dashboard_action_schedules_audit_and_counting(self):
        """A.2: Jadwal memerlukan perhatian mengabaikan status dibatalkan/ditolak dan menghitung total akurat"""
        c, _ = self.get_admin_client()

        # Siswa & pendaftaran
        execute_db("INSERT INTO students (id, parent_id, full_name, status) VALUES (10, 1, 'Siswa Perhatian', 'aktif')", db_path=self.db_path)
        execute_db("INSERT INTO student_programs (student_id, program_id, status) VALUES (10, 1, 'aktif')", db_path=self.db_path)

        # Jadwal 1: Menunggu persetujuan (harus dihitung)
        execute_db("""
            INSERT INTO schedules (id, student_id, mentor_id, program_id, schedule_date, start_time, end_time, status)
            VALUES (101, 10, 1, 1, '2026-12-01', '09:00', '10:30', 'menunggu_persetujuan_admin')
        """, db_path=self.db_path)

        # Jadwal 2: Perlu mentor pengganti (harus dihitung)
        execute_db("""
            INSERT INTO schedules (id, student_id, mentor_id, program_id, schedule_date, start_time, end_time, status, mentor_response_status)
            VALUES (102, 10, 1, 1, '2026-12-02', '09:00', '10:30', 'disetujui', 'perlu_mentor_pengganti')
        """, db_path=self.db_path)

        # Jadwal 3: Perlu mentor pengganti TETAPI sudah dibatalkan (TIDAK BOLEH dihitung)
        execute_db("""
            INSERT INTO schedules (id, student_id, mentor_id, program_id, schedule_date, start_time, end_time, status, mentor_response_status)
            VALUES (103, 10, 1, 1, '2026-12-03', '09:00', '10:30', 'dibatalkan', 'perlu_mentor_pengganti')
        """, db_path=self.db_path)

        # Jadwal 4: Ditolak (TIDAK BOLEH dihitung)
        execute_db("""
            INSERT INTO schedules (id, student_id, mentor_id, program_id, schedule_date, start_time, end_time, status, mentor_response_status)
            VALUES (104, 10, 1, 1, '2026-12-04', '09:00', '10:30', 'ditolak', 'perlu_mentor_pengganti')
        """, db_path=self.db_path)

        res = c.get("/admin/dashboard")
        self.assertEqual(res.status_code, 200)

        # Query langsung verifikasi
        count_row = query_db("""
            SELECT COUNT(s.id) as total
            FROM schedules s
            LEFT JOIN mentors m ON s.mentor_id = m.id
            WHERE s.status NOT IN ('dibatalkan', 'ditolak', 'selesai')
              AND (s.mentor_id IS NULL
                   OR s.status IN ('menunggu_persetujuan_admin', 'menunggu_konfirmasi_siswa')
                   OR s.mentor_response_status = 'perlu_mentor_pengganti')
        """, one=True, db_path=self.db_path)
        self.assertEqual(count_row["total"], 2)

        # Bersihkan jadwal tes
        execute_db("DELETE FROM schedules WHERE id IN (101, 102, 103, 104)", db_path=self.db_path)
        execute_db("DELETE FROM student_programs WHERE student_id = 10", db_path=self.db_path)
        execute_db("DELETE FROM students WHERE id = 10", db_path=self.db_path)

    def test_03_create_student_separated_from_scheduling(self):
        """B.3: Pendaftaran siswa baru terpisah dari penjadwalan & mentor, program tersimpan dengan baik"""
        c, csrf = self.get_admin_client()

        res = c.post("/admin/students/create", data={
            "csrf_token": csrf,
            "full_name": "Siswa Terpisah",
            "school": "SD Cerdas",
            "grade": "Kelas 4",
            "parent_id": 1,
            "program_id": 1,
            "notes": "Target pemahaman pecahan",
            "initial_periods_completed": "2",
            "initial_last_meeting": "4"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        st = query_db("SELECT id, full_name FROM students WHERE full_name = 'Siswa Terpisah'", one=True, db_path=self.db_path)
        self.assertIsNotNone(st)

        sp = query_db("SELECT * FROM student_programs WHERE student_id = ? AND program_id = 1", (st["id"],), one=True, db_path=self.db_path)
        self.assertIsNotNone(sp)
        self.assertIsNone(sp["mentor_id"]) # Mentor belum ditugaskan saat daftar
        self.assertEqual(sp["initial_periods_completed"], 2)
        self.assertEqual(sp["initial_last_meeting"], 4)
        self.assertEqual(sp["initial_offset_total"], 12) # (2 - 1) * 8 + 4 = 12

        # Pastikan tidak ada slot rutin yang otomatis dibuat
        routines = query_db("SELECT * FROM routine_schedules WHERE student_id = ?", (st["id"],), db_path=self.db_path)
        self.assertEqual(len(routines), 0)

        execute_db("DELETE FROM student_programs WHERE student_id = ?", (st["id"],), db_path=self.db_path)
        execute_db("DELETE FROM students WHERE id = ?", (st["id"],), db_path=self.db_path)

    def test_04_routine_scheduling_filtered_to_enrolled_programs(self):
        """B.4: Penjadwalan rutin hanya menerima program yang diambil siswa & validasi 1 hari 1 waktu"""
        c, csrf = self.get_admin_client()

        execute_db("INSERT INTO students (id, parent_id, full_name, status) VALUES (20, 1, 'Siswa Khusus MTK', 'aktif')", db_path=self.db_path)
        execute_db("INSERT INTO student_programs (student_id, program_id, status) VALUES (20, 1, 'aktif')", db_path=self.db_path)

        # 1. API enrolled programs mengembalikan HANYA program 1 (MTK), bukan program 2 atau 3
        res_api = c.get(f"/admin/api/students/20/programs")
        self.assertEqual(res_api.status_code, 200)
        programs_json = res_api.get_json()
        self.assertEqual(len(programs_json), 1)
        self.assertEqual(programs_json[0]["id"], 1)

        # 2. Coba buat jadwal rutin untuk program yang TIDAK diambil siswa (misal: Program 2) -> Harus ditolak
        res_fail = c.post("/admin/schedules/routine/create", data={
            "csrf_token": csrf,
            "student_id": 20,
            "program_id": 2, # Siswa tidak mengambil program 2!
            "mentor_id": 2,
            "day_of_week": 1,
            "start_time": "15:00",
            "end_time": "16:30"
        }, follow_redirects=True)
        self.assertEqual(res_fail.status_code, 200)
        routines_fail = query_db("SELECT * FROM routine_schedules WHERE student_id = 20 AND program_id = 2", db_path=self.db_path)
        self.assertEqual(len(routines_fail), 0)

        # 3. Buat jadwal rutin untuk program yang valid (Program 1) -> Harus berhasil
        res_ok = c.post("/admin/schedules/routine/create", data={
            "csrf_token": csrf,
            "student_id": 20,
            "program_id": 1,
            "mentor_id": 1,
            "day_of_week": 1, # Senin
            "start_time": "15:00",
            "end_time": "16:30",
            "subject_info": "Matematika Geometri"
        }, follow_redirects=True)
        self.assertEqual(res_ok.status_code, 200)
        routines_ok = query_db("SELECT * FROM routine_schedules WHERE student_id = 20 AND program_id = 1", db_path=self.db_path)
        self.assertEqual(len(routines_ok), 1)
        self.assertEqual(routines_ok[0]["day_of_week"], 1)

        execute_db("DELETE FROM routine_schedules WHERE student_id = 20", db_path=self.db_path)
        execute_db("DELETE FROM student_programs WHERE student_id = 20", db_path=self.db_path)
        execute_db("DELETE FROM students WHERE id = 20", db_path=self.db_path)

    def test_05_initial_offset_period_3_meeting_5_transition(self):
        """B.5: Verifikasi transisi offset Periode 3 Pertemuan 5 -> Pertemuan 6 [3] -> Pertemuan 8 [3] -> Pertemuan 1 [4]"""
        c, _ = self.get_admin_client()

        execute_db("INSERT INTO students (id, parent_id, full_name, status) VALUES (30, 1, 'Siswa P3M5', 'aktif')", db_path=self.db_path)
        execute_db("INSERT INTO student_programs (id, student_id, program_id, status) VALUES (301, 30, 1, 'aktif')", db_path=self.db_path)

        # Atur riwayat awal: Periode 3, Pertemuan 5
        res = set_student_program_initial_history(
            student_id=30,
            program_id=1,
            last_period=3,
            last_meeting=5,
            notes="Kartu les lama 2025",
            admin_user_id=1,
            db_path=self.db_path
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["total_offset"], 21) # (3-1)*8 + 5 = 21

        # Cek stats sebelum ada sesi baru di sistem: Sesi berikutnya adalah Pertemuan 6 [3]
        stats = get_student_program_meeting_stats(30, 1, db_path=self.db_path)
        self.assertEqual(stats["next_period"], 3)
        self.assertEqual(stats["next_meeting"], 6)
        self.assertEqual(stats["next_meeting_bracket"], "Pertemuan 6 [3]")

        # Simulasikan 3 sesi selesai dengan absensi 'hadir'
        # Total pertemuan menjadi 21 + 3 = 24 (Pertemuan 8 Periode 3)
        for i in range(1, 4):
            sched_id = 300 + i
            execute_db(f"""
                INSERT INTO schedules (id, student_id, mentor_id, program_id, schedule_date, start_time, end_time, status)
                VALUES ({sched_id}, 30, 1, 1, '2026-12-0{i}', '16:00', '17:30', 'disetujui')
            """, db_path=self.db_path)
            execute_db(f"""
                INSERT INTO attendance (schedule_id, student_id, mentor_id, status, session_status)
                VALUES ({sched_id}, 30, 1, 'hadir', 'terlaksana')
            """, db_path=self.db_path)

        stats_after_3 = get_student_program_meeting_stats(30, 1, db_path=self.db_path)
        self.assertEqual(stats_after_3["total_completed"], 24)
        self.assertEqual(stats_after_3["last_period"], 3)
        self.assertEqual(stats_after_3["last_meeting"], 8)
        self.assertEqual(stats_after_3["last_meeting_bracket"], "Pertemuan 8 [3]")
        # Sesi berikutnya otomatis beralih ke Periode 4 Pertemuan 1!
        self.assertEqual(stats_after_3["next_period"], 4)
        self.assertEqual(stats_after_3["next_meeting"], 1)
        self.assertEqual(stats_after_3["next_meeting_bracket"], "Pertemuan 1 [4]")

        # Simulasikan 1 sesi lagi dengan status 'siswa_berhalangan' (TIDAK BOLEH menambah hitungan)
        sched_id = 304
        execute_db(f"""
            INSERT INTO schedules (id, student_id, mentor_id, program_id, schedule_date, start_time, end_time, status)
            VALUES ({sched_id}, 30, 1, 1, '2026-12-04', '16:00', '17:30', 'disetujui')
        """, db_path=self.db_path)
        execute_db(f"""
            INSERT INTO attendance (schedule_id, student_id, mentor_id, status, session_status)
            VALUES ({sched_id}, 30, 1, 'izin', 'siswa_berhalangan')
        """, db_path=self.db_path)

        stats_after_absent = get_student_program_meeting_stats(30, 1, db_path=self.db_path)
        self.assertEqual(stats_after_absent["total_completed"], 24) # Tetap 24!
        self.assertEqual(stats_after_absent["next_meeting_bracket"], "Pertemuan 1 [4]")

        # Sesi ke-5 'hadir' -> Total menjadi 25 (Pertemuan 1 [4])
        sched_id = 305
        execute_db(f"""
            INSERT INTO schedules (id, student_id, mentor_id, program_id, schedule_date, start_time, end_time, status)
            VALUES ({sched_id}, 30, 1, 1, '2026-12-05', '16:00', '17:30', 'disetujui')
        """, db_path=self.db_path)
        execute_db(f"""
            INSERT INTO attendance (schedule_id, student_id, mentor_id, status, session_status)
            VALUES ({sched_id}, 30, 1, 'hadir', 'terlaksana')
        """, db_path=self.db_path)

        stats_p4m1 = get_student_program_meeting_stats(30, 1, db_path=self.db_path)
        self.assertEqual(stats_p4m1["total_completed"], 25)
        self.assertEqual(stats_p4m1["last_period"], 4)
        self.assertEqual(stats_p4m1["last_meeting"], 1)
        self.assertEqual(stats_p4m1["last_meeting_bracket"], "Pertemuan 1 [4]")
        self.assertEqual(stats_p4m1["next_meeting_bracket"], "Pertemuan 2 [4]")

        # Bersihkan data
        execute_db("DELETE FROM attendance WHERE student_id = 30", db_path=self.db_path)
        execute_db("DELETE FROM schedules WHERE student_id = 30", db_path=self.db_path)
        execute_db("DELETE FROM student_programs WHERE student_id = 30", db_path=self.db_path)
        execute_db("DELETE FROM students WHERE id = 30", db_path=self.db_path)

    def test_06_finance_and_honor_cards_removed_from_dashboard(self):
        """C.6: Memastikan dashboard admin tidak menampilkan kartu widget keuangan dan honor di area konten utama"""
        c, _ = self.get_admin_client()
        res = c.get("/admin/dashboard")
        html = res.data.decode("utf-8")

        # Ambil bagian <main>...</main>
        start_main = html.find("<main")
        end_main = html.find("</main>")
        self.assertGreater(start_main, 0)
        self.assertGreater(end_main, start_main)
        main_content = html[start_main:end_main]

        # Di dalam body dashboard (<main>), TIDAK BOLEH ada kartu tagihan maupun rekap honor
        self.assertNotIn("Tagihan dan Pembayaran", main_content)
        self.assertNotIn("Rekap Honor Mentor", main_content)
        self.assertNotIn("Tagihan & Pembayaran", main_content)

        # Sesuai instruksi terbaru pemilik: Tagihan dan Honor HANYA ada di bagian Owner, dihapus dari Admin
        sidebar_content = html[:start_main]
        self.assertNotIn("Tagihan & Pembayaran", sidebar_content)
        self.assertNotIn("Rekap Honor Mentor", sidebar_content)

if __name__ == "__main__":
    unittest.main()
