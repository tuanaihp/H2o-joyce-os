# Phase 0 — Báo cáo khảo sát (Recon Report)

Ngày: 2026-05-20 · Phạm vi: đọc, không sửa code · Nguồn đặc tả: `tai-lieu-update-tu-openai/`

Báo cáo này map codebase Joyce OS hiện tại sang đích của gói nâng cấp "H2O AI Workstation".
**DỪNG ở đây để review** theo quy trình Phase 0 của `DEVIN_MASTER_PROMPT.md`.

---

## 1. Hạ tầng kỹ thuật hiện tại

| Tầng | Hiện trạng | Ghi chú |
|---|---|---|
| Backend | **FastAPI 0.141.1** + Starlette 1.6.0, Python 3.12 (Docker) / 3.14 (máy dev), uvicorn | `server/main.py` = **20.434 dòng** — monolith, các feature bóc ra thành `APIRouter` riêng (tasks, reminders, learn, self_improve, packs, channels, conversations, coding, domain, graph, tools, h2o_gateway) rồi `include_router` tại module level |
| Frontend | **Vanilla JS + Alpine.js 3.14.1** (self-host ở `dashboard/vendor/`), không bundler | ~60 file JS nạp bằng `<script src="?v=N">`, cache-bust bằng tay. i18n hai file `dashboard/i18n/{vi,en}.json` + `window.t()` tự viết. CSS: `style.css` + `console.css` |
| Package manager | `pip` + `requirements.txt` (ghim chặt, có chú thích lý do từng pin). JS: **không có** package.json — test JS chạy thẳng bằng `node` | |
| State / DB | **SQLite**: `kanban.sqlite3` (task), `conversations.db` (hội thoại kênh), `session_brain.db`, `memory_index.db`, `conversation_state.db`, `usage_index.db`, `capability_registry.db`, `runtime.db` — cộng **JSON state** trong `STATE_DIR` (settings.json, mcp_servers.json, h2o_staff.json, h2o_projects.json, reminders.json trong vault…) và **vault Markdown** (`brains/<name>/` + git backup `git_brain.py`) | Không có ORM, không migrations framework — schema tạo tay trong từng store |
| Auth | Cookie `joyce_session` (admin, user+pass hash, TOTP 2FA), cookie `h2o_staff` (nhân viên, SĐT+PIN, throttle brute-force IP), API tokens có scope, bypass localhost cho route agent-local | `web_security.py` + middleware `_auth_guard` ở main.py; Host-header hardening `duong_dan_router` |
| Tenant / RBAC | **Không có multi-tenant thật.** Có: nhiều brain (thư mục riêng), staff ACL theo model (`h2o_staff.models` list) + deny-list route quản trị cho staff. Role nhân viên (6 chức vụ) hiện là **nhãn**, không lái quyền | Đích tới "User Permission ∩ Agent Scope ∩ Source ACL" mới chỉ có 2/4 mảnh |
| Agent runtime | `tasks.py` (Kanban queue + dispatcher riêng, mặc định orchestration=off), `agent_runtime.py`, `workflow_runtime.py`/`workflow_runs.py`, loop trong `self_improve.py`, `reminders.py`, `readonly_orchestrator.py` (chỉ-đọc), `capability_*` (registry/resolver/executor/index — SQLite) | Agent/skill/workflow/loop lưu = **file .md trong vault brain**, không phải DB |
| Model gateway | `model_router.py` (RouterPolicy, cost, admits) + `engine.py` + `model_limits.py` + `model-picker.js`. **10 provider**: anthropic-cli, codex/openai-oauth, grok-cli, antigravity-cli, openrouter, openai, anthropic, gemini, groq, ollama (cloud) + `ollama-local` | Chưa có tầng Nhanh/Cân bằng/Chuyên sâu/Riêng tư trừu tượng cho user thường — user chọn provider:model trực tiếp |
| Connector registry | `mcp_store.py` (mcp_servers.json v2) + `mcp_hub.py` (hub pattern, allow_patterns) + `/connect/*` 19 route (catalog, OAuth, health, audit) + plugin `plugins_host.py` (3 nguồn: bundled/vault/global, gate `JOYCE_ENABLE_*_PLUGINS`) + `packs` | Token connector đã lưu file riêng `*_oauth*/`, có audit log `/connect/audit` |
| Deployment | Dockerfile multi-stage (py3.12 + node22), 6 bản docker-compose (build/hostinger/https/multi/proxy + watchtower), `.bat` Windows (start/stop/autostart/tunnel), `joyce.service` systemd, `update.sh` self-update, watchdog | Cập nhật tự động qua `updater.py` + `update_state.py` |
| Test | `tests/run.py` — **~380 file Python** (tự chạy, không pytest trừ nhóm Adaptive) + **~169 file JS** (node trực tiếp). CI: `.github/workflows/ci.yml` = compileall → import main (bắt vòng import) → mọi test JS → pytest cho nhóm riêng. `test_route_table.py` giữ snapshot 379 route chống bóc-sai | Không có lint/typecheck config (không ruff/mypy/eslint) |

