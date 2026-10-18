<!-- translated-from: QUICKSTART.en.md sha256:2df57e012e22 -->
# Joyce OS - Quick start

*[English](../../../QUICKSTART.en.md) · [Tiếng Việt](../../../QUICKSTART.md) · [简体中文](../zh/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [日本語](../ja/QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Português](../pt-BR/QUICKSTART.md) · [한국어](../ko/QUICKSTART.md) · **Русский** · [Deutsch](../de/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · [Bahasa Indonesia](../id/QUICKSTART.md)*

## Вариант 1 - Hostinger VPS (Docker Manager, в один клик)

hPanel → VPS → **Docker Manager** → **Compose** → **Compose from URL**, вставьте входящий в поставку `docker-compose.hostinger.yml`; для HTTPS и домена задайте `DOMAIN_NAME=joyce.<vps-hostname>.hstgr.cloud` в **Environment**. **Deploy**, подождите 1-3 минуты, откройте приложение. При первом запуске попросят создать admin-аккаунт и один раз войти в Claude Code в терминале контейнера: `claude auth login --claudeai`. Обновление: **Redeploy** в Docker Manager.

## Вариант 2 - Docker на любой машине или VPS

На любой машине с Docker: `docker compose -f docker-compose.yml up -d`, откройте http://localhost:7777. Для HTTPS через Caddy добавьте `-f docker-compose.https.yml`.

## Вариант 3 - Запуск напрямую (Windows, без Docker)

Установите Python 3.12 + Node 22, один раз запустите `setup.bat` в папке проекта (создаст .venv, поставит зависимости и два CLI-движка), затем `start-joyce.bat` для фонового запуска (`stop-joyce.bat` - остановка), откройте http://localhost:7777.

## После запуска

Выберите движок/модель на **Models**; подключите сервисы в **Connections** (POS, реклама, календарь, Zalo…), чтобы отчёты шли по реальным данным; сделайте бэкап мозга в GitHub; следите за расходом токенов на **Usage**.

## Полная документация

См. [docs/README.md](../../../docs/README.md) - гайд по каждой функции; английские переводы в [docs/en/](../../../docs/en/README.md).

## Частые проблемы

Кнопка обновления в приложении на Hostinger не работает по задумке - используйте **Redeploy** в Docker Manager; если ChatGPT/Codex пишет «model not supported», выберите корректную модель Codex на странице Models; подробнее в `docs/17`.
