"""
DESI PRIVAT - Automated Test Suite
Memvalidasi 20 poin pengujian yang diminta secara komprehensif:
1. Login dan logout.
2. Pengalihan dashboard berdasarkan role.
3. Pembatasan akses setiap role.
4. CRUD siswa, wali, mentor, dan program.
5. Hubungan satu wali dengan beberapa anak.
6. Pengusulan dan persetujuan jadwal.
7. Konfirmasi kesediaan siswa atau wali.
8. Jadwal berulang.
9. Deteksi bentrokan jadwal.
10. Peringatan mentor yang belum merespons.
11. Penolakan jadwal dengan alasan.
12. Pergantian mentor dan riwayatnya.
13. Absensi dan perkembangan siswa.
14. Tampilan perkembangan pada dashboard wali.
15. Notifikasi website.
16. Mode pengujian integrasi WhatsApp.
17. Backup dan restore.
18. Arsip data.
19. Ekspor laporan.
20. Penyimpanan data setelah aplikasi ditutup dan dibuka kembali.
"""
import unittest
import os
import sys
import shutil
import sqlite3
from pathlib import Path

# Pastikan direktori root aplikasi ada di sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Fallback path jika dependensi terpasang di Python 3.11
_py311_site = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" / "Python311" / "Lib" / "site-packages"
if _py311_site.exists() and str(_py311_site) not in sys.path:
    sys.path.append(str(_py311_site))

from app import create_app
from config import Config, BASE_DIR
from services.database_service import get_direct_connection, query_db, execute_db, init_db, seed_test_data
from services.schedule_service import (
    check_schedule_conflict, create_schedule_proposal, generate_recurring_schedules,
    approve_schedule, mentor_respond_schedule, check_overdue_mentor_responses,
    execute_mentor_replacement, get_eligible_replacement_mentors,
    check_routine_schedule_conflict, create_routine_schedule,
    update_routine_schedule, delete_routine_schedule, get_routine_schedules
)
from services.notification_service import create_notification, get_user_notifications, get_unread_count, mark_as_read
from services.whatsapp_service import (
    send_whatsapp_message, get_delivery_logs, normalize_phone_number,
    generate_whatsapp_web_link, run_test_scenario
)
from services.meeting_service import (
    calculate_period_and_meeting, calculate_total_from_period_and_meeting,
    get_student_meeting_stats, record_or_update_attendance,
    set_student_initial_history
)
from services.backup_service import create_backup, list_backups, validate_backup_file, restore_backup
from services.report_service import get_dashboard_summary, get_schedules_report, generate_csv_string