### Route tree (trích snapshot `tests/python/route_table.json`, 379 mục)

```
Auth/Staff   : /auth/* (13) · /staff/login|me|logout · /h2o-staff CRUD (4)
Hội thoại    : /chat, /chat/stream · /sessions/* (19) · /conversations/* (10) · /chatbots/* (14)
             · /inbox (3) · /notifications · /push (4) · WS: /ws, /ws/voice-live, /ws/terminal, /ws/graph
Não/vault    : /files/* (16) · /brains (4) · /browse (2) · /graph · /memory · /vault (2)
             · /export, /import, /ingest-upload, /share/* (5), /s/* (public share)
Việc/tự động : /kanban* (16, router con) · /loop(s) · /reminders* (8) · /workflows/* (8)
             · /learn* (10) · /agents/* (11) · /runtime/* (9) · /viec
Năng lực     : /skills (6) · /plugins (3) · /packs (11) · /slash (3) · /tools (3)
Kết nối      : /connect/* (19) · /mcp/* (9) · /channels (7) · /telegram · /zalo-bot (4)
Model        : /providers · /ollama-local/* (9) · /oauth/openai/* (6) · /claude (6)
             · /grok (5) · /antigravity (2) · /openrouter · /tts, /stt, /voice/* (4)
Dự án/code   : /projects/* (12) · /coding/* (8) · /h2o-projects (4) · /terminal (2)
Hệ thống     : /config · /settings (2) · /update (2) · /backup/* (4) · /usage/* (7)
             · /autostart · /domain (3) · /branding · /health · /changelog · /stop
```

### Rail/nav hiện tại (dashboard/console.js `RAIL_GROUPS`)

```
Bộ não    : Đồ thị (home) · Trò chuyện · Tệp tin · Tự học (learn)
Code      : Terminal · Coding · Projects (dự án code local)
Năng lực  : Không gian (workspace) · Hội thoại · Kỹ năng · Plugin
Việc      : Kanban · Tự cải thiện
Kết nối   : MCP · Gói (packs) · Kênh · Model
Hệ thống  : Cài đặt · Link chia sẻ · Nhân viên · Tài khoản        [ghim đáy]
Ẩn        : chatbots(→tab Hội thoại), usage, pet, logs
```

## 2. CURRENT → TARGET → ACTION

Quy ước ACTION: **KEEP** giữ nguyên · **REFACTOR** sửa tại chỗ · **MERGE** gộp vào cái khác · **HIDE** giấu khỏi nav user thường (vào Admin Lab) · **DEPRECATE** bỏ dần · **NEW** phải làm mới.

