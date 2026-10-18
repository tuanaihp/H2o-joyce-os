<!-- translated-from: README.md sha256:ca164a476512 -->
<div align="center">

<img src="../../../dashboard/logo.svg" width="88" alt="Joyce OS Logo">

# Joyce OS

### IA agéntica con cerebro intercambiable + Second Brain: funciona con el modelo que quieras (Claude Code, ChatGPT/Codex, Antigravity CLI, OpenRouter, OpenAI, Gemini, Anthropic API, Groq, Ollama), con voz, grafo de conocimiento y auto-mejora diaria.

<!-- flags:start -->
<p align="center">
<b>🌐 Disponible en 12 idiomas</b><br><br>
<a href="../../../README.en.md"><img src="../../assets/flags/gb.svg" width="30" alt="English" title="English"></a>
<a href="../../../README.md"><img src="../../assets/flags/vn.svg" width="30" alt="Tiếng Việt" title="Tiếng Việt"></a>
<a href="../zh/README.md"><img src="../../assets/flags/cn.svg" width="30" alt="简体中文" title="简体中文"></a>
<img src="../../assets/flags/es.svg" width="30" alt="Español" title="Español">
<a href="../ja/README.md"><img src="../../assets/flags/jp.svg" width="30" alt="日本語" title="日本語"></a>
<a href="../hi/README.md"><img src="../../assets/flags/in.svg" width="30" alt="हिन्दी" title="हिन्दी"></a>
<a href="../pt-BR/README.md"><img src="../../assets/flags/br.svg" width="30" alt="Português" title="Português"></a>
<a href="../ko/README.md"><img src="../../assets/flags/kr.svg" width="30" alt="한국어" title="한국어"></a>
<a href="../ru/README.md"><img src="../../assets/flags/ru.svg" width="30" alt="Русский" title="Русский"></a>
<a href="../de/README.md"><img src="../../assets/flags/de.svg" width="30" alt="Deutsch" title="Deutsch"></a>
<a href="../fr/README.md"><img src="../../assets/flags/fr.svg" width="30" alt="Français" title="Français"></a>
<a href="../id/README.md"><img src="../../assets/flags/id.svg" width="30" alt="Bahasa Indonesia" title="Bahasa Indonesia"></a>
</p>
<!-- flags:end -->

[🇬🇧 English](../../../README.en.md) · [🇻🇳 Tiếng Việt](../../../README.md) · [🇨🇳 简体中文](../zh/README.md) · 🇪🇸 **Español** · [🇯🇵 日本語](../ja/README.md) · [🇮🇳 हिन्दी](../hi/README.md) · [🇧🇷 Português](../pt-BR/README.md) · [🇰🇷 한국어](../ko/README.md) · [🇷🇺 Русский](../ru/README.md) · [🇩🇪 Deutsch](../de/README.md) · [🇫🇷 Français](../fr/README.md) · [🇮🇩 Bahasa Indonesia](../id/README.md) · [🌍 Help translate](../../../CONTRIBUTING.en.md)

</div>

> 🌍 Esta es una traducción automática del README. Joyce responde en el idioma en que escribes; la interfaz existe en vietnamita e inglés. Documentación completa en [docs/en](../../../docs/en/README.md). Las correcciones son bienvenidas ([CONTRIBUTING](../../../CONTRIBUTING.en.md)).

## Instalación rápida con tu propia IA

Pasa el enlace de este repositorio a **Claude Code** o **Codex** corriendo en tu máquina y di «instala Joyce OS». Basta un comando (`powershell -ExecutionPolicy Bypass -File install.ps1` en Windows, `chmod +x install.sh && ./install.sh` en Linux/macOS) para instalar Python y dependencias, los cuatro cerebros CLI por suscripción (`claude`, `codex`, `agy`, `grok`), el `.env`, y arrancar el servidor en `http://localhost:7777`. Después inicia sesión por cerebro en la página **Models**.

## ¿Qué es Joyce?

Joyce OS no es un chatbot: es una IA agéntica auto-hospedada en tu equipo o VPS que lee/escribe archivos, llama herramientas (MCP), ejecuta skills, delega trabajo en segundo plano y programa recordatorios, todo dentro de un dashboard vistoso controlable por voz, más un **Second Brain** (memoria + wiki) que acumula conocimiento. Diez cerebros listos: Claude Code, ChatGPT/Codex, Grok Build y Antigravity CLI por suscripción, y OpenRouter, OpenAI, Google Gemini, Anthropic, Groq y Ollama Cloud con solo API key. La capacidad vive en Joyce, no en el modelo.

## ✨ Funciones destacadas

Destacados: conversación por voz manos libres, grafo de conocimiento offline, búsqueda de texto completo en sesiones, gestor de archivos con edición `.md`/`.txt`, Skills agrupadas y conmutable, Plugins como carpetas Python que añaden tools nativas a todos los motores, Agents con memoria propia y Workflows de varios pasos, loops en segundo plano y recordatorios, Kanban conducido por IA, auto-aprendizaje tras cada charla (deshacer con un toque), tienda de conexiones multi-cuenta (POS, Zalo, Ads, Google Workspace…), canales Telegram y Zalo, generación de imágenes con tu plan ChatGPT, página de uso por día y proveedor, backup del brain a GitHub, cambio de motor sin perder funciones, y seguridad con login forzado en despliegues públicos y secretos cifrados.

