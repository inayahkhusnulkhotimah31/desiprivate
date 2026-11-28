# Design Direction : DESI PRIVAT

## 1. Konteks Brand & Audiens (Gen Boomer & Gen Milenial)
**DESI PRIVAT** adalah platform manajemen bimbingan belajar privat keluarga (`Admin`, `Owner` read-only, `Mentor`, `Orang Tua/Wali`, `Developer`). Karena mayoritas pengguna adalah **Gen Boomer dan Gen Milenial**, keterbacaan tinggi, ketenangan visual, dan kesederhanaan alur menjadi prioritas utama.

---

## 2. Prinsip Visual & Motion (Wajib Dipenuhi)

1. **Palet Warna Terstruktur:**
   - **Primary (`#0093D6`):** Identitas brand, atmosfer hero sky-blue, gradient fade foto, menu sidebar aktif, dan highlight data.
   - **Secondary (`#A66B37`):** CTA konversi (`Konsultasi Program`, `Masuk ke Dashboard`, `+ Buat Jadwal`, `Cadangkan Database`) dan aksen kehangatan keluarga.
   - **Tertiary (`#111827` Ink + `#F7F7F5` Warm Alabaster + `#FFFFFF` + `#E5E7EB`):** Menjaga kenyamanan mata saat membaca tabel jadwal, tagihan, dan laporan belajar.

2. **Full-Bleed Photography + Fade + Teks Langsung (Tanpa Card):**
   - Hero, section profil/penutup landing, galeri dokumentasi, dan panel kiri login menggunakan foto kegiatan asli (`static/images/hero/*.jpg`) berukuran penuh dengan *directional gradient fade* (misalnya `#083A54` ke `#0093D6` ke transparan).
   - Judul, deskripsi singkat, dan tombol diletakkan **langsung di atas foto yang sudah di-fade** agar terasa lapang, editorial, dan modern (tidak memakai kotak card tambahan di atas foto).

3. **Ilustrasi Editorial Pendamping:**
   - Lengkapi halaman dengan ilustrasi vektor geometris/garis yang bersih (`static/images/`) untuk memperlihatkan gambaran alur kerja (alur penjadwalan bebas bentrok, rapor anak, ketersediaan mentor, empty state, dan halaman error).

4. **Transisi Perpindahan Halaman & Koreografi `scroll-craft`:**
   - **Page Transitions:** Terapkan transisi dinamis saat berpindah halaman atau tab (efek membuka tirai *curtain reveal*, geser horizontal kiri/kanan *slideIn/push*, dan *dissolve*) via CSS View Transitions (`@view-transition`) + transisi panel ringan yang menghormati `prefers-reduced-motion: reduce`.
   - **Scroll-Craft Pacing:** Setiap segmen landing memakai ritme gerak berbeda (layer parallax hero, reveal bertahap program, horizontal pan dokumentasi, dan penutup yang tenang). Animasi dibatasi hanya pada `transform`, `opacity`, dan `clip-path`.

5. **Aturan Teks & Tipografi:**
   - **Larangan Em Dash:** Hindari karakter em dash di seluruh UI, heading, maupun dokumentasi. Gunakan titik, koma, titik dua, atau titik tengah (`·`).
   - **Keterbacaan Boomer & Milenial:** Body minimal `15px`, sel tabel `14px`, padding nyaman, label tombol eksplisit bahasa Indonesia.