| # | Đích (spec) | Hiện có trong Joyce | ACTION | Ghi chú |
|---|---|---|---|---|
| 1 | Trang **Hôm nay** (morning brief, metrics, task, lịch, Pulse, hệ sinh thái) | Không có. Nguyên liệu sẵn: `/kanban` (task), `/reminders` (lịch), `/h2o-projects/check` (sức khoẻ app), `/inbox` (kết quả về), `/usage` | **NEW** | Ráp được ngay từ API thật, chưa cần data plane |
| 2 | Sidebar nhóm: Hôm nay/Công việc/Joyce/Tri thức/Ứng dụng/Quản trị | `RAIL_GROUPS` 6 nhóm kỹ thuật | **REFACTOR** | Map: Bộ não→Tri thức+Joyce; Code→Admin Lab; Kết nối→Quản trị/Integration |
| 3 | Context Switcher (workspace/BU) | Brain switcher (`brains-ui.js`) + workspace page + staff workspace | **REFACTOR** | Brain≈workspace gần đúng; BU/tenant chưa có khái niệm |
| 4 | Command Palette ⌘K | **Không có** — chỉ có ô search trong vài trang | **NEW** | Tái dùng `joyce_ui` actions + search sessions |
| 5 | Context Drawer (khách/dự án/task) | **Không có** — drawer chỉ có trong chat/file | **NEW** | Task drawer đầu tiên (kanban/show đã trả đủ dữ liệu) |
| 6 | Hộp thư **Chờ duyệt** | `kanban` status `review` + `needs_approval` + inbox | **REFACTOR** | Đã có mô hình approval ở task; chưa có inbox duyệt riêng, chưa có nút approve/reject API chuẩn |
| 7 | Joyce Chat contextual (gắn object) | `/chat`, sessions, assets gắn file/link vào phiên | **REFACTOR** | Gắn context = kéo object vào session (cơ chế assets có sẵn) |
| 8 | Đội ngũ AI = Central Agent Registry | `<brain>/agents/*.md` + `/agents` | **REFACTOR** | Cần thêm trường scope/budget/health/last-run hiển thị; hiện chỉ có file md + assets |
| 9 | Quy trình (run timeline, retry, evidence) | `/workflows`, `/workflows/runs`, loop engine | **REFACTOR** | Runs đã lưu; thiếu view timeline + audit chuẩn |
| 10 | Knowledge search + citation | `query-wiki` skill, `/files/search`, memory_index | **REFACTOR** | Citation [[wikilink]] đã là convention vault; cần UI + trả source/version |
| 11 | Learning Review Queue | `learn.py` (curator, tier chống self-poisoning) + trang Tự học | **REFACTOR** | Đã tương đương LearningProposal→Promote; thêm queue + reviewer field |
| 12 | Integration Center | `/connect` 19 route + MCP + packs + channels | **MERGE** | Gộp 3 trang Kết nối/MCP/Gói thành 1; giữ route cũ |
| 13 | Model Router Nhanh/Cân bằng/Sâu/Riêng tư | `model_router.py` (policy, cost) — nội bộ | **REFACTOR** | Đã có engine router; cần nhãn thân thiện + map per-staff |
| 14 | Nhân viên (account, workspace, model ACL) | `h2o_staff.py` + trang Nhân viên + 6 chức vụ | **KEEP** | Vừa mới làm; cần role→nav sau |
| 15 | Tenant/PostgreSQL/Supabase chung | **Không có** — SQLite local, mỗi app H2O một Supabase riêng | **NEW (nằm ngoài repo)** | Đây là việc của H2O Legacy/data plane, không phải của riêng Joyce |
| 16 | Audit + Outbox + Idempotency | `/connect/audit`, kanban `idempotency_key`, events trong task_store | **REFACTOR** | Có mầm; chưa thành audit trail thống nhất cho mọi mutation |
| 17 | Policy Gate / Tool Gateway | `mcp_hub.allow_patterns`, 3 mức quyền loop (full/auto/suggest), `_staff_blocked` | **REFACTOR** | Tương đương nhẹ; nâng cấp thành capability grant nếu cần |
| 18 | Code/Terminal/Local Model → Admin Lab | Nhóm Code + trang Model | **HIDE** (theo role) | Chỉ ẩn với staff, admin vẫn thấy đủ |
| 19 | H2O apps (CRM, Wedding, Academy, ConceptOS, ArtColor) | `h2o_projects.py` + trang Dự án + orb satellites | **KEEP + REFACTOR** | Hiện là link+ping; spec muốn đọc API từng app (cần API phía kia) |
| 20 | Vault/file browser | `/files/*` 16 route + brain-view | **KEEP** | Staff đã bị chặn /files — đúng hướng "không cho staff đọc vault admin" |

