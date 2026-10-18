<!-- translated-from: README.md sha256:ca164a476512 -->
<div align="center">

<img src="../../../dashboard/logo.svg" width="88" alt="Joyce OS Logo">

# Joyce OS

### IA agêntica com cérebro trocável + Second Brain - roda no modelo que você quiser (Claude Code, ChatGPT/Codex, Antigravity CLI, OpenRouter, OpenAI, Gemini, Anthropic API, Groq, Ollama), com voz, grafo de conhecimento e fica mais inteligente a cada dia.

<!-- flags:start -->
<p align="center">
<b>🌐 Disponível em 12 idiomas</b><br><br>
<a href="../../../README.en.md"><img src="../../assets/flags/gb.svg" width="30" alt="English" title="English"></a>
<a href="../../../README.md"><img src="../../assets/flags/vn.svg" width="30" alt="Tiếng Việt" title="Tiếng Việt"></a>
<a href="../zh/README.md"><img src="../../assets/flags/cn.svg" width="30" alt="简体中文" title="简体中文"></a>
<a href="../es/README.md"><img src="../../assets/flags/es.svg" width="30" alt="Español" title="Español"></a>
<a href="../ja/README.md"><img src="../../assets/flags/jp.svg" width="30" alt="日本語" title="日本語"></a>
<a href="../hi/README.md"><img src="../../assets/flags/in.svg" width="30" alt="हिन्दी" title="हिन्दी"></a>
<img src="../../assets/flags/br.svg" width="30" alt="Português" title="Português">
<a href="../ko/README.md"><img src="../../assets/flags/kr.svg" width="30" alt="한국어" title="한국어"></a>
<a href="../ru/README.md"><img src="../../assets/flags/ru.svg" width="30" alt="Русский" title="Русский"></a>
<a href="../de/README.md"><img src="../../assets/flags/de.svg" width="30" alt="Deutsch" title="Deutsch"></a>
<a href="../fr/README.md"><img src="../../assets/flags/fr.svg" width="30" alt="Français" title="Français"></a>
<a href="../id/README.md"><img src="../../assets/flags/id.svg" width="30" alt="Bahasa Indonesia" title="Bahasa Indonesia"></a>
</p>
<!-- flags:end -->

[🇬🇧 English](../../../README.en.md) · [🇻🇳 Tiếng Việt](../../../README.md) · [🇨🇳 简体中文](../zh/README.md) · [🇪🇸 Español](../es/README.md) · [🇯🇵 日本語](../ja/README.md) · [🇮🇳 हिन्दी](../hi/README.md) · 🇧🇷 **Português** · [🇰🇷 한국어](../ko/README.md) · [🇷🇺 Русский](../ru/README.md) · [🇩🇪 Deutsch](../de/README.md) · [🇫🇷 Français](../fr/README.md) · [🇮🇩 Bahasa Indonesia](../id/README.md) · [🌍 Help translate](../../../CONTRIBUTING.en.md)

</div>

> 🌍 Esta é uma tradução automática do README. O Joyce responde no idioma em que você escreve; a interface existe em vietnamita e inglês. Documentação completa em [docs/en](../../../docs/en/README.md). Correções são bem-vindas ([CONTRIBUTING](../../../CONTRIBUTING.en.md)).

## Instalação rápida com a sua própria IA

Passe o link deste repositório ao **Claude Code** ou **Codex** rodando na sua máquina e diga «instala o Joyce OS». Um único comando (`powershell -ExecutionPolicy Bypass -File install.ps1` no Windows, `chmod +x install.sh && ./install.sh` no Linux/macOS) instala Python e dependências, os quatro cérebros CLI por assinatura (`claude`, `codex`, `agy`, `grok`), o `.env`, e sobe o servidor em `http://localhost:7777`. Depois entre em cada cérebro pela página **Models**.

## O que é o Joyce?

Joyce OS não é um chatbot: é uma IA agêntica auto-hospedada na sua máquina ou VPS que lê/escreve arquivos, chama ferramentas (MCP), executa skills, delega trabalho em segundo plano e agenda lembretes, tudo dentro de um dashboard bonito controlável por voz, mais um **Second Brain** (memória + wiki) que acumula conhecimento com o tempo. Dez cérebros prontos: Claude Code, ChatGPT/Codex, Grok Build e Antigravity CLI pela sua assinatura, e OpenRouter, OpenAI, Google Gemini, Anthropic, Groq e Ollama Cloud só com API key. A capacidade mora no Joyce, não no modelo.

## ✨ Recursos em destaque

Destaques: conversa por voz hands-free, grafo de conhecimento que funciona offline, busca de texto completo nas sessões, gestor de arquivos que edita `.md`/`.txt` no navegador, Skills agrupadas e ligáveis, Plugins que adicionam tools nativas a todos os motores com uma pasta Python, Agents com memória própria e Workflows de várias etapas, loops em segundo plano e lembretes, Kanban dirigido por IA, auto-aprendizado após cada conversa (desfazer com um toque), loja de conexões multi-conta (POS, Zalo, Ads, Google Workspace…), canais Telegram e Zalo, geração de imagens com seu plano ChatGPT, página de uso por dia e provedor, backup do brain no GitHub, troca de motor sem perder funções, e segurança com login obrigatório em deploy público e segredos criptografados.

