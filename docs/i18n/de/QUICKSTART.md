<!-- translated-from: QUICKSTART.en.md sha256:2df57e012e22 -->
# Joyce OS - Quick start

*[English](../../../QUICKSTART.en.md) · [Tiếng Việt](../../../QUICKSTART.md) · [简体中文](../zh/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [日本語](../ja/QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Português](../pt-BR/QUICKSTART.md) · [한국어](../ko/QUICKSTART.md) · [Русский](../ru/QUICKSTART.md) · **Deutsch** · [Français](../fr/QUICKSTART.md) · [Bahasa Indonesia](../id/QUICKSTART.md)*

## Option 1 - Hostinger VPS (Docker Manager, ein Klick)

hPanel → VPS → **Docker Manager** → **Compose** → **Compose from URL**, füge die mitgelieferte `docker-compose.hostinger.yml` ein; für HTTPS mit Domain setze `DOMAIN_NAME=joyce.<vps-hostname>.hstgr.cloud` in **Environment**. **Deploy**, 1-3 Minuten warten, App öffnen. Beim ersten Start wirst du gebeten, ein Admin-Konto anzulegen und einmal Claude Code im Container-Terminal anzumelden: `claude auth login --claudeai`. Update: **Redeploy** im Docker Manager.

## Option 2 - Docker auf beliebiger Maschine oder VPS

Auf jeder Maschine mit Docker: `docker compose -f docker-compose.yml up -d`, öffne http://localhost:7777. Für automatisches HTTPS per Caddy `-f docker-compose.https.yml` dazu.

## Option 3 - Direkt ausführen (Windows, ohne Docker)

Installiere Python 3.12 + Node 22, führe einmal `setup.bat` im Projektordner aus (erstellt .venv, installiert Abhängigkeiten und die zwei CLI-Engines), dann `start-joyce.bat` im Hintergrund (`stop-joyce.bat` zum Stoppen), öffne http://localhost:7777.

## Wenn es läuft

Wähle Engine/Modell auf **Models**; verdrahte Verbindungen in **Connections** (POS, Ads, Kalender, Zalo…) für Berichte mit echten Zahlen; sichere das Brain zu GitHub; beobachte Token-Ausgaben auf **Usage**.

## Vollständige Dokumentation

Siehe [docs/README.md](../../../docs/README.md) - eine Anleitung pro Funktion; englische Übersetzungen in [docs/en/](../../../docs/en/README.md).

## Häufige Probleme

Dass der In-App-Update-Button auf Hostinger nichts tut, ist Absicht - nutze **Redeploy** im Docker Manager; meldet ChatGPT/Codex „model not supported“, wähle ein gültiges Codex-Modell auf der Models-Seite; mehr in `docs/17`.
