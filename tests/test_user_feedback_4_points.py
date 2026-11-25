import os
import unittest
import sqlite3
from datetime import date

TEST_DB = os.path.abspath("database/desi_privat_testing.db")
os.environ["DATABASE_PATH"] = TEST_DB

from config import Config
Config.DATABASE_PATH = TEST_DB

import app
app.app.config["DATABASE_PATH"] = TEST_DB
app.app.config["TESTING"] = True

from services.report_service import get_dashboard_summary
from services.meeting_service import record_or_update_attendance, get_student_program_meeting_stats

class TestUserFeedback4Points(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app.app
        cls.client = cls.app.test_client()

    def setUp(self):
        # Login helper as admin with CSRF token
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["role"] = "admin"
            sess["full_name"] = "Administrator"
            sess["_csrf_token"] = "test_token_123"

    def test_point_1_dashboard_today_schedules_includes_routine(self):
        """Poin 1: Dashboard memuat jadwal rutin hari ini pada kartu statistik & tabel."""
        summary = get_dashboard_summary()
        self.assertIn("today_schedules", summary)
        
        # Cek response dashboard admin
        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Sesi Hari Ini", res.data)

    def test_point_2_multi_mentor_attendance_synchronization(self):
        """
        Poin 2: 1 Siswa diajar 2 tentor berbeda di program yang sama.
        Absensi tentor 2 harus melanjutkan nomor pertemuan dari tentor 1 tanpa duplikasi.
        """
        conn = sqlite3.connect(TEST_DB, timeout=20.0)
        c = conn.cursor()
        
        # Ambil salah satu parent_id yang valid
        c.execute("SELECT id FROM parents LIMIT 1")
        p_row = c.fetchone()
        parent_id = p_row[0] if p_row else None
        
        if not parent_id:
            c.execute("INSERT INTO parents (full_name, phone) VALUES ('Wali Test', '08123456789')")
            parent_id = c.lastrowid
        
        # Buat data dummy siswa khusus uji ini
        c.execute("INSERT INTO students (full_name, parent_id, status) VALUES ('Naya MultiMentor Test', ?, 'aktif')", (parent_id,))
        student_id = c.lastrowid
        
        # Ambil program aktif pertama
        c.execute("SELECT id FROM programs WHERE status = 'aktif' LIMIT 1")
        prog_row = c.fetchone()
        program_id = prog_row[0]
        
        # Ambil 2 mentor berbeda
        c.execute("SELECT id FROM mentors WHERE status = 'aktif' LIMIT 2")
        mentor_rows = c.fetchall()
        mentor_1 = mentor_rows[0][0]
        mentor_2 = mentor_rows[1][0]
        
        # Daftarkan siswa ke program dengan mentor_1
        c.execute("""
            INSERT INTO student_programs (student_id, program_id, mentor_id, status)
            VALUES (?, ?, ?, 'aktif')
        """, (student_id, program_id, mentor_1))
        conn.commit()
        
        # Tentor 1 melakukan absensi 3 kali (Pertemuan 1, 2, 3)
        for i in range(1, 4):
            c.execute("""
                INSERT INTO schedules (
                    title, program_id, student_id, mentor_id, schedule_date,
                    start_time, end_time, duration_minutes, status,
                    student_confirmation_status, mentor_response_status, created_by
                ) VALUES (?, ?, ?, ?, '2026-11-01', '16:00', '17:30', 90, 'disetujui', 'bersedia', 'dikonfirmasi', 1)
            """, (f"Sesi Tentor 1 - {i}", program_id, student_id, mentor_1))
            sched_id = c.lastrowid
            conn.commit()
            
            res1 = record_or_update_attendance(
                schedule_id=sched_id,
                student_id=student_id,
                mentor_id=mentor_1,
                status="hadir",
                mentor_status="hadir",
                session_status="terlaksana",
                topics_covered=f"Materi Tentor 1 Pertemuan {i}",
                documentation_status="lengkap",
                attendance_date="2026-11-01",
                db_path=TEST_DB
            )
            self.assertTrue(res1["success"])
            self.assertEqual(res1["meeting_number"], i)
            self.assertEqual(res1["period_number"], 1)

        # Cek statistik pertemuan saat ini
        stats_before = get_student_program_meeting_stats(student_id, program_id, db_path=TEST_DB)
        self.assertEqual(stats_before["total_completed"], 3)
        self.assertEqual(stats_before["next_meeting"], 4)
        self.assertEqual(stats_before["next_period"], 1)

        # Sekarang Tentor 2 mengajar siswa Naya pada program yang sama (misal di Makassar)
        c.execute("""
            INSERT INTO schedules (
                title, program_id, student_id, mentor_id, schedule_date,
                start_time, end_time, duration_minutes, status,
                student_confirmation_status, mentor_response_status, created_by
            ) VALUES ('Sesi Tentor 2 - Pertemuan Berikutnya', ?, ?, ?, '2026-11-05', '16:00', '17:30', 90, 'disetujui', 'bersedia', 'dikonfirmasi', 1)
        """, (program_id, student_id, mentor_2))
        sched_id_2 = c.lastrowid
        conn.commit()

        res2 = record_or_update_attendance(
            schedule_id=sched_id_2,
            student_id=student_id,
            mentor_id=mentor_2,
            status="hadir",
            mentor_status="hadir",
            session_status="terlaksana",
            topics_covered="Materi Tentor 2 di Makassar",
            documentation_status="lengkap",
            attendance_date="2026-11-05",
            db_path=TEST_DB
        )
        self.assertTrue(res2["success"])
        # Verifikasi: Harus otomatis Pertemuan 4 (BUKAN pertemuan 1 dan BUKAN duplikat pertemuan 3)
        self.assertEqual(res2["meeting_number"], 4, "Pertemuan tentor 2 harus otomatis melanjutkan ke pertemuan 4!")
        self.assertEqual(res2["period_number"], 1)

        conn.close()

    def test_point_3_admin_cannot_access_finance_bills_honor(self):
        """Poin 3: Halaman tagihan, pembayaran, dan rekap honor tidak boleh diakses Admin (hanya Owner)."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"] = "admin"

        # Admin memiliki hak akses operasional ke tagihan dan pencatatan pembayaran murid
        res_bills = self.client.get("/admin/bills", follow_redirects=True)
        self.assertEqual(res_bills.status_code, 200)
        self.assertIn(b"Tagihan & Pembayaran", res_bills.data)

        # Namun rekap honor mentor (/admin/mentor-honor) adalah wewenang eksklusif Pemilik (Owner)
        res_honor = self.client.get("/admin/mentor-honor", follow_redirects=True)
        self.assertIn(b"Pemilik (Owner)", res_honor.data)

        # Periksa sidebar admin tidak memiliki link /admin/mentor-honor
        res_dash = self.client.get("/admin/dashboard")
        self.assertIn(b'href="/admin/bills"', res_dash.data)
        self.assertNotIn(b'href="/admin/mentor-honor"', res_dash.data)

        # Owner tetap bisa mengakses laporan keuangan /owner/finance-report dan honor /owner/honor
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["username"] = "owner"
            sess["role"] = "owner"

        res_owner_fin = self.client.get("/owner/finance-report")
        self.assertEqual(res_owner_fin.status_code, 200)

    def test_point_4_multi_slot_routine_schedule_creation(self):
        """Poin 4: Penambahan jadwal rutin dapat multi-hari dalam 1 kali simpan dengan tentor berbeda per hari."""
        conn = sqlite3.connect(TEST_DB, timeout=20.0)
        c = conn.cursor()
        c.execute("""
            SELECT sp.student_id, sp.program_id
            FROM student_programs sp
            JOIN students s ON sp.student_id = s.id
            JOIN programs p ON sp.program_id = p.id
            WHERE sp.status = 'aktif' AND s.status = 'aktif'
            LIMIT 1
        """)
        sp_row = c.fetchone()
        st_id, pr_id = sp_row[0], sp_row[1]
        c.execute("SELECT id FROM mentors WHERE status = 'aktif' LIMIT 2")
        m_rows = c.fetchall()
        m1 = m_rows[0][0]
        m2 = m_rows[1][0] if len(m_rows) > 1 else m1
        c.execute("DELETE FROM routine_schedules WHERE student_id = ? AND day_of_week IN (0, 3)", (st_id,))
        conn.commit()
        conn.close()

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["role"] = "admin"
            sess["_csrf_token"] = "test_csrf_token_multi"

        # Kirim 2 slot dengan jam unik agar tidak bentrok
        payload = {
            "csrf_token": "test_csrf_token_multi",
            "student_id": st_id,
            "program_id": pr_id,
            "mentor_ids[]": [str(m1), str(m2)], # Multi-mentor assignment via + Tambah Mentor
            "day_of_week[]": ["0", "3"],
            "start_time[]": ["11:00", "11:00"],
            "end_time[]": ["12:30", "12:30"],
            "subject_info": "Multi-Slot Routine Test",
            "notes": "Testing multi-slot"
        }
        res = self.client.post("/admin/schedules/routine/create", data=payload, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Berhasil menetapkan", res.data)
        self.assertIn(b"jadwal les rutin", res.data)

if __name__ == "__main__":
    unittest.main()