class TestDesiPrivat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = str(BASE_DIR / "database" / "test_desi_privat.db")
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass
        cls.orig_db_path = Config.DATABASE_PATH
        Config.DATABASE_PATH = cls.test_db_path
        init_db(cls.test_db_path)
        seed_test_data(cls.test_db_path)
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        Config.DATABASE_PATH = cls.orig_db_path
        if hasattr(cls, "test_db_path") and os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        execute_db("DELETE FROM schedules WHERE title LIKE 'Sesi Pengujian%' OR title LIKE 'Sesi Rutin Bahasa Inggris%' OR title LIKE 'Sesi Les Fisika Khusus%'")
        execute_db("DELETE FROM routine_schedules WHERE notes LIKE '%Uji%'")
        execute_db("DELETE FROM programs WHERE code = 'FIS-MOD' OR name = 'Fisika Modern Intensif'")
        execute_db("DELETE FROM students WHERE full_name = 'Dimas Pratama'")
        execute_db("DELETE FROM parents WHERE full_name = 'Bapak Bambang Soediro'")
        execute_db("UPDATE programs SET status = 'diarsipkan' WHERE id = 5")
        execute_db("UPDATE schedules SET status = 'disetujui' WHERE id = 1")
        execute_db("UPDATE schedules SET status = 'disetujui' WHERE id = 2")
        execute_db("UPDATE schedules SET status = 'menunggu_persetujuan_admin' WHERE id = 3")
        execute_db("UPDATE schedules SET status = 'menunggu_konfirmasi_siswa' WHERE id = 4")
        execute_db("UPDATE schedules SET status = 'disetujui' WHERE id = 5")
        execute_db("UPDATE students SET status = 'berhenti' WHERE id = 4")

    def tearDown(self):
        self.ctx.pop()

    def get_csrf(self, client):
        """Helper untuk mengambil token CSRF dari session test client."""
        with client.session_transaction() as sess:
            return sess.get("_csrf_token") or "dummy_csrf_for_test"

    # 1. Login dan Logout
    def test_01_login_and_logout(self):
        # Login dengan kredensial benar
        res = self.client.get("/login")
        self.assertEqual(res.status_code, 200)

        with self.client.session_transaction() as sess:
            csrf = sess.get("_csrf_token")

        res_login = self.client.post("/login", data={
            "csrf_token": csrf,
            "username": "admin",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b"Admin Pengelola", res_login.data)

        # Logout
        res_logout = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(res_logout.status_code, 200)
        self.assertIn(b"Masuk ke Sistem", res_logout.data)

        # Login dengan kredensial salah
        with self.client.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_fail = self.client.post("/login", data={
            "csrf_token": csrf,
            "username": "admin",
            "password": "wrong_password"
        }, follow_redirects=True)
        self.assertIn(b"ID Pengguna atau password salah", res_fail.data)

    # 2. Pengalihan dashboard berdasarkan role & penolakan login parent (Section E)
    def test_02_role_redirection(self):
        # Role aktif: admin, owner, mentor
        roles_creds = [
            ("admin", "admin123", "/admin/dashboard"),
            ("owner", "owner123", "/owner/dashboard"),
            ("mentor1", "mentor123", "/mentor/dashboard")
        ]
        for username, password, expected_url in roles_creds:
            c = self.app.test_client()
            c.get("/login")
            with c.session_transaction() as sess:
                csrf = sess.get("_csrf_token")
            res = c.post("/login", data={"csrf_token": csrf, "username": username, "password": password})
            self.assertEqual(res.status_code, 302)
            self.assertTrue(res.headers["Location"].endswith(expected_url))

        # Pengujian penolakan login parent (Section E)
        c_parent = self.app.test_client()
        c_parent.get("/login")
        with c_parent.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_parent = c_parent.post("/login", data={"csrf_token": csrf, "username": "parent1", "password": "parent123"}, follow_redirects=True)
        self.assertEqual(res_parent.status_code, 200)
        self.assertTrue(b"ID Pengguna atau password salah" in res_parent.data or b"Akses login untuk akun Orang Tua/Wali tidak lagi aktif" in res_parent.data)

    # 3. Pembatasan akses setiap role
    def test_03_role_authorization_restrictions(self):
        # Login sebagai Mentor
        c_mentor = self.app.test_client()
        c_mentor.get("/login")
        with c_mentor.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        c_mentor.post("/login", data={"csrf_token": csrf, "username": "mentor1", "password": "mentor123"})

        # Mentor coba akses rute admin -> Harus 403 Forbidden
        res_admin = c_mentor.get("/admin/dashboard")
        self.assertEqual(res_admin.status_code, 403)

        # Mentor coba akses rute wali -> Harus 403 atau 404 (modul parent telah dihapus)
        res_parent = c_mentor.get("/parent/dashboard")
        self.assertIn(res_parent.status_code, (403, 404))

        # Login sebagai Pemilik (Owner)
        c_owner = self.app.test_client()
        c_owner.get("/login")
        with c_owner.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        c_owner.post("/login", data={"csrf_token": csrf, "username": "owner", "password": "owner123"})

        # Pemilik coba POST (modifikasi data) di rute owner -> Harus 403 Forbidden (Read-only enforcement)
        res_post_owner = c_owner.post("/owner/dashboard", data={"test": "1"})
        self.assertEqual(res_post_owner.status_code, 403)

    # 4. CRUD siswa, wali, mentor, dan program
    def test_04_crud_operations(self):
        c_admin = self.app.test_client()
        c_admin.get("/login")
        with c_admin.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        c_admin.post("/login", data={"csrf_token": csrf, "username": "admin", "password": "admin123"})

        # Tambah Program Les
        with c_admin.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_prog = c_admin.post("/admin/programs/create", data={
            "csrf_token": csrf,
            "name": "Fisika Modern Intensif",
            "code": "FIS-MOD",
            "description": "Pembahasan konsep fisika tingkat lanjut",
            "level": "SMA Kelas 12"
        }, follow_redirects=True)
        self.assertIn(b"Fisika Modern Intensif", res_prog.data)

        # Tambah Wali
        with c_admin.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_parent = c_admin.post("/admin/parents/create", data={
            "csrf_token": csrf,
            "full_name": "Bapak Bambang Soediro",
            "phone": "081299990001",
            "email": "bambang@gmail.com",
            "address": "Jl. Kaliurang KM 7"
        }, follow_redirects=True)
        self.assertIn(b"Bapak Bambang Soediro", res_parent.data)

        # Ambil ID Wali yang baru
        p_row = query_db("SELECT id FROM parents WHERE full_name = 'Bapak Bambang Soediro'", one=True)
        self.assertIsNotNone(p_row)

        # Tambah Siswa
        with c_admin.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_student = c_admin.post("/admin/students/create", data={
            "csrf_token": csrf,
            "parent_id": p_row["id"],
            "full_name": "Dimas Pratama",
            "school": "SMA Negeri 1 Yogyakarta",
            "grade": "Kelas 10",
            "address": "Jl. Kaliurang KM 7"
        }, follow_redirects=True)
        self.assertIn(b"Dimas Pratama", res_student.data)

    # 5. Hubungan satu wali dengan beberapa anak
    def test_05_one_parent_multiple_children(self):
        # Ibu Ratna Kumalasari (id=1) harus memiliki setidaknya 2 anak: Naufal Pratama dan Alisha Putri
        children = query_db("SELECT full_name FROM students WHERE parent_id = 1")
        child_names = [c["full_name"] for c in children]
        self.assertIn("Naufal Pratama", child_names)
        self.assertIn("Alisha Putri", child_names)
        self.assertGreaterEqual(len(child_names), 2)

    # 6. Pengusulan dan persetujuan jadwal
    def test_06_schedule_proposal_and_approval(self):
        # Usulkan jadwal baru
        res = create_schedule_proposal(
            title="Sesi Pengujian Les Aljabar",
            program_id=1,
            student_id=1,
            mentor_id=1,
            schedule_date="2026-11-05",
            start_time="09:00",
            duration_minutes=90,
            session_notes="Uji coba sesi baru",
            created_by_user_id=3 # Mentor Sarah
        )
        self.assertTrue(res["success"])
        sched_id = res["schedule_id"]

        # Cek status usulan: menunggu_persetujuan_admin
        sched = query_db("SELECT status FROM schedules WHERE id = ?", (sched_id,), one=True)
        self.assertEqual(sched["status"], "menunggu_persetujuan_admin")

        # Admin menyetujui jadwal
        res_app = approve_schedule(sched_id, admin_user_id=1)
        self.assertTrue(res_app["success"])

        sched_after = query_db("SELECT status, approved_by FROM schedules WHERE id = ?", (sched_id,), one=True)
        self.assertEqual(sched_after["status"], "disetujui")
        self.assertEqual(sched_after["approved_by"], 1)

    # 7. Konfirmasi kesediaan siswa atau wali
    def test_07_student_confirmation(self):
        c_admin = self.app.test_client()
        c_admin.get("/login")
        with c_admin.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        c_admin.post("/login", data={"csrf_token": csrf, "username": "admin", "password": "admin123"})

        # Update konfirmasi siswa untuk jadwal id=4 (yang awalnya menunggu_konfirmasi_siswa)
        with c_admin.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res = c_admin.post("/admin/schedules/4/student-confirmation", data={
            "csrf_token": csrf,
            "confirmation_status": "bersedia",
            "notes": "Orang tua menyatakan bersedia melalui telepon."
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        sched = query_db("SELECT student_confirmation_status, status FROM schedules WHERE id = 4", one=True)
        self.assertEqual(sched["student_confirmation_status"], "bersedia")
        self.assertEqual(sched["status"], "menunggu_persetujuan_admin")

    # 8. Jadwal berulang (recurring schedule)
    def test_08_recurring_schedule(self):
        res = generate_recurring_schedules(
            title="Sesi Rutin Bahasa Inggris Mingguan",
            program_id=3,
            student_id=2, # Alisha Putri
            mentor_id=2,  # Budi Santoso
            days_of_week_list=[1, 3], # Selasa & Kamis
            start_date_str="2026-11-10",
            end_date_str="2026-11-20",
            start_time="10:00",
            duration_minutes=90,
            notes="Program bimbingan rutin pekanan",
            created_by_user_id=1
        )
        self.assertTrue(res["success"])
        self.assertGreater(res["count"], 0)

        # Pastikan sesi-sesi tersebut terdaftar di database
        schedules = query_db("SELECT count(*) as c FROM schedules WHERE recurring_rule_id = ?", (res["rule_id"],), one=True)
        self.assertEqual(schedules["c"], res["count"])

    # 9. Deteksi bentrokan jadwal
    def test_09_conflict_detection(self):
        # Sesi 1 sudah ada: 2026-10-19 pukul 16:00 - 17:30 untuk mentor=1 dan siswa=1
        conf = check_schedule_conflict(
            mentor_id=1,
            student_id=3, # Siswa lain, tapi mentor 1 sama
            schedule_date="2026-10-19",
            start_time="16:30",
            end_time="18:00"
        )
        self.assertTrue(conf["has_conflict"])
        self.assertIsNotNone(conf["mentor_conflict"])
        self.assertIn("Mentor Sarah Nurhaliza, S.Pd. telah memiliki jadwal", conf["message"])

        # Cek jika tidak ada bentrokan di jam berbeda
        no_conf = check_schedule_conflict(
            mentor_id=1,
            student_id=3,
            schedule_date="2026-10-19",
            start_time="08:00",
            end_time="09:30"
        )
        self.assertFalse(no_conf["has_conflict"])

    # 10. Peringatan mentor yang belum merespons
    def test_10_overdue_mentor_responses(self):
        overdue = check_overdue_mentor_responses()
        # Harus mengembalikan daftar jadwal atau list
        self.assertIsInstance(overdue, list)

    # 11. Penolakan jadwal dengan alasan wajib
    def test_11_reject_schedule_with_reason(self):
        # Buat jadwal baru
        res_prop = create_schedule_proposal(
            title="Sesi Les Fisika Khusus",
            program_id=2,
            student_id=1,
            mentor_id=1, # Mentor 1 (user_id=3)
            schedule_date="2026-11-15",
            start_time="14:00",
            duration_minutes=90,
            session_notes="Uji penolakan",
            created_by_user_id=1,
            status="disetujui"
        )
        sched_id = res_prop["schedule_id"]

        # Mentor tolak tanpa alasan -> Harus gagal
        fail_res = mentor_respond_schedule(sched_id, mentor_user_id=3, response_choice="tidak_bisa", reason="")
        self.assertFalse(fail_res["success"])

        # Mentor tolak dengan alasan jelas
        ok_res = mentor_respond_schedule(
            sched_id,
            mentor_user_id=3,
            response_choice="tidak_bisa",
            reason="Ada agenda ujian sertifikasi PPG di kampus."
        )
        self.assertTrue(ok_res["success"])

        # Periksa status di database: perlu_mentor_pengganti
        sched = query_db("SELECT mentor_response_status, mentor_response_notes FROM schedules WHERE id = ?", (sched_id,), one=True)
        self.assertEqual(sched["mentor_response_status"], "perlu_mentor_pengganti")
        self.assertIn("ujian sertifikasi PPG", sched["mentor_response_notes"])

    # 12. Pergantian mentor dan riwayatnya
    def test_12_mentor_replacement_and_history(self):
        # Ambil jadwal id=5 yang statusnya 'perlu_mentor_pengganti'
        sched_id = 5
        sched_before = query_db("SELECT mentor_id FROM schedules WHERE id = ?", (sched_id,), one=True)
        orig_mentor = sched_before["mentor_id"]

        # Cari mentor pengganti (misal mentor_id=2)
        res_rep = execute_mentor_replacement(
            schedule_id=sched_id,
            replacement_mentor_id=2,
            reason="Mentor Sarah berhalangan dinas luar kota, digantikan Mentor Budi.",
            admin_user_id=1
        )
        self.assertTrue(res_rep["success"])

        # Periksa mentor_id jadwal telah berubah
        sched_after = query_db("SELECT mentor_id, mentor_response_status FROM schedules WHERE id = ?", (sched_id,), one=True)
        self.assertEqual(sched_after["mentor_id"], 2)
        self.assertEqual(sched_after["mentor_response_status"], "menunggu_konfirmasi")

        # Periksa riwayat pergantian tersimpan di mentor_replacements
        rep_rec = query_db("SELECT * FROM mentor_replacements WHERE schedule_id = ? ORDER BY id DESC", (sched_id,), one=True)
        self.assertIsNotNone(rep_rec)
        self.assertEqual(rep_rec["original_mentor_id"], orig_mentor)
        self.assertEqual(rep_rec["replacement_mentor_id"], 2)

    # 13. Absensi dan perkembangan siswa
    def test_13_attendance_and_progress(self):
        # Buat absensi sesi 2
        sched_id = 2
        execute_db("""
            INSERT OR REPLACE INTO attendance (schedule_id, student_id, mentor_id, status, notes)
            VALUES (?, 2, 2, 'hadir', 'Siswa aktif bertanya tentang dialog bahasa Inggris.')
        """, (sched_id,))

        att = query_db("SELECT status, notes FROM attendance WHERE schedule_id = ?", (sched_id,), one=True)
        self.assertEqual(att["status"], "hadir")

        # Buat laporan perkembangan
        execute_db("""
            INSERT OR REPLACE INTO student_progress (
                schedule_id, student_id, mentor_id, program_id, session_date,
                topics_covered, skills_mastered, difficulties, recommendations, additional_notes
            ) VALUES (?, 2, 2, 3, '2026-10-24', ?, ?, ?, ?, ?)
        """, (
            sched_id,
            "Daily Conversation & Pronunciation Practice",
            "Percaya diri memperkenalkan diri dalam bahasa Inggris",
            "Pengucapan bunyi th dan vokal panjang",
            "Mendengarkan rekaman audio 10 menit setiap hari",
            "Alisha sangat ceria dan antusias."
        ))

        prog = query_db("SELECT topics_covered, skills_mastered FROM student_progress WHERE schedule_id = ?", (sched_id,), one=True)
        self.assertIn("Daily Conversation", prog["topics_covered"])

    # 14. Pemantauan perkembangan belajar tanpa akun login wali (Section E & F)
    def test_14_parent_progress_access(self):
        # Percobaan akses ke route parent manapun harus di-block (403 Forbidden atau 404 Not Found karena modul dihapus)
        c_guest = self.app.test_client()
        res_blocked = c_guest.get("/parent/dashboard")
        self.assertIn(res_blocked.status_code, (403, 404))

        res_prog_blocked = c_guest.get("/parent/progress")
        self.assertIn(res_prog_blocked.status_code, (403, 404))

        # Laporan perkembangan siswa tetap tersimpan permanen dan dapat dipantau oleh Admin
        c_admin = self.app.test_client()
        c_admin.get("/login")
        with c_admin.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        c_admin.post("/login", data={"csrf_token": csrf, "username": "admin", "password": "admin123"})
        res_admin_st = c_admin.get("/admin/students/2")
        self.assertEqual(res_admin_st.status_code, 200)

        # Dan dapat dipantau oleh Pemilik (Owner) dalam mode supervisi eksekutif
        c_owner = self.app.test_client()
        c_owner.get("/login")
        with c_owner.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        c_owner.post("/login", data={"csrf_token": csrf, "username": "owner", "password": "owner123"})
        res_owner_dash = c_owner.get("/owner/dashboard")
        self.assertEqual(res_owner_dash.status_code, 200)

    # 15. Notifikasi website
    def test_15_notifications_system(self):
        notif_id = create_notification(
            user_id=1,
            title="Pengujian Notifikasi Baru",
            message="Pesan notifikasi berhasil dibuat oleh test suite.",
            notif_type="info"
        )
        self.assertIsNotNone(notif_id)

        unread_before = get_unread_count(1)
        self.assertGreaterEqual(unread_before, 1)

        # Tandai dibaca
        mark_as_read(notif_id, user_id=1)
        notif = query_db("SELECT is_read FROM notifications WHERE id = ?", (notif_id,), one=True)
        self.assertEqual(notif["is_read"], 1)

    # 16. Mode pengujian integrasi WhatsApp
    def test_16_whatsapp_test_mode(self):
        res = send_whatsapp_message("081298765401", "Uji pesan tes WhatsApp", "uji_template")
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "simulasi")

        # Periksa tabel log pengiriman
        logs = get_delivery_logs(limit=5)
        log_phones = [l["recipient_phone"] for l in logs]
        self.assertIn("6281298765401", log_phones)

    # 17. Backup dan restore
    def test_17_backup_and_restore(self):
        # 1. Buat backup
        bk_res = create_backup(created_by="test_runner", notes="Uji backup otomatis")
        self.assertTrue(bk_res["success"])
        bk_file = bk_res["filepath"]

        # 2. Validasi file backup
        val = validate_backup_file(bk_file)
        self.assertTrue(val["valid"])

        # 3. Uji fungsi list_backups
        all_bk = list_backups()
        self.assertGreaterEqual(len(all_bk), 1)

        # 4. Uji restore
        restore_res = restore_backup(bk_res["backup_id"], requested_by="test_runner")
        self.assertTrue(restore_res["success"])

    # 18. Arsip data
    def test_18_data_archiving(self):
        # Siswa berhenti (id=4 Rina Wijaya)
        archived_st = query_db("SELECT * FROM students WHERE status = 'berhenti'", one=True)
        self.assertIsNotNone(archived_st)
        self.assertEqual(archived_st["status"], "berhenti")

        # Program diarsipkan (id=5 Persiapan Olimpiade Sains 2025)
        archived_pr = query_db("SELECT * FROM programs WHERE status = 'diarsipkan'", one=True)
        self.assertIsNotNone(archived_pr)
        self.assertEqual(archived_pr["status"], "diarsipkan")

    # 19. Ekspor laporan
    def test_19_reports_export(self):
        sched_data = get_schedules_report()
        headers = ["ID", "Judul", "Tanggal", "Siswa", "Mentor"]
        key_map = [("ID", "id"), ("Judul", "title"), ("Tanggal", "schedule_date"), ("Siswa", "student_name"), ("Mentor", "mentor_name")]
        csv_str = generate_csv_string(headers, sched_data, key_map)
        self.assertIn("ID,Judul,Tanggal,Siswa,Mentor", csv_str)
        self.assertIn("Naufal Pratama", csv_str)

    # 20. Penyimpanan data setelah aplikasi dibuka kembali
    def test_20_persistence(self):
        # Data tetap persisten dalam file SQLite
        conn = get_direct_connection()
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM users")
        user_count = cur.fetchone()[0]
        conn.close()
        self.assertGreaterEqual(user_count, 5)

    # 21. Pengujian Pilihan Arsip dan Hapus Otomatis Siswa
    def test_21_delete_student_and_safeguards(self):
        c = self.app.test_client()
        c.get("/login")
        with c.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        c.post("/login", data={"csrf_token": csrf, "username": "admin", "password": "admin123"})

        # 1. Pilihan Arsip: Siswa dengan riwayat jadwal (ID 1) dapat diarsipkan tanpa menghapus riwayat
        with c.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_archive = c.post("/admin/students/1/delete", data={"csrf_token": csrf, "action_type": "archive"}, follow_redirects=True)
        self.assertIn(b"berhasil diarsipkan", res_archive.data)
        st1 = query_db("SELECT id, status FROM students WHERE id = 1", one=True)
        self.assertIsNotNone(st1)
        self.assertEqual(st1["status"], "berhenti")

        # 2. Pilihan Hapus Otomatis: Siswa dapat dihapus otomatis beserta seluruh riwayat terkait
        new_id = execute_db("INSERT INTO students (parent_id, full_name, status) VALUES (1, 'Siswa Baru Belum Les', 'aktif')")
        with c.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_del = c.post(f"/admin/students/{new_id}/delete", data={"csrf_token": csrf, "action_type": "auto_delete"}, follow_redirects=True)
        self.assertIn(b"berhasil dihapus secara otomatis", res_del.data)
        st_deleted = query_db("SELECT id FROM students WHERE id = ?", (new_id,), one=True)
        self.assertIsNone(st_deleted)

    # 22. Pengujian Tambah, Ganti/Ubah, dan Hapus Program Les Siswa
    def test_22_student_program_management(self):
        c = self.app.test_client()
        c.get("/login")
        with c.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        c.post("/login", data={"csrf_token": csrf, "username": "admin", "password": "admin123"})

        # Buat siswa sementara
        test_student_id = execute_db("INSERT INTO students (parent_id, full_name, status) VALUES (1, 'Siswa Uji Program', 'aktif')")

        # 1. Tambah program les ke siswa (Program ID 1)
        with c.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_add = c.post(f"/admin/students/{test_student_id}/programs/add", data={
            "csrf_token": csrf,
            "program_id": 1,
            "mentor_id": 1,
            "start_date": "2026-10-24",
            "notes": "Program awal matematika"
        }, follow_redirects=True)
        self.assertIn(b"berhasil didaftarkan", res_add.data)

        sp = query_db("SELECT * FROM student_programs WHERE student_id = ? AND program_id = 1", (test_student_id,), one=True)
        self.assertIsNotNone(sp)
        sp_id = sp["id"]

        # 2. Ganti / Ubah program les siswa (Ganti ke program ID 2 dan ubah status ke aktif)
        with c.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_edit = c.post(f"/admin/students/{test_student_id}/programs/{sp_id}/edit", data={
            "csrf_token": csrf,
            "program_id": 2,
            "mentor_id": 2,
            "status": "aktif",
            "start_date": "2026-10-25",
            "end_date": "",
            "notes": "Pindah ke program mengaji"
        }, follow_redirects=True)
        self.assertIn(b"berhasil diperbarui", res_edit.data)

        sp_updated = query_db("SELECT * FROM student_programs WHERE id = ?", (sp_id,), one=True)
        self.assertEqual(sp_updated["program_id"], 2)
        self.assertEqual(sp_updated["mentor_id"], 2)

        # 3. Hapus program les dari daftar siswa
        with c.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_del = c.post(f"/admin/students/{test_student_id}/programs/{sp_id}/delete", data={
            "csrf_token": csrf
        }, follow_redirects=True)
        self.assertIn(b"berhasil dihapus dari daftar les", res_del.data)

        sp_deleted = query_db("SELECT * FROM student_programs WHERE id = ?", (sp_id,), one=True)
        self.assertIsNone(sp_deleted)

        # Bersihkan siswa uji coba
        execute_db("DELETE FROM students WHERE id = ?", (test_student_id,))

    # 23. Perhitungan Otomatis Siklus Periode & Pertemuan (Section A & D)
    def test_23_period_and_meeting_calculation(self):
        # 8 Pertemuan valid = 1 Periode
        # Rumus: period = ((total - 1) // 8) + 1, meeting = ((total - 1) % 8) + 1
        self.assertEqual(calculate_period_and_meeting(1), (1, 1, "Pertemuan 1 (1)"))
        self.assertEqual(calculate_period_and_meeting(7), (1, 7, "Pertemuan 7 (1)"))
        self.assertEqual(calculate_period_and_meeting(8), (1, 8, "Pertemuan 8 (1)"))
        self.assertEqual(calculate_period_and_meeting(9), (2, 1, "Pertemuan 1 (2)"))
        self.assertEqual(calculate_period_and_meeting(16), (2, 8, "Pertemuan 8 (2)"))
        self.assertEqual(calculate_period_and_meeting(17), (3, 1, "Pertemuan 1 (3)"))

        # Contoh Master Prompt: Siswa menyelesaikan 40 pertemuan -> pertemuan terakhir adalah 8 (5), berikutnya Pertemuan 1 (6)
        self.assertEqual(calculate_period_and_meeting(40), (5, 8, "Pertemuan 8 (5)"))
        p_next, m_next, str_next = calculate_period_and_meeting(41)
        self.assertEqual(str_next, "Pertemuan 1 (6)")

        # Contoh Master Prompt: Siswa menyelesaikan 3 pertemuan di Periode 4 (total 27 pertemuan) -> berikutnya Pertemuan 4 (4)
        self.assertEqual(calculate_period_and_meeting(27), (4, 3, "Pertemuan 3 (4)"))
        p_next2, m_next2, str_next2 = calculate_period_and_meeting(28)
        self.assertEqual(str_next2, "Pertemuan 4 (4)")

        # Konversi balik (Period, Meeting) ke Total
        self.assertEqual(calculate_total_from_period_and_meeting(1, 1), 1)
        self.assertEqual(calculate_total_from_period_and_meeting(1, 8), 8)
        self.assertEqual(calculate_total_from_period_and_meeting(2, 1), 9)
        self.assertEqual(calculate_total_from_period_and_meeting(4, 3), 27)
        self.assertEqual(calculate_total_from_period_and_meeting(6, 0), 40)

    # 24. Aturan Penambahan Absensi & Pencegahan Duplikasi (Section C)
    def test_24_attendance_cycle_increment_rules(self):
        st_id = execute_db("INSERT INTO students (parent_id, full_name, status) VALUES (1, 'Siswa Uji Siklus', 'aktif')")
        try:
            # 1. Siswa baru mulai dari Pertemuan 1 (1)
            stats0 = get_student_meeting_stats(st_id)
            self.assertEqual(stats0["total_meetings"], 0)
            self.assertEqual(stats0["next_meeting_str"], "Pertemuan 1 (1)")

            # 2. Buat jadwal 1 dan catat 'hadir' -> Terhitung Pertemuan 1 (1)
            s1 = execute_db("INSERT INTO schedules (student_id, mentor_id, program_id, schedule_date, start_time, end_time, duration_minutes, status) VALUES (?, 1, 1, '2026-11-01', '10:00', '11:30', 90, 'disetujui')", (st_id,))
            res1 = record_or_update_attendance(s1, st_id, 1, "hadir", topics_covered="Materi Aljabar Sesi 1")
            self.assertTrue(res1["success"])
            self.assertEqual(res1["meeting_number"], 1)
            self.assertEqual(res1["period_number"], 1)

            stats1 = get_student_meeting_stats(st_id)
            self.assertEqual(stats1["total_meetings"], 1)
            self.assertEqual(stats1["next_meeting_str"], "Pertemuan 2 (1)")

            # 3. Buat jadwal 2 dan catat 'izin' / 'tidak_hadir' -> TIDAK BOLEH menambah pertemuan valid
            s2 = execute_db("INSERT INTO schedules (student_id, mentor_id, program_id, schedule_date, start_time, end_time, duration_minutes, status) VALUES (?, 1, 1, '2026-11-02', '10:00', '11:30', 90, 'disetujui')", (st_id,))
            res2 = record_or_update_attendance(s2, st_id, 1, "izin", notes="Siswa sakit flu")
            self.assertTrue(res2["success"])
            self.assertIsNone(res2["meeting_number"])

            stats2 = get_student_meeting_stats(st_id)
            self.assertEqual(stats2["total_meetings"], 1)
            self.assertEqual(stats2["next_meeting_str"], "Pertemuan 2 (1)")

            # 4. Edit absensi jadwal 1 (misal mengubah catatan/materi) -> TIDAK BOLEH menambah periode/pertemuan
            res_edit = record_or_update_attendance(s1, st_id, 1, "hadir", topics_covered="Materi Aljabar Lanjutan Diperbarui")
            self.assertTrue(res_edit["success"])
            self.assertEqual(res_edit["meeting_number"], 1) # Tetap pertemuan 1
            self.assertEqual(res_edit["period_number"], 1)  # Tetap periode 1

            stats_edit = get_student_meeting_stats(st_id)
            self.assertEqual(stats_edit["total_meetings"], 1) # Tetap total 1
            self.assertEqual(stats_edit["next_meeting_str"], "Pertemuan 2 (1)")

            # Cek tabel absensi: tidak ada duplikasi rekaman untuk jadwal yang sama
            count_att = query_db("SELECT COUNT(*) as c FROM attendance WHERE schedule_id = ?", (s1,), one=True)["c"]
            self.assertEqual(count_att, 1)

        finally:
            execute_db("DELETE FROM attendance WHERE student_id = ?", (st_id,))
            execute_db("DELETE FROM schedules WHERE student_id = ?", (st_id,))
            execute_db("DELETE FROM students WHERE id = ?", (st_id,))

    # 25. Pengaturan Riwayat Awal Pertemuan untuk Siswa Lama (Section D)
    def test_25_initial_meeting_history_offset(self):
        st_id = execute_db("INSERT INTO students (parent_id, full_name, status) VALUES (1, 'Siswa Lama Riwayat', 'aktif')")
        try:
            # Skenario Master Prompt: Siswa sudah menyelesaikan 40 pertemuan sebelum sistem
            res_offset = set_student_initial_history(
                student_id=st_id,
                initial_offset=40,
                notes="Migrasi 5 periode awal sebelum website",
                admin_user_id=1
            )
            self.assertTrue(res_offset["success"])
            self.assertEqual(res_offset["new_offset"], 40)
            self.assertEqual(res_offset["stats"]["next_meeting_str"], "Pertemuan 1 (6)")

            # Siswa hadir pada sesi baru pertama di sistem
            s_new = execute_db("INSERT INTO schedules (student_id, mentor_id, program_id, schedule_date, start_time, end_time, duration_minutes, status) VALUES (?, 1, 1, '2026-11-03', '14:00', '15:30', 90, 'disetujui')", (st_id,))
            res_att = record_or_update_attendance(s_new, st_id, 1, "hadir", topics_covered="Materi Periode 6 Pertemuan 1")
            self.assertTrue(res_att["success"])
            self.assertEqual(res_att["meeting_number"], 1)
            self.assertEqual(res_att["period_number"], 6)
            self.assertEqual(res_att["cumulative_meeting"], 41)

            # Audit log tercatat
            audit = query_db("SELECT * FROM audit_logs WHERE action_type = 'ATUR_RIWAYAT_AWAL_PERTEMUAN' AND target_id = ? ORDER BY id DESC", (str(st_id),), one=True)
            self.assertIsNotNone(audit)
            self.assertIn("40", audit["details"])

        finally:
            execute_db("DELETE FROM attendance WHERE student_id = ?", (st_id,))
            execute_db("DELETE FROM schedules WHERE student_id = ?", (st_id,))
            execute_db("DELETE FROM students WHERE id = ?", (st_id,))

    # 26. Pengujian Skenario & Validasi WhatsApp (Section G)
    def test_26_whatsapp_scenarios_and_validation(self):
        # 1. Normalisasi nomor telepon
        self.assertEqual(normalize_phone_number("081298765401"), "6281298765401")
        self.assertEqual(normalize_phone_number("+62 812-9876-5401"), "6281298765401")
        self.assertEqual(normalize_phone_number("6281298765401"), "6281298765401")
        self.assertFalse(normalize_phone_number("123"))
        self.assertFalse(normalize_phone_number(""))

        # 2. Pembuatan tautan wa.me
        link = generate_whatsapp_web_link("081298765401", "Halo Selamat Siang")
        self.assertIn("https://wa.me/6281298765401?text=", link)

        # 3. Eksekusi 5 skenario pengujian
        # Skenario 1: Notifikasi Jadwal
        s1 = run_test_scenario("notifikasi_jadwal")
        self.assertTrue(s1["success"])
        self.assertEqual(s1["status"], "simulasi")

        # Skenario 2: Perubahan Jadwal
        s2 = run_test_scenario("perubahan_jadwal")
        self.assertTrue(s2["success"])
        self.assertEqual(s2["status"], "simulasi")

        # Skenario 3: Pengumuman Operasional
        s3 = run_test_scenario("operasional")
        self.assertTrue(s3["success"])
        self.assertEqual(s3["status"], "simulasi")

        # Skenario 4: Nomor Telepon Tidak Valid
        s4 = run_test_scenario("nomor_tidak_valid")
        self.assertFalse(s4["success"])
        self.assertEqual(s4["status"], "gagal")

        # Skenario 5: Kegagalan Koneksi API
        s5 = run_test_scenario("kegagalan_koneksi")
        self.assertFalse(s5["success"])
        self.assertEqual(s5["status"], "gagal")

    # 27. Formulir Jadwal yang Disederhanakan & Pembatasan Akses Mentor (Section B & F)
    def test_27_simplified_schedules_and_mentor_scope(self):
        # Penjadwalan rutin tanpa input periode tanggal berjalan mulus
        res_sched = generate_recurring_schedules(
            title="Sesi Sederhana",
            program_id=1,
            student_id=1,
            mentor_id=1,
            days_of_week_list=[0],
            start_time="14:00",
            duration_minutes=90,
            created_by_user_id=1
        )
        self.assertTrue(res_sched["success"])
        self.assertGreater(res_sched["count"], 0)

        # Mentor hanya dapat melihat siswa bimbingannya sendiri
        c_mentor = self.app.test_client()
        c_mentor.get("/login")
        with c_mentor.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        c_mentor.post("/login", data={"csrf_token": csrf, "username": "mentor1", "password": "mentor123"})

        res_students = c_mentor.get("/mentor/students")
        self.assertEqual(res_students.status_code, 200)
        # Mentor 1 membimbing Naufal Pratama (Program 1)
        self.assertIn(b"Naufal Pratama", res_students.data)

        # Mentor tidak memiliki akses mengubah program atau data master admin
        with c_mentor.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        res_unauth = c_mentor.post("/admin/programs/create", data={"csrf_token": csrf, "name": "Hack Program"})
        self.assertEqual(res_unauth.status_code, 403)

        # Bersihkan jadwal tes
        execute_db("DELETE FROM schedules WHERE title = 'Sesi Sederhana'")

    # 28. Penjadwalan Rutin Mingguan dan Deteksi Bentrokan Mentor
    def test_28_routine_schedules_system(self):
        # 1. Admin menambahkan jadwal rutin Sabtu 09:00 - 10:30 untuk Siswa 1 dan Mentor 1
        res1 = create_routine_schedule(
            student_id=1,
            program_id=1,
            mentor_id=1,
            day_of_week=5, # Sabtu
            start_time="09:00",
            end_time="10:30",
            subject_info="Aljabar Olimpiade",
            notes="Sesi rutin uji coba"
        )
        self.assertTrue(res1["success"])
        routine_id_1 = res1["id"]

        # 2. Admin menambahkan jadwal rutin Minggu 13:00 - 14:30 untuk Siswa 1 dan Mentor 1
        res2 = create_routine_schedule(
            student_id=1,
            program_id=1,
            mentor_id=1,
            day_of_week=6, # Minggu
            start_time="13:00",
            end_time="14:30",
            subject_info="Geometri Lanjutan"
        )
        self.assertTrue(res2["success"])
        routine_id_2 = res2["id"]

        # 3. Pengecekan bentrokan mentor:
        # Siswa 2 mencoba menjadwalkan Mentor 1 pada hari Sabtu di jam yang bertubrukan (09:30 - 11:00)
        conflict_check = check_routine_schedule_conflict(
            mentor_id=1,
            day_of_week=5,
            start_time="09:30",
            end_time="11:00",
            student_id=2
        )
        self.assertTrue(conflict_check["has_conflict"])
        self.assertIn("Bentrok jadwal mentor", conflict_check["message"])

        # Pengecekan jika waktu tidak bentrok (Sabtu 15:00 - 16:30)
        no_conflict = check_routine_schedule_conflict(
            mentor_id=1,
            day_of_week=5,
            start_time="15:00",
            end_time="16:30",
            student_id=2
        )
        self.assertFalse(no_conflict["has_conflict"])

        # 4. Update jadwal rutin
        res_upd = update_routine_schedule(
            routine_id=routine_id_1,
            day_of_week=5,
            start_time="10:45",
            end_time="12:15",
            mentor_id=1,
            subject_info="Aljabar Diperbarui"
        )
        self.assertTrue(res_upd["success"])

        # 5. Query daftar jadwal rutin mentor
        m1_routines = get_routine_schedules(mentor_id=1)
        self.assertGreaterEqual(len(m1_routines), 2)

        # 6. Hapus jadwal rutin
        res_del = delete_routine_schedule(routine_id_1)
        self.assertTrue(res_del["success"])
        delete_routine_schedule(routine_id_2)

    # 29. Pendaftaran Siswa Baru dengan Jadwal Rutin Tanpa Tanggal Pertemuan Fiktif (Master Prompt)
    def test_29_registration_with_routine_slots_no_phantom_dates(self):
        c_admin = self.app.test_client()
        c_admin.get("/login")
        with c_admin.session_transaction() as sess:
            csrf = sess.get("_csrf_token")
        c_admin.post("/login", data={"csrf_token": csrf, "username": "admin", "password": "admin123"})

        # Hitung jumlah record di tabel schedules sebelum registrasi
        count_before = query_db("SELECT COUNT(*) as c FROM schedules", one=True)["c"]

        # Admin mendaftarkan siswa baru dengan 2 slot jadwal rutin mingguan
        with c_admin.session_transaction() as sess:
            csrf = sess.get("_csrf_token")

        res_reg = c_admin.post("/admin/students/create", data={
            "csrf_token": csrf,
            "full_name": "Siswa Rutin Asli",
            "school": "SMP N 1 Sleman",
            "grade": "Kelas 7",
            "new_parent_name": "Ibu Kartika",
            "new_parent_phone": "081255556666",
            "program_id": 1,
            "mentor_id": 2, # Mentor Budi
            "subject_info": "Matematika Dasar & Aritmatika",
            "routine_day[]": ["5", "6"], # Sabtu & Minggu
            "routine_start[]": ["09:00", "13:00"],
            "routine_end[]": ["10:30", "14:30"],
            "initial_meeting_offset": "0"
        }, follow_redirects=True)

        self.assertEqual(res_reg.status_code, 200)

        # Ambil siswa yang baru dibuat
        st = query_db("SELECT id FROM students WHERE full_name = 'Siswa Rutin Asli'", one=True)
        self.assertIsNotNone(st)

        # Verifikasi slot jadwal rutin tersimpan di tabel routine_schedules
        routines = query_db("SELECT * FROM routine_schedules WHERE student_id = ?", (st["id"],))
        self.assertEqual(len(routines), 2)
        days = [r["day_of_week"] for r in routines]
        self.assertIn(5, days) # Sabtu
        self.assertIn(6, days) # Minggu

        # KRUSIAL: Verifikasi TIDAK ADA 8 tanggal pertemuan fiktif yang digenerate di tabel schedules!
        count_after = query_db("SELECT COUNT(*) as c FROM schedules", one=True)["c"]
        self.assertEqual(count_after, count_before, "Pendaftaran siswa baru tidak boleh membuat tanggal sesi otomatis di tabel schedules!")

        # Bersihkan data tes
        execute_db("DELETE FROM routine_schedules WHERE student_id = ?", (st["id"],))
        execute_db("DELETE FROM students WHERE id = ?", (st["id"],))
        execute_db("DELETE FROM parents WHERE full_name = 'Ibu Kartika'")

if __name__ == "__main__":
    unittest.main()


