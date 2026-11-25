import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.environ["DATABASE_PATH"] = str(BASE_DIR / "database" / "desi_privat_testing.db")
os.environ["FLASK_ENV"] = "development"

from app import create_app

app = create_app()

if __name__ == "__main__":
    print(f"Starting DESI PRIVAT test server on database: {os.environ['DATABASE_PATH']}")
    app.run(host="127.0.0.1", port=5001, debug=False)
