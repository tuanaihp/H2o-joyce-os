<!-- translated-from: README.md sha256:ca164a476512 -->
<div align="center">

<img src="../../../dashboard/logo.svg" width="88" alt="Joyce OS Logo">

# Joyce OS

### 頭脳を交換できるエージェント型 AI + Second Brain。お好みのモデルで動作（Claude Code、ChatGPT/Codex、Antigravity CLI、OpenRouter、OpenAI、Gemini、Anthropic API、Groq、Ollama）。音声、ナレッジグラフ付きで日々賢くなります。

<!-- flags:start -->
<p align="center">
<b>🌐 12 言語で読めます</b><br><br>
<a href="../../../README.en.md"><img src="../../assets/flags/gb.svg" width="30" alt="English" title="English"></a>
<a href="../../../README.md"><img src="../../assets/flags/vn.svg" width="30" alt="Tiếng Việt" title="Tiếng Việt"></a>
<a href="../zh/README.md"><img src="../../assets/flags/cn.svg" width="30" alt="简体中文" title="简体中文"></a>
<a href="../es/README.md"><img src="../../assets/flags/es.svg" width="30" alt="Español" title="Español"></a>
<img src="../../assets/flags/jp.svg" width="30" alt="日本語" title="日本語">
<a href="../hi/README.md"><img src="../../assets/flags/in.svg" width="30" alt="हिन्दी" title="हिन्दी"></a>
<a href="../pt-BR/README.md"><img src="../../assets/flags/br.svg" width="30" alt="Português" title="Português"></a>
<a href="../ko/README.md"><img src="../../assets/flags/kr.svg" width="30" alt="한국어" title="한국어"></a>
<a href="../ru/README.md"><img src="../../assets/flags/ru.svg" width="30" alt="Русский" title="Русский"></a>
<a href="../de/README.md"><img src="../../assets/flags/de.svg" width="30" alt="Deutsch" title="Deutsch"></a>
<a href="../fr/README.md"><img src="../../assets/flags/fr.svg" width="30" alt="Français" title="Français"></a>
<a href="../id/README.md"><img src="../../assets/flags/id.svg" width="30" alt="Bahasa Indonesia" title="Bahasa Indonesia"></a>
</p>
<!-- flags:end -->

[🇬🇧 English](../../../README.en.md) · [🇻🇳 Tiếng Việt](../../../README.md) · [🇨🇳 简体中文](../zh/README.md) · [🇪🇸 Español](../es/README.md) · 🇯🇵 **日本語** · [🇮🇳 हिन्दी](../hi/README.md) · [🇧🇷 Português](../pt-BR/README.md) · [🇰🇷 한국어](../ko/README.md) · [🇷🇺 Русский](../ru/README.md) · [🇩🇪 Deutsch](../de/README.md) · [🇫🇷 Français](../fr/README.md) · [🇮🇩 Bahasa Indonesia](../id/README.md) · [🌍 Help translate](../../../CONTRIBUTING.en.md)

</div>

> 🌍 これは README の機械翻訳です。Joyce はあなたが書いた言語で応答します。UI は現在ベトナム語と英語です。完全なドキュメントは [docs/en](../../../docs/en/README.md) にあります。修正は歓迎します（[CONTRIBUTING](../../../CONTRIBUTING.en.md)）。

## 自分の AI でクイックインストール

このリポジトリのリンクを自分のマシンで動いている **Claude Code** または **Codex** に渡し「Joyce OS をインストールして」と頼むだけ。1 コマンド（Windows は `powershell -ExecutionPolicy Bypass -File install.ps1`、Linux/macOS は `chmod +x install.sh && ./install.sh`）で Python と依存関係、サブスクを使う 4 つの CLI ブレイン（`claude`、`codex`、`agy`、`grok`）、`.env` が揃い、`http://localhost:7777` で起動します。あとはダッシュボードの **Models** ページで各ブレインにログインするだけです。

## Joyce とは？

Joyce OS はチャットボットではなく、あなたのマシン/VPS 上で動くセルフホスト型エージェント AI です。ファイル読み書き、ツール呼び出し（MCP）、スキル実行、バックグラウンドタスク、リマインダーを、音声操作できる美しいダッシュボードにまとめ、知識が貯まる **Second Brain**（メモリ + wiki）を内蔵。使えるブレインは 10 系統：サブスクの Claude Code・ChatGPT/Codex・Grok Build・Antigravity CLI と、API キーだけの OpenRouter・OpenAI・Google Gemini・Anthropic・Groq・Ollama Cloud。能力はモデルではなく Joyce 側にあります。

## ✨ 主な機能

主な機能：ハンズフリー音声会話、オフラインでも動く知識グラフ、全文検索できる会話履歴、`.md`/`.txt` を直接編集できるファイル管理、グループ化して個別オン/オフできる Skills、全エンジンにネイティブツールを足す Plugins（フォルダを置くだけ）、記憶を持つ Agents と多段 Workflows、バックグラウンドループとリマインダー、AI 自動運転の Kanban、会話ごとの自己学習（ワンタップで取り消し）、複数アカウント対応の接続ストア（POS、Zalo、広告、Google Workspace など）、Telegram と Zalo、ログイン中の ChatGPT プランでの画像生成、日別・プロバイダ別の使用量ページ、ブレインの GitHub 双方向バックアップ、機能を失わないエンジン切替、公開運転時のログイン強制と秘密鍵の暗号化。

