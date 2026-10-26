# Chat công việc hằng ngày - kế hoạch (TÀI LIỆU SỐNG)

Trạng thái (26/10/2026): **P1 đến P4 đã code và đang trên nhánh `claude/chat-cong-viec-1-3-27` (v1.3.27)**. **P5 (khu quản lý ở Tổng quan) chưa làm.** Xem mục 10 để biết chính xác đã làm gì, mục 3b để biết nó nằm ở file nào.

## Cách dùng tài liệu này (đọc trước khi làm gì liên quan)

Đây là tài liệu sống: mỗi lần nâng cấp thêm thì **cập nhật mục 2 (quyết định), mục 7 (giai đoạn) và THÊM một dòng vào mục 10 (nhật ký)**. Đừng viết lại lịch sử. Phiên sau chỉ cần đọc **mục 0 + mục 2 + mục 10** là hiểu đang ở đâu, khỏi quét lại code (đỡ tốn quota). Mục 3 là bản đồ file đã kiểm chứng ngày 26/10/2026; nếu code đã đổi thì sửa mục 3 trước.

## 0. Tóm tắt trong 12 dòng

- Nhân viên làm việc hằng ngày ngay trong **Trò chuyện**: mở brain phòng mình là thấy các **việc mẫu** (chip bấm được), bấm là có form ngắn rồi Joyce chạy.
- Mỗi phòng (và mỗi brain cá nhân) có nút **+** để tự thêm việc mẫu của mình.
- Làm xong bấm **"Đã xong"**: việc được ghi vào bảng **Việc → Công việc** của chính phòng đó (cột Xong). Không dựng tab mới cho việc xong.
- Mỗi lần xong, Joyce lưu hồ sơ việc vào `sources/`, và theo **ngưỡng cố định** mới chưng cất lên `wiki/` để dần hiểu quy trình kinh doanh H2O.
- Nhân viên chỉ thấy việc của **phòng chính** (brain đầu tiên được gán), kể cả khi đang đứng ở "Toàn khối".
- Quản lý/chủ chỉnh danh mục ở **Tổng quan → Phòng ban**.
- Lấy ý tưởng giao diện từ màn chat RevidAPI (chip chế độ + chip gợi ý việc), **không** sao chép giao diện, thương hiệu, hay hệ credit của họ.
- Nguyên tắc tiết kiệm quota: đếm, lọc, ngưỡng, ghi sổ do **code làm**; model chỉ soạn nội dung.

## 1. Mục tiêu và không làm

Mục tiêu: nhân viên không phải biết cách hỏi Joyce; việc làm xong tự thành tri thức quy trình của H2O.

Không làm: hệ credit/tính tiền theo lượt; tab riêng cho nhân viên; loop quét hàng loạt để "nâng cấp tri thức" (luật repo cấm, 16/08/2026); sao chép thương hiệu RevidAPI.

## 2. Quyết định đã chốt (chủ repo)

| Ngày | Quyết định |
|---|---|
| 26/10/2026 | Làm trong **Trò chuyện**, đổi phòng bằng ô chọn brain ở đầu trang; Tổng quan chỉ để quản lý. |
| 26/10/2026 | Chọn "Toàn khối": chỉ hiện việc của **phòng chính** của người đó (không gộp các phòng). |
| 26/10/2026 | **Mọi phòng có nút +** để chủ tự thêm hạng mục việc. |
| 26/10/2026 | Việc xong chỉ cần **xác nhận Done**, rồi nằm ở bảng Công việc riêng của phòng (đã có sẵn, xem mục 3). |
| 26/10/2026 | Brain cá nhân Thủy/Tuấn: em đề xuất việc theo tri thức sẵn có (mục 6.2): ý tưởng kinh doanh, tạo khoá học, banner, content, báo cáo họp và giải pháp. |
| 26/10/2026 | Tài liệu này là nguồn sự thật cho tính năng; phiên sau đọc tài liệu này, không quét lại. |
| 26/10/2026 | **Chưng cất**: bấm "Ghi nhớ cách làm này" là chạy NGAY, không chờ đủ 3 hồ sơ. Ngưỡng 3 hồ sơ vẫn giữ làm đường tự động. |
| 26/10/2026 | Việc nhân viên tự thêm **không cần quản lý duyệt** (thêm được thì xóa được). Mọi chức vụ, kể cả Học việc, đều thêm/xóa được trong phòng mình. |
| 26/10/2026 | "Toàn khối": **không gộp các phòng**, chỉ hiện việc phòng chính (chủ xác nhận). |
| 26/10/2026 | **"Đã xong" do Joyce tự đề nghị** khi việc chạy xong (thanh "Việc X xong chưa?" với nút Đã xong / Chưa), không bắt nhân viên đi tìm nút. |

