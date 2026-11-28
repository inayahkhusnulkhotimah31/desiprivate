# Skill : Katalog Skill & MCP Agent yang Terpasang

Seluruh skill di bawah ini terpasang secara global (`C:\Users\lenovo\.gemini\config\skills\` dan `C:\Users\lenovo\.gemini\config\plugins\`) agar tidak membebani ukuran repository Git maupun bundle deploy Vercel.

| Skill / MCP | Lokasi / Sumber | Fungsi Utama untuk DESI PRIVAT |
| :--- | :--- | :--- |
| **`ponytail`** | Global (`~/.gemini/config/skills/ponytail`) | Solusi perubahan terkecil yang tuntas, bersih, dan bebas over-engineering. |
| **`ponytail-audit`** | Global (`~/.gemini/config/skills/ponytail-audit`) | Audit menyeluruh repo untuk bug, celah keamanan, beban skala, tes, dan bloat kode. |
| **`ponytail-review`** | Global (`~/.gemini/config/skills/ponytail-review`) | Review diff dan kode terkait sebelum commit/merge. |
| **`brainstorming`** | Plugin `superpowers` | Eksplorasi ide desain & alur UX sebelum implementasi. |
| **`taste-skill`** | Global (`Leonxlnx/taste-skill`) | Standar art direction, tipografi, dan pencegahan desain generik. |
| **`ui-ux-pro-max`** | Global (`nextlevelbuilder/ui-ux-pro-max-skill`) | Design intelligence lintas platform, palet, dan standar UI/UX anti-slop. |
| **`frontend-design`** | Global (`anthropics/skills`) | Panduan desain frontend berkarakter kuat dan bebas pola generik AI. |
| **`impeccable`** | Global (`pbakaus/impeccable`) | Vocabulary desain (`polish`, `bolder`, `critique`, `audit`) & pengecekan hierarki/kontras. |
| **`scroll-craft`** | Global (`nateherkai/scroll-craft`) | Koreografi scroll landing page, depth planes foto, dan verifikasi motion/reduced-motion. |
| **`archify`** & **`archify-pr`** | Global (`tt-a1i/archify`) | Diagram arsitektur interaktif dan ringkasan perubahan PR. |
| **`scoped-code-ops`** | Global | Menjaga perubahan kode tetap terfokus di area target yang diminta. |
| **`verification-before-completion`** | Plugin `superpowers` | Memastikan tes & pengecekan berjalan tuntas sebelum klaim selesai. |
| **`figcraft` (MCP)** | `~/.gemini/config/mcp_config.json` | Koneksi live (`--attach 7979`) ke aplikasi FigCraft Windows. |
| **`video-analyzer` (MCP)** | `~/.gemini/config/mcp_config.json` (`guimatheus92/mcp-video-analyzer` + `yt-dlp`) | Analisis metadata, transkrip, OCR, dan keyframe video TikTok/YouTube/Instagram. |