## 🚀 インストール

3 つの方法：Hostinger Docker Manager（`DOMAIN_NAME`・`JOYCE_ADMIN_USER`・`JOYCE_ADMIN_PASSWORD` でドメイン + HTTPS）、任意 VPS で `docker compose up -d`（`http://<ip>:7777`）、または Windows で `setup.bat`/`start-joyce.bat` 直接実行。公開運転ではログインが必須。env で admin を事前作成し、その後 2FA（TOTP）を有効に。

## 🎬 初回セットアップ

初回起動のセットアップが案内します：1) admin アカウント作成（公開運転では必須）；2) ブレイン選択 - サブスク系は一度ログイン、API キー系は貼るだけ；3) モデル選択 - Models ページでいつでも機能を失わず変更可；4) 任意で接続（POS、広告、カレンダー、Zalo など）を設定して実データのレポートを開始。

## 📖 使い方ガイド

左ナビは **31 ページ** を 7 グループに集約：ブレイン（グラフ/チャット/ファイル/自己学習）、Code（実ターミナル）、能力（Agents/Skills/Workflows/Plugins/Chatbot/受信箱）、仕事（Kanban/定期タスク）、接続（ストア/チャンネル/Models）、システム（使用量/設定/マスコット/更新/アカウント）。全索引は [docs/README.md](../../../docs/README.md)、英語版は [docs/en/](../../../docs/en/README.md)。

## ⚙️ 設定（`.env`）

空欄のままでも動きます：`env.example` を `.env` にコピーして必要な変数だけ追加。主要変数：`JOYCE_HOST`/`JOYCE_PORT`（既定 127.0.0.1:7777）、`JOYCE_REQUIRE_LOGIN`、`JOYCE_ADMIN_USER`/`JOYCE_ADMIN_PASSWORD`、`JOYCE_STATE_DIR`、`BRAINS_DIR`、`JOYCE_ENABLE_USER_PLUGINS`、`TTS_VOICE`。全変数の説明は `docs/16-cau-hinh-env.md`。

## 🔐 セキュリティ

公開運転でログイン必須、ログイン試行のレート制限、書き込みリクエストの Origin 検証で CSRF 防止、`settings.json` 内の秘密情報は `JOYCE_STATE_DIR/.secret_key` の機械キーで暗号化、セッション 30 日で失効、ユーザー導入プラグインは既定で無効（`JOYCE_ENABLE_USER_PLUGINS=true` で有効化）。外部アクセスは HTTPS で。

## 🔄 アップデート

ローカルで `git push` すると CI が GHCR に新イメージをビルド。VPS では `./update.sh` がプルして再起動（データは volume に残る）。アプリの更新ページでは環境が許せばワンタップ更新とロールバックが可能。

## 🌐 リモートアクセス（Hostinger 以外の VPS）

Hostinger 以外の VPS では Cloudflare Tunnel：`docker compose --profile tunnel up -d` のあと `docker compose logs tunnel | grep trycloudflare` で `https://xxx.trycloudflare.com` を取得。

## 🏗️ アーキテクチャ

ブラウザ（音声 + グラフ）、Telegram、Zalo MCP が FastAPI（`server/`）+ MCP Hub（全エンジン共通の接続ストア）+ Second Brain（markdown ボールト）に集約。バックエンドは純粋な Python FastAPI、フロントはフレームワークなしの HTML/CSS/JS（`dashboard/`）で VPS でも軽快。

## 🩺 トラブルシューティング

コード変更が反映されないときは再起動。ポート占有なら旧プロセスを停止。Hostinger がイメージを取れないときは GHCR パッケージを Public に。ブレインが未ログインなら Models ページでログイン。古い会話の画像が灰色になるのは `attachments/` キャッシュの期限切れで仕様です。

## 📂 リポジトリ構成

`server/` バックエンド、`dashboard/` フロント（`i18n/` は言語ごとの JSON 辞書）、`brains/` 全 second brain、`system/` 同梱プラグインと接続テンプレート、`tests/`、`docs/` と `docs/en/` のドキュメント、`docker-compose*.yml`、`install.sh`/`update.sh`、`env.example`、`CHANGELOG.md`。

## 🙏 クレジット

謝辞：Claude Code と Claude Agent SDK（Anthropic）、Codex CLI（OpenAI）、OpenRouter・OpenAI・Gemini・Anthropic・Groq の各 API、接続ストア全体の基盤である Model Context Protocol、そして Second Brain + Bullet Journal のデジタル化パターン。

## 📄 ライセンス

**MIT** ライセンスのオープンソース - 自由に使用・改変・配布でき、クレジット表記のみ必要。[LICENSE](../../../LICENSE) を参照。

## ☕ Joyce OS を支援

Joyce OS は無料のオープンソースで、作者一人がコードと検証用サーバー費を負っています。仕事や生活の助けになっているなら、少額の支援がバグ修正や新機能の時間を生みます。
