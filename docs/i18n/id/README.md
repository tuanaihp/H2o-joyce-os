<!-- translated-from: README.md sha256:ca164a476512 -->
<div align="center">

<img src="../../../dashboard/logo.svg" width="88" alt="Joyce OS Logo">

# Joyce OS

### AI agentic dengan otak yang bisa diganti + Second Brain - berjalan di model pilihanmu (Claude Code, ChatGPT/Codex, Antigravity CLI, OpenRouter, OpenAI, Gemini, Anthropic API, Groq, Ollama), dengan suara, grafik pengetahuan, dan makin pintar tiap hari.

<!-- flags:start -->
<p align="center">
<b>🌐 Tersedia dalam 12 bahasa</b><br><br>
<a href="../../../README.en.md"><img src="../../assets/flags/gb.svg" width="30" alt="English" title="English"></a>
<a href="../../../README.md"><img src="../../assets/flags/vn.svg" width="30" alt="Tiếng Việt" title="Tiếng Việt"></a>
<a href="../zh/README.md"><img src="../../assets/flags/cn.svg" width="30" alt="简体中文" title="简体中文"></a>
<a href="../es/README.md"><img src="../../assets/flags/es.svg" width="30" alt="Español" title="Español"></a>
<a href="../ja/README.md"><img src="../../assets/flags/jp.svg" width="30" alt="日本語" title="日本語"></a>
<a href="../hi/README.md"><img src="../../assets/flags/in.svg" width="30" alt="हिन्दी" title="हिन्दी"></a>
<a href="../pt-BR/README.md"><img src="../../assets/flags/br.svg" width="30" alt="Português" title="Português"></a>
<a href="../ko/README.md"><img src="../../assets/flags/kr.svg" width="30" alt="한국어" title="한국어"></a>
<a href="../ru/README.md"><img src="../../assets/flags/ru.svg" width="30" alt="Русский" title="Русский"></a>
<a href="../de/README.md"><img src="../../assets/flags/de.svg" width="30" alt="Deutsch" title="Deutsch"></a>
<a href="../fr/README.md"><img src="../../assets/flags/fr.svg" width="30" alt="Français" title="Français"></a>
<img src="../../assets/flags/id.svg" width="30" alt="Bahasa Indonesia" title="Bahasa Indonesia">
</p>
<!-- flags:end -->

[🇬🇧 English](../../../README.en.md) · [🇻🇳 Tiếng Việt](../../../README.md) · [🇨🇳 简体中文](../zh/README.md) · [🇪🇸 Español](../es/README.md) · [🇯🇵 日本語](../ja/README.md) · [🇮🇳 हिन्दी](../hi/README.md) · [🇧🇷 Português](../pt-BR/README.md) · [🇰🇷 한국어](../ko/README.md) · [🇷🇺 Русский](../ru/README.md) · [🇩🇪 Deutsch](../de/README.md) · [🇫🇷 Français](../fr/README.md) · 🇮🇩 **Bahasa Indonesia** · [🌍 Help translate](../../../CONTRIBUTING.en.md)

</div>

> 🌍 Ini adalah terjemahan mesin dari README. Joyce menjawab dalam bahasa yang kamu tulis; antarmuka tersedia dalam bahasa Vietnam dan Inggris. Dokumentasi lengkap: [docs/en](../../../docs/en/README.md). Koreksi dipersilakan ([CONTRIBUTING](../../../CONTRIBUTING.en.md)).

## Instalasi cepat dengan AI milikmu

Berikan tautan repo ini ke **Claude Code** atau **Codex** yang berjalan di mesinmu dan bilang «install Joyce OS». Satu perintah (`powershell -ExecutionPolicy Bypass -File install.ps1` di Windows, `chmod +x install.sh && ./install.sh` di Linux/macOS) memasang Python dan dependensi, empat otak CLI berbasis langganan (`claude`, `codex`, `agy`, `grok`), `.env`, lalu menyalakan server di `http://localhost:7777`. Setelah itu masuk ke tiap otak dari halaman **Models**.

## Apa itu Joyce?

Joyce OS bukan chatbot: ia AI agentic self-hosted di mesin atau VPS-mu yang membaca/menulis file, memanggil tool (MCP), menjalankan skill, mendelegasikan pekerjaan latar belakang, dan menjadwalkan pengingat - semua dalam dashboard cantik yang bisa dikendalikan suara, plus **Second Brain** (memori + wiki) yang menumpuk pengetahuan. Sepuluh otak siap pakai: Claude Code, ChatGPT/Codex, Grok Build, dan Antigravity CLI lewat langgananmu, serta OpenRouter, OpenAI, Google Gemini, Anthropic, Groq, dan Ollama Cloud cukup dengan API key. Kemampuan ada di Joyce, bukan di model.

## ✨ Fitur unggulan

Sorotan: obrolan suara hands-free, grafik pengetahuan yang jalan offline, pencarian teks penuh sesi, manajer file yang mengedit `.md`/`.txt` langsung di browser, Skills bergrup dan bisa dinyala-matikan, Plugins yang menambah tool native untuk semua engine (cukup satu folder Python), Agents ber-memori sendiri dan Workflows multi-langkah, loop latar belakang dan pengingat, Kanban yang dijalankan AI, belajar mandiri tiap percakapan (urungkan satu ketukan), toko koneksi multi-akun (POS, Zalo, Ads, Google Workspace…), kanal Telegram dan Zalo, pembuatan gambar dengan langganan ChatGPT-mu, halaman pemakaian per hari per provider, backup brain dua arah ke GitHub, ganti engine tanpa kehilangan fitur, dan keamanan: login wajib saat jalan publik serta secret terenkripsi.

