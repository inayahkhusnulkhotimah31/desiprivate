# Rules — Cara Coding & Guardrail Proyek DESI PRIVAT

## 1. Aturan Keras Non-Negosiasi
1. **Zero Database Mutation:** Tidak boleh mengubah file `.db`, `schema.sql`, `supabase_schema.sql`, migrasi, atau logika query SQL apa pun.
2. **Visual-Only Scope:** Semua perubahan implementasi website hanya boleh dilakukan di `templates/`, `static/css/`, `static/js/`, dan `static/images/`.
3. **Pertahankan Kontrak Jinja2:**
   - Setiap `<form>` wajib mempertahankan `method`, `action`, `<input type="hidden" name="csrf_token" ...>`, dan semua atribut `name="..."` pada input/select/textarea.
   - Jangan mengubah nama variabel Jinja2 (`summary`, `current_user`, `action_schedules`, `today_dow`, dll.) atau nama endpoint `url_for(...)`.
   - Jangan menghapus ID elemen penting yang dipakai oleh test atau JS (`#landingNavMenu`, `#btnBannerAddSchedule`, `#actionAttentionSection`, dll.).
   - Pertahankan pembatasan tampilan **Read-Only** pada role `owner`.
4. **Preview-First Gate (FigCraft):** Setiap perombakan visual besar wajib memiliki preview di `design/desi-privat-client-preview.figcraft` (Wireframe -> Low-Fi -> High-Fi) untuk disetujui klien sebelum menyentuh kode `templates/` & `static/`.

---

## 2. Prinsip Coding Frontend ("Ponytail" + Clean CSS)
- **Perubahan Terkecil yang Tuntas:** Jangan over-engineering (tidak perlu migrasi ke React/Tailwind CLI/Webpack karena app berjalan murni dengan Flask + Jinja2 + static CSS/JS di Vercel).
- **Hapus Inline Style Bertahap:** Pindahkan inline `style="..."` yang berulang di `landing.html`, `login.html`, dan `admin/dashboard.html` ke token & class terstruktur di `static/css/main.css`.
- **Satu Sistem Token:** Semua warna, radius, shadow, dan spasi harus memakai CSS Custom Properties di `:root` (`static/css/main.css`), bukan angka hex acak di tiap template.
- **Bahasa Indonesia Konsisten & Alami:** Seluruh label UI, placeholder, empty state, dan CTA memakai bahasa Indonesia yang jelas, sopan, dan ramah orang tua maupun pengelola.
- **Aksesibilitas & Responsif:**
  - Kontras teks minimal WCAG AA (`>= 4.5:1`).
  - Semua grid (program, KPI, tabel jadwal, sidebar) wajib rapi di desktop (`1440px`), tablet (`768px`), dan mobile (`375px`–`430px`).
  - Hormati `prefers-reduced-motion: reduce` untuk animasi/transisi.
- **Integritas Tes:** Suite `python -m unittest tests/test_all_features.py` (20 skenario) harus tetap lulus 100% setelah setiap perubahan frontend.
