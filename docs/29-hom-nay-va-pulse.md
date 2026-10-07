# Hôm nay & H2O Pulse: bàn làm việc mở đầu ngày

Trang **Hôm nay** là bàn làm việc tổng quan: Joyce gom sẵn mọi thứ đang cần bạn ra tay (việc kẹt, việc chờ duyệt, app H2O hỏng, tin chưa đọc) vào một màn hình, thay vì bạn phải tự đi rào từng trang.

Triết lý của trang này: **không phải dashboard để ngắm, mà là danh sách can thiệp**. Con số nào không cần hành động thì nhỏ lại; thứ nào im lặng là mất tiền thì to và đỏ lên.

## Mở ở đâu trong Joyce

Mục **Hôm nay** (icon mặt trời) đứng đầu thanh điều hướng, trong nhóm riêng cùng tên. Với nhân viên đăng nhập lần đầu, đây còn là trang mặc định mở ra.

Trang gắn với **brain đang chọn**: đổi brain là đổi hàng đợi việc, số chờ duyệt và badge trên thanh bên.

## Trên trang có gì

| Khối | Nội dung | Bấm vào thì |
| --- | --- | --- |
| Thẻ chào + brief | Lời chào theo giờ, tên người đang xem, một câu tóm "có bao nhiêu nhóm việc cần chú ý" | - |
| 6 ô metric | Đang chạy / Chờ duyệt / Xong 24h / App H2O online / Hẹn hôm nay / Inbox chưa đọc | nhảy tới trang tương ứng |
| Ưu tiên hôm nay | Task kẹt và chờ duyệt lên đầu, rồi hàng chờ | mở trang Việc + drawer chi tiết task đó |
| Lịch hôm nay | Nhắc hẹn pending đến hạn hôm nay, gom xuyên mọi brain | mở trang Việc định kỳ |
| **H2O Pulse** | Feed cảnh báo LIVE, xếp theo mức độ | bấm item -> thẳng trang xử lý |
| Hệ sinh thái H2O | Từng app Vercel: chấm xanh/đỏ + ms phản hồi | mở webapp thật |

Khi một nguồn dữ liệu lỗi (kanban sqlite khoá, health check chết), trang hiện **banner vàng "thiếu nguồn"** kể tên nguồn đang lỗi, thay vì im lặng khiến bạn tưởng hệ thống đang sạch.

## H2O Pulse đọc thế nào

Pulse **không phải nhật ký**. Nó chỉ liệt kê tín hiệu có chi phí im lặng, xếp `severity x độ cũ`:

| Mức | Ví dụ |
| --- | --- |
| **critical** (đỏ) | Bộ não AI lỗi/hết phiên; app H2O không phản hồi |
| **high** (cam) | Task bị kẹt; connector/MCP hỏng |
| **medium** (vàng) | Việc chờ duyệt quá 4 giờ; hàng chờ đầy mà orchestration tắt; nhắc hẹn không có kênh báo |
| **low** (xám) | Kết quả nền chưa đọc trong Inbox |

Item **tự biến mất** khi nguồn hết lỗi - không có nút "đánh dấu đã đọc", vì feed phản ánh hiện trạng, không phải hộp thư.

## Dải "Chờ duyệt" trên trang Việc

Mọi task AI làm xong mà bạn đã tick "Yêu cầu duyệt kết quả" (hoặc worker tự đẩy sang `review`) nằm trong dải viền vàng ghim đầu trang Việc:

- **Duyệt**: task sang done ngay, không cần mở drawer.
- **Yêu cầu sửa**: task quay về hàng chờ (`todo`) để chỉnh/triage lại.
- Bấm thân task vẫn mở drawer chi tiết như cũ.

Số chờ duyệt còn hiện thành **badge đỏ cạnh mục Việc** trên thanh bên, tự làm mới mỗi 60 giây và mỗi lần đổi brain.

## Bảng lệnh Ctrl+K

Bấm **Ctrl+K** (Mac: Cmd+K) hoặc nút **"Tìm nhanh"** ở góc phải thanh tiêu đề:

- Gõ tên trang (không cần dấu: `viec` tìm ra "Việc") để nhảy tới.
- Lệnh sẵn có: Tạo việc mới, Làm mới trang đang xem.
- Mũi tên lên/xuống chọn, Enter mở, Esc đóng. Chuột bấm cũng được.

## Tắt/bật cả lớp Workstation

Cài đặt -> tab Chung -> thẻ **"Bàn làm việc Hôm nay"**. Tắt thì mục Hôm nay biến khỏi thanh bên ngay và trang về trạng thái placeholder; dữ liệu và API vẫn nguyên. Hữu ích khi muốn so sánh với giao diện cũ, hoặc một máy cài cho người không cần lớp này.

## Cho dev: nâng cấp đúng chỗ

