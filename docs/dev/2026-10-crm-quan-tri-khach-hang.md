# CRM quản trị khách hàng cho phòng ban - kế hoạch (TÀI LIỆU SỐNG)

Trạng thái (26/10/2026): **mới rà soát và lập kế hoạch, chưa code.** Chờ chủ chốt 4 câu hỏi ở mục 8 rồi mới làm P1.

## Cách dùng tài liệu này

Mỗi lần làm thêm thì cập nhật mục 6 (giai đoạn) và THÊM một dòng vào mục 9 (nhật ký). Đừng viết lại lịch sử. Phiên sau chỉ cần đọc mục 0, 2 và 9.

## 0. Tóm tắt

- File mẫu: `tai-lieu-update-tu-openai/update-quan-tri-crm/JOYCE_QUAN_LY_SHOP_REVID_PROTOTYPE_V1.html` (một trang HTML, dữ liệu mẫu "Tiệm bánh Mây", lưu bằng `localStorage`, chưa có server).
- Phần liên quan CRM trong file mẫu: **Danh bạ khách, Pipeline cơ hội, Việc cần làm, "Thêm nhanh bằng AI" (dán đoạn chat để ra liên hệ), Hộp chat khách có khung thông tin CRM, Chăm sóc khách (phân khúc + lịch nhắc)**.
- Các tab còn lại của file mẫu (Đơn bán hàng, Kho, Thu chi, Nhân sự và lương, Marketing, Ảnh AI, Báo giá) **không thuộc phạm vi CRM** và Joyce đã có chỗ riêng hoặc chưa cần. Không làm trong kế hoạch này.
- **Đề xuất vị trí: đặt CRM làm tab thứ ba của trang Chatbot** (thanh bên, nhóm Năng lực, id `conversations`), cạnh "Hòm thư bot" và "Bot". Tên tab: **Khách hàng**. Lý do ở mục 3.
- Joyce đã có sẵn nền: bảng `customers` (tên, tag, ghi chú, metadata), `conversations`, `messages` trong `server/conversations.py`. Kế hoạch là **mở rộng nền đó**, không dựng kho thứ hai.
- Nguyên tắc tiết kiệm quota (đã chốt trong repo): đếm, lọc, nhắc hạn, chia phòng do **code làm**; model chỉ đọc đoạn chat để trích thông tin và soạn nội dung.

## 1. Mục tiêu và không làm

Mục tiêu: nhân viên các phòng làm việc trực tiếp với khách (Bán hàng, CSKH, Học viên...) có một chỗ xem **mỗi khách là ai, đã nói gì, đang ở bước nào, việc gì đang chờ**, và Joyce tự thu thập thông tin từ hội thoại để hồ sơ khách ngày một đầy, rồi chưng cất thành tri thức wiki của phòng.

Không làm:
- Sao chép giao diện hay thương hiệu của file mẫu (đó là bản thảo ý tưởng, màu và chữ sẽ theo theme Joyce).
- Dựng đơn hàng, kho, thu chi (ngoài phạm vi).
- Tự gửi tin cho khách (CRM chỉ đọc và ghi hồ sơ; gửi tin vẫn đi qua Hòm thư bot và luật quyền sẵn có).
- Loop quét hàng loạt để "làm đẹp hồ sơ" (luật repo cấm, 16/08/2026). Việc trích thông tin chạy **khi có tin mới của khách**, theo ngưỡng cố định.

## 2. Hiện trạng đã kiểm chứng trong code (26/10/2026)

| Có sẵn | Ở đâu |
|---|---|
| Kho khách xuyên kênh: `customers(name, tags_json, note, metadata_json)` | `server/conversations.py` dòng 75 |
| Hội thoại, tin nhắn, tiếp quản người/AI, chưa đọc | `conversations.py`, giao diện `dashboard/conversations.js` (hai tab `inbox`, `bot`) |
| Hàm đọc/ghi cho CRM: `danh_sach_khach`, `khach`, `hoi_thoai_cua_khach`, `dat_tag_khach`, `dat_ghi_chu_khach`, `cho_tra_loi`, `thong_ke_khach` | `conversations.py` dòng 975 đến 1102 |
| Gói CRM ở Kho cài đặt (`joyce.khach-hang-crm`), chỉ đọc hộp thư và ghi tag, ghi chú | `docs/28-hoi-thoai-khach.md` |
| Kanban theo phòng, ghi việc đã xong (`ghi_viec_xong`) | `server/tasks.py`, `server/viec_mau.py` (v1.3.27) |
| Quyền nhân viên: phạm vi phòng, `_STAFF_DEPT_EDIT` chặn ghi `/kanban` | `server/main.py` dòng 21496 |

**Chưa có** (đây là phần file mẫu bổ sung): số điện thoại, công ty, nguồn khách; **cơ hội (deal) theo giai đoạn**; **việc chăm sóc gắn với khách**; **dòng thời gian tương tác**; **phân khúc khách**; **trích thông tin tự động từ đoạn chat**; **khách thuộc phòng nào**.

