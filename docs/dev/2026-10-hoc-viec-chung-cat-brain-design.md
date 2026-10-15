# Chưng cất chương trình Học việc vào brain - spec

Trạng thái: **đã duyệt 2026-10-15, cấp học việc đã chưng cất** vào `ThuyH2O - Hoc Viec`. Ngày: 2026-10-15.
Nguồn: `tai-lieu-update-tu-openai/update-dao-tao-nhan-vien/1-PROMPT_CLAUDE_CODE_H2O_HOC_VIEC_14_NGAY.md`.
Chạm tới: brain `ThuyH2O - Hoc Viec` và các brain phòng liên quan (`ThuyH2O Studio`, `ThuyH2O - Noi Quy va Bieu Mau`, `ThuyH2O - Hoc Vien`).

## Vấn đề

- Chương trình 14 ngày có nhiều lớp: quy định, lộ trình ngày, rubric, must-pass, gate, nhánh nghề,
  bài học. Sẽ còn thêm nhiều cấp độ khác.
- Kiến thức hiện nằm rải rác: 4 phiếu khảo sát tuần ở `ThuyH2O - Hoc Viec`, biểu mẫu và hợp đồng
  ở `ThuyH2O - Noi Quy va Bieu Mau`, quy trình nhập học ở `ThuyH2O - Hoc Vien`. Ghi chú trong memory
  đã xác nhận việc tìm kiếm phải dò nhiều brain.
- Agent `truong-hoc-viec` có mục "Nhiệm vụ chính" còn trống, nên chưa có chỗ nào mô tả chương trình
  mà agent đọc được một cách có kiểm soát.
- Dữ liệu cá nhân (điểm, chấm công, bài nộp, ảnh khách) không được đi vào brain. Chỉ kiến thức
  đã duyệt được chưng cất.

## Nguyên tắc (lấy từ mục 11 của prompt)

Tách ba lớp, ánh xạ thẳng vào cấu trúc brain có sẵn:

| Lớp | Nội dung | Nơi ở trong brain | Ai đọc |
|---|---|---|---|
| Nguồn gốc | Tài liệu chương trình đã được người có thẩm quyền ban hành | `sources/hoc-viec/` (bất biến, chỉ thêm) | Chỉ khi chưng cất |
| Kiến thức đã duyệt | Lộ trình, rubric, must-pass, gate, nhánh nghề, mẫu tin nhắn | `wiki/hoc-viec/` (chỉ trang `status: active`) | Agent và skill |
| Phần thiếu nội dung | Nhánh hoặc chính sách chưa đủ nguồn | `wiki/hoc-viec/` (`status: draft`) | Người duyệt |

Dữ liệu cá nhân (điểm, bài nộp, chấm công, rủi ro về từng người, ảnh khách) **ở lại cơ sở dữ liệu
của nền tảng đào tạo**, không vào brain. Brain chỉ nhận số liệu gộp, ẩn danh, khi có người duyệt.

## Đề xuất

### 1. Cấu trúc wiki đa cấp độ

```
wiki/hoc-viec/
  index.md                       # danh mục cấp độ đang có và trạng thái từng cấp
  cap-do/<ma-cap>/               # mỗi cấp độ một thư mục, thêm cấp mới không sửa cấp cũ
    tong-quan.md                 # mục tiêu, đối tượng, thời lượng, điều kiện qua cấp
    lo-trinh-ngay-0-14.md        # Ngày 0, 1-4, 5-6, 7 (gate), 8-10, 11-12, 13, 14
    nhanh-nghe/<ma-nhanh>.md     # Makeup, Hair, Combined: mỗi nhánh một trang, nhánh chưa đủ để DRAFT
    rubric-100-diem.md           # trọng số, ngưỡng, rubric version
    must-pass.md                 # năm điều kiện bắt buộc, không bù bằng tổng điểm
    gate-va-tong-ket.md          # gate 1, thi thực hành, tổng kết, các kết quả được phép
    bai-hoc/<so>-<ten>.md        # một bài một trang: checklist, bằng chứng cần nộp
    tin-nhan-mau.md              # mẫu tin chào, nhắc hạn, kết quả (có version)
    chinh-sach.md                # chỉ trạng thái chờ HR/pháp chế xác nhận cho tới khi duyệt
```

Mỗi trang có frontmatter tối thiểu: `status` (draft | active | superseded), `phien_ban`, `cap_do`,
`nguon` (đường dẫn tới `sources/`), `nguoi_duyet`, `ngay_duyet`. Đây là cùng quy ước với trang SOP
đã đề xuất trong `docs/dev/2026-10-process-factory-design.md`, nên không tạo quy ước thứ hai.

### 2. Vòng đời chưng cất

1. Tài liệu mới vào `sources/hoc-viec/` (ghi rõ phiên bản và người ban hành).
2. Chưng cất thẳng vào `wiki/hoc-viec/` kèm tham chiếu nguồn. Phần có nguồn rõ là `active` (dùng ngay);
   chỉ phần thiếu nội dung mới là `draft`. Không dùng `wiki/y-tuong/` (đó là kho ý tưởng của phòng). Tài liệu dài áp dụng quy tắc 3 lượt của `ingest-source`.
3. `lint-wiki` kiểm: trang mồ côi, thiếu nguồn, thiếu `status`, mâu thuẫn giữa rubric và must-pass.
4. Người có thẩm quyền duyệt từng trang: `draft` thành `active`, bản cũ thành `superseded` (giữ lại).
5. Ghi `wiki/log.md`. Agent `truong-hoc-viec` và skill chỉ đọc trang `active`.

### 3. Agent và skill trong brain