## 3. Hiện trạng code (đã kiểm chứng 26/10/2026)

- **Khối gợi ý ở màn chat trống**: `dashboard/chat-kb.js` (lúc viết còn là file chưa commit của phiên khác, kiểm tra trước khi dựng thêm). Nó vẽ "Tri thức trong brain" bằng chip; logic đọc `wiki/index.md` nằm ở `triThucPanel()` trong `dashboard/camnang.js`. Khối "Việc hằng ngày" mới đặt **ngay dưới** khối này, cùng kiểu chip.
- **Menu "+" ở ô chat**: `dashboard/composer-plus.js`, registry `register({id, order, icon, label, panel|submenu|run})`. Mục sẵn có: attach(10), brain_file(30), commands(40), connections(50), partners(60). Thêm `viec_mau` với `order: 20`.
- **Bảng công việc theo phòng**: trang Việc → Công việc, `renderKanban(el)` trong `dashboard/console.js`. Đã lọc theo brain đang chọn, có cột chờ duyệt/xong, nút "Duyệt xong", form thêm việc (`knAdd` gọi `POST /kanban/task`). **Chưa cần tab mới.**
- **API Kanban** (`server/tasks.py`): `POST /kanban/task` (title, intent, route, priority, brain, chat_id, idempotency_key...), `POST /kanban/task/move` (đổi trạng thái). **Bẫy**: `/kanban/task` luôn xếp việc vào hàng chờ (`triage`) để bộ điều phối chạy; dùng nó để "ghi nhận việc đã xong" sẽ làm việc bị CHẠY LẠI, tốn quota hai lần. Cần tham số mới tạo thẳng ở trạng thái `done` (mục 7, P3).
- **Phân quyền phòng ban**: `h2o_departments.brains_of_staff(staff)` trả danh sách brain theo thứ tự admin gán; **phần tử đầu = phòng chính**. `_staff_scope_roots` / `_STAFF_SCOPE` chặn brain ngoài phạm vi. Quyền sửa của nhân viên: `_STAFF_DEPT_EDIT = ("/agents", "/skills", "/workflows", "/kanban")` trong `server/main.py` (thêm `"/viec-mau"` khi làm P2).
- **Thống kê tự có**: `/api/joyce/v1/overview/departments` đếm `tasks.done24/open/blocked/running` theo từng phòng; Việc xong ghi vào Kanban sẽ **tự hiện** ở Tổng quan → Phòng ban và tab Sơ đồ.
- **Gắn nhãn hội thoại**: bảng `messages` (conversations.db) có sẵn cột `meta_json`, `task_id`, `step_id`; dùng `meta_json` ghi `{"viec_mau": "<slug>"}` cho tin được gửi từ một việc mẫu.
- **Brain phòng ban dùng chung bộ agent/workflow mẫu giống nhau** (giam-dinh-*, tu-cai-tien-agent...) nên **không** lấy danh mục việc từ `agents/` hay `workflows/`; lấy từ các trang SOP trong `wiki/` (ví dụ Bán hàng có "Quy trình tư vấn báo giá online").
- **Công cụ tạo ảnh/banner**: tool `joyce_generate_image`. **Chưng cất**: skill hệ thống `ingest-source`. **Bài học agent**: cơ chế `JOYCE_LESSON`.

## 3b. Bản đồ code ĐÃ LÀM (v1.3.27)

