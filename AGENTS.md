# AGENTS.md — Aturan Utama Workspace DESI PRIVAT

Dokumen ini dibaca otomatis oleh coding agent di seluruh percakapan pada workspace `DESI PRIVAT`.

## Batas Keras (WAJIB DIPATUHI)
1. **DILARANG MENGUBAH DATABASE:** Jangan pernah mengubah, menghapus, mereset, atau memigrasi `database/desi_privat.db`, `database/desi_privat_testing.db`, `database/schema.sql`, `database/supabase_schema.sql`, maupun query/skema di `services/` dan `scripts/`.
2. **FOKUS VISUAL SAJA (FRONTEND-ONLY):** Perubahan hanya boleh menyentuh layer presentasi: `templates/`, `static/css/`, `static/js/`, dan `static/images/`. Jangan mengubah logika bisnis backend di `routes/`, `services/`, `app.py`, atau `config.py`.
3. **JAGA KONTRAK JINJA2 & KEAMANAN:** Jangan mengubah `name="..."` pada form input, token `csrf_token`, endpoint `url_for(...)`, variabel template dari controller, atau guard RBAC (`admin`, `owner` read-only, `mentor`, `parent`, `developer`).
4. **FIGCRAFT PREVIEW-FIRST GATE:** Sebelum merombak tampilan website live, buat/perbarui preview 3 tahap di FigCraft (`Wireframe -> Low-Fidelity -> High-Fidelity`) di `design/desi-privat-client-preview.figcraft` sebagai bahan pertimbangan klien.
5. **VERIFIKASI WAJIB:** Setelah perubahan visual, jalankan `python -m unittest tests/test_all_features.py` (mode baca/tes terisolasi) dan cek tampilan responsif desktop + mobile.

## Peta Pengetahuan `.agent/`
- Arsitektur & Peta Rute/Template: `.agent/architecture.md`
- Aturan Coding & Kualitas: `.agent/rules.md`
- Daftar Skill Terpasang & Cara Pakai: `.agent/skill.md`
- Arah Desain & Audit Visual: `.agent/design.md`
- Design Tokens & Katalog Komponen: `.agent/components.md`
- Alur Kerja Visual & Deploy Vercel: `.agent/workflow.md`
- Referensi Desain Kurasi: `.agent/ref/curated-references.md`
- Referensi Manual User (Aturan >100% Upgrade): `.agent/ref/manual-references.md`