- Agent `truong-hoc-viec`: điền mục "Nhiệm vụ chính" (hiện đang trống), chỉ đọc `wiki/hoc-viec/`
  trang `active`, và không ghi điểm hay nhận xét về cá nhân vào brain.
- Không tạo 11 skill trong brain. Các skill trong prompt là năng lực của **nền tảng đào tạo** (code,
  quyền, cơ sở dữ liệu). Brain chỉ cần một skill tri thức, `h2o-hoc-viec-chuong-trinh`, mô tả cách
  đọc lộ trình, rubric và must-pass, kèm đường dẫn tới trang `active` tương ứng.
- Giữ lại `h2o-y-tuong` và `h2o-studio-thuyh2o-hoc-viec` đã có.

### 4. Cấu trúc để thêm cấp độ

Thêm cấp độ mới là thêm một thư mục `cap-do/<ma-cap>/` và một dòng trong `wiki/hoc-viec/index.md`.
Không sửa trang của cấp cũ. Cấp mới đi qua cùng vòng đời chưng cất (mục 2). Đây là lý do cấu trúc
theo cấp độ được chọn thay vì một trang lớn.

## Không làm

- Không đưa điểm, bài nộp, chấm công, tên học viên, hay nhận xét cá nhân vào brain hoặc memory.
- Không để AI tự chấm, tự cho đậu hay rớt, hoặc tự ghi kết luận về một người vào wiki.
- Không khẳng định "học việc không lương" hay phân loại quan hệ lao động. Chờ HR/pháp chế xác nhận.
- Không chép nội dung ảnh khách hàng hay ảnh bằng chứng vào brain.
- Không xây dựng nền tảng đào tạo (bảng cơ sở dữ liệu, Telegram, giao diện) trong spec này. Đó là
  một việc riêng, sẽ có spec riêng sau khi kiến thức đã nằm đúng chỗ.

## Quyết định đã chốt (2026-10-15)

1. **Phiếu khảo sát 4 tuần** là đánh giá kết quả từng tuần để lên cấp. Đề xuất (chờ xác nhận): quy đổi
   điểm ESI theo nhóm rubric; lên cấp khi trung bình đạt ngưỡng, không tuần nào trượt must-pass, điểm
   tăng qua các tuần, và mentor xác nhận.
2. **Tài liệu V1** không có. Joyce soạn bản tạm: `sources/hoc-viec/H2O_JOYCE_HR_LEARNING_OS_HOC_VIEC_V1.md`.
3. **Nơi đặt:** `ThuyH2O - Hoc Viec`, thuộc đào tạo nhân sự, chia cấp độ: học việc, thử việc, nhân viên,
   chuyên gia.
4. **Người duyệt:** trưởng đào tạo duyệt nội dung chương trình; HR và pháp chế duyệt chính sách.
5. **Nhánh Hair:** nháp.

## Bước tiếp theo

Cấp 1 Học việc (14 ngày) và Cấp 2 Thực tập sinh Makeup (56 ngày) đã chưng cất, ở
`wiki/hoc-viec/cap-do/hoc-viec/` và `wiki/hoc-viec/cap-do/thuc-tap-sinh/`. Link trong wiki dùng đường dẫn
đầy đủ vì hai cấp có trang trùng tên (rubric, must-pass, tổng quan).

Lộ trình theo sơ đồ của chủ studio (15/10): Học việc, Thực tập sinh, Nhân viên, Chuyên viên cấp cao,
Chuyên gia, Quản lý, Trưởng phòng, CO-Giám đốc, CTHĐQT. CTV cùng tầng Nhân viên, hai đường vào (thuê ngoài,
từ Thực tập sinh), đã chưng cất đủ ở `cap-do/ctv/` theo tài liệu Cấp 3 (giai đoạn đánh giá 3 tháng, KPI có công
thức, rubric 85/70, must-pass 6 điều). Thử việc không phải cấp riêng. Cấp 4 Nhân viên Makeup (12 tháng) đã chưng cất ở `cap-do/nhan-vien/`;
quy trình dịch vụ trỏ tới SOP có sẵn ở `San Xuat - Makeup` và `San Xuat - Boi Toc`. Cấp 5 Chuyên viên cấp cao đã chưng cất ở `cap-do/chuyen-vien-cap-cao/`; sau cấp này tách hai hướng
độc lập Chuyên gia hoặc Quản lý (theo tài liệu Cấp 5). Cấp 6 Chuyên gia đã chưng cất ở `cap-do/chuyen-gia/` dạng đề xuất (`muc_do: de-xuat`, v0.1), vì tài
liệu nguồn tự ghi là chưa được H2O duyệt. Quản lý nhóm (tài liệu Cấp 7) và Trưởng phòng (Cấp 8) đã chưng cất ở
`cap-do/quan-ly/` và `cap-do/truong-phong/` dạng dùng được; mục tiêu số là tạm, lương chưa đề cập. Quy tắc khảo sát 4 tuần áp dụng tạm (`cap-do/hoc-viec/khao-sat-4-tuan`).
Giám đốc vận hành (tài liệu Cấp 9) đã chưng cất ở `cap-do/giam-doc/` dạng dùng được; Chủ tịch HĐQT (Cấp 10) ở
`cap-do/chu-tich-hdqt/` dạng đề xuất, vì tài liệu nguồn yêu cầu đối chiếu Điều lệ và pháp lý. Lộ trình đã đủ 9 bậc theo sơ đồ.
Chủ studio chốt 15/10: chức danh CO-Giám đốc, chín phòng (thêm Hậu kỳ, Vận hành, Học viện), H2O là hộ kinh doanh nên CTHĐQT là chức danh nội bộ.
