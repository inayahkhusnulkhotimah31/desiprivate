"""
Entry point Serverless Function untuk Vercel.
Vercel mengenali file ini sebagai WSGI application handler.
"""
import os
import sys
from pathlib import Path

# Pastikan direktori root masuk ke sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Aktifkan penanda environment Vercel
os.environ["VERCEL"] = "1"

from app import create_app

# Instansiasi WSGI app untuk Vercel
_raw_app = create_app()

class SafeWSGIHandler:
    """WSGI Middleware untuk menangani path rewriting Vercel dan error handling aman."""
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        try:
            # Perbaiki PATH_INFO jika Vercel rewrite mengubahnya menjadi /api/index
            original_path = environ.get("HTTP_X_FORWARDED_URI") or environ.get("HTTP_X_VERCEL_MATCHED_PATH")
            if original_path:
                environ["PATH_INFO"] = original_path.split("?")[0]
            elif environ.get("PATH_INFO") in ("/api/index", "/api/index.py", "/api"):
                environ["PATH_INFO"] = "/"
            return self.wsgi_app(environ, start_response)
        except Exception as e:
            import traceback
            err_trace = traceback.format_exc()
            print("WSGI Serverless Exception (Handled):", err_trace, file=sys.stderr)
            # Alihkan ke halaman login secara aman daripada menampilkan layar crash
            status = '302 Found'
            headers = [('Location', '/login')]
            start_response(status, headers)
            return []

app = SafeWSGIHandler(_raw_app)
handler = app

if __name__ == "__main__":
    _raw_app.run()
