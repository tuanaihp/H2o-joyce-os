<!-- translated-from: QUICKSTART.en.md sha256:2df57e012e22 -->
# Joyce OS - Quick start

*[English](../../../QUICKSTART.en.md) · [Tiếng Việt](../../../QUICKSTART.md) · [简体中文](../zh/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · **日本語** · [हिन्दी](../hi/QUICKSTART.md) · [Português](../pt-BR/QUICKSTART.md) · [한국어](../ko/QUICKSTART.md) · [Русский](../ru/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · [Bahasa Indonesia](../id/QUICKSTART.md)*

## 方法 1 - Hostinger VPS（Docker Manager、ワンクリック）

hPanel → VPS → **Docker Manager** → **Compose** → **Compose from URL** で同梱の `docker-compose.hostinger.yml` を貼り付け。HTTPS + ドメインが必要なら **Environment** に `DOMAIN_NAME=joyce.<vps-hostname>.hstgr.cloud` を設定。**Deploy** して 1-3 分待ち、アプリを開く。初回は admin 作成を求められ、コンテナ端末で一度 Claude Code にログイン: `claude auth login --claudeai`。更新は Docker Manager の **Redeploy**。

## 方法 2 - 任意のマシン/VPS の Docker

Docker のある任意マシンで `docker compose -f docker-compose.yml up -d`、http://localhost:7777 を開く。Caddy で自動 HTTPS にするなら `-f docker-compose.https.yml` を追加。

## 方法 3 - 直接実行（Windows、Docker なし）

Python 3.12 + Node 22 を入れ、プロジェクトフォルダで `setup.bat` を一度実行（.venv 作成、依存関係と 2 つの CLI エンジンを導入）、`start-joyce.bat` でバックグラウンド起動（`stop-joyce.bat` で停止）、http://localhost:7777 を開く。

## 起動したら

**Models** ページでエンジン/モデルを選び、**Connections** で接続（POS、広告、カレンダー、Zalo など）を配線して実データのレポートに。brain は GitHub にバックアップ。**Usage** ページでトークン消費を確認。

## 完全なドキュメント

[docs/README.md](../../../docs/README.md) 参照 - 機能ごとのガイド。英訳は [docs/en/](../../../docs/en/README.md)。

## よくある問題

Hostinger でアプリ内更新ボタンが効かないのは仕様 - Docker Manager の **Redeploy** を使う。ChatGPT/Codex が「model not supported」と言うなら Models ページで有効な Codex モデルを選ぶ。詳しくは `docs/17`。
