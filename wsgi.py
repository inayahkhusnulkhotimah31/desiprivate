"""
DESI PRIVAT - WSGI Entry Point
Digunakan untuk server web hosting produksi (Gunicorn, uWSGI, Passenger, dsb.)
"""
from app import create_app

# Instance WSGI aplikasi Flask untuk produksi
application = create_app()
app = application

if __name__ == "__main__":
    app.run()

