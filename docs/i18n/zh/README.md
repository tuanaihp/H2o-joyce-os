<!-- translated-from: README.md sha256:ca164a476512 -->
<div align="center">

<img src="../../../dashboard/logo.svg" width="88" alt="Joyce OS Logo">

# Joyce OS

### 可更换大脑的 agentic AI + Second Brain，使用你想要的任意模型（Claude Code、ChatGPT/Codex、Antigravity CLI、OpenRouter、OpenAI、Gemini、Anthropic API、Groq、Ollama），带语音、知识图谱，并且每天变得更聪明。

<!-- flags:start -->
<p align="center">
<b>🌐 提供 12 种语言</b><br><br>
<a href="../../../README.en.md"><img src="../../assets/flags/gb.svg" width="30" alt="English" title="English"></a>
<a href="../../../README.md"><img src="../../assets/flags/vn.svg" width="30" alt="Tiếng Việt" title="Tiếng Việt"></a>
<img src="../../assets/flags/cn.svg" width="30" alt="简体中文" title="简体中文">
<a href="../es/README.md"><img src="../../assets/flags/es.svg" width="30" alt="Español" title="Español"></a>
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

[🇬🇧 English](../../../README.en.md) · [🇻🇳 Tiếng Việt](../../../README.md) · 🇨🇳 **简体中文** · [🇪🇸 Español](../es/README.md) · [🇯🇵 日本語](../ja/README.md) · [🇮🇳 हिन्दी](../hi/README.md) · [🇧🇷 Português](../pt-BR/README.md) · [🇰🇷 한국어](../ko/README.md) · [🇷🇺 Русский](../ru/README.md) · [🇩🇪 Deutsch](../de/README.md) · [🇫🇷 Français](../fr/README.md) · [🇮🇩 Bahasa Indonesia](../id/README.md) · [🌍 Help translate](../../../CONTRIBUTING.en.md)

</div>

> 🌍 这是 README 的机器翻译版本。Joyce 会用你输入的语言回复；界面目前有越南语和英语。完整文档见英文版 [docs/en](../../../docs/en/README.md)。欢迎指正（[CONTRIBUTING](../../../CONTRIBUTING.en.md)）。

## 用你自己的 AI 快速安装

把本仓库链接发给你机器上正在运行的 **Claude Code** 或 **Codex**，说“帮我装 Joyce OS”。它只需运行一条命令（Windows 用 `powershell -ExecutionPolicy Bypass -File install.ps1`，Linux/macOS 用 `chmod +x install.sh && ./install.sh`），即可装齐 Python 与依赖、四个吃订阅额的 CLI 大脑（`claude`、`codex`、`agy`、`grok`）、`.env`，并在 `http://localhost:7777` 启动服务。之后在仪表盘 **Models** 页逐个登录即可。

## Joyce 是什么？

Joyce OS 不是聊天机器人，而是跑在你机器/VPS 上的自托管 agentic AI：读写文件、调用工具（MCP）、运行技能、派发后台任务、自动定时，全部收进一个可用语音控制的漂亮仪表盘，外加随时间积累知识的 **Second Brain**（记忆 + wiki）。十个可用大脑：订阅制的 Claude Code、ChatGPT/Codex、Grok Build、Antigravity CLI，以及只需 API key 的 OpenRouter、OpenAI、Google Gemini、Anthropic、Groq、Ollama Cloud。能力在 Joyce 而不在模型。

## ✨ 亮点功能

亮点：免提语音对话、离线可用的知识图谱、全文检索的历史会话、可直接编辑 `.md`/`.txt` 的文件管理、分组可开关的 Skills、以文件夹形式投放的 Plugins（给所有引擎加原生工具）、带记忆的角色 Agents 与多步 Workflows、后台循环与定时提醒、AI 自动运行的 Kanban、每轮对话后的自学习（可一键撤销）、多账号连接商店（POS/Zalo/广告/Google Workspace…）、Telegram 与 Zalo 通道、用已登录的 ChatGPT 订阅画图、按天按供应商统计的用量页、脑库到 GitHub 的双向备份、换引擎不丢功能、公网部署强制登录与加密密钥。

## 🚀 安装

