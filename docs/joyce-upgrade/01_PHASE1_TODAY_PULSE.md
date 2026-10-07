# Phase 1 - Trang Hôm nay + H2O Pulse + Chờ duyệt trong Việc

Ngày: 2026-10-05. Bám spec `tai-lieu-update-tu-openai` + 4 quyết định đã duyệt:
Joyce = **Experience Layer** (chỉ đọc/tổng hợp nguồn có sẵn), nhân viên vẫn thấy
Code/Models, approval **gộp vào trang Việc** (không tách rail), Pulse = feed cảnh
báo "cần người ra tay" xếp severity x độ cũ.

## Đã làm

### Backend - `server/joyce_today.py` (mới, ~380 dòng)

- `GET /api/joyce/v1/today` - một điểm rót cho trang Hôm nay: viewer (tên nhân
  viên nếu cookie staff, tên workspace nếu admin), weekday/date, morning brief
  deterministic, 6 metric, task ưu tiên (blocked > review > ready > todo >
  running, theo priority), lịch hôm nay (reminders pending xuyên mọi brain),
  Pulse, lưới app H2O, `approvals_pending`.
- `GET /api/joyce/v1/pulse` - feed cảnh báo độc lập (dùng cho badge/poll sau).
- DI theo đúng convention `register(app, deps)` - module không import main.
- **Cache ping app H2O 120s** (`_ping_projects` + lock): ping_all() đi mạng ngoài
  ~15 app x timeout, gọi thẳng mỗi lần load Today là treo trang.
- **Per-source try/except**: một nguồn chết (kanban sqlite khoá, connect_health
  lỗi...) chỉ đẩy tên nguồn vào `sources_down` + `partial: true`, feed vẫn trả về
  với nguồn còn sống. Log `[joyce-today]` ra stdout.

### Pulse - 8 nguồn, severity x độ cũ

| Nguồn | Tín hiệu | Severity |
|---|---|---|
| connect_health._engines | bộ não AI lỗi/hết phiên | critical |
| h2o_projects ping | app Vercel offline | critical |
| connect_health.snapshot | connector/MCP lỗi | high |
| kanban blocked | task kẹt + lý do | high |
| kanban review >4h | chờ duyệt quá lâu | medium |
| kanban chờ + orch off | hàng đợi "chết câm" | medium |
| reminders notify_status | nhắc hẹn thiếu kênh báo | medium |
| inbox unread | kết quả nền chưa đọc | low |

Mọi item: `{severity, source, title, meta, since, href}` - `href` là id trang
console (`kanban`/`projects`/`mcp`/`channels`/`models`/`home`), bấm là nhảy tới
đúng chỗ xử lý. Không có nút "đã đọc" - item tự biến mất khi nguồn hết lỗi.

### Frontend - `dashboard/console.js`

- Rail: nhóm mới **Hôm nay** (icon `sun`) đứng ĐẦU, một mục `today`.
- `renderToday()`: header chào theo giờ + vai trò (admin/nhân viên) + brain,
  thẻ morning brief, 6 metric card, lưới 2x2: Ưu tiên hôm nay / Lịch hôm nay /
  H2O Pulse (chấm severity + tuổi cảnh báo) / Hệ sinh thái H2O (dot xanh-đỏ +
  ms, bấm mở webapp). Banner vàng khi `partial` (nguồn dữ liệu thiếu).
- **Dải "Chờ duyệt"** ghim đầu trang Việc (viền vàng warn, dot nhấp): lọc
  `columns.review`, đếm số, mỗi task có Duyệt (move->done) + Yêu cầu sửa
  (move->todo) ngay trong dải, bấm thân mở drawer chi tiết như cũ.
- Review task ở mọi nơi (attention panel, drawer) giờ có nút **Yêu cầu sửa**
  đi kèm Duyệt; nút Thử lại bỏ khỏi review (dư thừa với Yêu cầu sửa).
- CSS td-* + .kn-approve nằm trong `_injectExtraCss()` theo convention.
- i18n đủ vi+en (`page.today.*`, `today.*`, `nav.group.hom_nay`,
  `kanban.approve_strip`, `kanban.act_reject`).

### Test

- `tests/python/test_joyce_today.py` - 21 assert: thứ tự severity, từng nguồn
  báo đúng mức, review mới <4h KHÔNG lên pulse, **mọi nguồn chết feed vẫn sống
  + kể tên nguồn**, lịch trong ngày, brief deterministic.