| Việc | File |
|---|---|
| API, đọc/ghi việc mẫu, hồ sơ, chưng cất | `server/viec_mau.py` (đăng ký ở `server/main.py`, ngay sau `knowledge_sky`) |
| Bộ việc mẫu đi kèm app (by: seed) | `system/viec-mau/<tên brain>/<slug>.md` (6 bộ: Ban Hang, Ban Hang - Sales Hinh Anh, CSKH, CSKH - Sau Dich Vu va Khieu Nai, Ca Nhan - Thuy, Ca Nhan - Tuan). Brain con ("A - B") dùng bộ của brain cha ("A") nếu chưa có bộ riêng. Sinh bằng script, sửa tay file cũng được |
| Ghi việc đã xong thẳng cột Xong | `TasksFeature.ghi_viec_xong` (`server/tasks.py`) + tham số `result` của `TaskStore.enqueue` (`server/task_store.py`) |
| Giao diện: khay chip, form, nút +, thanh Đã xong, mục menu "+" | `dashboard/viec-mau.js` (khay `#vmTray` trong `index.html`, thêm vào `CHAT_NODE_IDS` của `console.js`) |
| Chữ | khoá `vm.*` trong `i18n/vi.json`, `en.json` (de chưa có, theo thông lệ) |
| Icon thêm | nhóm `viec-mau` trong `icons.manifest.json` rồi `python tools/gen_icons.py` |
| Test | `tests/python/test_viec_mau.py`, `test_viec_mau_nhan_vien.py`, `tests/js/test_viec_mau.js` |

Ghi đè theo lớp: file trong `<brain>/viec-mau/` đè bản seed cùng slug; xóa việc seed = ghi file `hidden: true` (không đụng file của app). Hồ sơ mỗi lần làm: `<brain>/sources/viec-lam/<ngày>-<slug>-<mã8>.md`; mốc chưng cất: `<brain>/Joyce/viec-mau-state.json`.

**Khác với bản thiết kế ban đầu (đã chủ động đổi):**
- Khay chip nằm **ngay trên ô nhập** (`#vmTray`), không chèn vào `#chatArea`, để không giẫm lên khối "Tri thức trong brain" của `chat-kb.js` (file đó còn là WIP chưa commit của phiên khác; khi nó được merge, hai khối tự cùng hiện vì khay này coi `.chat-kb` là con hợp lệ của khung chat trống).
- Nút "Đã xong" **không** gọi `POST /kanban/task` mà gọi `POST /viec-mau/xong`. Lý do thứ hai ngoài bẫy chạy lại: `_STAFF_DEPT_EDIT` chặn nhân viên thường GHI vào `/kanban` (chỉ Trưởng phòng trở lên), nên nhân viên sẽ bị 403. `/viec-mau` không nằm trong danh sách đó nên mọi chức vụ dùng được.
- Chưa gắn `meta_json.viec_mau` vào tin chat (cần chạm vào đường lưu tin của `app.js`); thay bằng việc client nhớ việc đang chạy và gửi `slug` + `key` lúc bấm Đã xong. Làm sau nếu cần truy ngược tin nhắn.
- Việc chưng cất dùng đúng đường "Nạp vào wiki" có sẵn (`_claim_and_spawn`, capability `mcp-read`, engine phụ), nên chạy ngay kể cả khi "AI tự vận hành" của brain đang tắt. Model rẻ là model NỀN mà chủ chọn ở trang Models (chưa ép riêng).

## 4. Thiết kế

### 4.1 Màn hình Trò chuyện (nhân viên)

Màn chat trống: khối "Tri thức trong brain" (có sẵn) + khối **"Việc hằng ngày"** bên dưới. Chip gom theo nhóm (ví dụ Tư vấn, Chăm sóc, Báo cáo); chip cuối mỗi nhóm là **+**. Bấm chip mở form ngắn ngay trong khung chat (các ô nhập của việc, nút Gửi, nút Hủy). Gửi xong là một tin chat bình thường kèm `meta_json.viec_mau`. Mục "Tác vụ" trong menu "+" mở cùng danh sách khi đang gõ dở. Chọn brain nào thì hiện việc của brain đó; chọn "Toàn khối" thì hiện việc của **phòng chính**.

### 4.2 Định dạng "việc mẫu"

Thư mục phẳng ở gốc brain, giống `agents/` và `workflows/`: `<brain>/viec-mau/<slug>.md`. Gọi là "việc mẫu" để khỏi nhầm với "task" của Kanban.

