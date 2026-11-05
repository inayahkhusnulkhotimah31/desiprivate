# DESI PRIVAT
## Sistem Informasi Manajemen Tempat Les Privat

**DESI PRIVAT** adalah sistem informasi manajemen tempat les privat berbasis web yang dibangun secara *full-stack* menggunakan **Python Flask, SQLite, HTML5, CSS3, JavaScript modern, dan Jinja2**. Aplikasi ini mengintegrasikan seluruh proses operasional bimbingan belajar privat, mulai dari pengelolaan data siswa, orang tua/wali murid, mentor pengajar, program bimbingan, penjadwalan rutin & satuan dengan deteksi bentrokan waktu cerdas, konfirmasi kesediaan, absensi sesi, pelaporan perkembangan belajar anak, audit aktivitas, backup & restore database, hingga pusat notifikasi in-app dan integrasi WhatsApp Business Platform resmi.

---

## 🌟 Daftar Fitur Utama

### 1. Autentikasi & Pembagian Peran (Role-Based Access Control)
- **4 Role Resmi:**
  1. **Admin / Pengelola:** Hak akses penuh atas operasional, pengelolaan data master, persetujuan jadwal, manajemen akun, audit log, backup, dan laporan.
  2. **Pemilik (Owner):** Hak akses supervisi dan laporan eksekutif bersifat **Baca Saja (Read-Only)** yang ditegakkan secara ketat di sisi backend.
  3. **Mentor Pengajar:** Mengelola jadwal mengajar yang ditugaskan, kalender ketersediaan waktu luang, mengusulkan jadwal, konfirmasi/penolakan mengajar dengan alasan wajib, absensi sesi, dan penulisan laporan perkembangan siswa.
  4. **Orang Tua / Wali Murid:** Akses data yang terisolasi aman hanya untuk anak yang terhubung dengan akunnya, dilengkapi **Pemilih Anak (Child Selector)** jika memiliki lebih dari satu anak, kalender les, riwayat kehadiran, serta rekap perkembangan belajar terbaru.
- **Keamanan Akun:**
  - Password di-hash menggunakan algoritma modern Scrypt.
  - Sesi aman dengan proteksi cookie HTTP-Only dan SameSite.
  - Seluruh form modifikasi data dilindungi oleh token CSRF (*Cross-Site Request Forgery*).
  - Role ditentukan otomatis dari database, bukan dari input form login.
  - Pengalihan otomatis (*auto-redirect*) ke dashboard yang sesuai.

### 2. Manajemen Data Master Operasional (CRUD)
- **Data Siswa:** Tambah, detail profil, ubah, arsip (*status: aktif, nonaktif, berhenti*), riwayat jadwal, kehadiran, dan riwayat perkembangan belajar.
- **Data Orang Tua / Wali:** Relasi 1 wali dapat memiliki 1 atau banyak anak (*multi-child*), pembuatan akun login langsung, data kontak, dan alamat.
- **Data Mentor:** Profil, keahlian mata pelajaran, waktu luang ketersediaan, beban jadwal mengajar aktif, dan status respons.
- **Data Program Les:** Pengaturan silabus, tingkat jenjang (SD, SMP, SMA), pembedaan program aktif dan arsip, serta rekap siswa terdaftar.
- **Pencarian & Filter Multi-Dimensi:** Pencarian instan dan filter berdasarkan nama, status, program, mentor, dan tanggal.

### 3. Sistem Penjadwalan Cerdas & Jadwal Berulang
- **Deteksi Bentrokan Waktu Otomatis (*Conflict Detection*):**
  - Memeriksa jadwal mentor dan siswa secara *real-time* baik saat pembuatan jadwal satuan maupun jadwal berulang.
  - Memberikan peringatan detail jika terjadi tumpang tindih waktu (*overlapping*).
- **Alur Persetujuan Bertahap:**
  1. Mentor mengusulkan jadwal untuk siswa bimbingannya.
  2. Status usulan: `menunggu_konfirmasi_siswa` / `menunggu_persetujuan_admin`.
  3. Admin dapat mencatat hasil koordinasi kesediaan siswa/wali.
  4. Admin menyetujui jadwal menjadi jadwal resmi (`disetujui`).
  5. Notifikasi otomatis dikirimkan ke dashboard mentor dan wali murid.
- **Jadwal Berulang Mingguan (*Recurring Schedules*):**
  - Pilihan hari tertentu dalam seminggu (misal: Senin & Rabu).
  - Rentang tanggal mulai dan akhir periode les.
  - Pengecekan bentrokan otomatis pada **setiap** tanggal yang digenerasi.

