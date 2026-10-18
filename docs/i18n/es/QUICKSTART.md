<!-- translated-from: QUICKSTART.en.md sha256:2df57e012e22 -->
# Joyce OS - Quick start

*[English](../../../QUICKSTART.en.md) · [Tiếng Việt](../../../QUICKSTART.md) · [简体中文](../zh/QUICKSTART.md) · **Español** · [日本語](../ja/QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Português](../pt-BR/QUICKSTART.md) · [한국어](../ko/QUICKSTART.md) · [Русский](../ru/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · [Bahasa Indonesia](../id/QUICKSTART.md)*

## Opción 1 - VPS de Hostinger (Docker Manager, un clic)

hPanel → VPS → **Docker Manager** → **Compose** → **Compose from URL**, pega el `docker-compose.hostinger.yml` incluido; para HTTPS con dominio define `DOMAIN_NAME=joyce.<vps-hostname>.hstgr.cloud` en **Environment**. **Deploy**, espera 1-3 minutos y abre la app. La primera vez pide crear la cuenta admin e iniciar sesión en Claude Code una vez en la terminal del contenedor: `claude auth login --claudeai`. Actualizar: **Redeploy** en Docker Manager.

## Opción 2 - Docker en cualquier máquina o VPS

En cualquier máquina con Docker: `docker compose -f docker-compose.yml up -d` y abre http://localhost:7777. Para HTTPS con Caddy añade `-f docker-compose.https.yml`.

## Opción 3 - Ejecutar directamente (Windows, sin Docker)

Instala Python 3.12 + Node 22, ejecuta `setup.bat` una vez en la carpeta del proyecto (crea .venv, instala dependencias y los dos motores CLI), luego `start-joyce.bat` en segundo plano (`stop-joyce.bat` para parar) y abre http://localhost:7777.

## Una vez en marcha

Elige motor/modelo en **Models**; conecta servicios en **Connections** (POS, ads, calendario, Zalo…) para reportes con datos reales; respalda el brain a GitHub; vigila el gasto de tokens en **Usage**.

## Documentación completa

Ver [docs/README.md](../../../docs/README.md) - una guía por función; traducciones al inglés en [docs/en/](../../../docs/en/README.md).

## Problemas comunes

Que el botón de actualizar de la app no haga nada en Hostinger es a propósito: usa **Redeploy** de Docker Manager; si ChatGPT/Codex dice «model not supported» elige un modelo Codex válido en Models; más en `docs/17`.
