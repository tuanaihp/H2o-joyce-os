<!-- translated-from: README.md sha256:ca164a476512 -->
<div align="center">

<img src="../../../dashboard/logo.svg" width="88" alt="Joyce OS Logo">

# Joyce OS

### IA agentique à cerveau interchangeable + Second Brain - fonctionne avec le modèle de votre choix (Claude Code, ChatGPT/Codex, Antigravity CLI, OpenRouter, OpenAI, Gemini, Anthropic API, Groq, Ollama), avec voix, graphe de connaissances, et s'améliore chaque jour.

<!-- flags:start -->
<p align="center">
<b>🌐 Disponible en 12 langues</b><br><br>
<a href="../../../README.en.md"><img src="../../assets/flags/gb.svg" width="30" alt="English" title="English"></a>
<a href="../../../README.md"><img src="../../assets/flags/vn.svg" width="30" alt="Tiếng Việt" title="Tiếng Việt"></a>
<a href="../zh/README.md"><img src="../../assets/flags/cn.svg" width="30" alt="简体中文" title="简体中文"></a>
<a href="../es/README.md"><img src="../../assets/flags/es.svg" width="30" alt="Español" title="Español"></a>
<a href="../ja/README.md"><img src="../../assets/flags/jp.svg" width="30" alt="日本語" title="日本語"></a>
<a href="../hi/README.md"><img src="../../assets/flags/in.svg" width="30" alt="हिन्दी" title="हिन्दी"></a>
<a href="../pt-BR/README.md"><img src="../../assets/flags/br.svg" width="30" alt="Português" title="Português"></a>
<a href="../ko/README.md"><img src="../../assets/flags/kr.svg" width="30" alt="한국어" title="한국어"></a>
<a href="../ru/README.md"><img src="../../assets/flags/ru.svg" width="30" alt="Русский" title="Русский"></a>
<a href="../de/README.md"><img src="../../assets/flags/de.svg" width="30" alt="Deutsch" title="Deutsch"></a>
<img src="../../assets/flags/fr.svg" width="30" alt="Français" title="Français">
<a href="../id/README.md"><img src="../../assets/flags/id.svg" width="30" alt="Bahasa Indonesia" title="Bahasa Indonesia"></a>
</p>
<!-- flags:end -->

[🇬🇧 English](../../../README.en.md) · [🇻🇳 Tiếng Việt](../../../README.md) · [🇨🇳 简体中文](../zh/README.md) · [🇪🇸 Español](../es/README.md) · [🇯🇵 日本語](../ja/README.md) · [🇮🇳 हिन्दी](../hi/README.md) · [🇧🇷 Português](../pt-BR/README.md) · [🇰🇷 한국어](../ko/README.md) · [🇷🇺 Русский](../ru/README.md) · [🇩🇪 Deutsch](../de/README.md) · 🇫🇷 **Français** · [🇮🇩 Bahasa Indonesia](../id/README.md) · [🌍 Help translate](../../../CONTRIBUTING.en.md)

</div>

> 🌍 Ceci est une traduction automatique du README. Joyce répond dans la langue dans laquelle vous écrivez ; l'interface existe en vietnamien et en anglais. Documentation complète : [docs/en](../../../docs/en/README.md). Corrections bienvenues ([CONTRIBUTING](../../../CONTRIBUTING.en.md)).

## Installation rapide avec votre propre IA

Donnez le lien de ce dépôt à **Claude Code** ou **Codex** qui tourne sur votre machine et dites « installe Joyce OS ». Une seule commande (`powershell -ExecutionPolicy Bypass -File install.ps1` sous Windows, `chmod +x install.sh && ./install.sh` sous Linux/macOS) installe Python et les dépendances, les quatre cerveaux CLI sur abonnement (`claude`, `codex`, `agy`, `grok`), le `.env`, puis démarre le serveur sur `http://localhost:7777`. Connectez ensuite chaque cerveau depuis la page **Models**.

## Qu'est-ce que Joyce ?

Joyce OS n'est pas un chatbot : c'est une IA agentique auto-hébergée sur votre machine ou VPS qui lit/écrit des fichiers, appelle des outils (MCP), exécute des skills, délègue du travail en arrière-plan et programme des rappels, le tout dans un beau dashboard pilotable à la voix, plus un **Second Brain** (mémoire + wiki) qui accumule la connaissance. Dix cerveaux prêts : Claude Code, ChatGPT/Codex, Grok Build et Antigravity CLI via votre abonnement, et OpenRouter, OpenAI, Google Gemini, Anthropic, Groq et Ollama Cloud avec une simple clé API. La capacité vit dans Joyce, pas dans le modèle.

## ✨ Fonctionnalités principales

Points forts : conversation vocale mains libres, graphe de connaissances utilisable hors ligne, recherche plein texte dans les sessions, gestionnaire de fichiers éditant `.md`/`.txt` dans le navigateur, Skills groupées et commutables, Plugins ajoutant des outils natifs à tous les moteurs (un dossier Python suffit), Agents avec mémoire propre et Workflows multi-étapes, boucles en arrière-plan et rappels, Kanban piloté par l'IA, auto-apprentissage après chaque échange (annulation en un geste), magasin de connexions multi-comptes (POS, Zalo, Ads, Google Workspace…), canaux Telegram et Zalo, génération d'images via votre abonnement ChatGPT, page d'usage par jour et fournisseur, sauvegarde du brain vers GitHub, changement de moteur sans perte de fonctions, et sécurité : login obligatoire en déploiement public et secrets chiffrés.