## 🚀 Instalación

Tres caminos: Hostinger Docker Manager (dominio + HTTPS con `DOMAIN_NAME`, `JOYCE_ADMIN_USER`, `JOYCE_ADMIN_PASSWORD`), `docker compose up -d` en cualquier VPS (`http://<ip>:7777`), o `setup.bat`/`start-joyce.bat` directo en Windows. En ejecución pública Joyce exige iniciar sesión; pre-crea el admin por env y luego activa 2FA (TOTP).

## 🎬 Primera configuración

El asistente de primera ejecución te guía por: 1) cuenta admin (obligatoria si es público); 2) elegir cerebro - por suscripción se inicia sesión una vez, con API key basta pegarla; 3) elegir modelo - cambiable en Models sin perder funciones; 4) opcionalmente conectar servicios (POS, ads, calendario, Zalo…) para reportes con datos reales.

## 📖 Guía de uso

La barra lateral agrupa **31 páginas** en 7 grupos: Cerebro (grafo/chat/archivos/auto-aprendizaje), Code (terminal real), Capacidades (Agents/Skills/Workflows/Plugins/Chatbot/bandeja), Trabajo (Kanban/tareas programadas), Conexiones (tienda/canales/Models), Sistema (uso/ajustes/mascota/actualización/cuenta). Índice completo: [docs/README.md](../../../docs/README.md); en inglés, [docs/en/](../../../docs/en/README.md).

## ⚙️ Configuración (`.env`)

Todo vacío y aun así arranca: copia `env.example` a `.env` y añade lo necesario. Comunes: `JOYCE_HOST`/`JOYCE_PORT` (127.0.0.1:7777), `JOYCE_REQUIRE_LOGIN`, `JOYCE_ADMIN_USER`/`JOYCE_ADMIN_PASSWORD`, `JOYCE_STATE_DIR`, `BRAINS_DIR`, `JOYCE_ENABLE_USER_PLUGINS`, `TTS_VOICE`. Detalle por variable en `docs/16-cau-hinh-env.md`.

## 🔐 Seguridad

Login obligatorio al correr en público, rate-limit en el acceso, verificación de Origin contra CSRF, secretos cifrados en `settings.json` con la clave de la máquina en `JOYCE_STATE_DIR/.secret_key`, sesiones de 30 días, y plugins de usuario desactivados por defecto (`JOYCE_ENABLE_USER_PLUGINS=true` para habilitarlos). Usa HTTPS para el acceso remoto.

## 🔄 Actualización

Tras un `git push` local el CI construye la imagen en GHCR; en el VPS `./update.sh` tira y reinicia (los datos viven en el volumen). La página Actualizar de la app tiene actualización con un toque y rollback cuando el entorno lo permite.

## 🌐 Acceso remoto (VPS que no sea Hostinger)

En un VPS fuera de Hostinger usa Cloudflare Tunnel: `docker compose --profile tunnel up -d` y `docker compose logs tunnel | grep trycloudflare` para obtener `https://xxx.trycloudflare.com`.

## 🏗️ Arquitectura

El navegador (voz + grafo), Telegram y el MCP de Zalo confluyen en FastAPI (`server/`) + MCP Hub (tienda de conexiones compartida por todos los motores) + Second Brain (vault markdown). Backend Python FastAPI puro; frontend HTML/CSS/JS sin framework (`dashboard/`), ligero para VPS.

## 🩺 Solución de problemas

Si un cambio de código no aparece, reinicia el servidor; si el puerto está ocupado mata el proceso viejo; si Hostinger no descarga la imagen, pon el paquete GHCR en Public; si un cerebro pide login, hazlo en Models; imágenes antiguas en gris = caché `attachments/` expirada, es normal.

## 📂 Estructura del repositorio

`server/` backend, `dashboard/` frontend (`i18n/` un JSON por idioma), `brains/` todos los second brains, `system/` plugins y plantillas de conexión incluidos, `tests/`, `docs/` y `docs/en/` documentación, `docker-compose*.yml`, `install.sh`/`update.sh`, `env.example`, `CHANGELOG.md`.

## 🙏 Inspiración y créditos

Gracias a: Claude Code y Claude Agent SDK (Anthropic), Codex CLI (OpenAI), las APIs de OpenRouter/OpenAI/Gemini/Anthropic/Groq, el estándar Model Context Protocol (toda la tienda de conexiones lo usa), y el patrón Second Brain + Bullet Journal digitalizado.

## 📄 Licencia

Código abierto bajo licencia **MIT** - úsalo, modifícalo y distribúyelo libremente, conservando la atribución. Ver [LICENSE](../../../LICENSE).

## ☕ Apoya Joyce OS

Joyce OS es gratis y open source; su autor costea solo el código y los servidores de prueba. Si te ayuda en tu trabajo o tu vida, un pequeño apoyo le da más tiempo para corregir errores y crear funciones.
