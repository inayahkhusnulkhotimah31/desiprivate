"""
DESI PRIVAT - Test Suite: Multi-Program Siswa, Riwayat Periode Independen & Developer Monitoring
Memverifikasi kepatuhan sistem terhadap seluruh spesifikasi:
- BAGIAN 2: Multi-Program Siswa, Periode Independen per Program, Penyesuaian Siswa Lama
- BAGIAN 3: Developer Monitoring Real-Time, Field-Level Diffs, Audit Trail
- BAGIAN 4: Pengujian & Integritas Data (Zero Data Loss)
"""
import os
import unittest
import json
from pathlib import Path

# Set environment ke testing
os.environ["FLASK_ENV"] = "testing"

from app import create_app
from config import TestingConfig
from services.database_service import get_direct_connection, init_db, query_db, execute_db
from services.meeting_service import (
    calculate_period_and_meeting, calculate_total_from_period_and_meeting,
    get_student_program_meeting_stats, get_student_meeting_stats,
    set_student_program_initial_history, record_or_update_attendance,
    format_meeting_label
)
from services.audit_service import (
    log_audit, get_audit_logs, get_student_change_logs, compute_field_diff
)

class TestMultiProgramAndDeveloperMonitoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = TestingConfig.DATABASE_PATH
        # Pastikan direktori database ada
        os.makedirs(os.path.dirname(cls.db_path), exist_ok=True)
        # Inisialisasi skema lengkap
        init_db(cls.db_path)
        cls.app = create_app(TestingConfig)
        cls.client = cls.app.test_client()

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    # ========================================================
    # 1. PERHITUNGAN SIKLUS PERIODE & FORMAT LABEL PERTEMUAN
    # ========================================================
    def test_01_period_and_bracket_formatting(self):
        """Memverifikasi aturan 1 periode = 8 pertemuan dan format label [bracket]."""
        # Pertemuan 1 s.d 8 = Periode 1 (format: Pertemuan X)
        p1, m1, _ = calculate_period_and_meeting(1)
        self.assertEqual((p1, m1), (1, 1))
        self.assertEqual(format_meeting_label(p1, m1, "bracket"), "Pertemuan 1")

        p8, m8, _ = calculate_period_and_meeting(8)
        self.assertEqual((p8, m8), (1, 8))
        self.assertEqual(format_meeting_label(p8, m8, "bracket"), "Pertemuan 8")

        # Pertemuan 9 = Periode 2, Pertemuan 1 (format: Pertemuan 1 [2])
        p9, m9, _ = calculate_period_and_meeting(9)
        self.assertEqual((p9, m9), (2, 1))
        self.assertEqual(format_meeting_label(p9, m9, "bracket"), "Pertemuan 1 [2]")

        # Pertemuan 16 = Periode 2, Pertemuan 8 (format: Pertemuan 8 [2])
        p16, m16, _ = calculate_period_and_meeting(16)
        self.assertEqual((p16, m16), (2, 8))
        self.assertEqual(format_meeting_label(p16, m16, "bracket"), "Pertemuan 8 [2]")

        # Pertemuan 17 = Periode 3, Pertemuan 1 (format: Pertemuan 1 [3])
        p17, m17, _ = calculate_period_and_meeting(17)
        self.assertEqual((p17, m17), (3, 1))
        self.assertEqual(format_meeting_label(p17, m17, "bracket"), "Pertemuan 1 [3]")

        # Periode 3 Pertemuan 5 = Total 21 -> Pertemuan 6 [3] berikutnya (kumulatif 22)
        total_offset = calculate_total_from_period_and_meeting(3, 5)
        self.assertEqual(total_offset, 21)
        p_next, m_next, _ = calculate_period_and_meeting(total_offset + 1)
        self.assertEqual((p_next, m_next), (3, 6))
        self.assertEqual(format_meeting_label(p_next, m_next, "bracket"), "Pertemuan 6 [3]")

    # ========================================================
    # 2. MULTI-PROGRAM SISWA DENGAN PERIODE INDEPENDEN
    # ========================================================
    def test_02_student_multi_program_independent_periods(self):
        """Memverifikasi satu siswa dapat memiliki banyak program dengan periode independen."""
        # 1. Buat data orang tua & siswa uji
        p_id = execute_db(
            "INSERT INTO parents (full_name, phone, address) VALUES (?, ?, ?)",
            ("Wali Andi Multi", "081999888771", "Sleman")
        )
        s_id = execute_db(
            "INSERT INTO students (parent_id, full_name, school, grade, status) VALUES (?, ?, ?, ?, 'aktif')",
            (p_id, "Andi Multi Program", "SD Bintang", "Kelas 5")
        )

        # 2. Pastikan ada 2 program les (misal: Program 1: Math School, Program 2: English)
        prog1 = query_db("SELECT id FROM programs WHERE status = 'aktif' ORDER BY id ASC LIMIT 1", one=True)
        prog2 = query_db("SELECT id FROM programs WHERE status = 'aktif' ORDER BY id DESC LIMIT 1", one=True)
        self.assertIsNotNone(prog1)
        self.assertIsNotNone(prog2)
        prog1_id = prog1["id"]
        prog2_id = prog2["id"]

        # Pastikan ada mentor uji
        mentor = query_db("SELECT id FROM mentors WHERE status = 'aktif' LIMIT 1", one=True)
        mentor_id = mentor["id"] if mentor else None

        # 3. Daftarkan Program 1 (Math) dengan riwayat awal: Periode 3, Pertemuan 5 (Offset: 21)
        res_p1 = set_student_program_initial_history(
            student_id=s_id,
            program_id=prog1_id,
            last_period=3,
            last_meeting=5,
            notes="Siswa lama dari bimbel offline",
            admin_user_id=1
        )
        self.assertTrue(res_p1["success"])
        self.assertEqual(res_p1["total_offset"], 21)
        self.assertEqual(res_p1["stats"]["next_meeting_bracket"], "Pertemuan 6 [3]")

        # 4. Daftarkan Program 2 (English) dengan riwayat awal: Periode 2, Pertemuan 8 (Offset: 16)
        res_p2 = set_student_program_initial_history(
            student_id=s_id,
            program_id=prog2_id,
            last_period=2,
            last_meeting=8,
            notes="Sudah tuntas periode 2 di cabang lain",
            admin_user_id=1
        )
        self.assertTrue(res_p2["success"])
        self.assertEqual(res_p2["total_offset"], 16)
        # Sesi berikutnya harus masuk ke Periode 3 Pertemuan 1 [3]!
        self.assertEqual(res_p2["stats"]["next_meeting_bracket"], "Pertemuan 1 [3]")

        # 5. Verifikasi independensi: Ambil statistik masing-masing program
        stat1 = get_student_program_meeting_stats(s_id, prog1_id)
        stat2 = get_student_program_meeting_stats(s_id, prog2_id)

        self.assertEqual(stat1["total_completed"], 21)
        self.assertEqual(stat1["last_period"], 3)
        self.assertEqual(stat1["last_meeting"], 5)
        self.assertEqual(stat1["next_meeting_bracket"], "Pertemuan 6 [3]")

        self.assertEqual(stat2["total_completed"], 16)
        self.assertEqual(stat2["last_period"], 2)
        self.assertEqual(stat2["last_meeting"], 8)
        self.assertEqual(stat2["next_meeting_bracket"], "Pertemuan 1 [3]")

        # 6. Verifikasi TIDAK ADA absensi fiktif yang terbuat di tabel attendance
        att_rows = query_db("SELECT COUNT(*) as c FROM attendance WHERE student_id = ?", (s_id,), one=True)
        self.assertEqual(att_rows["c"], 0)

        # 7. Tambahkan 1 jadwal dan absensi 'hadir' KHUSUS untuk Program 1
        sch_id = execute_db(
            """
            INSERT INTO schedules (
                title, program_id, student_id, mentor_id, schedule_date,
                start_time, end_time, duration_minutes, status
            ) VALUES (?, ?, ?, ?, '2026-11-10', '16:00', '17:30', 90, 'disetujui')
            """,
            ("Sesi Math", prog1_id, s_id, mentor_id)
        )

        att_res = record_or_update_attendance(
            schedule_id=sch_id,
            student_id=s_id,
            mentor_id=mentor_id,
            status="hadir",
            topics_covered="Persamaan Linear Dua Variabel"
        )
        self.assertTrue(att_res["success"])
        # Nomor pertemuan harus Pertemuan 6 [3] (kumulatif 22)
        self.assertEqual(att_res["period_number"], 3)
        self.assertEqual(att_res["meeting_number"], 6)
        self.assertEqual(att_res["cumulative_meeting"], 22)
        self.assertEqual(att_res["meeting_label_bracket"], "Pertemuan 6 [3]")

        # 8. Verifikasi bahwa Program 2 TETAP independen dan TIDAK terpengaruh absensi Program 1
        stat2_after = get_student_program_meeting_stats(s_id, prog2_id)
        self.assertEqual(stat2_after["total_completed"], 16)
        self.assertEqual(stat2_after["next_meeting_bracket"], "Pertemuan 1 [3]")

    # ========================================================
    # 3. DETEKSI DUPLIKASI SISWA
    # ========================================================
    def test_03_check_duplicate_student_api(self):
        """Memverifikasi endpoint pencegahan duplikasi siswa saat pendaftaran."""
        # Siswa "Andi Multi Program" sudah terdaftar di test_02
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["role"] = "admin"

        # Cek nama yang mirip "Andi"
        resp = self.client.get("/admin/api/check-duplicate-student?name=Andi")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("matches", data)
        self.assertTrue(len(data["matches"]) > 0)
        found = any("Andi" in m["full_name"] for m in data["matches"])
        self.assertTrue(found)

        # Cek nama yang tidak ada
        resp_none = self.client.get("/admin/api/check-duplicate-student?name=ZzzzXyyy999")
        data_none = resp_none.get_json()
        self.assertEqual(len(data_none["matches"]), 0)

    # ========================================================
    # 4. FIELD-LEVEL DIFFS PADA AUDIT LOG
    # ========================================================
    def test_04_field_level_diffs_and_audit(self):
        """Memverifikasi pencatatan field-level diffs (old vs new values) saat update data siswa."""
        old_data = {"school": "SD N 1", "grade": "Kelas 4", "address": "Jalan Kaliurang"}
        new_data = {"school": "Al-Madiinah Islamic School", "grade": "Kelas 5", "address": "Jalan Kaliurang"}

        changed_fields, old_diff, new_diff = compute_field_diff(old_data, new_data)
        self.assertIn("school", changed_fields)
        self.assertIn("grade", changed_fields)
        self.assertNotIn("address", changed_fields) # Nilai sama

        self.assertEqual(old_diff["school"], "SD N 1")
        self.assertEqual(new_diff["school"], "Al-Madiinah Islamic School")
        self.assertEqual(old_diff["grade"], "Kelas 4")
        self.assertEqual(new_diff["grade"], "Kelas 5")

        # Catat via log_audit
        log_id = log_audit(
            user_id=1,
            user_name="admin",
            action_type="UBAH_SISWA",
            target_entity="students",
            target_id=38,
            details="Mengubah data sekolah dan kelas",
            module_name="Siswa",
            old_values=old_diff,
            new_values=new_diff,
            fields_changed=changed_fields
        )
        self.assertIsNotNone(log_id)

        # Ambil kembali dari student change logs
        diffs = get_student_change_logs(student_id=38, limit=5)
        self.assertTrue(len(diffs) > 0)
        first_diff = dict(diffs[0])
        self.assertIn("school", first_diff["fields_changed"])

    # ========================================================
    # 5. AUTENTIKASI & KEAMANAN DEVELOPER DASHBOARD
    # ========================================================
    def test_05_developer_auth_and_dashboard_protection(self):
        """Memverifikasi proteksi ketat route developer."""
        # 1. Akses tanpa sesi developer -> Harus diredirect ke /developer/login
        resp_unauth = self.client.get("/developer/dashboard")
        self.assertEqual(resp_unauth.status_code, 302)
        self.assertIn("/developer/login", resp_unauth.location)

        # 2. Akses API monitoring tanpa sesi developer -> 403 Forbidden
        resp_api_unauth = self.client.get("/developer/api/system-health")
        self.assertEqual(resp_api_unauth.status_code, 403)

        # 3. Login dengan kredensial developer yang benar
        resp_login = self.client.post("/developer/login", data={
            "username": "developer",
            "password": "DesiPrivat@Dev2026!"
        }, follow_redirects=False)
        self.assertEqual(resp_login.status_code, 302)
        self.assertIn("/developer/dashboard", resp_login.location)

        # 4. Akses dashboard & API setelah login -> Sukses 200
        with self.client.session_transaction() as sess:
            sess["is_developer"] = True
            sess["developer_username"] = "developer"

        resp_dash = self.client.get("/developer/dashboard")
        self.assertEqual(resp_dash.status_code, 200)
        self.assertIn(b"Developer Monitoring", resp_dash.data)

        resp_health = self.client.get("/developer/api/system-health")
        self.assertEqual(resp_health.status_code, 200)
        health_data = resp_health.get_json()
        self.assertTrue(health_data["database_ok"])
        self.assertEqual(health_data["integrity"], "ok")

        # 5. Export aktivitas CSV & JSON
        resp_csv = self.client.get("/developer/export?format=csv")
        self.assertEqual(resp_csv.status_code, 200)
        self.assertIn(b"ID,Waktu,User / Admin", resp_csv.data)

        resp_json = self.client.get("/developer/export?format=json")
        self.assertEqual(resp_json.status_code, 200)

        # 6. Logout developer
        resp_logout = self.client.get("/developer/logout")
        self.assertEqual(resp_logout.status_code, 302)

    # ========================================================
    # 6. INTEGRITAS DATABASE (ZERO DATA LOSS)
    # ========================================================
    def test_06_database_integrity_check(self):
        """Memverifikasi tidak ada korupsi atau anomali pada database."""
        conn = get_direct_connection(self.db_path)
        cur = conn.cursor()
        integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
        self.assertEqual(integrity, "ok")
        conn.close()

if __name__ == "__main__":
    unittest.main()

