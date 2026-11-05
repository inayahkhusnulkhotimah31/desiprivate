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
app = create_app()

if __name__ == "__main__":
    app.run()
