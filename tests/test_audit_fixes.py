"""
Targeted security & bug-fix regression tests from ponytail-audit.
Menggunakan file DB sementara terisolasi di temp agar database produksi
dan test suite lain tidak saling menimpa.
"""
import os
import tempfile
import unittest
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from config import Config, TestingConfig
from services.database_service import init_db, seed_test_data, execute_db, query_db


class TestAuditFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.temp_db = tempfile.mkstemp(prefix="audit_test_", suffix=".db")
        os.close(fd)
        cls.orig_db_path = Config.DATABASE_PATH
        cls.orig_testing = Config.TESTING
        Config.DATABASE_PATH = cls.temp_db
        Config.TESTING = True
        TestingConfig.DATABASE_PATH = cls.temp_db

        cls.app = create_app(TestingConfig)
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            init_db()
            seed_test_data()

    @classmethod
    def tearDownClass(cls):
        Config.DATABASE_PATH = cls.orig_db_path
        Config.TESTING = cls.orig_testing
        if os.path.exists(cls.temp_db):
            try:
                os.remove(cls.temp_db)
            except OSError:
                pass

    def setUp(self):
        self._prev_db = Config.DATABASE_PATH
        self._prev_testing = Config.TESTING
        Config.DATABASE_PATH = self.temp_db
        Config.TESTING = True

    def tearDown(self):
        Config.DATABASE_PATH = self._prev_db
        Config.TESTING = self._prev_testing

    def test_config_exposes_whatsapp_settings(self):
        self.assertTrue(hasattr(Config, "WHATSAPP_TEST_MODE"))
        self.assertTrue(hasattr(Config, "WHATSAPP_API_URL"))
        self.assertTrue(hasattr(Config, "WHATSAPP_PHONE_NUMBER_ID"))
        self.assertTrue(hasattr(Config, "WHATSAPP_ACCESS_TOKEN"))

    def test_status_badge_escapes_html(self):
        filt = self.app.jinja_env.filters["status_badge"]
        rendered = filt('<script>alert(1)</script>')
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_login_blocks_protocol_relative_open_redirect(self):
        resp = self.client.get("/login")
        html = resp.data.decode("utf-8")
        marker = 'name="csrf_token" value="'
        token = html.split(marker, 1)[1].split('"', 1)[0]
        post_resp = self.client.post(
            "/login?next=//evil.example.com",
            data={"username": "admin", "password": "admin123", "csrf_token": token},
            follow_redirects=False,
        )
        self.assertEqual(post_resp.status_code, 302)
        self.assertNotIn("evil.example.com", post_resp.location)

    def test_developer_login_rejects_wrong_username_and_safe_limit(self):
        bad = self.client.post(
            "/developer/login",
            data={"username": "wronguser", "password": "wrongpassword"},
            follow_redirects=False,
        )
        self.assertEqual(bad.status_code, 200)
        with self.client.session_transaction() as sess:
            sess["is_developer"] = True
            sess["developer_username"] = "developer"
        api_resp = self.client.get("/developer/api/activities?limit=notanumber")
        self.assertEqual(api_resp.status_code, 200)
        self.assertTrue(api_resp.get_json()["success"])

    def test_deactivated_parent_blocked_on_existing_session(self):
        with self.app.app_context():
            u = query_db("SELECT id, username FROM users WHERE role = 'parent' LIMIT 1", one=True)
            created_temp = False
            if not u:
                uid = execute_db(
                    "INSERT INTO users (username, password_hash, role, full_name, is_active) VALUES (?, ?, 'parent', 'Audit Parent', 0)",
                    ("audit_parent_tmp", "pbkdf2:sha256:1$x$y"),
                )
                u = {"id": uid, "username": "audit_parent_tmp"}
                created_temp = True
            else:
                execute_db("UPDATE users SET is_active = 0 WHERE id = ?", (u["id"],))
        try:
            with self.client.session_transaction() as sess:
                sess.clear()
                sess["user_id"] = u["id"]
                sess["role"] = "parent"
            resp = self.client.get("/parent/dashboard")
            self.assertEqual(resp.status_code, 403)
        finally:
            with self.app.app_context():
                if created_temp:
                    execute_db("DELETE FROM users WHERE id = ?", (u["id"],))
                else:
                    execute_db("UPDATE users SET is_active = 1 WHERE id = ?", (u["id"],))


if __name__ == "__main__":
    unittest.main()
