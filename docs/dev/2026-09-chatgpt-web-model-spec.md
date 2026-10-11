# ChatGPT Web (model) - hồ sơ đã gỡ

Trạng thái: **ĐÃ GỠ ở 0.64.20** (phiên bản Joyce gốc).
File này chỉ còn làm hồ sơ: ghi lại việc đã gỡ gì và thay bằng gì. Không dùng nó làm đặc tả để làm lại.

## Đã gỡ gì

- Module: `web_transport`, `web_engine`, `web_state`, `web_tool_protocol` (không còn trong `server/`).
- Route: mọi đường `/web-chat...`, và các hàm `la_model_web`, `MODEL_WEB`, `_web_bat`, `_dung_web_engine`
  trong `server/main.py`.
- Dashboard: khối ChatGPT Web (`veThreChatGPTWeb`, `webChatBox`) trong `dashboard/console.js`.
- Docker: gói `xvfb` trong `Dockerfile`, vì chỉ ChatGPT Web cần.
- Biến `JOYCE_ENABLE_WEB_CHAT` trong tài liệu cấu hình (`docs/16-cau-hinh-env.md`, bản tiếng Anh).
- Công cụ: thư viện trình duyệt bản đầy đủ. Trang Công cụ chỉ còn trình duyệt, cài bản nhẹ `--only-shell`.

## Thay bằng gì

Model Codex thật, dùng qua gói ChatGPT đã đăng nhập. Model cũ mang tên `chatgpt-web` bị chuyển sang
model Codex khi chạy (`_codex_safe_model`), nên các cấu hình đã lưu vẫn chạy được.

## Kiểm chứng việc gỡ

`tests/python/test_go_chatgpt_web.py` kiểm từng mục trên: module đã xoá, route đã mất, không còn nhắc
tên cũ trong mã, không còn biến môi trường trong tài liệu, và không còn tài liệu `docs/29-chatgpt-web.md`.

## Ghi chú

Nội dung đặc tả gốc (chi tiết kỹ thuật của lớp trình duyệt) không còn trong repo. Nếu cần, xem lịch sử git
trước commit gỡ. File này không khôi phục được nó.