```
---
type: viec-mau
title: Tư vấn báo giá online        # ngắn, hiện trên chip
group: Tư vấn                        # nhóm hiển thị, không để trống
icon: message-circle                 # tên icon có trong icons.manifest.json
inputs:                              # tối đa 5 ô; không có thì chỉ cần prompt
  - { key: khach, label: Tên khách, type: text, required: true }
  - { key: goi, label: Gói quan tâm, type: select, options: [Studio, Ngoại cảnh] }
route: auto                          # auto | wf:<slug> | agent:<slug>
sop: wiki/quy-trinh/<trang>.md       # trang SOP gốc (nếu có), Joyce đọc trước khi làm
by: seed                             # seed | tên người thêm
order: 10
hidden: false
---
Thân file = prompt, dùng {khach}, {goi} để chèn giá trị ô nhập.
```

### 4.3 Nút +

Form nhỏ: tên việc, nhóm (chọn nhóm có sẵn hoặc gõ nhóm mới), nội dung lệnh, tuỳ chọn ô nhập, icon. Ghi qua một API riêng `server/viec_mau.py` (router, theo mẫu `knowledge_sky.py`): `GET /viec-mau?brain=`, `POST /viec-mau` (tạo/sửa/ẩn). API tự đặt slug, chặn trùng tên, chặn ghi đè việc `seed` khi chưa xác nhận, và kiểm quyền brain theo phạm vi nhân viên. Có ở **mọi** brain, kể cả brain cá nhân.

### 4.4 Chạy một việc

Chip -> form -> ghép prompt -> gửi vào chat hiện tại (engine đang chọn) với `meta_json.viec_mau`. Nếu việc có `sop`, nhắc Joyce đọc trang đó trước. Việc dài, nhiều bước: dùng `route: wf:<slug>` để đưa sang workflow chạy nền, kết quả tự về chat (luật mặc định của repo).

### 4.5 Xong việc -> bảng Công việc

Dưới kết quả của một việc mẫu hiện nút **"Đã xong"**. Bấm: (1) tạo bản ghi ở Kanban của đúng brain với trạng thái `done` ngay từ đầu (tham số mới, không qua hàng chờ), tiêu đề = tên việc + tham số chính, gắn `idempotency_key` để bấm đúp không nhân đôi; (2) chuyển sang bước 4.6. Nhân viên mở **Việc → Công việc** của phòng là thấy việc ở cột Xong.

### 4.6 Vòng nhớ (chưng cất theo cách ít tốn quota)

1. **Ghi sổ (code, 0 quota):** mỗi lần xong, ghi `sources/viec-lam/<yyyy-mm-dd>-<slug>-<n>.md`: ai làm, giờ, ô nhập, kết quả cuối, nhân viên có sửa kết quả không.
2. **Đếm ngưỡng (code):** với mỗi việc mẫu, đếm hồ sơ mới từ lần chưng cất gần nhất. Đủ **3 hồ sơ mới**, hoặc nhân viên bấm "Ghi nhớ cách làm này", mới xếp **một** việc nền `[Chưng cất] <tên việc>`.
3. **Chưng cất (model, rẻ):** dùng skill `ingest-source` cập nhật trang `wiki/quy-trinh/viec-mau/<slug>.md`: cách làm thực tế, biến thể hay gặp, lỗi hay gặp, so với SOP gốc đổi ở đâu. Đặt model nền cho việc này là model rẻ/miễn phí (GLM-4.7-Flash chạy local qua Ollama đã cài ngày 26/10/2026, hoặc Z.ai miễn phí).
4. Nhân viên sửa kết quả đáng kể thì ghi thêm bài học theo cơ chế `JOYCE_LESSON` hiện có.
5. Cập nhật `wiki/index.md` để Joyce tra cứu được trang mới (chỉ mục là nơi Joyce đọc đầu tiên).

Không dùng loop quét định kỳ. Mọi bước chạy **tại thời điểm làm việc**, đúng nguyên tắc repo.

### 4.7 Quyền

Đọc danh sách: theo phạm vi brain của nhân viên. Thêm/sửa/ẩn: người có quyền sửa brain đó (nhân viên được sửa trong phòng mình, như `/skills`, `/workflows`, `/kanban`). Việc do nhân viên thêm ghi `by: <tên>` để quản lý nhìn ra. Brain cá nhân chỉ chủ brain thấy.

### 4.8 Luật repo phải tuân khi làm