Điểm cần kiểm lại trước khi code (chưa xác minh): route HTTP nào đang phơi `danh_sach_khach` ra dashboard (tìm trong `main.py` không thấy `/customers`; có thể do store pack cắm vào hoặc nằm file khác). P1 bắt đầu bằng việc xác minh điểm này.

## 3. Vì sao đặt ở tab thứ ba của Chatbot

Đã cân 3 chỗ:

| Chỗ | Ưu | Nhược |
|---|---|---|
| **Tab "Khách hàng" trong Chatbot (đề xuất)** | Khách vốn nằm ở đây; nhân viên đang mở trang này mỗi ngày; bấm khách là sang hội thoại ngay; không thêm mục thanh bên; dữ liệu cùng một kho | Trang Chatbot đã đông (Hòm thư, Bot) |
| Mục thanh bên riêng "CRM" | Dễ thấy | Thêm một mục nữa cho nhân viên; tách khỏi hội thoại; trùng nhiệm vụ |
| Tab trong Kinh doanh (`kinhdoanh`) | Gần số liệu bán hàng | Nhân viên CSKH, Học viên không làm ở đó; xa hộp thư |

Quyết định theo phòng: **không tạo CRM riêng từng phòng**. Cùng một kho khách, mỗi phòng thấy **khách thuộc phòng mình** (cột `phong`/brain), chủ thấy tất cả. Giống cách việc mẫu đã chốt: nhân viên chỉ thấy việc của phòng chính, "Toàn khối" không gộp phòng.

## 4. Thiết kế

### 4.1 Dữ liệu (mở rộng `conversations.py`, cùng file SQLite, không kho mới)

- `customers` thêm cột: `phone`, `company`, `source`, `brain` (phòng đang phụ trách), `owner` (nhân viên phụ trách). Thêm bằng `ALTER TABLE` có kiểm tra, không phá dữ liệu cũ; sao lưu một lần trước khi đổi schema như cách đã làm với việc cắt nhóm.
- `crm_deals(id, customer_id, brain, title, value, stage, owner, created_at, updated_at, closed_at)`. Giai đoạn mặc định: Mới, Đang tư vấn, Chờ chốt, Đã chốt, Mất. Danh sách giai đoạn **sửa được theo phòng** (Bán hàng khác CSKH).
- `crm_events(id, customer_id, kind, text, by, created_at)`: dòng thời gian (đổi giai đoạn, ghi chú, việc xong, tin quan trọng). Không chép lại cả tin nhắn, chỉ trỏ `conversation_id`.
- **Việc chăm sóc không tạo bảng mới**: dùng Kanban của phòng (`metadata.customer_id`), hạn nằm ở trường hạn sẵn có. Nhờ vậy nhân viên vẫn thấy ở Việc → Công việc, không có hai chỗ để quên.

### 4.2 Giao diện (tab "Khách hàng", file mới `dashboard/crm.js`, i18n `crm.*`)

Ba chế độ giống file mẫu nhưng theo theme Joyce:
1. **Danh bạ**: danh sách khách bên trái (tên, SĐT, công ty, nhãn, ngày chat cuối), khung chi tiết bên phải (thông tin, dòng thời gian, cơ hội, nút "Mở hội thoại", "Tạo việc chăm sóc").
2. **Pipeline**: cột theo giai đoạn của phòng, bấm "Chuyển bước" (không kéo thả ở bản đầu để chạy được trên điện thoại).
3. **Việc cần làm**: việc Kanban có `customer_id`, lọc hôm nay, trễ hạn.

Thêm: ô **"Thêm nhanh bằng AI"** (dán đoạn chat, email, danh thiếp -> trích tên, SĐT, công ty, nhu cầu, rồi **hiện bản nháp cho nhân viên xác nhận** trước khi lưu, không tự ghi).

Trên điện thoại: một cột, bấm khách mở chi tiết có nút quay lại (giống Hòm thư bot).

### 4.3 Joyce thu thập và lưu thông minh hơn

Đây là phần chủ nhấn mạnh. Làm theo thứ tự rẻ đến đắt:
1. **Luật cố định, không model**: khi khách nhắn, bắt SĐT, email bằng quy tắc; gắn `source` theo kênh; cập nhật "chat cuối".
2. **Model chỉ khi có đủ điều kiện**: khi hội thoại có từ N tin khách mới kể từ lần trích trước (N cố định, đề xuất 8) hoặc nhân viên bấm "Cập nhật hồ sơ từ chat". Model đọc đoạn mới và trả JSON: nhu cầu, ngân sách, hạn, phản đối, bước tiếp. Kết quả vào `customers.metadata_json` và một dòng `crm_events`, **không** ghi đè trường nhân viên đã sửa tay.
3. **Chưng cất lên wiki phòng**: nút **"Ghi nhớ cách xử lý khách này"** (cùng mẫu với "Ghi nhớ cách làm này" của việc mẫu) chưng ngay vào `wiki/khach-hang/<slug>.md` của brain phòng. Không tự chưng hàng loạt.
4. Gói `joyce.khach-hang-crm` hiện có vẫn dùng được: các tool `crm_*` đọc cùng kho nên hỏi bằng lời ("khách nào chờ hơn 2 tiếng") vẫn chạy.