三条路径：Hostinger Docker Manager（域名 + HTTPS，设 `DOMAIN_NAME`、`JOYCE_ADMIN_USER`、`JOYCE_ADMIN_PASSWORD`）、任意 VPS 的 `docker compose up -d`（`http://<ip>:7777`）、或直接运行 `setup.bat`/`start-joyce.bat`。公网运行时 Joyce 强制先登录；建议预置 admin 并在之后开启 2FA（TOTP）。

## 🎬 首次设置

首次打开 Joyce 的设置向导会带你完成：1) 创建 admin 账号（公网部署必填）；2) 选择大脑 - 订阅制登录一次即可，API key 只需粘贴；3) 选择模型，随时可在 Models 页更换且不丢功能；4) 可选地接入连接（POS、广告、日历、Zalo…），从此报表都是真实数据。

## 📖 使用指南

左侧导航把 **31 个页面** 归入 7 组：大脑（图谱/聊天/文件/自学习）、Code（真终端）、能力（Agents/Skills/Workflows/Plugins/Chatbot/收件箱）、工作（Kanban/定时任务）、连接（连接商店/通道/Models）、系统（用量/设置/宠物/更新/账号）。完整目录见 [docs/README.md](../../../docs/README.md)，英文版在 [docs/en/](../../../docs/en/README.md)。

## ⚙️ 配置（`.env`）

全部留空也能跑：复制 `env.example` 为 `.env` 再加需要的变量。常用：`JOYCE_HOST`/`JOYCE_PORT`（默认 127.0.0.1:7777）、`JOYCE_REQUIRE_LOGIN`、`JOYCE_ADMIN_USER`/`JOYCE_ADMIN_PASSWORD`、`JOYCE_STATE_DIR`、`BRAINS_DIR`、`JOYCE_ENABLE_USER_PLUGINS`、`TTS_VOICE`。逐条说明见 `docs/16-cau-hinh-env.md`。

## 🔐 安全

公网运行强制登录、登录限流、写请求校验 Origin 防 CSRF、密钥在 `settings.json` 中加密（机器级 key 在 `JOYCE_STATE_DIR/.secret_key`）、30 天会话过期、用户安装的插件默认禁用（需 `JOYCE_ENABLE_USER_PLUGINS=true`）。远程访问请走 HTTPS。

## 🔄 更新

本地改完代码 `git push` 后 CI 自动构建新镜像到 GHCR；VPS 上 `./update.sh` 拉取并重启（数据在 volume 里不丢）。应用内“更新”页有一键更新与回退（取决于环境）。

## 🌐 远程访问（非 Hostinger 的 VPS）

非 Hostinger 的 VPS 用 Cloudflare Tunnel：`docker compose --profile tunnel up -d`，然后 `docker compose logs tunnel | grep trycloudflare` 取回 `https://xxx.trycloudflare.com`。

## 🏗️ 架构

浏览器（语音 + 图谱）、Telegram、Zalo MCP 都汇聚到 FastAPI（`server/`）+ MCP Hub（所有引擎共用连接商店）+ Second Brain（markdown 库）。后端是纯 Python FastAPI，前端是无框架的 HTML/CSS/JS（`dashboard/`），VPS 上很轻。

## 🩺 故障排除

改了代码没生效就重启服务；端口被占先杀旧进程；Hostinger 拉不到镜像就把 GHCR 包设为 Public；大脑提示未登录就去 Models 页登录；旧会话里图片变灰是 `attachments/` 缓存过期，属正常。

## 📂 目录结构

`server/` 后端、`dashboard/` 前端（`i18n/` 每语言一个 JSON 词典）、`brains/` 所有 second brain、`system/` 随包插件与连接模板、`tests/`、`docs/` 与 `docs/en/` 文档、`docker-compose*.yml`、`install.sh`/`update.sh`、`env.example`、`CHANGELOG.md`。

## 🙏 灵感与致谢

致谢：Claude Code 与 Claude Agent SDK（Anthropic）、Codex CLI（OpenAI）、OpenRouter/OpenAI/Gemini/Anthropic/Groq 的 API、Model Context Protocol 标准（全部连接商店基于它）、Second Brain + Bullet Journal 数字化模式。

## 📄 许可证

以 **MIT** 许可证开源 - 自由使用、修改、分发，保留署名即可。见 [LICENSE](../../../LICENSE)。

## ☕ 支持 Joyce OS

Joyce OS 免费开源，作者独自一人承担代码与服务器开销。如果它对你的工作或生活有帮助，欢迎小额支持，让作者有更多时间修 bug、写新功能。
