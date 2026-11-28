# Architecture — DESI PRIVAT

## 1. Gambaran Umum Sistem
**DESI PRIVAT** adalah Sistem Informasi Manajemen Tempat Les Privat berbasis web (*full-stack*) menggunakan **Python Flask**, **Jinja2**, **SQLite** (dengan sinkronisasi cloud **Supabase** saat berjalan di **Vercel**), **HTML5**, **CSS3**, dan **JavaScript**.

- **Production URL:** `https://desiprivate.vercel.app/`
- **Repository:** `https://github.com/inayahkhusnulkhotimah31/desiprivate.git`
- **Entrypoint:**
  - Lokal: `app.py` (`create_app()`) / `wsgi.py`
  - Vercel Serverless: `api/index.py` + `vercel.json` (rewrite `/(.*)` -> `/api/index`)

---

## 2. Batas Imutabel vs Zona Kerja Visual

| Zona | Folder / File | Status Saat Ini |
| :--- | :--- | :--- |
| **Database & Skema** | `database/desi_privat.db`, `database/schema.sql`, `database/supabase_schema.sql` | **READ-ONLY / DILARANG UBAH** |
| **Backend Services** | `services/*.py` (`database_service.py`, `schedule_service.py`, `finance_service.py`, `whatsapp_service.py`, `backup_service.py`, `audit_service.py`, `report_service.py`, `cloud_sync_service.py`, dll.) | **READ-ONLY / DILARANG UBAH** |
| **Backend Routes** | `routes/*.py` (`auth.py`, `admin.py`, `owner.py`, `mentor.py`, `parent.py`, `developer.py`) | **READ-ONLY / DILARANG UBAH** |
| **Core Config & Scripts** | `app.py`, `config.py`, `scripts/*.py` | **READ-ONLY / DILARANG UBAH** |
| **Zona Visual (Target)** | `templates/**/*.html`, `static/css/main.css`, `static/js/main.js`, `static/images/*` | **BOLEH DIROMBAK (Setelah Approval Preview FigCraft)** |
| **Desain & Dokumen** | `design/*`, `.agent/*`, `AGENTS.md` | **AKTIF DIKELOLA** |

---

## 3. Peta Blueprint & Template (`templates/`)

### A. Publik & Autentikasi (`routes/auth.py`)
- `templates/landing.html` — Halaman publik utama (Navbar mengambang, Hero mosaik, Profil Usaha, 4 Program Les, Dokumentasi, Footer).
- `templates/login.html` — Split-screen login + helper akun demo (`admin`, `owner`, `mentor1`, `parent1`).
- `templates/errors/{400,403,404,500}.html` — Halaman error standar.

### B. Kerangka Aplikasi Terautentikasi
- `templates/base.html` — Layout utama (Sidebar navigasi dinamis per role, Topbar, Flash messages, Mobile menu).

### C. Modul Admin (`routes/admin.py` -> `templates/admin/`)
16 template: `dashboard.html`, `schedules.html`, `students.html`, `student_detail.html`, `mentors.html`, `parents.html`, `programs.html`, `bills.html`, `payments.html`, `mentor_honor.html`, `receipt_print.html`, `accounts.html`, `notifications.html`, `reports.html`, `audit_logs.html`, `backups.html`.

### D. Modul Pemilik / Owner — Read-Only (`routes/owner.py` -> `templates/owner/`)
16 template: `dashboard.html`, `attendance.html`, `attendance_detail.html`, `students.html`, `mentors.html`, `parents.html`, `admins.html`, `schedules.html`, `replacements.html`, `bills.html`, `finance.html`, `finance_report.html`, `honor.html`, `progress.html`, `reports.html`, `audit_logs.html`.

### E. Modul Mentor (`routes/mentor.py` -> `templates/mentor/`)
6 template: `dashboard.html`, `schedules.html`, `availability.html`, `students.html`, `attendance.html`, `progress.html`.

### F. Modul Orang Tua / Wali (`routes/parent.py` -> `templates/parent/`)
6 template: `dashboard.html` (dilengkapi **Child Selector** untuk wali dengan >1 anak), `schedules.html`, `attendance.html`, `progress.html`, `bills.html`, `no_children.html`.

### G. Modul Developer (`routes/developer.py` -> `templates/developer/`)
2 template: `login.html`, `dashboard.html`.
