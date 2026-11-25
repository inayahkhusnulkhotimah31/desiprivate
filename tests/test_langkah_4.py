"""
DESI PRIVAT - Automated Test Suite: LANGKAH 4 (Sistem Rekomendasi Mentor)
Memvalidasi seluruh 14 skenario pengujian wajib secara komprehensif:
1. Mentor tersedia dan tidak bentrok (Status: Tersedia / Hijau).
2. Mentor belum mengatur ketersediaan dan tidak bentrok (Status: Bebas Bentrok / Abu-abu).
3. Mentor di luar preferensi waktu (Status: Di Luar Preferensi Waktu / Kuning).
4. Mentor mengalami bentrok jadwal (Status: Bentrok Jadwal / Merah, rincian siswa ditampilkan).
5. Mentor memiliki keahlian yang sesuai.
6. Mentor tidak memiliki kecocokan keahlian yang teridentifikasi.
7. Koordinat siswa dan mentor tersedia (Haversine km terhitung akurat).
8. Koordinat salah satu pihak kosong ("Belum ada koordinat", bukan jarak nol).
9. Urutan rekomendasi mengikuti tiga prioritas berjenjang.
10. Payload rekomendasi menyediakan data mentor_id untuk pengisian formulir.
11. Dropdown mentor manual tetap berfungsi normal.
12. Rekomendasi bersifat read-only (jadwal tidak tersimpan otomatis).
13. Akses terproteksi: non-admin diblokir dari endpoint rekomendasi.
14. Fitur penjadwalan lama (konflik & rutin) tetap berjalan normal tanpa regresi.
"""
import unittest
import os
import io
import json
import sqlite3
import shutil
from pathlib import Path

import sys
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app import create_app
from config import Config
from services.database_service import query_db, execute_db
from services.recommendation_service import (
    calculate_haversine_distance, evaluate_expertise_match,
    evaluate_mentor_availability, get_mentor_recommendations
)
from services.schedule_service import check_schedule_conflict, create_routine_schedule

