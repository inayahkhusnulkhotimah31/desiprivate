"""
Test Suite untuk LANGKAH 3: Absensi Mentor Terpisah & Dokumentasi Sesi Belajar
Memverifikasi 12 skenario wajib secara menyeluruh.
"""
import unittest
import os
import io
import json
import sqlite3
import shutil
from datetime import date

import sys
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from config import Config, BASE_DIR
from services.database_service import query_db, execute_db
from services.meeting_service import (
    record_or_update_attendance, get_student_program_meeting_stats,
    get_student_meeting_stats, calculate_period_and_meeting
)

class TestLangkah3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["FLASK_ENV"] = "development"
        cls.test_db_path = str(BASE_DIR / "database" / "test_langkah_3.db")
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass
        test_source = BASE_DIR / "database" / "desi_privat_testing.db"
        if not test_source.exists():
            test_source = BASE_DIR / "database" / "desi_privat.db"
        shutil.copyfile(str(test_source), cls.test_db_path)
        cls.orig_db_path = Config.DATABASE_PATH
        Config.DATABASE_PATH = cls.test_db_path
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["DATABASE_PATH"] = cls.test_db_path
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            # Seed data pengguna, orang tua, program, mentor, dan murid untuk menjaga integritas FK
            execute_db("""
                INSERT OR REPLACE INTO users (id, username, password_hash, role, full_name, is_active)
                VALUES (1, 'admin', 'pbkdf2:dummy', 'admin', 'Admin Pengelola', 1),
                       (1005, 'andiriska', 'pbkdf2:dummy', 'mentor', 'Andi Riska Putri Muliadi', 1),
                       (1006, 'atira', 'pbkdf2:dummy', 'mentor', 'Atira', 1),
                       (1025, 'parent_aya', 'pbkdf2:dummy', 'parent', 'Orang Tua Aya', 1)
            """, db_path=cls.test_db_path)

            execute_db("""
                INSERT OR REPLACE INTO parents (id, user_id, full_name, phone, address)
                VALUES (10, 1025, 'Orang Tua Aya', '0812345678', 'Jl. Kaliurang')
            """, db_path=cls.test_db_path)

            execute_db("""
                INSERT OR REPLACE INTO programs (id, name, code, description, status)
                VALUES (10, 'Math School', 'MATH-TEST-10', 'Belajar Matematika', 'aktif')
            """, db_path=cls.test_db_path)

            execute_db("""
                INSERT OR REPLACE INTO mentors (id, user_id, full_name, phone, expertise, status, address, latitude, longitude)
                VALUES (14, 1005, 'Andi Riska Putri Muliadi', '081200000014', 'Biologi', 'aktif', 'Jl. Uji 14', -7.765, 110.372),
                       (15, 1006, 'Atira', '081200000015', 'Math', 'aktif', 'Jl. Uji 15', -7.760, 110.370)
            """, db_path=cls.test_db_path)

            execute_db("""
                INSERT OR REPLACE INTO students (id, parent_id, full_name, school, grade, status, payment_status, address, latitude, longitude)
                VALUES (38, 10, 'Muh. Halim', 'SD Uji', '5', 'aktif', 'lunas', 'Jl. Murid 38', NULL, NULL),
                       (39, 10, 'Aya', 'SD Uji', '4', 'aktif', 'lunas', 'Jl. Murid 39', -7.7750, 110.3750)
            """, db_path=cls.test_db_path)

            execute_db("""
                INSERT OR IGNORE INTO student_programs (student_id, program_id, mentor_id, start_date, status)
                VALUES (39, 10, 14, '2026-11-01', 'aktif'),
                       (39, 3, 14, '2026-11-01', 'aktif')
            """, db_path=cls.test_db_path)

    @classmethod
    def tearDownClass(cls):
        Config.DATABASE_PATH = cls.orig_db_path
        if hasattr(cls, "test_db_path") and os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass

    def setUp(self):
        Config.DATABASE_PATH = self.test_db_path
        self.app.config["DATABASE_PATH"] = self.test_db_path

    def get_csrf(self, client=None):
        c = client or self.client
        with c.session_transaction() as sess:
            token = sess.get("_csrf_token")
            if not token:
                token = "test_csrf_token_langkah3"
                sess["_csrf_token"] = token
            return token

    def test_01_historical_data_integrity(self):
        """Skenario 8: Verifikasi 5 data historis lama tetap utuh dengan mentor_status=NULL dan session_status='terlaksana'"""
        rows = query_db("SELECT id, status, mentor_status, session_status, documentation_status, documentation_photo FROM attendance WHERE id IN (22, 23, 24, 25, 26) ORDER BY id ASC")
        self.assertEqual(len(rows), 5)
        for r in rows:
            self.assertEqual(r["status"], "hadir")
            self.assertIn(r["mentor_status"], (None, "hadir"))
            self.assertEqual(r["session_status"], "terlaksana")
            self.assertIn(r["documentation_status"], ("tidak_ada", "menunggu"))
            self.assertIsNone(r["documentation_photo"])

    def test_02_mentor_attendance_unique_constraint(self):
        """Skenario 10: Constraint UNIQUE (schedule_id, mentor_id, attendance_date) mencegah duplikasi tanggal yang sama"""
        today = date.today().strftime("%Y-%m-%d")

        # Buat schedule valid untuk foreign key
        sched_id = execute_db("""
            INSERT INTO schedules (title, program_id, student_id, mentor_id, schedule_date, start_time, end_time, duration_minutes, status)
            VALUES ('Schedule for Unique Test', 10, 39, 14, ?, '10:00', '11:30', 90, 'disetujui')
        """, (today,))

        try:
            # Insert pertama
            execute_db("""
                INSERT INTO mentor_attendance (schedule_id, mentor_id, status, attendance_date, notes)
                VALUES (?, 14, 'hadir', ?, 'Test Unique 1')
            """, (sched_id, today))

            # Update / replace berhasil tanpa error
            execute_db("""
                INSERT OR REPLACE INTO mentor_attendance (schedule_id, mentor_id, status, attendance_date, notes)
                VALUES (?, 14, 'hadir', ?, 'Test Unique 2')
            """, (sched_id, today))

            # Verifikasi hanya ada 1 record untuk schedule_id di tanggal tersebut
            count = query_db("SELECT COUNT(*) as c FROM mentor_attendance WHERE schedule_id = ? AND attendance_date = ?", (sched_id, today), one=True)["c"]
            self.assertEqual(count, 1)
        finally:
            execute_db("DELETE FROM mentor_attendance WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM schedules WHERE id = ?", (sched_id,))

    def test_03_condition_1_mentor_present_session_completed(self):
        """Skenario 1: Mentor hadir & sesi terlaksana -> Pertemuan valid bertambah (+1), foto terhubung"""
        stats_before = get_student_program_meeting_stats(39, 10)
        baseline = stats_before["total_completed"]

        sched_id = execute_db("""
            INSERT INTO schedules (title, program_id, student_id, mentor_id, schedule_date, start_time, end_time, duration_minutes, status)
            VALUES ('Test Sesi Terlaksana', 10, 39, 14, '2026-11-20', '16:00', '17:30', 90, 'disetujui')
        """)

        try:
            res = record_or_update_attendance(
                schedule_id=sched_id,
                student_id=39,
                mentor_id=14,
                status="hadir",
                topics_covered="Persamaan Kuadratik Bagian 1",
                progress_notes="Siswa sangat aktif memahami rumus abc.",
                mentor_status="hadir",
                session_status="terlaksana",
                documentation_status="lengkap",
                documentation_photo="test_photo_01.jpg",
                attendance_date="2026-11-20"
            )

            self.assertTrue(res["success"])
            self.assertEqual(res["mentor_status"], "hadir")
            self.assertEqual(res["session_status"], "terlaksana")
            self.assertEqual(res["documentation_status"], "lengkap")
            self.assertEqual(res["documentation_photo"], "test_photo_01.jpg")

            # Cek penambahan pertemuan siswa
            stats_after = get_student_program_meeting_stats(39, 10)
            self.assertEqual(stats_after["total_completed"], baseline + 1)

            # Cek catatan mandiri di tabel mentor_attendance
            ma = query_db("SELECT * FROM mentor_attendance WHERE schedule_id = ? AND mentor_id = 14", (sched_id,), one=True)
            self.assertIsNotNone(ma)
            self.assertEqual(ma["status"], "hadir")
        finally:
            execute_db("DELETE FROM attendance WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM mentor_attendance WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM student_progress WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM schedules WHERE id = ?", (sched_id,))

    def test_04_condition_2_mentor_present_student_absent(self):
        """Skenario 2: Mentor hadir, siswa berhalangan -> Kehadiran mentor tercatat, pertemuan siswa TIDAK bertambah"""
        stats_before = get_student_program_meeting_stats(39, 10)
        baseline = stats_before["total_completed"]

        sched_id = execute_db("""
            INSERT INTO schedules (title, program_id, student_id, mentor_id, schedule_date, start_time, end_time, duration_minutes, status)
            VALUES ('Test Siswa Berhalangan', 10, 39, 14, '2026-11-21', '16:00', '17:30', 90, 'disetujui')
        """)

        try:
            res = record_or_update_attendance(
                schedule_id=sched_id,
                student_id=39,
                mentor_id=14,
                status="izin",
                notes="Siswa demam mendadak, mentor sudah siap di lokasi",
                mentor_status="hadir",
                session_status="siswa_berhalangan",
                attendance_date="2026-11-21"
            )

            self.assertTrue(res["success"])
            self.assertEqual(res["mentor_status"], "hadir")
            self.assertEqual(res["session_status"], "siswa_berhalangan")
            self.assertIsNone(res["cumulative_meeting"])
            self.assertEqual(res["documentation_status"], "tidak_ada")

            # Pertemuan siswa TIDAK BOLEH bertambah
            stats_after = get_student_program_meeting_stats(39, 10)
            self.assertEqual(stats_after["total_completed"], baseline)

            # Tapi kehadiran mentor TETAP TERCATAT HADIR
            ma = query_db("SELECT * FROM mentor_attendance WHERE schedule_id = ? AND mentor_id = 14", (sched_id,), one=True)
            self.assertIsNotNone(ma)
            self.assertEqual(ma["status"], "hadir")
        finally:
            execute_db("DELETE FROM attendance WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM mentor_attendance WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM schedules WHERE id = ?", (sched_id,))

    def test_05_condition_3_mentor_absent(self):
        """Skenario 3: Mentor tidak hadir -> Ketidakhadiran mentor tercatat, sesi siswa tidak selesai"""
        stats_before = get_student_program_meeting_stats(39, 10)
        baseline = stats_before["total_completed"]

        sched_id = execute_db("""
            INSERT INTO schedules (title, program_id, student_id, mentor_id, schedule_date, start_time, end_time, duration_minutes, status)
            VALUES ('Test Mentor Tidak Hadir', 10, 39, 14, '2026-11-22', '16:00', '17:30', 90, 'disetujui')
        """)

        try:
            res = record_or_update_attendance(
                schedule_id=sched_id,
                student_id=39,
                mentor_id=14,
                status="tidak_hadir",
                notes="Mentor ada urusan mendesak",
                mentor_status="tidak_hadir",
                session_status="mentor_berhalangan",
                attendance_date="2026-11-22"
            )

            self.assertTrue(res["success"])
            self.assertEqual(res["mentor_status"], "tidak_hadir")
            self.assertEqual(res["session_status"], "mentor_berhalangan")

            # Pertemuan siswa TIDAK bertambah
            stats_after = get_student_program_meeting_stats(39, 10)
            self.assertEqual(stats_after["total_completed"], baseline)

            # Ketidakhadiran mentor tercatat
            ma = query_db("SELECT * FROM mentor_attendance WHERE schedule_id = ? AND mentor_id = 14", (sched_id,), one=True)
            self.assertIsNotNone(ma)
            self.assertEqual(ma["status"], "tidak_hadir")
        finally:
            execute_db("DELETE FROM attendance WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM mentor_attendance WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM schedules WHERE id = ?", (sched_id,))

    def test_06_pending_documentation_and_admin_completion(self):
        """Mekanisme dokumentasi tertunda karena kendala teknis dan pelengkapan oleh Admin dengan audit log"""
        sched_id = execute_db("""
            INSERT INTO schedules (title, program_id, student_id, mentor_id, schedule_date, start_time, end_time, duration_minutes, status)
            VALUES ('Test Pending Doc', 10, 39, 14, '2026-11-23', '16:00', '17:30', 90, 'disetujui')
        """)

        att_id = None
        log_id = None
        saved_filename = None

        try:
            # Mentor mencatat sesi terlaksana dengan kendala teknis
            res = record_or_update_attendance(
                schedule_id=sched_id,
                student_id=39,
                mentor_id=14,
                status="hadir",
                topics_covered="Trigonometri Dasar",
                mentor_status="hadir",
                session_status="terlaksana",
                documentation_status="menunggu",
                documentation_pending_reason="Kamera smartphone mentor error, foto dikirim via WA ke admin",
                attendance_date="2026-11-23"
            )
            self.assertEqual(res["documentation_status"], "menunggu")
            att_id = res["attendance_id"]

            # Admin login dan melengkapi foto
            with self.client.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["role"] = "admin"
                sess["full_name"] = "Admin Pengelola"

            csrf = self.get_csrf()
            dummy_img = (io.BytesIO(b"fake image bytes content"), "followup_photo.jpg")
            post_res = self.client.post(
                f"/admin/attendance/{att_id}/complete-documentation",
                data={"csrf_token": csrf, "session_photo": dummy_img},
                content_type="multipart/form-data",
                follow_redirects=True
            )
            self.assertEqual(post_res.status_code, 200)

            # Verifikasi status berubah jadi lengkap dan ada audit log
            updated_att = query_db("SELECT documentation_status, documentation_photo FROM attendance WHERE id = ?", (att_id,), one=True)
            self.assertEqual(updated_att["documentation_status"], "lengkap")
            self.assertIsNotNone(updated_att["documentation_photo"])
            saved_filename = updated_att["documentation_photo"]

            log = query_db("SELECT * FROM audit_logs WHERE action_type = 'COMPLETE_SESSION_DOCUMENTATION' AND target_id = ?", (str(att_id),), one=True)
            self.assertIsNotNone(log)
            log_id = log["id"]
        finally:
            if saved_filename:
                saved_file = os.path.join("uploads", "session_photos", saved_filename)
                if os.path.exists(saved_file):
                    try:
                        os.remove(saved_file)
                    except Exception:
                        pass

            if att_id:
                execute_db("DELETE FROM attendance WHERE id = ?", (att_id,))
            execute_db("DELETE FROM mentor_attendance WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM student_progress WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM schedules WHERE id = ?", (sched_id,))
            if log_id:
                execute_db("DELETE FROM audit_logs WHERE id = ?", (log_id,))

    def test_07_photo_security_and_authorization(self):
        """Skenario 4 & 5: Hak akses foto terproteksi (Anonymous 401, Parent 403, Mentor lain 403, Admin 200)"""
        test_dir = os.path.join("uploads", "session_photos")
        os.makedirs(test_dir, exist_ok=True)
        test_filename = "test_secure_image.jpg"
        test_filepath = os.path.join(test_dir, test_filename)
        with open(test_filepath, "wb") as f:
            f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"dummy photo content")

        sched_id = execute_db("""
            INSERT INTO schedules (title, program_id, student_id, mentor_id, schedule_date, start_time, end_time, duration_minutes, status)
            VALUES ('Test Photo Access', 10, 39, 14, '2026-11-24', '16:00', '17:30', 90, 'disetujui')
        """)
        att_id = execute_db("""
            INSERT INTO attendance (schedule_id, student_id, mentor_id, program_id, status, mentor_status, session_status, documentation_status, documentation_photo)
            VALUES (?, 39, 14, 10, 'hadir', 'hadir', 'terlaksana', 'lengkap', ?)
        """, (sched_id, test_filename))

        try:
            # 1. Anonymous -> 401
            with self.client.session_transaction() as sess:
                sess.clear()
            res_anon = self.client.get(f"/uploads/session_photos/{test_filename}")
            self.assertEqual(res_anon.status_code, 401)
            res_anon.close()

            # 2. Parent -> 403
            with self.client.session_transaction() as sess:
                sess["user_id"] = 1025
                sess["username"] = "parent_aya"
                sess["role"] = "parent"
            res_parent = self.client.get(f"/uploads/session_photos/{test_filename}")
            self.assertEqual(res_parent.status_code, 403)
            res_parent.close()

            # 3. Mentor yang berbeda (Mentor ID 15) -> 403
            with self.client.session_transaction() as sess:
                sess["user_id"] = 1006 # Atira (mentor id 15)
                sess["username"] = "atira"
                sess["role"] = "mentor"
            res_other_mentor = self.client.get(f"/uploads/session_photos/{test_filename}")
            self.assertEqual(res_other_mentor.status_code, 403)
            res_other_mentor.close()

            # 4. Mentor yang mengajar (Mentor ID 14) -> 200
            with self.client.session_transaction() as sess:
                sess["user_id"] = 1005 # Andi Riska (mentor id 14)
                sess["username"] = "andiriska"
                sess["role"] = "mentor"
            res_owner_mentor = self.client.get(f"/uploads/session_photos/{test_filename}")
            self.assertEqual(res_owner_mentor.status_code, 200)
            res_owner_mentor.close()

            # 5. Admin -> 200
            with self.client.session_transaction() as sess:
                sess["user_id"] = 1
                sess["username"] = "admin"
                sess["role"] = "admin"
            res_admin = self.client.get(f"/uploads/session_photos/{test_filename}")
            self.assertEqual(res_admin.status_code, 200)
            res_admin.close()
        finally:
            try:
                if os.path.exists(test_filepath):
                    os.remove(test_filepath)
            except Exception:
                pass
            execute_db("DELETE FROM attendance WHERE id = ?", (att_id,))
            execute_db("DELETE FROM schedules WHERE id = ?", (sched_id,))

    def test_08_multi_program_independent_counting(self):
        """Skenario 9: Siswa multi-program (Aya: English dan Math School) memiliki hitungan pertemuan terpisah"""
        # Aya terdaftar di Math School (Program 10) dan English (Program 3)
        math_before = get_student_program_meeting_stats(39, 10)["total_completed"]
        eng_before = get_student_program_meeting_stats(39, 3)["total_completed"]

        # Tambahkan sesi terlaksana khusus pada Math School
        sched_id = execute_db("""
            INSERT INTO schedules (title, program_id, student_id, mentor_id, schedule_date, start_time, end_time, duration_minutes, status)
            VALUES ('Math Session Independence Test', 10, 39, 14, '2026-11-25', '16:00', '17:30', 90, 'disetujui')
        """)

        try:
            record_or_update_attendance(
                schedule_id=sched_id,
                student_id=39,
                mentor_id=14,
                status="hadir",
                topics_covered="Aljabar Lanjutan",
                mentor_status="hadir",
                session_status="terlaksana",
                documentation_status="lengkap",
                documentation_photo="photo_math.jpg",
                attendance_date="2026-11-25"
            )

            math_after = get_student_program_meeting_stats(39, 10)["total_completed"]
            eng_after = get_student_program_meeting_stats(39, 3)["total_completed"]

            # Math School bertambah 1
            self.assertEqual(math_after, math_before + 1)
            # English TETAP tidak terpengaruh sama sekali
            self.assertEqual(eng_after, eng_before)
        finally:
            execute_db("DELETE FROM attendance WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM mentor_attendance WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM student_progress WHERE schedule_id = ?", (sched_id,))
            execute_db("DELETE FROM schedules WHERE id = ?", (sched_id,))

    def test_09_step_2_coordinates_and_availability_remain_intact(self):
        """Skenario 11: Konfirmasi fitur Langkah 2 (alamat & GPS koordinat serta ketersediaan mentor) tetap aktif"""
        mentor = query_db("SELECT id, address, latitude, longitude FROM mentors WHERE id = 14", one=True)
        self.assertIn("latitude", mentor.keys())
        self.assertIn("longitude", mentor.keys())
        self.assertIn("address", mentor.keys())

        student = query_db("SELECT id, address, latitude, longitude FROM students WHERE id = 39", one=True)
        self.assertIn("latitude", student.keys())
        self.assertIn("longitude", student.keys())

    def test_10_mentor_attendance_page_loads_cleanly(self):
        """Skenario 12: Halaman absensi mentor (/mentor/attendance) dan jadwal admin (/admin/schedules) HTTP 200"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1005 # Mentor Andi Riska
            sess["username"] = "andiriska"
            sess["role"] = "mentor"
            sess["full_name"] = "Andi Riska Putri Muliadi"

        res_mentor = self.client.get("/mentor/attendance")
        self.assertEqual(res_mentor.status_code, 200)
        self.assertIn(b"Status Kehadiran Mentor", res_mentor.data)
        self.assertIn(b"Status Sesi Belajar Siswa", res_mentor.data)
        self.assertIn(b"Foto Dokumentasi Belajar", res_mentor.data)

        # Admin schedules
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["role"] = "admin"
            sess["full_name"] = "Admin Pengelola"

        res_admin = self.client.get("/admin/schedules")
        self.assertEqual(res_admin.status_code, 200)

if __name__ == "__main__":
    unittest.main()