Giữ số phiên bản trước khi code (`docs/quy-uoc-dev.md`); màu chỉ dùng token theme (hai giao diện); mọi chữ qua `t()` và thêm khoá vi/en; không dùng gạch dài; có test JS/Python; CHANGELOG ngắn cho điện thoại; mô tả skill tối đa 150 ký tự nếu có tạo skill.

## 5. Quản lý (Tổng quan → Phòng ban)

Thêm mục "Việc làm được" trong chi tiết từng phòng: danh sách việc mẫu (sửa, ẩn, xoá), số lần chạy 7 ngày, hồ sơ chờ chưng cất, nút "Chưng cất ngay". Bảng điều hành chỉ hiện số liệu tổng (việc nào chạy nhiều nhất), không có nút làm việc.

## 6. Danh mục việc mẫu đề xuất

Đây là **ứng viên**, sẽ đối chiếu với các trang SOP thật trong `wiki/` của từng brain ở P1 rồi mới tạo; chủ duyệt danh sách trước.

### 6.1 Phòng ban

- **Bán hàng:** tư vấn báo giá online; kịch bản chốt sale (studio, ngoại cảnh); soạn tin chăm sóc sau chụp; báo giá gói chụp.
- **CSKH:** xử lý khiếu nại; chăm sóc sau dịch vụ; kịch bản gọi xe cho khách.
- **Kế toán:** lập phiếu thu/chi; đối soát cuối ngày; tổng hợp báo cáo thuế tháng.
- **Marketing:** viết bài fanpage; kịch bản video; tạo banner.
- **Nhân sự:** tạo mô tả công việc; phiếu đề nghị tuyển dụng; hợp đồng thử việc; đánh giá sau phỏng vấn.
- **Sản xuất:** checklist ngày chụp; bàn giao hậu kỳ; checklist makeup/tóc.
- **Vệ sinh, Truyền thông, Văn thư:** checklist cuối ca; phản hồi khủng hoảng; soạn văn bản/quyết định.

### 6.2 Brain cá nhân (đề xuất theo tri thức hiện có)

**Cá nhân - Thủy** (wiki đã có các nhóm đào tạo, content-marketing, kinh doanh, sáng tạo, vận hành):
- *Khoá học:* tạo khoá học mới từ khung 7 giai đoạn; soạn nội dung một buổi dạy; báo giá khoá học; kịch bản tuyển sinh.
- *Content:* kịch bản video; bài đăng fanpage; podcast truyền cảm hứng; chương sách makeup.
- *Banner:* banner khoá học; ảnh bìa sự kiện (dùng `joyce_generate_image`).
- *Kinh doanh:* kịch bản tư vấn chốt sale; chăm sóc học viên (nhịp 2 tuần/lần).
- *Họp và giải pháp:* tóm tắt nội dung buổi họp; đề xuất giải pháp cho một vấn đề.

**Cá nhân - Tuấn** (wiki mới có `y-tuong/`):
- *Ý tưởng kinh doanh:* đánh giá một ý tưởng; kế hoạch 30 ngày; phân tích đối thủ.
- *Khoá học:* dàn ý khoá; *Banner:* tạo banner; *Content:* bài viết, kịch bản.
- *Họp và giải pháp:* tóm tắt buổi họp; đề xuất giải pháp.
- *Học tập:* luyện tiếng Anh 10 phút (đã có agent `giao-vien-tieng-anh`).

## 7. Giai đoạn triển khai

