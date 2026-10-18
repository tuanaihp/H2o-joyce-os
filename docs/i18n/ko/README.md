<!-- translated-from: README.md sha256:ca164a476512 -->
<div align="center">

<img src="../../../dashboard/logo.svg" width="88" alt="Joyce OS Logo">

# Joyce OS

### 두뇌를 교체할 수 있는 에이전트형 AI + Second Brain - 원하는 모델로 실행 (Claude Code, ChatGPT/Codex, Antigravity CLI, OpenRouter, OpenAI, Gemini, Anthropic API, Groq, Ollama), 음성과 지식 그래프를 갖추고 매일 더 똑똑해집니다.

<!-- flags:start -->
<p align="center">
<b>🌐 12개 언어로 제공</b><br><br>
<a href="../../../README.en.md"><img src="../../assets/flags/gb.svg" width="30" alt="English" title="English"></a>
<a href="../../../README.md"><img src="../../assets/flags/vn.svg" width="30" alt="Tiếng Việt" title="Tiếng Việt"></a>
<a href="../zh/README.md"><img src="../../assets/flags/cn.svg" width="30" alt="简体中文" title="简体中文"></a>
<a href="../es/README.md"><img src="../../assets/flags/es.svg" width="30" alt="Español" title="Español"></a>
<a href="../ja/README.md"><img src="../../assets/flags/jp.svg" width="30" alt="日本語" title="日本語"></a>
<a href="../hi/README.md"><img src="../../assets/flags/in.svg" width="30" alt="हिन्दी" title="हिन्दी"></a>
<a href="../pt-BR/README.md"><img src="../../assets/flags/br.svg" width="30" alt="Português" title="Português"></a>
<img src="../../assets/flags/kr.svg" width="30" alt="한국어" title="한국어">
<a href="../ru/README.md"><img src="../../assets/flags/ru.svg" width="30" alt="Русский" title="Русский"></a>
<a href="../de/README.md"><img src="../../assets/flags/de.svg" width="30" alt="Deutsch" title="Deutsch"></a>
<a href="../fr/README.md"><img src="../../assets/flags/fr.svg" width="30" alt="Français" title="Français"></a>
<a href="../id/README.md"><img src="../../assets/flags/id.svg" width="30" alt="Bahasa Indonesia" title="Bahasa Indonesia"></a>
</p>
<!-- flags:end -->

[🇬🇧 English](../../../README.en.md) · [🇻🇳 Tiếng Việt](../../../README.md) · [🇨🇳 简体中文](../zh/README.md) · [🇪🇸 Español](../es/README.md) · [🇯🇵 日本語](../ja/README.md) · [🇮🇳 हिन्दी](../hi/README.md) · [🇧🇷 Português](../pt-BR/README.md) · 🇰🇷 **한국어** · [🇷🇺 Русский](../ru/README.md) · [🇩🇪 Deutsch](../de/README.md) · [🇫🇷 Français](../fr/README.md) · [🇮🇩 Bahasa Indonesia](../id/README.md) · [🌍 Help translate](../../../CONTRIBUTING.en.md)

</div>

> 🌍 이것은 README의 기계 번역본입니다. Joyce는 당신이 쓰는 언어로 답합니다. 인터페이스는 현재 베트남어와 영어로 제공됩니다. 전체 문서는 [docs/en](../../../docs/en/README.md)에 있습니다. 수정 환영 ([CONTRIBUTING](../../../CONTRIBUTING.en.md)).

## 내 AI로 빠른 설치

이 저장소 링크를 내 컴퓨터에서 실행 중인 **Claude Code**나 **Codex**에 주고 «Joyce OS 설치해줘»라고 하면 끝. 명령 한 줄(Windows: `powershell -ExecutionPolicy Bypass -File install.ps1`, Linux/macOS: `chmod +x install.sh && ./install.sh`)로 Python과 의존성, 구독으로 도는 네 개의 CLI 두뇌(`claude`, `codex`, `agy`, `grok`), `.env`까지 설치하고 `http://localhost:7777`에서 서버를 켭니다. 이후 대시보드 **Models** 페이지에서 각 두뇌에 로그인하면 됩니다.

## Joyce란?

Joyce OS는 챗봇이 아니라 내 컴퓨터/VPS에서 도는 셀프 호스팅 에이전트형 AI입니다. 파일을 읽고 쓰고, 도구(MCP)를 호출하고, 스킬을 실행하고, 백그라운드 작업을 맡기고, 알림을 예약합니다. 이 모든 것을 음성으로 조작하는 대시보드에 담고, 시간이 갈수록 지식이 쌓이는 **Second Brain**(메모리 + wiki)을 갖췄습니다. 사용 가능한 두뇌는 10종: 구독 기반 Claude Code, ChatGPT/Codex, Grok Build, Antigravity CLI와 API 키만 있으면 되는 OpenRouter, OpenAI, Google Gemini, Anthropic, Groq, Ollama Cloud. 능력은 모델이 아니라 Joyce에 있습니다.

## ✨ 주요 기능

주요 기능: 핸즈프리 음성 대화, 오프라인 지식 그래프, 대화 전문 검색, `.md`/`.txt` 직접 편집 파일 관리자, 그룹화/토글 가능한 Skills, 모든 엔진에 네이티브 도구를 더하는 Plugins(Python 폴더 하나), 자체 메모리를 가진 Agents와 다단계 Workflows, 백그라운드 루프와 리마인더, AI 자동 운영 Kanban, 대화마다 이뤄지는 자기학습(한 번에 되돌리기), 멀티 계정 연결 스토어(POS, Zalo, 광고, Google Workspace 등), Telegram·Zalo 채널, 로그인된 ChatGPT 요금제로 이미지 생성, 일별·제공자별 사용량 페이지, GitHub로 두뇌 양방향 백업, 기능 손실 없는 엔진 교체, 공개 실행 시 로그인 강제와 비밀키 암호화.