- `tests/js/test_trang_hom_nay.js` - đăng ký đủ 4 chỗ + railGroups() thật bung
  được nhóm, strip chờ duyệt tồn tại + nút từ chối, không có rail 'approvals'
  tách riêng, i18n hai vế.
- Sửa `test_settings_tabs.js`: expectation nhóm foot còn thiếu `staff` (stale từ
  commit 53dcedb - bản thân staff là mục rail có chủ đích).

## Đã kiểm chứng thật

- Server chạy code mới: `/api/joyce/v1/pulse` + `/api/joyce/v1/today` trả 200
  với Bearer token; dữ liệu thật (app H2O Legacy ping 434ms OK, inbox unread=2
  -> 1 item low, brief "1 nhóm việc cần chú ý").
- `route_table.json` cập nhật 396 -> 399 (2 endpoint mới + `/joyce/index` vốn đã
  có sẵn ở chỗ khác trong main.py).
- `tests/run.py joyce_today` 21/21 xanh; `trang_hom_nay` + `settings_tabs` xanh.
- `node --check console.js` sạch; i18n JSON hợp lệ.

## Chưa làm (biết rõ, không giấu)

- Brief là **deterministic** - bản LLM-viết-có-hồn để phase sau (cần aux model
  + cache, không chặn trang).
- Nhân viên thấy cùng Pulse vận hành như admin - role-scoping theo 6 chức vụ là
  bước sau (spec: role-based navigation).
- Learning Review Queue, Integration Center hợp nhất, Tool Gateway/Policy Gate
  thật - Phase 3+ của spec, chờ quyết định data plane chung.

## Bổ sung ngày 05/10 - hoàn thiện Phase 1 (commit kế tiếp 13e9588)

- **Feature flag** `settings.features.workstation_v1` (mặc định bật): tắt thì
  trang Hôm nay ẩn khỏi rail (đẩy vào RAIL_AN) và renderPage rơi về placeholder.
- **Badge rail**: Việc = số chờ duyệt, Hôm nay = số cảnh báo critical+high. Poll
  `/api/joyce/v1/pulse` mỗi 60s + khi đổi brain; endpoint pulse trả thêm
  trường `approvals`. Badge sống trong Alpine store (`nav.badges` + badgeTick),
  hiện cả ở rail thu gọn.
- **⌘K command palette**: overlay lười-dựng, danh mục = mọi trang RAIL_ITEMS
  (gồm cả trang ẩn - power user) + lệnh "Tạo việc mới" (mở Việc + bật form) +
  "Làm mới trang". Lọc bỏ dấu (`_vtNoAccent`), phím ↑↓/Enter/Esc, click cũng được.
- **Context drawer**: bấm task trên trang Hôm nay -> về Việc + mở ngay
  `kn-drawer` chi tiết qua `window.JoyceKanbanShow` (tái dùng, không tạo drawer
  thứ hai). Ô Lịch hôm nay bấm -> trang Việc định kỳ.
- CSS palette `.cmdk-*` và `.rail-badge` trong console.css (v85),
  console.js v177.

## Bổ sung ngày 05/10 (lần 2) - khép kín flag + landing + verify E2E

- **`POST /settings` nhánh `features`** (main.py): allowlist key
  `workstation_v1` (bool). Endpoint này từng là bẫy "lưu báo ok nhưng key lạ
  bị nuốt" nên nhánh riêng là bắt buộc - không có nó thì công tắc UI lưu ảo.
- **Thẻ công tắc Workstation** trong Cài đặt -> Chung -> nhóm Giao diện (cạnh
  Đồ thị não): bật/tắt `features.workstation_v1`, đổi là rail ẩn/hiện mục Hôm
  nay ngay (không cần F5). Mặc định BẬT khi thiếu key.
- **Nút ⌘K trên cview-head** (`#cmdkTrigger` + `window.JoyceCmdk`): người mới
  nhìn thấy palette tồn tại thay vì phải biết trước phím tắt. i18n
  `cmdk.trigger`, mobile chỉ còn icon kính lúp.
- **Nhân viên đáp vào Hôm nay**: `initAuthGate` (app.js) sau khi nhận cookie
  staff hợp lệ, nếu chưa có trang đã nhớ (`joyce_last_page`) và đang đứng ở
  `home` -> `JoyceNav.go("today")`. Admin giữ nguyên cockpit; người đã dùng
  (có trang nhớ) giữ nguyên trang cũ.