### 4. Konfirmasi Mentor & Pergantian Mentor Pengganti
- Status respons mentor: `menunggu_konfirmasi`, `dikonfirmasi`, `tidak_bisa`, `perlu_mentor_pengganti`.
- Jika mentor berhalangan, mentor **wajib** menyertakan alasan penolakan.
- **Peringatan Keterlambatan Respons:** Sistem mendeteksi mentor yang belum merespons melewati ambang batas waktu (default: 24 jam) dan memunculkan badge peringatan darurat pada dashboard Admin.
- **Pergantian Mentor (*Mentor Replacement*):**
  - Admin dapat mencari mentor pengganti yang aktif dan tidak bentrok jadwalnya.
  - Mencatat alasan pergantian, mentor awal, mentor pengganti, waktu pergantian, dan admin yang bertugas.
  - Mengirim notifikasi ke mentor pengganti, mentor lama, dan orang tua murid.
  - Riwayat pergantian tersimpan secara permanen (*immutable history*).

### 5. Absensi Kehadiran & Laporan Perkembangan Belajar
- **Absensi Sesi:** Status `hadir`, `izin`, `tidak_hadir (alpa)` dengan pembatasan anti-duplikasi ganda untuk sesi yang sama.
- **Laporan Perkembangan Siswa:**
  - Sesi, siswa, mentor, program les.
  - Materi yang dipelajari (*topics covered*).
  - Kemampuan yang telah dikuasai (*skills mastered*).
  - Kesulitan / kendala yang dialami (*difficulties*).
  - Rekomendasi untuk sesi berikutnya (*recommendations*).
  - Catatan tambahan mentor.
  - **Keterhubungan Langsung:** Begitu mentor menyimpan laporan, data langsung tersedia di dashboard orang tua anak terkait (*sorted newest first*).

### 6. Pusat Notifikasi Website & Integrasi WhatsApp Resmi
- **Notifikasi In-App:** Penerima, judul, pesan, kategori jenis, timestamp, status baca/belum baca.
- **Integrasi WhatsApp Business Platform (Meta Cloud API):**
  - Terpisah dari kode utama aplikasi via file `.env` dan `config.py`.
  - Normalisasi nomor telepon otomatis (format lokal `08xx` dikonversi ke internasional `628xx`).
  - **Mode Pengujian (WhatsApp Test Mode):** Berjalan dalam mode simulasi aman secara default (`WHATSAPP_TEST_MODE=true`), mencatat seluruh payload ke tabel `notification_delivery_logs` tanpa risiko pemblokiran atau pulsa.
  - Tabel log pengiriman memuat status (`simulasi`, `sukses`, `gagal`), respons gateway, dan waktu pengiriman.

### 7. Riwayat Aktivitas (Audit Log) & Pengarsipan Data
- Pencatatan seluruh aktivitas penting: Tambah/Ubah/Arsip Siswa, Mentor, Program, Setujui Jadwal, Ganti Mentor, Backup, dan Restore.
- Catatan bersifat *append-only* (tidak dapat diubah/dihapus via antarmuka).
- Dapat dipantau oleh Admin dan Pemilik.

### 8. Laporan, Rekapitulasi, & Ekspor Data
- Laporan jadwal, rekap kehadiran, rekap perkembangan siswa, riwayat pergantian mentor, data siswa, dan beban mentor.
- Filter tanggal, siswa, mentor, dan program.
- **Ekspor CSV:** Pembuatan berkas CSV secara instan dan aman (tanpa menyertakan password hash atau token rahasia).
- Tampilan cetak (*print-friendly*).

### 9. Pencadangan & Pemulihan Database (Backup & Restore)
- Pembuatan cadangan database SQLite konsisten ke folder `backups/`.
- Verifikasi integritas file SQLite (`PRAGMA quick_check`) dan kelengkapan tabel sebelum pemulihan.
- **Pre-Restore Snapshot:** Sistem otomatis mencadangkan kondisi database aktif saat ini sebelum proses pemulihan dijalankan.
- Konfirmasi pengetikan teks `PULIHKAN` untuk mencegah pemulihan tidak disengaja.

---

## 📁 Struktur Folder Proyek

