# Manual Design References : DESI PRIVAT (Input Pengguna)

Dokumen ini mencatat referensi visual resmi dari pemilik proyek serta aturan **>100% Upgrade** untuk desain **DESI PRIVAT** (`c:\Users\Coding\04 - Desi Private`).

---

## Target Audiens & Gaya Utama
- **Audiens Utama:** **Gen Boomer & Gen Milenial** (orang tua/wali murid, pemilik lembaga, admin, dan mentor).
- **Gaya Wajib:** **Minimalist, Calm & Editorial Clarity** dengan ruang napas lega (*generous whitespace*), teks nyaman dibaca (`15-16px` body, `14px` tabel), kontras tinggi anti-silau (`#F7F7F5` Warm Alabaster), label tombol eksplisit bahasa Indonesia, **tanpa em dash**, serta **foto full-bleed dengan efek fade dan teks langsung di atas foto (tanpa membungkus teks dalam card)**.

---

## Referensi Resmi dari User

### 1. Referensi Gambar, Link Web & Video TikTok
1. **Image Ref #1 (`Grow+` Editorial Hero + Trust Bar):**
   - *Pola yang diambil:* Tipografi judul bersih berwibawa, baris bukti sosial yang tenang di bawah hero, dan *floating metric pill* yang halus.
2. **Image Ref #2 (`Wix` Airy Minimalist Landing & Centered Auth Card):**
   - *Pola yang diambil:* Halaman Login sangat bersih & lega dengan kartu login putih terpusat, label input besar & jelas, satu CTA utama yang tegas.
3. **Image Ref #3 (`TaskFlow` Clean White Navbar + Serene Sky-Blue Hero):**
   - *Pola yang diambil:* Navbar putih bersih, atmosfer biru langit (`#0093D6`) yang tenang, serta *product preview* yang bersih.
4. **TikTok `@heroinspo.com` Video #1 (`7599720674722073859`, 20 detik):**
   - *Teridentifikasi via `yt-dlp`:* **"What makes a website feel premium? Built by QCLAY. Clear hierarchy, refined visuals, and design decisions that elevate perception from the first second."**
   - *Takeaway:* Kesan premium dibangun dari detik pertama melalui hierarki ukuran teks yang tegas, komposisi visual lapang, dan transisi masuk yang halus.
5. **TikTok `@heroinspo.com` Video #2 (`7607176378517097750`, 27 detik):**
   - *Teridentifikasi via `yt-dlp`:* **"Is this the cleanest website layout you've seen? Built by Zeyox Studio. Precise hierarchy, refined spacing, and design decisions that create a seamless bridge between brand and user."**
   - *Takeaway:* Tata letak bersih (*ultra-clean content-first*), spasi presisi antar elemen, serta jembatan mulus antar bagian melalui animasi geser dan fade.
6. **SQSP Weekly (`https://www.sqspweekly.com/`):** Grid editorial simetris & garis pemisah 1px yang rapi.
7. **Awwwards Nominees (`https://www.awwwards.com/websites/nominees/`), Dribbble (`https://dribbble.com/tags/web-design`), Mobbin (`https://mobbin.com/discover/apps/web/latest`):** Inspirasi *full-bleed photo fade*, tipografi langsung di atas visual, ilustrasi editorial, dan transisi halaman dinamis.

---

## Aturan Khusus Visual & Motion dari User
1. **Hindari Em Dash:** Dilarang menampilkan tanda em dash di seluruh salinan UI, judul, dan dokumentasi. Gunakan titik, koma, titik dua, atau titik tengah (`·`).
2. **Full Foto + Fade + Teks Langsung (Tanpa Card):** Bagian hero, transisi profil, galeri dokumentasi, dan panel kiri login menggunakan foto asli `static/images/hero/` penuh melebar dengan gradient fade lembut dan teks diletakkan langsung di atas area fade (tidak dikotakkan dalam card).
3. **Tambah Ilustrasi Editorial:** Gunakan ilustrasi vektor bersih untuk memperjelas fitur (misalnya alur belajar, jadwal bebas bentrok, rapor anak, dan state kosong/error).
4. **Animasi & Transisi Halaman Dinamis (`scroll-craft`):**
   - Transisi perpindahan halaman terasa hidup: tirai membuka (*curtain reveal*), geser horizontal (*slide left/right*), dan *cross-dissolve*.
   - Setiap bagian *landing page* memiliki ritme animasi scroll berbeda (`scroll-craft`), hanya memakai `transform`, `opacity`, dan `clip-path`, serta tetap rapi saat `prefers-reduced-motion` aktif.

---

## Palet Warna Resmi
- **Primary (`#0093D6` Cerulean Sky Blue):** `#0072A8` (kontras teks/hover), `#EBF7FD` (tint), `#BAE4F8` (border halus), `#083A54` (deep sky untuk scrim fade).
- **Secondary (`#A66B37` Warm Caramel):** `#8A5629` (hover), `#FAF3EC` (warm linen), `#EBD8C5` (border hangat).
- **Tertiary:** Charcoal Ink `#111827`, Body `#374151`, Muted `#6B7280`, Warm Alabaster `#F7F7F5`, Pure White `#FFFFFF`, Hairline `#E5E7EB`, Sage `#15803D`/`#ECFDF5`, Crimson `#B91C1C`/`#FEF2F2`.