| Muốn sửa | Đụng vào |
| --- | --- |
| Thêm nguồn cảnh báo vào Pulse | `server/joyce_today.py` -> hàm `_pulse()` (mỗi nguồn một khối try/except riêng) |
| Thêm metric/today field | `server/joyce_today.py` -> `api_today()`; đổi dep thì sửa `TodayDeps` + chỗ `register()` trong `server/main.py` (~dòng 16175) |
| Đổi ngưỡng "chờ duyệt quá lâu" | `_REVIEW_STALE_SEC` trong `joyce_today.py` (mặc định 4h) |
| Đổi TTL ping app H2O | `_PING_TTL` (120s) trong `joyce_today.py` |
| Giao diện trang Hôm nay | `renderToday()` trong `dashboard/console.js`; CSS `.td-*` trong `_injectExtraCss()` |
| Dải Chờ duyệt | `renderKanban()` -> `#knApproveStrip` + `doTaskAction()`; CSS `.kn-approve` |
| Badge rail | `_pollBadges()` trong `dashboard/console.js`; CSS `.rail-badge` |
| Bảng lệnh | `_cmdkBuild/_cmdkItems` trong `dashboard/console.js` (thêm lệnh = thêm dict vào list `items`) |
| Cờ tính năng | `settings.features.workstation_v1`; đọc ở `freshSettings()` (console.js ~dòng 9323), toggle ở `renderSettings()` |
| Brief LLM | `_brief_ai_today()` trong `main.py` (engine cô lập) + `api_brief_ai`/`_brief_cache` trong `joyce_today.py`; đổi giọng = sửa prompt trong `api_brief_ai`, đổi TTL = `_BRIEF_TTL` |
| Thêm lệnh commands | bản đồ `_v1_cmd_today()` trong `main.py` (whitelist cứng - mỗi lệnh gọi đúng hàm endpoint cũ) |
| i18n | nhóm `today.*`, `page.today.*`, `kanban.approve_*`, `cmdk.*`, `settings.ws*`, `nav.group.hom_nay` |

API: `GET /api/joyce/v1/today` (một điểm rót cả trang) và `GET /api/joyce/v1/pulse` (feed riêng, trả `approvals`, `partial`, `sources_down`). Contract v1 còn có: `GET /api/joyce/v1/tasks`, `GET /api/joyce/v1/approvals`, `POST .../approvals/{id}/approve` + `/reject` (admin-only, staff 403), `GET .../context/task/{id}`, `GET .../agents`. Cả nhóm qua auth middleware chung; không có store mới nào được tạo - mọi thứ đọc qua adapter của kanban/reminders/inbox/h2o_projects/connect_health hiện có.

Phase 4 thêm:

- `GET /api/joyce/v1/brief-ai` - lời chào viết bằng **model việc nền** (aux model chủ đã chọn ở Models). Engine chạy trong thư mục trống, không MCP, không tool (cổng `can_use_tool` từ chối hết), prompt chỉ chứa số đếm + tiêu đề task. Cache 10 phút theo chữ ký số liệu (F5 không tốn token lại); aux lỗi/chậm/chưa cấu hình → `fallback: true` kèm brief deterministic, UI không chờ. Frontend gọi lười sau khi trang đã vẽ - không bao giờ chặn load.
- `GET /api/joyce/v1/knowledge/search?q=` - bọc `/files/search` (quét gốc brain trong threadpool, khớp không dấu); mỗi item gắn `source: "vault"`. **Staff 403** (đọc vault = quyền chủ).
- `GET/POST /api/joyce/v1/chat/threads` - bọc `/sessions` (scope staff giữ nguyên: nhân viên chỉ thấy kênh `staff:<id>` của mình). POST tạo phiên kênh `web` (admin) hoặc `staff:<id>` (nhân viên). Kênh cộng sự `agent:/workflow:/coding:` vẫn đi `/sessions/new`.
- `POST /api/joyce/v1/commands` - **whitelist lệnh, không phải shell**: `kanban.nudge` (kích dispatcher), `pulse.refresh` (xoá cache ping app H2O), `orchestration.auto|.manual|.off` (đổi chế độ bảng Việc). Lệnh lạ → 404. **Staff 403**.
- `GET /api/joyce/v1/learning-proposals` - hàng chờ "Joyce đã học gì" = commit học trong git brain (bọc `/learn/review`). `POST .../learning-proposals` = đẩy ghi chú vào hàng học (staff 403, text <20 ký tự → 400). `POST .../learning-proposals/undo` = revert 1-click (staff 403).
- `POST /api/joyce/v1/agent-runs` - giao việc cho đội ngũ = enqueue task kanban (`tasks_feature.enqueue`), trả `task_id`, hỗ trợ `needs_approval`/`chat_id`/`idempotency_key` (retry không nhân đôi task). **Staff 403** như write `/kanban`.
- `GET /api/joyce/v1/integrations` - **Integration Center (mặt máy đọc)**: gộp connector MCP (bản redacted, không secrets) + health, engines (bộ não), app H2O (cache ping), bot kênh; `summary.down` = số thứ đang hỏng. UI Kết nối giữ nguyên - đây là contract tổng hợp cho client khác, không di chuyển route.
- `GET /api/joyce/v1/context/{type}/{id}` - context drawer tổng quát. Hiện chỉ `type=task` có adapter nội bộ; type domain (customer/lead/project...) trả 404 kèm `supported` - đối tượng đó sống ở H2O Legacy.
- `POST /api/joyce/v1/chat/threads/{id}/messages` - append tin user vào phiên (staff chỉ phiên kênh `staff:<id>` của mình, phiên lạ 404). Reply vẫn stream qua `/chat` - endpoint này để seed thread, không tự chạy engine.

Test liên quan: `tests/python/test_joyce_today.py`, `tests/js/test_trang_hom_nay.js`, `tests/js/test_settings_tabs.js` (kỳ vọng nhóm rail), `tests/python/test_route_table.py` (snapshot route).