| GĐ | Nội dung | Nghiệm thu |
|---|---|---|
| P0 | Chốt hiện trạng: xem lại `chat-kb.js` đã commit chưa; giữ số phiên bản; duyệt danh sách ứng viên mục 6 | Chủ duyệt danh sách |
| P1 (XONG 1.3.27) | Định dạng `viec-mau`, `GET /viec-mau`, khối "Việc hằng ngày" ở chat, chip điền form rồi gửi, seed thí điểm 3 brain (Bán hàng - Sales, CSKH, Cá nhân - Thủy) | Chọn brain thấy đúng việc; "Toàn khối" chỉ ra việc phòng chính; chạy được một việc |
| P2 (XONG 1.3.27) | Nút **+** ở mọi brain (thêm/sửa/ẩn), mục "Tác vụ" trong menu "+" của ô chat, quyền nhân viên | Nhân viên thêm việc trong phòng mình; không thêm được phòng khác |
| P3 (XONG 1.3.27) | Nút "Đã xong": tham số tạo việc thẳng `done` trong `server/tasks.py`, ghi sổ `sources/viec-lam/` | Việc hiện ở cột Xong; bấm đúp không nhân đôi; bộ điều phối không chạy lại |
| P4 (XONG 1.3.27) | Vòng chưng cất theo ngưỡng, model rẻ, cập nhật `wiki/index.md` | 3 hồ sơ sinh ra đúng một trang wiki; không có loop nền |
| P5 (CHƯA LÀM) | Mục "Việc làm được" ở Tổng quan → Phòng ban; seed các phòng còn lại | Quản lý sửa/ẩn việc, thấy số lần chạy |

Mỗi giai đoạn: một nhánh riêng, một số phiên bản, test xanh, CHANGELOG, rồi cập nhật mục 10.

## 8. Rủi ro

- Việc xong ghi qua API cũ sẽ bị chạy lại (xem mục 3): bắt buộc làm tham số `done` ở P3 trước khi bật nút.
- Danh mục việc quá dài thì khó dùng: giới hạn hiển thị 8 chip mỗi nhóm, còn lại ở "Xem thêm".
- Brain phòng dùng chung agent mẫu: không gắn việc vào agent chung, gắn vào `route` và `sop`.
- `chat-kb.js` đang do phiên khác sửa dở: kiểm tra trước, làm trên worktree riêng.

## 9. Câu hỏi mở

Cả ba câu hỏi của bản đầu đã được chủ trả lời 26/10/2026 (xem mục 2). Còn mở:

1. Có muốn chip hiện cả khi chat đã có tin (hiện chỉ hiện khi khung chat trống; lúc đang chat dùng menu "+" > "Việc hằng ngày") không?
2. Bong bóng tin của nhân viên đang hiện NGUYÊN lệnh đã ghép (dài). Có muốn rút gọn thành "Tư vấn báo giá online: Chị Mai" và giấu phần lệnh không? (cần gắn `meta_json`, xem mục 3b)
3. Bộ việc mẫu của các phòng còn lại (Kế toán, Marketing, Nhân sự, Sản xuất, Vệ sinh, Truyền thông, Văn thư) chờ chủ duyệt danh sách ở mục 6.1 rồi thêm vào `system/viec-mau/`.

## 10. Nhật ký cập nhật (THÊM DÒNG MỚI Ở CUỐI, không sửa dòng cũ)

- **26/10/2026** - Viết kế hoạch lần đầu. Kiểm chứng code: khối chat trống do `chat-kb.js`; Kanban theo brain đã có đủ cột Xong (không cần tab mới); `POST /kanban/task` luôn xếp hàng chờ nên cần tham số tạo thẳng `done`; phòng chính = phần tử đầu của `brains_of_staff`. Chốt 5 quyết định ở mục 2. Chưa có code.
- **26/10/2026 (v1.3.27)** - Chủ trả lời 3 câu hỏi mở và bảo bắt đầu code. Đã làm P1 đến P4 trên nhánh `claude/chat-cong-viec-1-3-27`: API `/viec-mau` (đọc, thêm/sửa, xóa, Đã xong, Ghi nhớ), 6 bộ việc mẫu seed, khay chip trên ô nhập + form + nút + + thanh "Đã xong?" + mục menu "+", ghi hồ sơ `sources/viec-lam/`, chưng cất theo ngưỡng 3 hoặc nút. Đã thử trong trình duyệt thật (sandbox cổng 7791): chip, form, kiểm ô bắt buộc, gửi, thanh Đã xong, việc vào cột Xong, thêm và xóa việc, điện thoại không tràn ngang. Phát hiện: nhân viên thường bị chặn ghi `/kanban` (xem mục 3b); `origin/main` thiếu hàm `TaskStore.next_idea_candidate` khiến bộ điều phối lỗi mỗi nhịp khi brain chưa bật tự vận hành (bản sửa nằm trong thay đổi chưa commit của một phiên khác ở thư mục chính). Việc kế tiếp: P5 và bộ việc mẫu các phòng còn lại.
