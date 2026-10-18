<!-- translated-from: QUICKSTART.en.md sha256:2df57e012e22 -->
# Joyce OS - Quick start

*[English](../../../QUICKSTART.en.md) · [Tiếng Việt](../../../QUICKSTART.md) · [简体中文](../zh/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [日本語](../ja/QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Português](../pt-BR/QUICKSTART.md) · [한국어](../ko/QUICKSTART.md) · [Русский](../ru/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · **Bahasa Indonesia***

## Opsi 1 - Hostinger VPS (Docker Manager, satu klik)

hPanel → VPS → **Docker Manager** → **Compose** → **Compose from URL**, tempel `docker-compose.hostinger.yml` bawaan; untuk HTTPS + domain set `DOMAIN_NAME=joyce.<vps-hostname>.hstgr.cloud` di **Environment**. **Deploy**, tunggu 1-3 menit, buka app. Pertama kali diminta buat akun admin lalu login Claude Code sekali di terminal kontainer: `claude auth login --claudeai`. Update: **Redeploy** di Docker Manager.

## Opsi 2 - Docker di mesin atau VPS mana pun

Di mesin mana pun dengan Docker: `docker compose -f docker-compose.yml up -d`, buka http://localhost:7777. Untuk HTTPS via Caddy tambahkan `-f docker-compose.https.yml`.

## Opsi 3 - Jalankan langsung (Windows, tanpa Docker)

Pasang Python 3.12 + Node 22, jalankan `setup.bat` sekali di folder proyek (membuat .venv, memasang dependensi dan dua engine CLI), lalu `start-joyce.bat` di latar belakang (`stop-joyce.bat` untuk berhenti), buka http://localhost:7777.

## Setelah berjalan

Pilih engine/model di **Models**; sambungkan koneksi di **Connections** (POS, iklan, kalender, Zalo…) agar laporan memakai angka asli; backup brain ke GitHub; pantau pemakaian token di **Usage**.

## Dokumentasi lengkap

Lihat [docs/README.md](../../../docs/README.md) - panduan per fitur; terjemahan Inggris di [docs/en/](../../../docs/en/README.md).

## Masalah umum

Tombol update in-app yang tidak bereaksi di Hostinger memang disengaja - pakai **Redeploy** di Docker Manager; kalau ChatGPT/Codex bilang "model not supported", pilih model Codex yang valid di halaman Models; selebihnya di `docs/17`.
