<!-- translated-from: QUICKSTART.en.md sha256:2df57e012e22 -->
# Joyce OS - Quick start

*[English](../../../QUICKSTART.en.md) · [Tiếng Việt](../../../QUICKSTART.md) · [简体中文](../zh/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [日本語](../ja/QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · **Português** · [한국어](../ko/QUICKSTART.md) · [Русский](../ru/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · [Bahasa Indonesia](../id/QUICKSTART.md)*

## Opção 1 - VPS Hostinger (Docker Manager, um clique)

hPanel → VPS → **Docker Manager** → **Compose** → **Compose from URL**, cole o `docker-compose.hostinger.yml` incluído; para HTTPS com domínio defina `DOMAIN_NAME=joyce.<vps-hostname>.hstgr.cloud` em **Environment**. **Deploy**, aguarde 1-3 minutos e abra o app. Na primeira vez ele pede para criar a conta admin e logar o Claude Code uma vez no terminal do contêiner: `claude auth login --claudeai`. Atualizar: **Redeploy** no Docker Manager.

## Opção 2 - Docker em qualquer máquina ou VPS

Em qualquer máquina com Docker: `docker compose -f docker-compose.yml up -d` e abra http://localhost:7777. Para HTTPS via Caddy adicione `-f docker-compose.https.yml`.

## Opção 3 - Rodar direto (Windows, sem Docker)

Instale Python 3.12 + Node 22, rode `setup.bat` uma vez na pasta do projeto (cria .venv, instala dependências e os dois motores CLI), depois `start-joyce.bat` em segundo plano (`stop-joyce.bat` para parar) e abra http://localhost:7777.

## Depois de rodando

Escolha motor/modelo em **Models**; conecte serviços em **Connections** (POS, ads, agenda, Zalo…) para relatórios com dados reais; faça backup do brain no GitHub; acompanhe gasto de tokens em **Usage**.

## Documentação completa

Veja [docs/README.md](../../../docs/README.md) - um guia por recurso; traduções em inglês em [docs/en/](../../../docs/en/README.md).

## Problemas comuns

O botão de atualizar do app não fazer nada na Hostinger é proposital - use **Redeploy** do Docker Manager; se ChatGPT/Codex disser «model not supported» escolha um modelo Codex válido na página Models; mais em `docs/17`.