## 3. Source of truth của từng entity

| Entity | Nơi giữ thật | Rủi ro trùng/rò |
|---|---|---|
| Session chat | `conversations.db` + `sessions.py` (SQLite) | `conversation_state.db` song song — hai store hội thoại, cần map rõ |
| Task/Kanban | `server/kanban.sqlite3` qua `task_store.py` | `/viec/all` và `/kanban` hai view một nguồn — OK |
| Reminder/cron | `<brain>/Joyce/reminders.json` per-brain | per-brain → tổng hợp "lịch hôm nay" phải quét nhiều file |
| Agent/Skill/Workflow/Loop | **file .md trong vault** (`agents/`, `skills/`, `workflows/`, `Joyce/loops/`) | `Joyce/index.md` là chỉ mục TỰ SINH — không viết tay |
| Nhân viên | `STATE_DIR/h2o_staff.json` + `staff_workspaces/` | workspace per-staff tách khỏi brain — chưa link vào task ownership |
| Brain/tri thức | `brains/<name>/` markdown + git | `memory_index.db` là projection — không phải SoR (đúng spec: cache chỉ chứa projection) |
| Kết nối MCP | `STATE_DIR/mcp_servers.json` + cred file riêng | connectors (OAuth) + MCP truyền thống hai cơ chế song song |
| Plugin | `system/plugins/` + `STATE_DIR/plugins/` + `<vault>/plugins/` | 3 nguồn nạp — cần 1 registry view |
| Settings | `STATE_DIR/settings.json` (`config.py`) | không per-user — staff dùng chung config admin |
| Dự án H2O | `h2o_projects.json` | chỉ là link registry, chưa có data của app |
| Usage/quota | `usage_index.db` + `usage_store.py` | per-provider, chưa per-user |

**Nguy cơ duplicate-data lớn nhất** theo spec: nếu Phase 2 vẽ Today/Tasks mà tự tạo bảng mới thay vì đọc `kanban.sqlite3`/`conversations.db`/vault → vi phạm "One Data Plane". Mọi widget phải đọc qua adapter từ store hiện có.

## 4. Baseline kiểm thử (thực chạy, không che lỗi)

Chạy trên máy dev Windows, `.venv` Python 3.14:

| Bộ | Kết quả | Ghi chú |
|---|---|---|
| `python tests/run.py --py` | **310/380 xanh** (809s) | 70 đỏ — danh sách đầy đủ trong `tests-baseline.log` |
| `python tests/run.py --js` | **158/169 xanh** (28s) | 11 đỏ — danh sách dưới |
| Byte-compile server | PASS (`py_compile` sạch mọi file sửa) | |
| JS syntax (`node --check` console.js, app.js, hud.js…) | PASS | |
| Lint/typecheck/build | **không có** — repo không dùng ruff/mypy/eslint/bundler | gate tương đương = compileall + import main + test suite |
| E2E | không có framework riêng; test JS nhiều file là DOM-level | |

### Test JS đang đỏ (baseline — lỗi có sẵn, chưa gán nguyên nhân)

```
test_gan_file_vao_cuoc.js          test_i18n.mjs
test_logo_linh_vat.js              test_mic_doc_chong_va_loa_theo_mic.js
test_mic_khong_tu_gui.js           test_pet_bang_mau.js
test_pet_thanh_truot_mau.js        test_settings_tabs.js
test_trang_coding.js               test_ui_actions.js
test_viec_nen_khong_khoa_chat.js
```