## 🚀 설치

세 가지 경로: Hostinger Docker Manager(`DOMAIN_NAME`, `JOYCE_ADMIN_USER`, `JOYCE_ADMIN_PASSWORD`로 도메인 + HTTPS), 아무 VPS에서 `docker compose up -d`(`http://<ip>:7777`), 또는 Windows에서 `setup.bat`/`start-joyce.bat` 직접 실행. 공개 실행 시 로그인이 필수이며 env로 admin을 미리 만들고 2FA(TOTP)를 켜세요.

## 🎬 최초 설정

첫 실행 마법사가 안내합니다: 1) admin 계정(공개 시 필수); 2) 두뇌 선택 - 구독은 한 번 로그인, API 키는 붙여넣기만 하면 됨; 3) 모델 선택 - Models 페이지에서 언제든 기능 손실 없이 변경; 4) 선택적으로 연결(POS, 광고, 캘린더, Zalo 등)을 연결하면 실데이터 리포트 시작.

## 📖 사용 가이드

왼쪽 내비가 **31개 페이지**를 7개 그룹으로 묶습니다: 두뇌(그래프/채팅/파일/자기학습), Code(실제 터미널), 능력(Agents/Skills/Workflows/Plugins/Chatbot/수신함), 작업(Kanban/정기 작업), 연결(스토어/채널/Models), 시스템(사용량/설정/마스코트/업데이트/계정). 전체 목차는 [docs/README.md](../../../docs/README.md), 영어판은 [docs/en/](../../../docs/en/README.md).

## ⚙️ 설정 (`.env`)

전부 비워둬도 동작합니다: `env.example`을 `.env`로 복사하고 필요한 변수만 추가하세요. 주요 변수: `JOYCE_HOST`/`JOYCE_PORT`(기본 127.0.0.1:7777), `JOYCE_REQUIRE_LOGIN`, `JOYCE_ADMIN_USER`/`JOYCE_ADMIN_PASSWORD`, `JOYCE_STATE_DIR`, `BRAINS_DIR`, `JOYCE_ENABLE_USER_PLUGINS`, `TTS_VOICE`. 변수별 설명은 `docs/16-cau-hinh-env.md`.

## 🔐 보안

공개 실행 시 로그인 강제, 로그인 시도 레이트 리밋, 쓰기 요청의 Origin 검증으로 CSRF 차단, `settings.json`의 비밀값은 `JOYCE_STATE_DIR/.secret_key`의 기기 키로 암호화, 세션 30일 만료, 사용자 설치 플러그인은 기본 비활성(`JOYCE_ENABLE_USER_PLUGINS=true`로 활성화). 원격 접속은 HTTPS로 하세요.

## 🔄 업데이트

로컬에서 `git push`하면 CI가 GHCR에 새 이미지를 빌드합니다. VPS에서는 `./update.sh`가 풀 후 재시작(데이터는 볼륨에 유지). 앱의 업데이트 페이지는 환경이 허용하면 원클릭 업데이트와 롤백을 제공합니다.

## 🌐 원격 접속 (Hostinger가 아닌 VPS)

Hostinger가 아닌 VPS에서는 Cloudflare Tunnel: `docker compose --profile tunnel up -d` 후 `docker compose logs tunnel | grep trycloudflare`로 `https://xxx.trycloudflare.com` 획득.

## 🏗️ 아키텍처

브라우저(음성 + 그래프), Telegram, Zalo MCP가 FastAPI(`server/`) + MCP Hub(모든 엔진 공용 연결 스토어) + Second Brain(markdown 볼트)로 모입니다. 백엔드는 순수 Python FastAPI, 프론트엔드는 무프레임워크 HTML/CSS/JS(`dashboard/`)로 VPS에서 가볍습니다.

## 🩺 문제 해결

코드 변경이 안 보이면 서버 재시작. 포트가 잡혀 있으면 이전 프로세스 종료. Hostinger가 이미지를 못 가져오면 GHCR 패키지를 Public으로. 두뇌가 로그인을 요구하면 Models 페이지에서 로그인. 옛 대화의 회색 이미지는 `attachments/` 캐시 만료로 정상입니다.

## 📂 저장소 구조

`server/` 백엔드, `dashboard/` 프론트엔드(`i18n/` 언어별 JSON 사전), `brains/` 모든 second brain, `system/` 번들 플러그인과 연결 템플릿, `tests/`, `docs/`·`docs/en/` 문서, `docker-compose*.yml`, `install.sh`/`update.sh`, `env.example`, `CHANGELOG.md`.

## 🙏 영감 및 크레딧

감사: Claude Code와 Claude Agent SDK(Anthropic), Codex CLI(OpenAI), OpenRouter/OpenAI/Gemini/Anthropic/Groq API, 연결 스토어 전체의 기반이 되는 Model Context Protocol, 그리고 Second Brain + Bullet Journal 디지털 패턴.

## 📄 라이선스

**MIT** 라이선스 오픈소스 - 자유롭게 사용·수정·배포 가능, 저작자 표기만 유지하면 됩니다. [LICENSE](../../../LICENSE) 참조.

## ☕ Joyce OS 후원

Joyce OS는 무료 오픈소스이며 개발자 한 명이 코드와 테스트 서버 비용을 부담합니다. 일이나 생활에 도움이 된다면 소액 후원이 버그 수정과 신기능 개발 시간을 만들어 줍니다.