## 🚀 Installation

Trois voies : Hostinger Docker Manager (domaine + HTTPS via `DOMAIN_NAME`, `JOYCE_ADMIN_USER`, `JOYCE_ADMIN_PASSWORD`), `docker compose up -d` sur tout VPS (`http://<ip>:7777`), ou `setup.bat`/`start-joyce.bat` en direct sous Windows. En exécution publique Joyce impose le login ; créez l'admin via env puis activez la 2FA (TOTP).

## 🎬 Première configuration

L'assistant de première ouverture guide : 1) compte admin (obligatoire en public) ; 2) choix du cerveau - un login pour l'abonnement, une clé à coller sinon ; 3) choix du modèle - modifiable sur Models sans perdre de fonctions ; 4) branchement optionnel des connexions (POS, pubs, agenda, Zalo…) pour des rapports sur données réelles.

## 📖 Guide d'utilisation

La barre latérale regroupe **31 pages** en 7 groupes : Cerveau (graphe/chat/fichiers/auto-apprentissage), Code (vrai terminal), Capacités (Agents/Skills/Workflows/Plugins/Chatbot/boîte de réception), Travail (Kanban/tâches récurrentes), Connexions (magasin/canaux/Models), Système (usage/réglages/mascotte/mise à jour/compte). Sommaire complet : [docs/README.md](../../../docs/README.md) ; en anglais, [docs/en/](../../../docs/en/README.md).

## ⚙️ Configuration (`.env`)

Tout vide et ça tourne quand même : copiez `env.example` en `.env` et ajoutez le nécessaire. Principales variables : `JOYCE_HOST`/`JOYCE_PORT` (127.0.0.1:7777 par défaut), `JOYCE_REQUIRE_LOGIN`, `JOYCE_ADMIN_USER`/`JOYCE_ADMIN_PASSWORD`, `JOYCE_STATE_DIR`, `BRAINS_DIR`, `JOYCE_ENABLE_USER_PLUGINS`, `TTS_VOICE`. Détail de chaque variable dans `docs/16-cau-hinh-env.md`.

## 🔐 Sécurité

Login obligatoire en public, rate-limit sur le login, vérification de l'Origin contre le CSRF, secrets chiffrés dans `settings.json` avec la clé machine de `JOYCE_STATE_DIR/.secret_key`, sessions de 30 jours, et plugins utilisateur désactivés par défaut (`JOYCE_ENABLE_USER_PLUGINS=true` pour les activer). Accès distant en HTTPS.

## 🔄 Mise à jour

Après un `git push` local, la CI construit l'image sur GHCR ; sur le VPS `./update.sh` tire et redémarre (les données restent dans le volume). La page Mise à jour de l'app offre update en un clic et rollback quand l'environnement le permet.

## 🌐 Accès à distance (VPS autre que Hostinger)

Sur un VPS hors Hostinger, utilisez Cloudflare Tunnel : `docker compose --profile tunnel up -d` puis `docker compose logs tunnel | grep trycloudflare` pour obtenir `https://xxx.trycloudflare.com`.

## 🏗️ Architecture

Le navigateur (voix + graphe), Telegram et le MCP Zalo convergent vers FastAPI (`server/`) + MCP Hub (magasin de connexions partagé par tous les moteurs) + Second Brain (vault markdown). Backend en pur Python FastAPI ; frontend HTML/CSS/JS sans framework (`dashboard/`), léger pour un VPS.

## 🩺 Dépannage

Un changement de code n'apparaît pas : redémarrez le serveur. Port occupé : tuez l'ancien processus. Hostinger ne récupère pas l'image : passez le package GHCR en Public. Un cerveau demande le login : faites-le sur la page Models. Cadres gris pour les vieilles images : le cache `attachments/` a expiré, c'est voulu.

## 📂 Structure du dépôt

`server/` backend, `dashboard/` frontend (`i18n/` un dictionnaire JSON par langue), `brains/` tous les second brains, `system/` plugins et modèles de connexion fournis, `tests/`, `docs/` et `docs/en/` documentation, `docker-compose*.yml`, `install.sh`/`update.sh`, `env.example`, `CHANGELOG.md`.

## 🙏 Inspiration et remerciements

Merci à : Claude Code et Claude Agent SDK (Anthropic), Codex CLI (OpenAI), les API d'OpenRouter/OpenAI/Gemini/Anthropic/Groq, le standard Model Context Protocol (tout le magasin de connexions s'appuie dessus), et le motif Second Brain + Bullet Journal numérisé.

## 📄 Licence

Open source sous licence **MIT** - utilisez, modifiez et redistribuez librement, en gardant l'attribution. Voir [LICENSE](../../../LICENSE).

## ☕ Soutenir Joyce OS

Joyce OS est gratuit et open source ; son auteur assume seul le code et les serveurs de test. Si Joyce vous aide dans votre travail ou votre vie, un petit soutien lui donne plus de temps pour corriger des bugs et écrire de nouvelles fonctions.