```
desi_privat/
├── app.py                      # Inisialisasi Flask, context processor, filter Jinja, error handlers
├── config.py                   # Konfigurasi aplikasi, env loader, dan setting keamanan
├── requirements.txt            # Daftar pustaka dependensi Python
├── README.md                   # Dokumentasi teknis & panduan penggunaan
├── .env.example                # Template konfigurasi environment variables
├── .env                        # Konfigurasi lokal aktif
├── database/
│   ├── desi_privat.db          # Database SQLite aktif
│   └── schema.sql              # Skema DDL tabel, relasi foreign key, dan indeks
├── routes/
│   ├── __init__.py
│   ├── auth.py                 # Rute login, logout, proteksi CSRF, kontrol akses role
│   ├── admin.py                # Dashboard & seluruh manajemen operasional Admin
│   ├── owner.py                # Dashboard pengawasan eksekutif Pemilik (Read-Only)
│   ├── mentor.py               # Dashboard mengajar, ketersediaan, absensi, & laporan perkembangan
│   └── parent.py               # Dashboard orang tua/wali murid dengan pemilih anak
├── services/
│   ├── __init__.py
│   ├── database_service.py     # Koneksi SQLite, query_db, execute_db, inisialisasi & seeding
│   ├── schedule_service.py     # Deteksi bentrokan, jadwal rutin, persetujuan, & ganti mentor
│   ├── notification_service.py # Pengelolaan notifikasi in-app
│   ├── whatsapp_service.py     # WhatsApp Business Platform API & mode simulasi pengujian
│   ├── backup_service.py       # Backup atomic, validasi integritas, snapshot & safe restore
│   ├── audit_service.py        # Pencatatan audit log aktivitas admin/sistem
│   └── report_service.py       # Agregasi metrik, rekap multi-dimensi, & generator CSV
├── static/
│   ├── css/
│   │   └── main.css            # Desain antarmuka: Soft Blue, Navy, White, Glassmorphism
│   └── js/
│       └── main.js             # Deteksi bentrokan dinamis, modal dialog, toggle password
├── templates/
│   ├── base.html               # Kerangka utama, sidebar responsif, header, flash alert
│   ├── login.html              # Halaman login profesional dengan helper akun demo
│   ├── errors/                 # Template error 400, 403, 404, 500
│   ├── admin/                  # Template modul Admin (11 template halaman)
│   ├── owner/                  # Template modul Pemilik (8 template pengawasan)
│   ├── mentor/                 # Template modul Mentor (6 template pengajaran)
│   └── parent/                 # Template modul Orang Tua/Wali (5 template anak)
├── backups/                    # Direktori penyimpanan berkas cadangan database (.db)
└── tests/
    └── test_all_features.py    # Test suite otomatis mencakup 20 skenario pengujian
```

---

## 💻 Persyaratan Sistem

- **Sistem Operasi:** Windows 10/11, Linux, atau macOS.
- **Python:** Versi 3.10 atau 3.11+.
- **Browser Modern:** Google Chrome, Microsoft Edge, Mozilla Firefox, atau Safari.

---

## 🚀 Panduan Instalasi & Menjalankan Aplikasi pada Windows

### 1. Buat dan Aktifkan Virtual Environment (Opsional namun Disarankan)
Buka terminal **PowerShell** atau **Command Prompt** di folder proyek:

```powershell
# Buat virtual environment bernama venv
python -m venv venv

# Aktifkan virtual environment pada Windows PowerShell:
.\venv\Scripts\Activate.ps1

# (Jika menggunakan Command Prompt biasa):
# .\venv\Scripts\activate.bat
```

### 2. Instal Dependensi
Pastikan file `requirements.txt` terinstal:

```powershell
python -m pip install -r requirements.txt
```

### 3. Konfigurasi Lingkungan (.env)
Salin template konfigurasi jika belum memiliki file `.env`:

```powershell
copy .env.example .env
```

### 4. Inisialisasi Database & Data Awal
Database SQLite (`database/desi_privat.db`) akan diinisialisasi dan diisi dengan data pengujian secara otomatis saat aplikasi pertama kali dijalankan. Namun jika ingin melakukan reset atau inisialisasi manual:

```powershell
python -c "from services.database_service import init_db, seed_test_data; init_db(); seed_test_data(); print('Database berhasil disiapkan!')"
```

### 5. Jalankan Aplikasi
Jalankan server Flask:

```powershell
python app.py
```

Output pada terminal akan menampilkan:
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

Buka peramban (browser) Anda dan akses alamat:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Akun Pengujian Resmi (Demo Kredensial)

Sistem telah dilengkapi data awal yang saling terhubung antar role. Gunakan akun berikut untuk menguji masing-masing peran:

| Peran (Role) | ID Pengguna (Username) | Kata Sandi (Password) | Hak Akses Utama |
| :--- | :--- | :--- | :--- |
| **Admin Pengelola** | `admin` | `admin123` | Akses penuh operasional, jadwal, CRUD, backup, audit log |
| **Pemilik (Owner)** | `owner` | `owner123` | Supervisi eksekutif, rekap, laporan (Mode Baca / Read-Only) |
| **Mentor 1 (Sarah)** | `mentor1` | `mentor123` | Jadwal mengajar, usulan jadwal, ketersediaan, absensi, laporan perkembangan |
| **Mentor 2 (Budi)** | `mentor2` | `mentor123` | Jadwal mengajar, ketersediaan, mentor pengganti |
| **Mentor 3 (Dian)** | `mentor3` | `mentor123` | Pengajar calistung dan SD |
| **Wali Murid 1 (Ibu Ratna)** | `parent1` | `parent123` | Memiliki **2 anak** (Naufal Pratama & Alisha Putri), fitur pemilih anak |
| **Wali Murid 2 (Bapak Hendra)** | `parent2` | `parent123` | Orang tua dari Kevin Ardiansyah |

*Catatan: Pada halaman login terdapat tombol helper **💡 Klik di sini untuk Akun Pengujian** yang dapat mengisi username dan password secara otomatis untuk mempermudah evaluasi.*

---

## 🧪 Menjalankan Pengujian Otomatis (20 Poin Pengujian)

Aplikasi memiliki automated test suite menggunakan pustaka bawaan `unittest` yang menguji ke-20 poin persyaratan secara menyeluruh:

```powershell
python -m unittest tests/test_all_features.py
```

Hasil pengujian yang diharapkan:
```
----------------------------------------------------------------------
Ran 20 tests in 1.3s

OK
```

---

## 💾 Panduan Backup & Restore Database

1. Masuk sebagai **Admin** (`admin` / `admin123`).
2. Masuk ke menu **Backup & Restore** pada navigasi sidebar.
3. **Membuat Cadangan:** Klik tombol **"Cadangkan Database Sekarang"**. Berkas snapshot database SQLite akan dibuat di folder `backups/` dengan nama timestamp (contoh: `desi_privat_backup_YYYYMMDD_HHMMSS.db`).
4. **Memulihkan Cadangan (Restore):**
   - Pada tabel riwayat berkas cadangan, klik tombol **"Pulihkan"** pada berkas yang ingin dikembalikan.
   - Sistem akan memvalidasi integritas berkas cadangan tujuan terlebih dahulu.
   - Sebelum restorasi berlangsung, sistem **secara otomatis membuat snapshot darurat** dari kondisi database aktif saat ini demi keamanan data.
   - Ketikkan kata konfirmasi `PULIHKAN` pada dialog modal, lalu klik konfirmasi.
   - Database berhasil dipulihkan tanpa merusak konsistensi data.

---

## 📱 Panduan Pengaturan Integrasi WhatsApp Platform

Sistem notifikasi WhatsApp dirancang menggunakan arsitektur **WhatsApp Business Platform resmi (Meta Cloud API)**:

1. **Mode Pengujian / Simulasi (Default):**
   - Secara default, aplikasi berjalan dengan `WHATSAPP_TEST_MODE=true` di file `.env`.
   - Dalam mode ini, pengiriman notifikasi divalidasi dan dicatat ke tabel `notification_delivery_logs` dengan status `simulasi`.
   - Admin dapat membuka menu **Notifikasi & WhatsApp** untuk melihat log pesan yang berhasil disimulasikan.
2. **Menghubungkan ke Akun Produksi Meta (WhatsApp Cloud API):**
   - Daftarkan akun bisnis Anda di [Meta for Developers](https://developers.facebook.com/).
   - Buat aplikasi WhatsApp Business API dan dapatkan:
     - `WHATSAPP_PHONE_NUMBER_ID`
     - `WHATSAPP_ACCESS_TOKEN` (Permanent System User Token)
   - Buka file `.env` dan perbarui nilainya:
     ```env
     WHATSAPP_TEST_MODE=false
     WHATSAPP_PHONE_NUMBER_ID=nomor_id_telepon_dari_meta
     WHATSAPP_ACCESS_TOKEN=token_akses_permanen_meta
     ```
   - Restart aplikasi `python app.py`. Notifikasi WhatsApp akan terkirim secara langsung ke nomor orang tua/wali murid resmi.
   - Jika kredensial belum diatur atau koneksi internet bermasalah, pusat notifikasi internal website tetap berjalan normal tanpa kendala.

---

## 🔒 Catatan Keamanan & Batasan Eksternal

1. **Pembayaran:** Sesuai ketentuan operasional DESI PRIVAT, transaksi dan pembayaran les ditangani di luar aplikasi melalui koordinasi WhatsApp pengelola. Aplikasi tidak menyimpan nomor kartu atau transaksi pembayaran online.
2. **Kredensial Produksi:** File `.env` bersifat privat untuk setiap server dan tidak boleh disebarkan ke publik. Token dan hash password tidak dimasukkan ke dalam file ekspor laporan.
