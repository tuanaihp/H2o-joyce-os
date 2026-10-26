# REVIEW.md — Joyce OS

Hướng dẫn cho reviewer (người hoặc agent) khi soi thay đổi trong repo này.
Khung theo phương pháp `ai-code-review` (7 tầng, Anthropic): finding phải có
bằng chứng, gắn nhãn đúng, không flag rác.

## Hỏng ở đây trông như thế nào

- **Dispatcher chết lặng**: task kẹt `ready`/`blocked` mãi mà không báo lỗi.
  Dấu hiệu hay gặp: method `TaskStore` bị đổi signature/mất (đã 2 lần xảy ra
  sau đợt port Javis — `next_idea_candidate`, `prepared(needs_approval)`),
  worker `tasks.py` gọi kwarg không tồn tại.
- **Fallback không nhảy**: engine hết quota/lỗi auth nhưng việc vẫn chết thay
  vì chuyển mắt xích. Hay nằm ở `aux_engine.swap()` — một nhánh bỏ qua chuỗi
  hoặc provider in câu "hết lượt" ra luồng `final` thay vì `error`.
- **Workflow không nhận input**: bước prompt thiếu `{{input}}` → agent không
  thấy dữ liệu đầu vào → kết quả rỗng ("thư mục trống").
- **Lộ secret**: API key, token, nội dung `.env`, auth.json đi vào log,
  chat, file vault, hoặc gửi ra MCP ngoài.
- **Wiki bị vi phạm luật**: ghi đè `wiki/log.md` (append-only), xoá mâu thuẫn
  thay vì giữ cả hai, sửa `sources/` (bất biến), bỏ qua `wiki/index.md`.
- **Quyền tự nâng**: đề xuất/agent tự thêm execution_mode, gọi tool ngoài
  scope, bỏ cổng duyệt `needs_approval`.
- **Nhân đôi hành động ngoài**: đổi engine chạy lại việc đã gọi tool (gửi
  tin, tạo file) — fallback chỉ được retry khi chưa làm gì.

## Luôn soi kỹ

- `server/tasks.py`, `server/task_store.py`: mọi thay đổi signature của
  `TaskStore` phải đối chiếu TOÀN BỘ caller trong `tasks.py`, `main.py`,
  `factory.py`. Bug signature lệch đã giết dispatcher 2 lần.
- `server/aux_engine.py`: `swap()`, `_FallbackChain`, nhận diện "hết lượt"
  — một nhánh sai là cả chuỗi fallback vô dụng.
- `server/factory.py`: pipeline nhà máy — nhầm điều kiện gate là tự áp thứ
  không nên áp.
- `server/main.py` (đường `_mk`/workflow): mode truyền vào engine chain,
  `task_models.*` routing.
- `plugins/`: code chạy trong server với quyền người dùng — min_mode khai
  sai = vượt quyền.
- `dashboard/i18n/*.json`: key thêm ở `vi.json` phải có ở `en.json`, ngược
  lại fallback sai ngôn ngữ.

## Bỏ qua (đừng flag)

- `node_modules/`, `**/node_modules/**`
- `brains/*/sources/**` — dữ liệu người dùng, bất biến
- `brains/*/wiki/log.md` phần entry cũ — append-only, không "sửa" lịch sử
- `*.example.json`, file backup `*.bak`, `dashboard/dist` (nếu có)
- Comment style, docstring tiếng Việt/Anh lẫn lộn — đó là convention repo.

## Luật

- Mỗi finding phải kèm `file:line` bằng chứng — không đoán từ tên hàm.
- Nhãn đúng 1 trong 3: **Important** (bug thật/đáng chặn), **Nit** (vặt),
  **Pre-existing** (có trước thay đổi — không đổ lỗi tác giả).
- Cap nit: tối đa **3** mỗi lượt — noise đắt hơn bug với tác giả agent.
- Summary mở đầu bằng SỐ ĐẾM ("2 Important, 1 Nit, 0 Pre-existing"); không
  có gì sửa thì nói thẳng "không có finding" — đừng bịa.
- Trước khi post, tự hỏi "finding này có refute được không?" — không chắc
  thì bỏ, không post.
- Không nói "test pass" khi chưa chạy test — trích lệnh + kết quả thật.
