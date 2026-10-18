<!-- translated-from: QUICKSTART.en.md sha256:2df57e012e22 -->
# Joyce OS - Quick start

*[English](../../../QUICKSTART.en.md) · [Tiếng Việt](../../../QUICKSTART.md) · [简体中文](../zh/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [日本語](../ja/QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Português](../pt-BR/QUICKSTART.md) · [한국어](../ko/QUICKSTART.md) · [Русский](../ru/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · **Français** · [Bahasa Indonesia](../id/QUICKSTART.md)*

## Option 1 - VPS Hostinger (Docker Manager, un clic)

hPanel → VPS → **Docker Manager** → **Compose** → **Compose from URL**, collez le `docker-compose.hostinger.yml` fourni ; pour HTTPS avec domaine, définissez `DOMAIN_NAME=joyce.<vps-hostname>.hstgr.cloud` dans **Environment**. **Deploy**, attendez 1-3 minutes, ouvrez l'app. Au premier lancement on vous demande de créer le compte admin puis de connecter Claude Code une fois dans le terminal du conteneur : `claude auth login --claudeai`. Mise à jour : **Redeploy** dans Docker Manager.

## Option 2 - Docker sur n'importe quelle machine ou VPS

Sur toute machine avec Docker : `docker compose -f docker-compose.yml up -d`, ouvrez http://localhost:7777. Pour HTTPS via Caddy ajoutez `-f docker-compose.https.yml`.

## Option 3 - Exécution directe (Windows, sans Docker)

Installez Python 3.12 + Node 22, lancez `setup.bat` une fois dans le dossier du projet (crée .venv, installe les dépendances et les deux moteurs CLI), puis `start-joyce.bat` en arrière-plan (`stop-joyce.bat` pour arrêter), ouvrez http://localhost:7777.

## Une fois lancé

Choisissez moteur/modèle sur **Models** ; branchez les services dans **Connections** (POS, pubs, agenda, Zalo…) pour des rapports sur données réelles ; sauvegardez le brain sur GitHub ; surveillez les dépenses de tokens sur **Usage**.

## Documentation complète

Voir [docs/README.md](../../../docs/README.md) - un guide par fonctionnalité ; traductions anglaises dans [docs/en/](../../../docs/en/README.md).

## Problèmes courants

Le bouton de mise à jour in-app qui ne fait rien sur Hostinger est voulu - utilisez **Redeploy** dans Docker Manager ; si ChatGPT/Codex dit « model not supported », choisissez un modèle Codex valide sur la page Models ; plus dans `docs/17`.