## 🚀 Instalação

Três caminhos: Hostinger Docker Manager (domínio + HTTPS com `DOMAIN_NAME`, `JOYCE_ADMIN_USER`, `JOYCE_ADMIN_PASSWORD`), `docker compose up -d` em qualquer VPS (`http://<ip>:7777`), ou `setup.bat`/`start-joyce.bat` direto no Windows. Em execução pública o Joyce exige login; crie o admin via env e ative 2FA (TOTP) depois.

## 🎬 Configuração inicial

O assistente de primeiro uso conduz: 1) conta admin (obrigatória em público); 2) escolha do cérebro - assinatura pede um login, API key é só colar; 3) escolha do modelo - trocável na página Models sem perder funções; 4) opcionalmente conectar serviços (POS, ads, agenda, Zalo…) para relatórios com dados reais.

## 📖 Guia de uso

A barra lateral organiza **31 páginas** em 7 grupos: Cérebro (grafo/chat/arquivos/auto-aprendizado), Code (terminal real), Capacidades (Agents/Skills/Workflows/Plugins/Chatbot/caixa de entrada), Trabalho (Kanban/tarefas recorrentes), Conexões (loja/canais/Models), Sistema (uso/configurações/mascote/atualização/conta). Índice completo: [docs/README.md](../../../docs/README.md); em inglês, [docs/en/](../../../docs/en/README.md).

## ⚙️ Configuração (`.env`)

Tudo em branco e funciona igual: copie `env.example` para `.env` e adicione o que precisar. Comuns: `JOYCE_HOST`/`JOYCE_PORT` (padrão 127.0.0.1:7777), `JOYCE_REQUIRE_LOGIN`, `JOYCE_ADMIN_USER`/`JOYCE_ADMIN_PASSWORD`, `JOYCE_STATE_DIR`, `BRAINS_DIR`, `JOYCE_ENABLE_USER_PLUGINS`, `TTS_VOICE`. Detalhe por variável em `docs/16-cau-hinh-env.md`.

## 🔐 Segurança

Login obrigatório quando público, rate-limit no login, verificação de Origin contra CSRF, segredos criptografados em `settings.json` com a chave da máquina em `JOYCE_STATE_DIR/.secret_key`, sessões de 30 dias, e plugins de usuário desligados por padrão (`JOYCE_ENABLE_USER_PLUGINS=true` para ligar). Acesso remoto via HTTPS.

## 🔄 Atualização

Depois de um `git push` local o CI constrói a imagem no GHCR; no VPS `./update.sh` puxa e reinicia (dados no volume). A página Atualizar do app tem atualização em um toque e rollback quando o ambiente permite.

## 🌐 Acesso remoto (VPS que não seja Hostinger)

Em VPS fora da Hostinger use Cloudflare Tunnel: `docker compose --profile tunnel up -d` e `docker compose logs tunnel | grep trycloudflare` para obter `https://xxx.trycloudflare.com`.

## 🏗️ Arquitetura

O navegador (voz + grafo), Telegram e o MCP do Zalo convergem no FastAPI (`server/`) + MCP Hub (loja de conexões compartilhada por todos os motores) + Second Brain (vault markdown). Backend Python FastAPI puro; frontend HTML/CSS/JS sem framework (`dashboard/`), leve para VPS.

## 🩺 Solução de problemas

Se uma mudança de código não aparece, reinicie o servidor; se a porta está presa, mate o processo antigo; se a Hostinger não baixa a imagem, deixe o pacote GHCR Public; se um cérebro pede login, faça na página Models; imagens antigas cinzas no chat = cache `attachments/` expirado, é o esperado.

## 📂 Estrutura do repositório

`server/` backend, `dashboard/` frontend (`i18n/` um JSON por idioma), `brains/` todos os second brains, `system/` plugins e modelos de conexão embutidos, `tests/`, `docs/` e `docs/en/` documentação, `docker-compose*.yml`, `install.sh`/`update.sh`, `env.example`, `CHANGELOG.md`.

## 🙏 Inspiração e créditos

Obrigado a: Claude Code e Claude Agent SDK (Anthropic), Codex CLI (OpenAI), APIs da OpenRouter/OpenAI/Gemini/Anthropic/Groq, o padrão Model Context Protocol (toda a loja de conexões roda nele), e o padrão Second Brain + Bullet Journal digitalizado.

## 📄 Licença

Código aberto sob licença **MIT** - use, modifique e distribua livremente, mantendo a atribuição. Veja [LICENSE](../../../LICENSE).

## ☕ Apoie o Joyce OS

Joyce OS é grátis e open source; o autor banca sozinho o código e os servidores de teste. Se ele ajuda no seu trabalho ou na sua vida, um pequeno apoio dá mais tempo para corrigir bugs e criar recursos.