- **Bug vá trong lúc rà**: trùng `id="knApprove"` giữa strip chờ-duyệt và
  checkbox "cần duyệt" trong form thêm việc -> `querySelector` trả strip div
  (đứng trước), `.checked` undefined -> checkbox im lặng mất tác dụng. Đổi id
  strip thành `knApproveStrip`.
- **Verify E2E trên server chạy thật** (state tạm, Bearer token): POST task ->
  move review -> `/pulse` trả `approvals:1` (chưa lên feed vì <4h, đúng ngưỡng)
  -> move done -> `approvals:0`. Task thứ hai -> review -> move blocked ->
  pulse hiện item `high/kanban` href=kanban. Thu hồi token + dọn state sau test.
- **`POST /settings section=features` verify bằng TestClient**: ghi false ->
  read_settings + GET /settings đều trả `{"workstation_v1": false}`.
- Test: `test_joyce_today` xanh; `test_settings_tabs`, `test_kanban_snapshot`,
  `test_phong_to_md_che_het_rail`, `test_trang_hom_nay`, `test_route_table`
  4/4 xanh. `test_luu_cai_dat_giong` ĐỎ từ baseline (không liên quan).

## Bổ sung ngày 05/10 (lần 3) - contract /api/joyce/v1 (Phase 3-lite)

Chỉ làm phần đọc-tổng-hợp + duyệt task (đúng quyết định Experience Layer);
chat/threads, learning-proposals, knowledge/search chờ Phase 4 + data plane.

- `GET /api/joyce/v1/tasks` - board_view passthrough (columns + counts +
  orchestration), lỗi kanban trả 200 + ok:false chứ không 500.
- `GET /api/joyce/v1/approvals` - danh sách review kèm `stale` flag
  (> `_REVIEW_STALE_SEC`) và `stale_after_sec` để client tự tính.
- `POST /api/joyce/v1/approvals/{id}/approve` -> move done; `/reject` -> move
  todo + lý do (khớp "Yêu cầu sửa" của UI). **Staff 403 tại đây** - v1 không
  nằm trong `_STAFF_DENY` nên phải tự kiểm `_staff_of`, khớp rào /kanban.
- `GET /api/joyce/v1/context/task/{id}` - task + events + runs qua dep
  `task_get` (tái dùng logic /kanban/task/show).
- `GET /api/joyce/v1/agents` - `agents_index(brain, kem_prompt=False)` bản nhẹ.
- Deps mới trong main.py: `task_get`, `task_move` (async, đi đúng đường
  store.move + _asnapshot + wake), `agents_list`.
- UI: nút Duyệt/Yêu cầu sửa trong `doTaskAction` chuyển từ `/kanban/task/move`
  sang endpoint v1 (act done/todo chỉ tồn tại trên task review nên map 1:1).
  `/kanban/task/move` giữ nguyên làm compat cho các caller khác.
- Chưa làm: `POST /commands` (palette là điều hướng client-side, chưa cần
  server round-trip), `context/:type/:id` cho Customer/Lead/WeddingProject
  (đối tượng domain H2O - chờ data plane), `chat/threads`, `knowledge/search`,
  `learning-proposals` (Phase 4).
- route_table.json: 399 -> 405 routes; test mới: 10 assert v1 trong
  test_joyce_today (tasks/approvals/approve/reject/context/agents + staff 403).
- Spec Phase 2 chi tiết nhỏ: `generated_at` + map `sources` trong response
  /today -> UI hiện "Cập nhật HH:MM" trên header và nhãn nguồn trên từng panel
  (kanban / reminders / pulse / h2o_projects). Pulse item kanban đơn-task giờ
  kèm `task_id`: bấm item -> về Việc + mở ngay drawer đúng task (không chỉ
  tới trang rồi tự tìm).

## Bổ sung ngày 05/10 (lần 4) - Phase 4: brief LLM + nốt contract v1

- `GET /api/joyce/v1/brief-ai` - câu chào viết bằng aux model (model việc nền
  chủ chọn ở Models). Engine cô lập đúng khuôn `_reply_policy_ask`: cwd trống,
  không MCP, `allowed_tools` giả để can_use_tool từ chối mọi tool, prompt chỉ
  mang số đếm + tiêu đề task + pulse top. Cache `_brief_cache` TTL 600s khoá
  theo chữ ký số liệu; aux lỗi/trống/chưa cấu hình -> `fallback: true` + brief
  deterministic. Frontend fetch lười sau khi trang vẽ xong -> không bao giờ
  chặn load. Verify live: aux trả câu thật ("Chào anh, hệ thống đang sạch..."),
  request 2 trả `cached: true`.