## 🚀 Instalasi

Tiga jalan: Hostinger Docker Manager (domain + HTTPS lewat `DOMAIN_NAME`, `JOYCE_ADMIN_USER`, `JOYCE_ADMIN_PASSWORD`), `docker compose up -d` di VPS mana pun (`http://<ip>:7777`), atau langsung `setup.bat`/`start-joyce.bat` di Windows. Saat berjalan publik Joyce mewajibkan login; buat admin lewat env lalu nyalakan 2FA (TOTP).

## 🎬 Pengaturan pertama

Wizard pertama kali memandu: 1) akun admin (wajib jika publik); 2) pilih otak - langganan cukup login sekali, API key tinggal tempel; 3) pilih model - bisa diganti di Models tanpa kehilangan fitur; 4) opsional sambungkan koneksi (POS, iklan, kalender, Zalo…) agar laporan memakai angka asli.

## 📖 Panduan penggunaan

Navigasi kiri merangkum **31 halaman** dalam 7 grup: Otak (grafik/chat/file/belajar mandiri), Code (terminal asli), Kemampuan (Agents/Skills/Workflows/Plugins/Chatbot/kotak masuk), Pekerjaan (Kanban/tugas berulang), Koneksi (toko/kanal/Models), Sistem (pemakaian/pengaturan/maskot/pembaruan/akun). Daftar isi lengkap: [docs/README.md](../../../docs/README.md); dalam bahasa Inggris, [docs/en/](../../../docs/en/README.md).

## ⚙️ Konfigurasi (`.env`)

Biarkan kosong pun tetap jalan: salin `env.example` ke `.env` lalu tambah yang perlu. Umum: `JOYCE_HOST`/`JOYCE_PORT` (bawaan 127.0.0.1:7777), `JOYCE_REQUIRE_LOGIN`, `JOYCE_ADMIN_USER`/`JOYCE_ADMIN_PASSWORD`, `JOYCE_STATE_DIR`, `BRAINS_DIR`, `JOYCE_ENABLE_USER_PLUGINS`, `TTS_VOICE`. Rincian tiap variabel di `docs/16-cau-hinh-env.md`.

## 🔐 Keamanan

Login wajib saat publik, rate-limit pada login, verifikasi Origin anti-CSRF, secret terenkripsi di `settings.json` dengan kunci mesin di `JOYCE_STATE_DIR/.secret_key`, sesi kedaluwarsa 30 hari, dan plugin pasangan pengguna nonaktif bawaan (`JOYCE_ENABLE_USER_PLUGINS=true` untuk mengaktifkan). Akses jarak jauh lewat HTTPS.

## 🔄 Pembaruan

Setelah `git push` lokal, CI membangun image baru ke GHCR; di VPS `./update.sh` menarik dan me-restart (data aman di volume). Halaman Pembaruan di app menyediakan update satu klik dan rollback bila lingkungan mendukung.

## 🌐 Akses jarak jauh (VPS selain Hostinger)

Di VPS selain Hostinger pakai Cloudflare Tunnel: `docker compose --profile tunnel up -d` lalu `docker compose logs tunnel | grep trycloudflare` untuk mengambil `https://xxx.trycloudflare.com`.

## 🏗️ Arsitektur

Browser (suara + grafik), Telegram, dan Zalo MCP bertemu di FastAPI (`server/`) + MCP Hub (toko koneksi bersama semua engine) + Second Brain (vault markdown). Backend Python FastAPI murni; frontend HTML/CSS/JS tanpa framework (`dashboard/`), ringan untuk VPS.

## 🩺 Pemecahan masalah

Perubahan kode tidak terlihat: restart server. Port terpakai: hentikan proses lama. Hostinger tidak bisa menarik image: jadikan package GHCR Public. Otak minta login: login di halaman Models. Gambar lama abu-abu di chat = cache `attachments/` kedaluwarsa, memang begitu.

## 📂 Struktur repositori

`server/` backend, `dashboard/` frontend (`i18n/` satu JSON per bahasa), `brains/` semua second brain, `system/` plugin dan templat koneksi bawaan, `tests/`, `docs/` dan `docs/en/` dokumentasi, `docker-compose*.yml`, `install.sh`/`update.sh`, `env.example`, `CHANGELOG.md`.

## 🙏 Inspirasi & penghargaan

Terima kasih kepada: Claude Code dan Claude Agent SDK (Anthropic), Codex CLI (OpenAI), API OpenRouter/OpenAI/Gemini/Anthropic/Groq, standar Model Context Protocol (seluruh toko koneksi berjalan di atasnya), dan pola Second Brain + Bullet Journal digital.

## 📄 Lisensi

Open source berlisensi **MIT** - bebas dipakai, diubah, dan disebarluaskan, cukup pertahankan atribusi. Lihat [LICENSE](../../../LICENSE).

## ☕ Dukung Joyce OS

Joyce OS gratis dan open source; penulisnya seorang diri menanggung kode dan biaya server uji. Kalau Joyce membantu kerja atau hidupmu, dukungan kecil memberi lebih banyak waktu untuk memperbaiki bug dan menulis fitur baru.