> Lưu ý: `test_settings_tabs.js` và `test_ui_actions.js` CÓ THỂ đỏ vì các thay đổi gần đây của chính đợt staff/nav (tab Cài đặt đổi, thêm trang Nhân viên) — cần mở từng test xác nhận đâu là pre-existing đâu là do mình.

### Test Python đang đỏ (baseline 310/380 — 70 đỏ)

Đã vá 1 cái do chính đợt này gây ra: `test_route_table` đỏ vì snapshot chưa có 17 route staff/H2O (`/h2o-staff`, `/h2o-projects`, `/staff/*`) — chạy `--update` chụp lại thành **396 route**, test xanh lại và file JSON sẽ commit kèm.

69 test đỏ còn lại — danh sách đầy đủ trong `tests-baseline.log`. Nhóm nổi bật: `test_antigravity_cli`, `test_agy_*`, `test_grok_cli`, `test_go_chatgpt_web`, `test_composio_connection`, `test_share_link`, `test_share_ten`, `test_terminal`, `test_watchdog`, `test_windows_no_console`, `test_voice_*` (12 file), `test_hoi_thoai_*`, `test_bot_*`, `test_model_router_phase12`, `test_sessions_kenh_cong_su`, `test_cai_windows`, `test_install_admin`… Phần lớn phụ thuộc CLI ngoài (claude/codex/agy/grok), tài khoản hoặc môi trường (Windows/no-console, watchdog) — **không kết luận hỏng cho tới khi đọc output từng test**. Vài test JS (`test_settings_tabs`, `test_ui_actions`) và `test_sessions_kenh_cong_su` nghi liên quan thay đổi staff/nav gần đây — cần mở từng cái xác nhận.

## 5. Nhận định cho Phase 1+

1. **Kiến trúc khác đáng kể so với spec** — spec giả định shared PostgreSQL/Supabase + IAM + Outbox chung của hệ sinh thái H2O; Joyce hiện là app độc lập (SQLite + cookie auth nội bộ). "Dùng chung Auth/RBAC" chỉ thực hiện được khi phía H2O Legacy/CRM mở API/SSO. **Đây là điểm theo prompt phải DỪNG REVIEW**: đề xuất tách "Phase data-plane" khỏi phạm vi Joyce, Joyce chỉ làm phần Experience Layer + adapter điểm-gắn.
2. **Làm ngay được, giá trị cao, rủi ro thấp** (không phụ thuộc data plane): trang Hôm nay tổng hợp từ kanban/reminders/h2o-projects/inbox; command palette; regroup rail; task context drawer; approval inbox trên nền kanban `review`; ẩn nhóm Code/Model với staff.
3. **Điểm dễ vi phạm**: không tạo table/store mới cho thực thể đã có SoR (task, conversation, reminder); mọi widget đọc qua adapter; mock data của prototype tuyệt đối không vào DB.
4. **main.py 20k dòng**: mọi WP chạm main.py phải đi theo pattern `APIRouter` + `register(app, deps)` đã có sẵn (tasks/reminders/learn/self_improve làm mẫu), không nhét thêm route vào monolith.
5. **route_table.json** là dây bảo hiểm chống đổi route khi tái cấu trúc nav — khi thêm `/api/joyce/v1/*` phải `--update` snapshot đi kèm commit.

## 6. Open questions cho owner

1. Data plane chung (Supabase/IAM) có nằm trong phạm vi đợt này không, hay Joyce chỉ làm Experience Layer trước? *(khuyến nghị: chỉ Experience Layer)*
2. 6 chức vụ mới có cần lái navigation ngay (nhân viên không thấy Code/Model/Admin) không, hay phase sau?
3. Approval inbox: gom vào trang Việc (kanban) hay tách rail riêng như prototype?
4. "H2O Pulse" định nghĩa nguồn cảnh báo: từ kanban blocked + app offline + inbox chưa đọc — đúng ý không?
