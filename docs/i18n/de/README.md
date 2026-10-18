<!-- translated-from: README.md sha256:ca164a476512 -->
<div align="center">

<img src="../../../dashboard/logo.svg" width="88" alt="Joyce OS Logo">

# Joyce OS

### Agentische KI mit austauschbarem Gehirn + Second Brain - läuft auf dem Modell deiner Wahl (Claude Code, ChatGPT/Codex, Antigravity CLI, OpenRouter, OpenAI, Gemini, Anthropic API, Groq, Ollama), mit Sprache, Wissensgraph und wird jeden Tag schlauer.

<!-- flags:start -->
<p align="center">
<b>🌐 In 12 Sprachen verfügbar</b><br><br>
<a href="../../../README.en.md"><img src="../../assets/flags/gb.svg" width="30" alt="English" title="English"></a>
<a href="../../../README.md"><img src="../../assets/flags/vn.svg" width="30" alt="Tiếng Việt" title="Tiếng Việt"></a>
<a href="../zh/README.md"><img src="../../assets/flags/cn.svg" width="30" alt="简体中文" title="简体中文"></a>
<a href="../es/README.md"><img src="../../assets/flags/es.svg" width="30" alt="Español" title="Español"></a>
<a href="../ja/README.md"><img src="../../assets/flags/jp.svg" width="30" alt="日本語" title="日本語"></a>
<a href="../hi/README.md"><img src="../../assets/flags/in.svg" width="30" alt="हिन्दी" title="हिन्दी"></a>
<a href="../pt-BR/README.md"><img src="../../assets/flags/br.svg" width="30" alt="Português" title="Português"></a>
<a href="../ko/README.md"><img src="../../assets/flags/kr.svg" width="30" alt="한국어" title="한국어"></a>
<a href="../ru/README.md"><img src="../../assets/flags/ru.svg" width="30" alt="Русский" title="Русский"></a>
<img src="../../assets/flags/de.svg" width="30" alt="Deutsch" title="Deutsch">
<a href="../fr/README.md"><img src="../../assets/flags/fr.svg" width="30" alt="Français" title="Français"></a>
<a href="../id/README.md"><img src="../../assets/flags/id.svg" width="30" alt="Bahasa Indonesia" title="Bahasa Indonesia"></a>
</p>
<!-- flags:end -->

[🇬🇧 English](../../../README.en.md) · [🇻🇳 Tiếng Việt](../../../README.md) · [🇨🇳 简体中文](../zh/README.md) · [🇪🇸 Español](../es/README.md) · [🇯🇵 日本語](../ja/README.md) · [🇮🇳 हिन्दी](../hi/README.md) · [🇧🇷 Português](../pt-BR/README.md) · [🇰🇷 한국어](../ko/README.md) · [🇷🇺 Русский](../ru/README.md) · 🇩🇪 **Deutsch** · [🇫🇷 Français](../fr/README.md) · [🇮🇩 Bahasa Indonesia](../id/README.md) · [🌍 Help translate](../../../CONTRIBUTING.en.md)

</div>

> 🌍 Dies ist eine maschinelle Übersetzung der README. Joyce antwortet in der Sprache, in der du schreibst; die Oberfläche gibt es auf Vietnamesisch und Englisch. Vollständige Doku: [docs/en](../../../docs/en/README.md). Korrekturen willkommen ([CONTRIBUTING](../../../CONTRIBUTING.en.md)).

## Schnelle Installation mit deiner eigenen KI

Gib den Link zu diesem Repository an **Claude Code** oder **Codex**, das auf deinem Rechner läuft, und sag „installiere Joyce OS“. Ein einziger Befehl (`powershell -ExecutionPolicy Bypass -File install.ps1` unter Windows, `chmod +x install.sh && ./install.sh` unter Linux/macOS) installiert Python und Abhängigkeiten, die vier Abo-CLI-Gehirne (`claude`, `codex`, `agy`, `grok`), die `.env` und startet den Server auf `http://localhost:7777`. Danach meldest du jedes Gehirn auf der Seite **Models** an.

## Was ist Joyce?

Joyce OS ist kein Chatbot, sondern eine selbst gehostete agentische KI auf deinem Rechner oder VPS: liest und schreibt Dateien, ruft Werkzeuge auf (MCP), führt Skills aus, vergibt Hintergrundarbeit und plant Erinnerungen - alles in einem hübschen, sprachsteuerbaren Dashboard, plus ein **Second Brain** (Gedächtnis + Wiki), das Wissen über die Zeit ansammelt. Zehn einsatzbereite Gehirne: Claude Code, ChatGPT/Codex, Grok Build und Antigravity CLI über dein Abo, und OpenRouter, OpenAI, Google Gemini, Anthropic, Groq sowie Ollama Cloud mit nur einem API-Key. Die Fähigkeit steckt in Joyce, nicht im Modell.

## ✨ Top-Funktionen

Highlights: freihändige Sprachdialoge, offline-fähiger Wissensgraph, Volltextsuche über Gesprächsverläufe, Dateimanager mit direkter `.md`/`.txt`-Bearbeitung, gruppier- und schaltbare Skills, Plugins, die jedem Engine native Tools geben (ein Python-Ordner genügt), Agents mit eigenem Gedächtnis und mehrstufige Workflows, Hintergrund-Loops und Erinnerungen, von KI selbst betriebener Kanban, Selbstlernen nach jedem Gespräch (mit einem Tipp rückgängig), Multi-Account-Verbindungsstore (POS, Zalo, Ads, Google Workspace…), Telegram- und Zalo-Kanäle, Bilderzeugung über dein eingeloggtes ChatGPT-Abo, Verbrauchsseite nach Tag und Anbieter, Zwei-Wege-Backup des Brains zu GitHub, Engine-Wechsel ohne Funktionsverlust, sowie Sicherheit: Login-Pflicht bei öffentlichem Betrieb und verschlüsselte Geheimnisse.