### 4.4 Quyền và riêng tư

- Nhân viên mọi chức vụ: xem và sửa khách của phòng mình, thêm việc chăm sóc, đổi giai đoạn (giống quyết định việc mẫu: thêm được thì xoá được). **Xoá khách** chỉ Trưởng phòng trở lên, vì xoá mất lịch sử.
- Route mới nằm ngoài `_STAFF_DEPT_EDIT` nhưng **phải ép về phạm vi phòng của nhân viên** bằng `_STAFF_SCOPE` như `viec_mau.py` đã làm; có test chặn đọc khách phòng khác.
- Số điện thoại, email chỉ hiển thị cho người trong phòng; log không in nội dung hồ sơ.
- Hồ sơ khách là dữ liệu cá nhân của người ngoài: mặc định **không** đưa vào wiki phần SĐT, email nguyên văn (wiki ghi "khách A, nhu cầu X", không ghi số).

## 5. Khác biệt so với file mẫu (cố ý)

| File mẫu | Bản Joyce |
|---|---|
| Dữ liệu `localStorage` trên một trình duyệt | Lưu server, dùng chung cả phòng |
| Pipeline cố định 3 cột | Giai đoạn sửa được theo phòng |
| "Tạo việc chăm sóc" chỉ hiện thông báo | Tạo việc thật trong Kanban |
| "AI đã nhận diện 1 liên hệ" lưu thẳng | Hiện nháp, nhân viên xác nhận mới lưu |
| Ghi chú tự viết tay | Joyce gợi ý, người xác nhận |
| Có đơn hàng, kho, thu chi gắn trong CRM | Ngoài phạm vi |

## 6. Giai đoạn

Mỗi giai đoạn nhỏ, có test và merge riêng. Đặt xí chỗ số phiên bản trước khi code theo `docs/quy-uoc-dev.md`.

| GĐ | Nội dung | Kết quả |
|---|---|---|
| **P0** | Xác minh route khách hiện tại, đọc `dashboard/conversations.js` và test CRM cũ, chốt 4 câu hỏi mục 8 | Tài liệu này cập nhật |
| **P1** | Mở rộng schema (cột + `crm_deals` + `crm_events`), API đọc/ghi có ép phạm vi phòng, test quyền | Backend + test, chưa có giao diện |
| **P2** | Tab "Khách hàng": Danh bạ + chi tiết + dòng thời gian, i18n vi/en, di động | Nhân viên xem và sửa hồ sơ |
| **P3** | Pipeline + việc chăm sóc nối Kanban (`customer_id`) | Theo dõi cơ hội và việc |
| **P4** | Trích thông tin: luật cố định, nút "Cập nhật hồ sơ từ chat", ngưỡng N, nháp xác nhận | Joyce thu thập thông minh hơn |
| **P5** | "Ghi nhớ cách xử lý khách này" chưng lên wiki phòng; phân khúc và lịch nhắc (Chăm sóc khách) | Tri thức tích luỹ |

## 7. Rủi ro

- Trang Chatbot đang đông; thêm tab thứ ba phải giữ bố cục di động. Giảm bằng cách tab Khách hàng tải lười (không gọi API khi chưa mở).
- `ALTER TABLE` trên kho hội thoại đang chạy: phải có bản sao lưu và đổi trong một giao dịch.
- Trích bằng model có thể sai, sinh thông tin bịa về khách: luôn hiện nháp, ghi rõ nguồn là "Joyce trích từ chat", người xác nhận mới thành sự thật.
- Dữ liệu cá nhân khách: xem 4.4.
- Nhiều phiên Claude đang sửa dở `main.py`, `console.js`, `index.html`: làm trong worktree riêng từ `origin/main`, không đụng thư mục chính.

## 8. Câu hỏi chờ chủ chốt

1. Đặt **tab "Khách hàng" trong trang Chatbot** (đề xuất) hay mục thanh bên riêng?
2. Một khách có thể thuộc **nhiều phòng** cùng lúc (ví dụ vừa Bán hàng vừa CSKH), hay mỗi khách một phòng phụ trách?
3. Giai đoạn pipeline mặc định cho từng phòng: dùng 5 giai đoạn ở 4.1 hay anh có quy trình riêng (ví dụ Học viên: Đăng ký, Học thử, Đóng học phí, Đang học)?
4. Có cho Joyce **tự trích hồ sơ** khi đủ N tin (phải nhớ là tốn lượt model) hay chỉ khi nhân viên bấm nút?

## 9. Nhật ký

- 26/10/2026: Rà soát file mẫu và nền sẵn có trong `conversations.py`; viết kế hoạch; chưa code.