- `GET /api/joyce/v1/knowledge/search` - bọc `/files/search`, item gắn
  `source: "vault"`. **Staff 403** (đọc vault = quyền chủ; v1 không nằm trong
  deny-list nên tự kiểm).
- `GET/POST /api/joyce/v1/chat/threads` - bọc `sessions_list` (staff scope giữ
  nguyên bên trong dep) + tạo phiên `web`/`staff:<id>`. CẠM BẪY: endpoint cũ
  có default `Query()` - gọi tay phải truyền trọn tham số (đã vá).
- `POST /api/joyce/v1/commands` - whitelist cứng trong `_v1_cmd_today`:
  `kanban.nudge`, `pulse.refresh`, `orchestration.auto|.manual|.off`. Lệnh lạ
  404, staff 403. Không shell, không lệnh tuỳ ý - đây là cổng cho palette/
  Telegram sau này.
- `GET /api/joyce/v1/learning-proposals` + `POST .../undo` - bọc `/learn/review`
  + `/learn/undo` (commit học trong git brain + revert 1-click). Staff đọc
  được danh sách, undo 403. Verify live: `{"ok":true,"git_repo":false,"items":[]}`
  (brain test không phải git checkout -> rỗng đúng).
- `GET /api/joyce/v1/learning-proposals` + `POST .../undo` - bọc `/learn/review`
  + `/learn/undo` (commit học trong git brain + revert 1-click). Staff đọc
  được danh sách, undo 403. Verify live: `{"ok":true,"git_repo":false,"items":[]}`
  (brain test không phải git checkout -> rỗng đúng).

## Bổ sung ngày 05/10 (lần 5) - khép contract v1 theo spec

- `POST /api/joyce/v1/agent-runs` - giao việc cho đội ngũ = `tasks_feature.enqueue`
  (đúng đường /kanban/task), trả `task_id`, hỗ trợ `needs_approval` + `chat_id`.
  Staff 403 (khớp rào write /kanban). Live: enqueue tạo task thật rồi context
  đọc lại được đúng id.
- `POST /api/joyce/v1/learning-proposals` - đẩy ghi chú vào hàng học
  (`learn_feature.enqueue`, chỉ là nguyên liệu - pipeline curator + duyệt giữ
  nguyên). Text <20 ký tự -> 400; staff 403.
- `GET /api/joyce/v1/context/{type}/{id}` - route tổng quát của spec. Chỉ
  `type=task` có adapter nội bộ; `customer/lead/project/...` trả 404 kèm
  `supported: ["task"]` vì đó là đối tượng domain của H2O Legacy - đúng
  nguyên tắc Experience Layer không chế mock.
- `POST /api/joyce/v1/chat/threads/{id}/messages` - append tin user vào phiên
  (`store.append_message`), staff chỉ phiên kênh `staff:<id>` của mình.
  Reply vẫn stream qua `/chat` với session id đó - endpoint không tự chạy
  engine, tránh nhân đôi user message (vì /chat tự append nội bộ).
- `GET /api/joyce/v1/integrations` - Integration Center mặt máy đọc (Phase 5):
  gộp connector MCP (bản `_public` redacted của mcp_store) + connect_health,
  engines, app H2O (cache ping), bot kênh; `summary.down` đếm thứ đang hỏng.
  UI trang Kết nối (renderConnect) vốn đã là Integration Center - giữ nguyên,
  endpoint này là contract cho client khác.
- `agent-runs` hỗ trợ `idempotency_key` truyền thẳng xuống enqueue (retry an
  toàn - DoD "idempotency"). Reduced-motion CSS cho workstation/palette/badge
  (Phase 6 a11y) - các khối cũ chỉ giải quyết avatar/bubble.
- route_table.json: 412 -> 417 mục; test_joyce_today -> 59 assert.
- Còn lại ngoài khả năng Experience Layer (ghi rõ, không làm): context adapter
  cho Customer/Lead/WeddingProject (chờ data plane H2O Legacy), Integration
  Center gộp trang, model mode Fast/Balanced/Deep, role 6 chức vụ lái quyền
  chi tiết (hiện staff/admin đã rào đầy đủ).