## 🚀 Installation

Drei Wege: Hostinger Docker Manager (Domain + HTTPS via `DOMAIN_NAME`, `JOYCE_ADMIN_USER`, `JOYCE_ADMIN_PASSWORD`), `docker compose up -d` auf jedem VPS (`http://<ip>:7777`), oder direkt `setup.bat`/`start-joyce.bat` unter Windows. Bei öffentlichem Betrieb erzwingt Joyce den Login; lege den Admin per env an und aktiviere danach 2FA (TOTP).

## 🎬 Ersteinrichtung

Der Ersteinrichtungs-Assistent führt durch: 1) Admin-Konto (bei öffentlichem Betrieb Pflicht); 2) Gehirn wählen - Abo einmal anmelden, API-Key nur einfügen; 3) Modell wählen - jederzeit auf Models wechselbar, ohne Funktionsverlust; 4) optional Verbindungen einrichten (POS, Ads, Kalender, Zalo…) für Berichte mit echten Zahlen.

## 📖 Bedienungsanleitung

Die linke Navigation fasst **31 Seiten** in 7 Gruppen: Gehirn (Graph/Chat/Dateien/Selbstlernen), Code (echtes Terminal), Fähigkeiten (Agents/Skills/Workflows/Plugins/Chatbot/Posteingang), Arbeit (Kanban/wiederkehrende Aufgaben), Verbindungen (Store/Kanäle/Models), System (Verbrauch/Einstellungen/Maskottchen/Update/Konto). Vollständiges Inhaltsverzeichnis: [docs/README.md](../../../docs/README.md); auf Englisch [docs/en/](../../../docs/en/README.md).

## ⚙️ Konfiguration (`.env`)

Alles leer lassen und es läuft trotzdem: `env.example` nach `.env` kopieren und hinzufügen, was nötig ist. Wichtig: `JOYCE_HOST`/`JOYCE_PORT` (Standard 127.0.0.1:7777), `JOYCE_REQUIRE_LOGIN`, `JOYCE_ADMIN_USER`/`JOYCE_ADMIN_PASSWORD`, `JOYCE_STATE_DIR`, `BRAINS_DIR`, `JOYCE_ENABLE_USER_PLUGINS`, `TTS_VOICE`. Jede Variable erklärt unter `docs/16-cau-hinh-env.md`.

## 🔐 Sicherheit

Login-Pflicht bei öffentlichem Betrieb, Rate-Limit beim Login, Origin-Prüfung gegen CSRF, in `settings.json` verschlüsselte Geheimnisse mit dem Maschinenschlüssel aus `JOYCE_STATE_DIR/.secret_key`, 30-Tage-Sessions, und vom Nutzer installierte Plugins sind standardmäßig aus (`JOYCE_ENABLE_USER_PLUGINS=true` zum Anschalten). Fernzugriff bitte über HTTPS.

## 🔄 Aktualisierung

Nach einem lokalen `git push` baut CI das neue Image auf GHCR; auf dem VPS holt `./update.sh` es und startet neu (Daten bleiben im Volume). Die Update-Seite der App bietet Ein-Klick-Update und Rollback, wo die Umgebung es erlaubt.

## 🌐 Fernzugriff (VPS, nicht Hostinger)

Auf einem VPS außerhalb Hostingers nutze Cloudflare Tunnel: `docker compose --profile tunnel up -d`, dann `docker compose logs tunnel | grep trycloudflare` für `https://xxx.trycloudflare.com`.

## 🏗️ Architektur

Browser (Sprache + Graph), Telegram und der Zalo-MCP laufen in FastAPI (`server/`) + MCP Hub (der von allen Engines geteilte Verbindungsstore) + Second Brain (Markdown-Vault) zusammen. Backend ist reines Python-FastAPI; Frontend frameworkloses HTML/CSS/JS (`dashboard/`), leicht für VPS.

## 🩺 Fehlerbehebung

Zeigt eine Code-Änderung keine Wirkung, Server neu starten; Port belegt, alten Prozess beenden; Hostinger kann das Image nicht ziehen, GHCR-Paket auf Public stellen; meldet ein Gehirn fehlenden Login, auf der Models-Seite anmelden; graue alte Bilder im Chat sind abgelaufener `attachments/`-Cache, das ist Absicht.

## 📂 Repository-Aufbau

`server/` Backend, `dashboard/` Frontend (`i18n/` ein JSON-Wörterbuch je Sprache), `brains/` alle Second Brains, `system/` gebündelte Plugins und Verbindungsvorlagen, `tests/`, `docs/` und `docs/en/` Dokumentation, `docker-compose*.yml`, `install.sh`/`update.sh`, `env.example`, `CHANGELOG.md`.

## 🙏 Inspiration & Danksagung

Dank an: Claude Code und Claude Agent SDK (Anthropic), Codex CLI (OpenAI), die APIs von OpenRouter/OpenAI/Gemini/Anthropic/Groq, den Model-Context-Protocol-Standard (darauf läuft der ganze Verbindungsstore), und das Muster Second Brain + digitalisiertes Bullet Journal.

## 📄 Lizenz

Open Source unter der **MIT**-Lizenz - frei nutzen, ändern und weitergeben, nur die Namensnennung behalten. Siehe [LICENSE](../../../LICENSE).

## ☕ Unterstütze Joyce OS

Joyce OS ist kostenlos und open source; der Autor trägt Code und Testserver allein. Wenn Joyce bei Arbeit oder Alltag hilft, gibt eine kleine Unterstützung mehr Zeit für Bugfixes und neue Funktionen.
