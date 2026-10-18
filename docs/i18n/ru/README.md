<!-- translated-from: README.md sha256:ca164a476512 -->
<div align="center">

<img src="../../../dashboard/logo.svg" width="88" alt="Joyce OS Logo">

# Joyce OS

### Агентный ИИ со сменным мозгом + Second Brain: работает на любой модели (Claude Code, ChatGPT/Codex, Antigravity CLI, OpenRouter, OpenAI, Gemini, Anthropic API, Groq, Ollama), с голосом, графом знаний и становится умнее каждый день.

<!-- flags:start -->
<p align="center">
<b>🌐 Доступно на 12 языках</b><br><br>
<a href="../../../README.en.md"><img src="../../assets/flags/gb.svg" width="30" alt="English" title="English"></a>
<a href="../../../README.md"><img src="../../assets/flags/vn.svg" width="30" alt="Tiếng Việt" title="Tiếng Việt"></a>
<a href="../zh/README.md"><img src="../../assets/flags/cn.svg" width="30" alt="简体中文" title="简体中文"></a>
<a href="../es/README.md"><img src="../../assets/flags/es.svg" width="30" alt="Español" title="Español"></a>
<a href="../ja/README.md"><img src="../../assets/flags/jp.svg" width="30" alt="日本語" title="日本語"></a>
<a href="../hi/README.md"><img src="../../assets/flags/in.svg" width="30" alt="हिन्दी" title="हिन्दी"></a>
<a href="../pt-BR/README.md"><img src="../../assets/flags/br.svg" width="30" alt="Português" title="Português"></a>
<a href="../ko/README.md"><img src="../../assets/flags/kr.svg" width="30" alt="한국어" title="한국어"></a>
<img src="../../assets/flags/ru.svg" width="30" alt="Русский" title="Русский">
<a href="../de/README.md"><img src="../../assets/flags/de.svg" width="30" alt="Deutsch" title="Deutsch"></a>
<a href="../fr/README.md"><img src="../../assets/flags/fr.svg" width="30" alt="Français" title="Français"></a>
<a href="../id/README.md"><img src="../../assets/flags/id.svg" width="30" alt="Bahasa Indonesia" title="Bahasa Indonesia"></a>
</p>
<!-- flags:end -->

[🇬🇧 English](../../../README.en.md) · [🇻🇳 Tiếng Việt](../../../README.md) · [🇨🇳 简体中文](../zh/README.md) · [🇪🇸 Español](../es/README.md) · [🇯🇵 日本語](../ja/README.md) · [🇮🇳 हिन्दी](../hi/README.md) · [🇧🇷 Português](../pt-BR/README.md) · [🇰🇷 한국어](../ko/README.md) · 🇷🇺 **Русский** · [🇩🇪 Deutsch](../de/README.md) · [🇫🇷 Français](../fr/README.md) · [🇮🇩 Bahasa Indonesia](../id/README.md) · [🌍 Help translate](../../../CONTRIBUTING.en.md)

</div>

> 🌍 Это машинный перевод README. Joyce отвечает на языке, на котором вы пишете; интерфейс доступен на вьетнамском и английском. Полная документация: [docs/en](../../../docs/en/README.md). Правки приветствуются ([CONTRIBUTING](../../../CONTRIBUTING.en.md)).

## Быстрая установка с вашим ИИ

Передайте ссылку на этот репозиторий **Claude Code** или **Codex**, запущенным на вашем компьютере, и скажите «установи Joyce OS». Одна команда (`powershell -ExecutionPolicy Bypass -File install.ps1` в Windows, `chmod +x install.sh && ./install.sh` в Linux/macOS) поставит Python и зависимости, четыре CLI-мозга на подписке (`claude`, `codex`, `agy`, `grok`), `.env`, и поднимет сервер на `http://localhost:7777`. Затем войдите в каждый мозг на странице **Models**.

## Что такое Joyce?

Joyce OS - не чат-бот, а self-hosted агентный ИИ на вашей машине или VPS: читает и пишет файлы, вызывает инструменты (MCP), запускает навыки, ставит фоновые задачи и напоминания - всё в красивом дашборде с голосовым управлением, плюс **Second Brain** (память + wiki), накапливающий знания. Доступно десять мозгов: по подписке Claude Code, ChatGPT/Codex, Grok Build и Antigravity CLI, а также OpenRouter, OpenAI, Google Gemini, Anthropic, Groq и Ollama Cloud - достаточно API-ключа. Способности живут в Joyce, а не в модели.

## ✨ Ключевые возможности

Ключевое: голосовое общение hands-free, офлайн-граф знаний, полнотекстовый поиск по сессиям, файловый менеджер с правкой `.md`/`.txt` в браузере, группируемые отключаемые Skills, Plugins, добавляющие нативные инструменты всем движкам одной папкой Python, Agents с собственной памятью и многошаговые Workflows, фоновые циклы и напоминания, Kanban под управлением ИИ, самообучение после каждого разговора (откат одним нажатием), мультиаккаунтный магазин подключений (POS, Zalo, Ads, Google Workspace…), каналы Telegram и Zalo, генерация картинок на вашем плане ChatGPT, страница расхода по дням и провайдерам, двусторонний бэкап мозга в GitHub, смена движка без потери функций, и безопасность: обязательный вход при публичном запуске и шифрование секретов.