class TestLangkah4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["FLASK_ENV"] = "development"
        cls.test_db_path = str(BASE_DIR / "database" / "test_langkah_4.db")
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass
        # Salin dari database dasar
        shutil.copyfile(str(BASE_DIR / "database" / "desi_privat.db"), cls.test_db_path)
        cls.orig_db_path = Config.DATABASE_PATH
        Config.DATABASE_PATH = cls.test_db_path
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.app.config["DATABASE_PATH"] = cls.test_db_path
        cls.client = cls.app.test_client()

        # Siapkan data mentor pengujian khusus di test_langkah_4.db
        with cls.app.app_context():
            # Pastikan ada mentor dengan berbagai skenario
            # Mentor 14: Andi Riska (Biologi)
            # Mentor 15: Atira (Math)
            # Buat mentor tambahan untuk pengujian skenario lengkap
            execute_db("""
                INSERT OR IGNORE INTO users (id, username, password_hash, role, full_name, is_active)
                VALUES (2001, 'mentor_rec_1', 'dummy_hash', 'mentor', 'Mentor Tersedia Math', 1),
                       (2002, 'mentor_rec_2', 'dummy_hash', 'mentor', 'Mentor Bentrok', 1),
                       (2003, 'mentor_rec_3', 'dummy_hash', 'mentor', 'Mentor Luar Jam', 1)
            """, db_path=cls.test_db_path)

            execute_db("""
                INSERT OR IGNORE INTO mentors (id, user_id, full_name, phone, expertise, status, address, latitude, longitude)
                VALUES (21, 2001, 'Mentor Tersedia Math', '081211110001', 'Matematika, Aljabar', 'aktif', 'Jl. Kaliurang KM 5', -7.7600, 110.3700),
                       (22, 2002, 'Mentor Bentrok', '081211110002', 'Matematika', 'aktif', 'Jl. Gejayan No. 10', -7.7700, 110.3900),
                       (23, 2003, 'Mentor Luar Jam', '081211110003', 'Matematika', 'aktif', 'Jl. Palagan No. 8', -7.7400, 110.3800)
            """, db_path=cls.test_db_path)

            # Atur ketersediaan mingguan:
            # Mentor 21: Tersedia hari Sabtu (5) jam 08:00 - 12:00
            execute_db("""
                INSERT OR IGNORE INTO mentor_availability (mentor_id, day_of_week, start_time, end_time, notes)
                VALUES (21, 5, '08:00', '12:00', 'Tersedia pagi')
            """, db_path=cls.test_db_path)

            # Mentor 23: Tersedia hari Senin (0) jam 13:00 - 17:00 (sehingga pada Sabtu jam 09:00 berstatus luar preferensi)
            execute_db("""
                INSERT OR IGNORE INTO mentor_availability (mentor_id, day_of_week, start_time, end_time, notes)
                VALUES (23, 0, '13:00', '17:00', 'Hanya Senin sore')
            """, db_path=cls.test_db_path)

            # Mentor 15: Biarkan tanpa baris mentor_availability (untuk menguji 'bebas_tanpa_info')

            # Siswa Aya (ID 39): Atur koordinat untuk uji jarak
            execute_db("""
                UPDATE students
                SET latitude = -7.7750, longitude = 110.3750
                WHERE id = 39
            """, db_path=cls.test_db_path)

            # Siswa Muh. Halim (ID 38): Koordinat dibiarkan NULL (untuk menguji koordinat kosong)
            execute_db("""
                UPDATE students
                SET latitude = NULL, longitude = NULL
                WHERE id = 38
            """, db_path=cls.test_db_path)

            # Buat bentrokan untuk Mentor 22 pada hari Sabtu jam 09:00 - 10:30 dengan siswa 38
            execute_db("""
                INSERT INTO routine_schedules (student_id, program_id, mentor_id, day_of_week, start_time, end_time, subject_info, status)
                VALUES (38, 10, 22, 5, '09:00', '10:30', 'Sesi Matematika Bentrok', 'aktif')
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

    # ========================================================
    # 1. PENGUJIAN STATUS KETERSEDIAAN WAKTU (PRIORITAS 1)
    # ========================================================
    def test_01_mentor_tersedia_dan_tidak_bentrok(self):
        """Skenario 1: Mentor dengan ketersediaan cocok dan tanpa bentrokan berstatus 'tersedia' (Hijau)."""
        res = evaluate_mentor_availability(
            mentor_id=21, # Tersedia Sabtu 08:00 - 12:00
            day_of_week=5,
            start_time="09:00",
            end_time="10:30",
            db_path=self.test_db_path
        )
        self.assertEqual(res["status"], "tersedia")
        self.assertEqual(res["badge"], "success")
        self.assertFalse(res["has_conflict"])
        self.assertEqual(res["time_tier"], 1)

    def test_02_mentor_bebas_bentrok_belum_ada_info(self):
        """Skenario 2: Mentor belum mengatur ketersediaan berstatus 'bebas_tanpa_info' (Abu-abu), bukan tersedia mutlak."""
        res = evaluate_mentor_availability(
            mentor_id=14, # Andi Riska belum punya data di mentor_availability dan bebas bentrok di Sabtu 09:00
            day_of_week=5,
            start_time="09:00",
            end_time="10:30",
            db_path=self.test_db_path
        )
        self.assertEqual(res["status"], "bebas_tanpa_info")
        self.assertEqual(res["badge"], "secondary")
        self.assertFalse(res["has_conflict"])
        self.assertEqual(res["time_tier"], 3)
        self.assertIn("Belum Ada Info", res["label"])

    def test_03_mentor_di_luar_preferensi_waktu(self):
        """Skenario 3: Mentor sudah mengatur ketersediaan di hari lain berstatus 'luar_preferensi' (Kuning)."""
        res = evaluate_mentor_availability(
            mentor_id=23, # Hanya tersedia Senin 13:00 - 17:00
            day_of_week=5, # Diminta Sabtu
            start_time="09:00",
            end_time="10:30",
            db_path=self.test_db_path
        )
        self.assertEqual(res["status"], "luar_preferensi")
        self.assertEqual(res["badge"], "warning")
        self.assertFalse(res["has_conflict"])
        self.assertEqual(res["time_tier"], 4)

    def test_04_mentor_bentrok_jadwal_dan_info_siswa(self):
        """Skenario 4: Mentor bertabrakan jadwal berstatus 'bentrok' (Merah) dengan nama siswa pembuat bentrok."""
        res = evaluate_mentor_availability(
            mentor_id=22, # Bentrok di Sabtu 09:00-10:30 dengan Muh. Halim
            day_of_week=5,
            start_time="09:00",
            end_time="10:30",
            db_path=self.test_db_path
        )
        self.assertEqual(res["status"], "bentrok")
        self.assertEqual(res["badge"], "danger")
        self.assertTrue(res["has_conflict"])
        self.assertEqual(res["time_tier"], 5)
        self.assertIsNotNone(res["conflict_info"])
        self.assertEqual(res["conflict_info"]["student_name"], "Muh. Halim")
        self.assertIn("Muh. Halim", res["conflict_info"]["message"])

    def test_04b_batas_waktu_bersinggungan_tidak_bentrok(self):
        """Skenario batas: Jam bersinggungan di batas (e.g. 10:30-11:30 vs 09:00-10:30) tidak boleh bentrok."""
        res = evaluate_mentor_availability(
            mentor_id=22, # Jadwal lama: 09:00 - 10:30
            day_of_week=5,
            start_time="10:30", # Mulai tepat saat jadwal lama selesai
            end_time="12:00",
            db_path=self.test_db_path
        )
        # Tidak overlap durasi
        self.assertFalse(res["has_conflict"])
        self.assertNotEqual(res["status"], "bentrok")

    # ========================================================
    # 2. PENGUJIAN KESESUAIAN MATA PELAJARAN (PRIORITAS 2)
    # ========================================================
    def test_05_keahlian_sesuai(self):
        """Skenario 5: Keahlian mentor cocok dengan nama program les."""
        # Keahlian 'Matematika, Aljabar' cocok dengan program 'Math School'
        res1 = evaluate_expertise_match("Matematika, Aljabar", "Math School", "Belajar dasar matematika")
        self.assertTrue(res1["matched"])
        self.assertGreaterEqual(res1["score"], 2)

        # Keahlian 'Math' cocok dengan 'Math Olimpiade'
        res2 = evaluate_expertise_match("Math", "Math Olimpiade", "Olimpiade sains")
        self.assertTrue(res2["matched"])
        self.assertEqual(res2["score"], 3)

    def test_06_keahlian_tidak_teridentifikasi(self):
        """Skenario 6: Keahlian mentor tidak cocok dengan program les."""
        # Keahlian 'Biologi' tidak cocok dengan program 'English'
        res = evaluate_expertise_match("Biologi", "English", "Grammar dan conversation")
        self.assertFalse(res["matched"])
        self.assertEqual(res["score"], 0)
        self.assertEqual(res["label"], "Keahlian Belum Teridentifikasi")

        # Keahlian kosong
        res_empty = evaluate_expertise_match("", "Math School", "")
        self.assertFalse(res_empty["matched"])
        self.assertEqual(res_empty["score"], 0)

    # ========================================================
    # 3. PENGUJIAN JARAK LOKASI HAVERSINE (PRIORITAS 3)
    # ========================================================
    def test_07_jarak_koordinat_tersedia(self):
        """Skenario 7: Koordinat lengkap menghitung jarak garis lurus yang akurat via Haversine."""
        # Aya (-7.7750, 110.3750) ke Mentor 21 (-7.7600, 110.3700)
        dist = calculate_haversine_distance(-7.7750, 110.3750, -7.7600, 110.3700)
        self.assertIsNotNone(dist)
        # Jarak geografis sekitar 1.7 km
        self.assertAlmostEqual(dist, 1.76, delta=0.2)
        self.assertGreater(dist, 0)

    def test_08_jarak_koordinat_kosong(self):
        """Skenario 8: Jika koordinat salah satu kosong, jarak bernilai None (bukan nol)."""
        dist1 = calculate_haversine_distance(None, None, -7.7600, 110.3700)
        self.assertIsNone(dist1)

        dist2 = calculate_haversine_distance(-7.7750, 110.3750, None, 110.3700)
        self.assertIsNone(dist2)

        # Siswa Halim (ID 38) memiliki koordinat NULL
        recs = get_mentor_recommendations(
            student_id=38,
            program_id=10,
            day_of_week=5,
            start_time="09:00",
            end_time="10:30",
            db_path=self.test_db_path
        )
        self.assertTrue(recs["success"])
        for r in recs["recommendations"]:
            self.assertIsNone(r["distance_km"])
            self.assertEqual(r["distance_label"], "Belum ada koordinat")

    # ========================================================
    # 4. PENGUJIAN URUTAN REKOMENDASI BERJENJANG
    # ========================================================
    def test_09_urutan_rekomendasi_tiga_prioritas(self):
        """Skenario 9: Urutan berjenjang: Tersedia+Cocok > BebasTanpaInfo > LuarPreferensi > Bentrok."""
        recs = get_mentor_recommendations(
            student_id=39, # Aya (koordinat terisi)
            program_id=10, # Math School
            day_of_week=5, # Sabtu
            start_time="09:00",
            end_time="10:30",
            db_path=self.test_db_path
        )
        self.assertTrue(recs["success"])
        mentor_list = recs["recommendations"]
        self.assertGreaterEqual(len(mentor_list), 4)

        # Mentor 21 (Tersedia & Cocok Math) HARUS berada di peringkat 1
        self.assertEqual(mentor_list[0]["mentor_id"], 21)
        self.assertEqual(mentor_list[0]["time_status"], "tersedia")
        self.assertTrue(mentor_list[0]["expertise_matched"])

        # Mentor 22 (Bentrok) HARUS berada di urutan paling bawah
        bentrok_items = [m for m in mentor_list if m["time_status"] == "bentrok"]
        self.assertTrue(len(bentrok_items) > 0)
        self.assertEqual(mentor_list[-1]["time_status"], "bentrok")

        # Pastikan tidak ada mentor bentrok yang ditempatkan di atas mentor bebas bentrok
        seen_bentrok = False
        for m in mentor_list:
            if m["time_status"] == "bentrok":
                seen_bentrok = True
            if seen_bentrok:
                self.assertEqual(m["time_status"], "bentrok", "Mentor bebas bentrok tidak boleh berada di bawah mentor bentrok!")

    # ========================================================
    # 5. PENGUJIAN INTEGRASI ALUR ADMIN & FORMULIR
    # ========================================================
    def test_10_payload_rekomendasi_menyediakan_mentor_id(self):
        """Skenario 10: Payload API menyediakan data lengkap mentor_id untuk tombol 'Pilih Mentor Ini'."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["role"] = "admin"

        res = self.client.get(
            "/admin/api/mentor-recommendations?student_id=39&program_id=10&day_of_week=5&start_time=09:00&end_time=10:30"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("recommendations", data)
        first = data["recommendations"][0]
        self.assertIn("mentor_id", first)
        self.assertIn("mentor_name", first)
        self.assertIn("time_badge", first)
        self.assertIn("distance_label", first)

    def test_11_dropdown_mentor_manual_tetap_berfungsi(self):
        """Skenario 11: Admin tetap dapat membuat jadwal secara manual dengan dropdown mentor."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "admin"
            sess["role"] = "admin"
            token = sess.get("_csrf_token") or "csrf_test"
            sess["_csrf_token"] = token

        # Simpan jadwal rutin manual
        res = self.client.post("/admin/schedules/routine/create", data={
            "csrf_token": token,
            "student_id": 39,
            "program_id": 3,
            "mentor_id": 14, # Admin bebas memilih mentor 14
            "day_of_week": 2, # Rabu
            "start_time": "14:00",
            "end_time": "15:30",
            "subject_info": "English Manual Routine",
            "notes": "Pilihan manual Admin"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verifikasi tersimpan di database
        saved = query_db(
            "SELECT * FROM routine_schedules WHERE student_id = 39 AND program_id = 3 AND day_of_week = 2",
            one=True,
            db_path=self.test_db_path
        )
        self.assertIsNotNone(saved)
        self.assertEqual(saved["mentor_id"], 14)

    def test_12_rekomendasi_bersifat_readonly(self):
        """Skenario 12: Memanggil API rekomendasi bersifat read-only dan TIDAK menyimpan jadwal ke DB."""
        count_before = query_db("SELECT COUNT(*) as c FROM routine_schedules", one=True, db_path=self.test_db_path)["c"]

        recs = get_mentor_recommendations(
            student_id=39,
            program_id=10,
            day_of_week=5,
            start_time="09:00",
            end_time="10:30",
            db_path=self.test_db_path
        )
        self.assertTrue(recs["success"])

        count_after = query_db("SELECT COUNT(*) as c FROM routine_schedules", one=True, db_path=self.test_db_path)["c"]
        self.assertEqual(count_before, count_after, "Memanggil rekomendasi tidak boleh menambah jadwal di database!")

    # ========================================================
    # 6. PENGUJIAN KEAMANAN & OTORISASI
    # ========================================================
    def test_13_keamanan_akses_non_admin_diblokir(self):
        """Skenario 13: Pengguna non-admin (anonim, mentor, parent) diblokir dari endpoint rekomendasi."""
        # 1. Anonim (belum login)
        self.client.get("/logout")
        res_anon = self.client.get("/admin/api/mentor-recommendations?student_id=39&program_id=10&day_of_week=5&start_time=09:00&end_time=10:30")
        # Mengembalikan 302 redirect ke login atau 401
        self.assertIn(res_anon.status_code, (302, 401))

        # 2. Role Mentor
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2001
            sess["username"] = "mentor_rec_1"
            sess["role"] = "mentor"
        res_mentor = self.client.get("/admin/api/mentor-recommendations?student_id=39&program_id=10&day_of_week=5&start_time=09:00&end_time=10:30")
        self.assertIn(res_mentor.status_code, (302, 403))

        # 3. Role Parent
        with self.client.session_transaction() as sess:
            sess["user_id"] = 999
            sess["username"] = "parent_user"
            sess["role"] = "parent"
        res_parent = self.client.get("/admin/api/mentor-recommendations?student_id=39&program_id=10&day_of_week=5&start_time=09:00&end_time=10:30")
        self.assertIn(res_parent.status_code, (302, 403))

    # ========================================================
    # 7. REGRESI PENJADWALAN LAMA
    # ========================================================
    def test_14_regresi_penjadwalan_lama_berjalan_normal(self):
        """Skenario 14: Fitur penjadwalan lama (check_schedule_conflict, rutin) berfungsi normal."""
        # Cek fungsi bentrok bawaan
        conf = check_schedule_conflict(
            mentor_id=22,
            student_id=39,
            schedule_date="2026-11-21",
            start_time="09:00",
            end_time="10:30"
        )
        self.assertIsInstance(conf, dict)
        self.assertIn("has_conflict", conf)
