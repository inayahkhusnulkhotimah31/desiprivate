# Workflow — Alur Kerja Desain, Implementasi & Deploy DESI PRIVAT

## Fase 1: Persiapan & Referensi (Saat Ini)
1. Baca `.agent/architecture.md`, `.agent/rules.md`, dan `.agent/ref/manual-references.md`.
2. Tinjau preview 3 tahap di FigCraft:
   - File utama: `design/desi-privat-client-preview.figcraft`
   - Hasil render PNG: `design/previews/` (`page1-wireframe.png`, `page2-lowfi.png`, `page3-hifi.png`, dan `hifi-frames/*.png`).
3. Jika ada revisi tata letak atau klien ingin melihat alternatif lain, perbarui `design/build_figcraft_preview.py` -> jalankan ulang `figcraft-cli.exe run` -> ekspor PNG -> buka di FigCraft.

## Fase 2: Gerbang Persetujuan Klien (Approval Gate)
- Jangan ubah `templates/` atau `static/` sebelum user/klien menyetujui arah visual di FigCraft (dan mengisi `.agent/ref/manual-references.md` jika ada referensi tambahan).

## Fase 3: Implementasi Visual (Frontend-Only)
1. Aktifkan skill `taste-skill` / `impeccable` (dan `scroll-craft` untuk `landing.html`).
2. Mulai dari `static/css/main.css` (definisikan token & komponen terstruktur tanpa merusak class legacy yang masih dipakai halaman lain).
3. Perbarui bertahap per kelompok halaman:
   - Gelombang 1: `templates/landing.html` & `templates/login.html`
   - Gelombang 2: `templates/base.html` & `templates/admin/dashboard.html`
   - Gelombang 3: Halaman operasional Admin, Owner (read-only), Mentor, dan Parent (`Child Selector`).
4. Pastikan **0 perubahan** pada `database/`, `services/`, `routes/`, `app.py`, `config.py`.

## Fase 4: Verifikasi & Auto-Push ke GitHub
1. Jalankan automated test suite:
   ```powershell
   python -m unittest tests/test_all_features.py
   ```
2. Jalankan `python app.py` secara lokal dan cek visual desktop (`1440px`) + mobile (`390px`) untuk memastikan tidak ada layout pecah atau teks terpotong.
3. Commit perubahan:
   ```powershell
   git add templates/ static/ design/ .agent/ AGENTS.md
   git commit -m "style(ui): revamp visual interface ..."
   ```
   Hook `.git/hooks/post-commit` akan otomatis menjalankan `git push origin main` -> Vercel (`https://desiprivate.vercel.app/`) akan otomatis men-deploy versi terbaru.

## Catatan FigCraft Live Mode (Opsional)
Jika ingin melihat agent mengedit kanvas FigCraft secara real-time:
1. Tutup FigCraft yang sedang berjalan, lalu buka dengan port kontrol:
   ```powershell
   & "C:\Program Files\ArtCraft\FigCraft\figcraft.exe" --control 7979
   ```
2. Di `~/.gemini/config/mcp_config.json`, ubah `args` milik `figcraft` menjadi `["mcp", "--attach", "7979"]`.
