<!-- translated-from: QUICKSTART.en.md sha256:2df57e012e22 -->
# Joyce OS - Quick start

*[English](../../../QUICKSTART.en.md) · [Tiếng Việt](../../../QUICKSTART.md) · **简体中文** · [Español](../es/QUICKSTART.md) · [日本語](../ja/QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Português](../pt-BR/QUICKSTART.md) · [한국어](../ko/QUICKSTART.md) · [Русский](../ru/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · [Bahasa Indonesia](../id/QUICKSTART.md)*

## 方式 1 - Hostinger VPS（Docker Manager，一键）

hPanel → VPS → **Docker Manager** → **Compose** → **Compose from URL**，粘贴随包附带的 `docker-compose.hostinger.yml`；如需 HTTPS 和域名，在 **Environment** 中设 `DOMAIN_NAME=joyce.<vps-hostname>.hstgr.cloud`。**Deploy**，等 1-3 分钟，打开应用。首次运行会要求创建 admin 账号，并在容器终端里登录一次 Claude Code：`claude auth login --claudeai`。更新：在 Docker Manager 里点 **Redeploy**。

## 方式 2 - 任意机器或 VPS 上的 Docker

在任意装好 Docker 的机器上运行 `docker compose -f docker-compose.yml up -d`，然后打开 http://localhost:7777。要经 Caddy 自动 HTTPS，加 `-f docker-compose.https.yml`。

## 方式 3 - 直接运行（Windows，不用 Docker）

装 Python 3.12 + Node 22，在项目目录里运行一次 `setup.bat`（建 .venv、装依赖、装两个 CLI 引擎），再用 `start-joyce.bat` 后台运行（`stop-joyce.bat` 停止），打开 http://localhost:7777。

## 运行起来之后

在 **Models** 页选引擎/模型；在 **Connections** 页接连接（POS、广告、日历、Zalo…）让报表跑真实数字；把 brain 备份到 GitHub；在 **Usage** 页盯 token 开销。

## 完整文档

见 [docs/README.md](../../../docs/README.md) - 每个功能一页指南；英文翻译在 [docs/en/](../../../docs/en/README.md)。

## 常见问题

Hostinger 上应用内更新按钮没反应属设计使然 - 用 Docker Manager 的 **Redeploy**；ChatGPT/Codex 报“model not supported”就在 Models 页选合法 Codex 模型；更多见 `docs/17`。