## 🚀 Установка

Три пути: Hostinger Docker Manager (домен + HTTPS через `DOMAIN_NAME`, `JOYCE_ADMIN_USER`, `JOYCE_ADMIN_PASSWORD`), `docker compose up -d` на любом VPS (`http://<ip>:7777`), либо прямой запуск `setup.bat`/`start-joyce.bat` в Windows. При публичном запуске Joyce требует вход; задайте admin через env и затем включите 2FA (TOTP).

## 🎬 Первичная настройка

Мастер первого запуска проведёт по шагам: 1) учётка admin (обязательна при публичном запуске); 2) выбор мозга - по подписке один вход, по API-ключу просто вставить ключ; 3) выбор модели - меняется в Models без потери функций; 4) по желанию подключить сервисы (POS, реклама, календарь, Zalo…), чтобы отчёты строились на реальных данных.

## 📖 Руководство пользователя

Левая навигация собирает **31 страницу** в 7 групп: Мозг (граф/чат/файлы/самообучение), Code (настоящий терминал), Возможности (Agents/Skills/Workflows/Plugins/Chatbot/входящие), Работа (Kanban/периодические задачи), Подключения (магазин/каналы/Models), Система (расход/настройки/маскот/обновление/аккаунт). Полное оглавление: [docs/README.md](../../../docs/README.md); на английском - [docs/en/](../../../docs/en/README.md).

## ⚙️ Конфигурация (`.env`)

Можно оставить всё пустым: скопируйте `env.example` в `.env` и добавьте нужное. Основные переменные: `JOYCE_HOST`/`JOYCE_PORT` (по умолчанию 127.0.0.1:7777), `JOYCE_REQUIRE_LOGIN`, `JOYCE_ADMIN_USER`/`JOYCE_ADMIN_PASSWORD`, `JOYCE_STATE_DIR`, `BRAINS_DIR`, `JOYCE_ENABLE_USER_PLUGINS`, `TTS_VOICE`. Подробно по каждой - `docs/16-cau-hinh-env.md`.

## 🔐 Безопасность

Обязательный вход при публичном запуске, rate-limit на вход, проверка Origin против CSRF, шифрование секретов в `settings.json` машинным ключом из `JOYCE_STATE_DIR/.secret_key`, сессии по 30 дней, пользовательские плагины выключены по умолчанию (`JOYCE_ENABLE_USER_PLUGINS=true` - включить). Удалённый доступ - по HTTPS.

## 🔄 Обновление

После `git push` локально CI собирает образ в GHCR; на VPS `./update.sh` тянет и перезапускает (данные в volume не трогаются). Страница «Обновление» в приложении даёт обновление в один клик и откат там, где среда позволяет.

## 🌐 Удалённый доступ (VPS не на Hostinger)

На VPS вне Hostinger используйте Cloudflare Tunnel: `docker compose --profile tunnel up -d`, затем `docker compose logs tunnel | grep trycloudflare` - получите `https://xxx.trycloudflare.com`.

## 🏗️ Архитектура

Браузер (голос + граф), Telegram и Zalo MCP сходятся в FastAPI (`server/`) + MCP Hub (общий магазин подключений для всех движков) + Second Brain (markdown-хранилище). Бэкенд - чистый Python FastAPI; фронтенд - HTML/CSS/JS без фреймворков (`dashboard/`), лёгкий для VPS.

## 🩺 Устранение неполадок

Изменения кода не видны - перезапустите сервер. Порт занят - завершите старый процесс. Hostinger не тянет образ - сделайте пакет GHCR публичным. Мозг просит вход - войдите на странице Models. Серые рамки вместо старых картинок - истёкший кэш `attachments/`, так задумано.

## 📂 Структура репозитория

`server/` бэкенд, `dashboard/` фронтенд (`i18n/` - по JSON-словарю на язык), `brains/` все second brain, `system/` встроенные плагины и шаблоны подключений, `tests/`, `docs/` и `docs/en/` документация, `docker-compose*.yml`, `install.sh`/`update.sh`, `env.example`, `CHANGELOG.md`.

## 🙏 Вдохновение и благодарности

Благодарности: Claude Code и Claude Agent SDK (Anthropic), Codex CLI (OpenAI), API OpenRouter/OpenAI/Gemini/Anthropic/Groq, стандарт Model Context Protocol (весь магазин подключений работает на нём), и паттерн Second Brain + Bullet Journal.

## 📄 Лицензия

Открытый код по лицензии **MIT** - свободно используйте, меняйте и распространяйте, сохраняя указание авторства. См. [LICENSE](../../../LICENSE).

## ☕ Поддержать Joyce OS

Joyce OS - бесплатный open source; автор в одиночку оплачивает код и тестовые серверы. Если Joyce помогает в работе или жизни, небольшая поддержка даст больше времени на исправление ошибок и новые функции.
