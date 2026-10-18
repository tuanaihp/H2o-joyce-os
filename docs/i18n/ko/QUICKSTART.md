<!-- translated-from: QUICKSTART.en.md sha256:2df57e012e22 -->
# Joyce OS - Quick start

*[English](../../../QUICKSTART.en.md) · [Tiếng Việt](../../../QUICKSTART.md) · [简体中文](../zh/QUICKSTART.md) · [Español](../es/QUICKSTART.md) · [日本語](../ja/QUICKSTART.md) · [हिन्दी](../hi/QUICKSTART.md) · [Português](../pt-BR/QUICKSTART.md) · **한국어** · [Русский](../ru/QUICKSTART.md) · [Deutsch](../de/QUICKSTART.md) · [Français](../fr/QUICKSTART.md) · [Bahasa Indonesia](../id/QUICKSTART.md)*

## 방법 1 - Hostinger VPS (Docker Manager, 원클릭)

hPanel → VPS → **Docker Manager** → **Compose** → **Compose from URL**, 포함된 `docker-compose.hostinger.yml`을 붙여넣기. HTTPS + 도메인이 필요하면 **Environment**에 `DOMAIN_NAME=joyce.<vps-hostname>.hstgr.cloud` 설정. **Deploy** 후 1-3분 기다려 앱을 연다. 첫 실행에서 admin 생성을 요청하고, 컨테이너 터미널에서 Claude Code에 한 번 로그인: `claude auth login --claudeai`. 업데이트는 Docker Manager의 **Redeploy**.

## 방법 2 - 아무 머신/VPS의 Docker

Docker가 있는 아무 머신에서 `docker compose -f docker-compose.yml up -d`, http://localhost:7777 열기. Caddy로 자동 HTTPS하려면 `-f docker-compose.https.yml` 추가.

## 방법 3 - 직접 실행 (Windows, Docker 없이)

Python 3.12 + Node 22 설치 후 프로젝트 폴더에서 `setup.bat` 한 번 실행(.venv 생성, 의존성과 두 CLI 엔진 설치), `start-joyce.bat`로 백그라운드 실행(`stop-joyce.bat`으로 중지), http://localhost:7777 열기.

## 실행된 후

**Models** 페이지에서 엔진/모델 선택; **Connections**에서 연결(POS, 광고, 캘린더, Zalo 등)을 연결해 실데이터 리포트; brain을 GitHub에 백업; **Usage** 페이지에서 토큰 지출 확인.

## 전체 문서

[docs/README.md](../../../docs/README.md) 참조 - 기능별 가이드; 영문 번역은 [docs/en/](../../../docs/en/README.md).

## 흔한 문제

Hostinger에서 앱 내 업데이트 버튼이 안 먹는 건 의도된 동작 - Docker Manager의 **Redeploy** 사용; ChatGPT/Codex가 "model not supported"라면 Models 페이지에서 유효한 Codex 모델 선택; 더 많은 내용은 `docs/17`.
