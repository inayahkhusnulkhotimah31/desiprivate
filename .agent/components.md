# Components & Design Tokens — DESI PRIVAT

## 1. Design Tokens Final (Primary `#0093D6` · Secondary `#A66B37` · Tertiary `#111827` & `#F7F7F5`)

### Warna Utama
- **Primary (Cerulean Sky):** `--brand-primary: #0093D6`, `--brand-primary-dark: #0072A8`, `--brand-primary-soft: #EBF7FD`, `--brand-primary-border: #BAE4F8`, `--brand-primary-deep: #083A54`.
- **Secondary (Warm Caramel):** `--brand-secondary: #A66B37`, `--brand-secondary-hover: #8A5629`, `--brand-secondary-soft: #FAF3EC`, `--brand-secondary-border: #EBD8C5`.
- **Tertiary (Minimalist Neutrals):**
  - `--bg-app: #F7F7F5` (Warm Alabaster anti-glare)
  - `--surface-card: #FFFFFF`
  - `--ink-primary: #111827`, `--ink-body: #374151`, `--ink-muted: #6B7280`
  - `--border-hairline: #E5E7EB`
- **Semantik:**
  - `--status-ok-bg: #ECFDF5`, `--status-ok-text: #15803D`
  - `--status-warn-bg: #FAF3EC`, `--status-warn-text: #8A5629`
  - `--status-danger-bg: #FEF2F2`, `--status-danger-text: #B91C1C`

### Tipografi & Geometri (Nyaman untuk Boomer & Milenial)
- **Heading:** `'Poppins', 'Plus Jakarta Sans', sans-serif` (700/600, tracking `-0.02em` pada H1).
- **UI & Tabel:** `'Inter', sans-serif` (`15px` body, `14px` tabel, `13px` label/badge).
- **Radius:** Hero Canvas `24px`, Card `16px`, Input/Nav Item `10px`, Pill CTA/Badge `9999px`.
- **Border & Shadow:** `1px solid #E5E7EB` sebagai struktur utama; shadow lembut `0 8px 24px rgba(17, 24, 39, 0.05)` hanya untuk floating navbar, modal, dan auth card.

---

## 2. Katalog Komponen (52 Halaman dalam `design/00 - desi private.figcraft`)

1. **Minimalist Navbar (`landing.html`):** Logo kiri, link berjarak lega di tengah, tombol pill tegas di kanan.
2. **Serene Sky Hero (`landing.html`):** Kontainer rounded `#0093D6`, judul putih kontras tinggi, 2 CTA jelas, dan preview jendela dashboard bersih di bagian bawah/kanan.
3. **Centered Floating Auth Card (`login.html`, `developer/login.html`):** Kanvas `#F7F7F5` bersih, kartu `500px`, input tinggi `48px`, quick-demo role pills.
4. **Minimalist App Shell (`base.html`):** Sidebar putih `248px` dengan 1px border kanan, item aktif berlatar `#EBF7FD` dan bar kiri `4px #0093D6`; topbar putih `72px` dengan judul halaman + badge peran.
5. **KPI Row & Operational Banner:** Kartu putih hairline, angka besar `28px` (`Poppins Bold`), keterangan singkat tanpa noise.
6. **Clean Data Table & Action Bar:** Bar filter horizontal bersih, header tabel `12px` uppercase muted, baris `14px` dengan jarak nyaman, dan pill status semantik.
7. **Parent Child Selector (`parent/*.html`):** Pill switcher besar yang mudah diklik untuk berpindah antar profil anak.
8. **Print Receipt (`admin/receipt_print.html`) & Error States (`errors/*.html`):** Kartu terpusat bersih siap cetak/pemulihan cepat.
