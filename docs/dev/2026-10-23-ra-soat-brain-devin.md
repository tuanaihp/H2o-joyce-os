# Rà soát tài liệu Devin nạp và chưng cất vào Joyce OS (23/10/2026)

Phạm vi: toàn bộ `brains/` (61 brain). Chỉ đọc, chưa sửa file nào. Dữ liệu nhạy cảm chỉ đếm, không ghi nguyên văn.
Công cụ rà soát nằm ở scratchpad phiên làm việc (audit.py, audit2.py, audit3.py), chạy lại được.

## 1. Quy mô

| Mục | Số liệu |
|---|---|
| Brain | 61 (5.746 file, 417 MB) |
| File ghi trong 10 ngày qua | 2.967 (đa số lúc 17:42 ngày 22/10, một đợt ghi hàng loạt) |
| `sources/` | 1.257 file |
| `wiki/` | 1.112 trang (gồm file khung) |
| Trang wiki có chữ trích từ file gốc | 337 |
| Apple Notes đã xuất vào `Ca Nhan - Thuy` | 625 ghi chú (563 xử lý, 62 bỏ qua), sửa từ 2018 đến 20/10/2026 |

Quy ước của Devin: `sources/D-*.md` luôn là stub trỏ về file gốc; chữ trích nằm trong trang wiki, mục "Nội dung đầy đủ từ nguồn".

## 2. Độ phủ so với thư viện gốc `D:\QUY TRÌNH H2O 2024`

Thư viện có 9.623 file, trong đó 6.986 file văn phòng (doc, docx, pdf, xls, xlsx, ppt, pptx). Đã nạp **298 file (4,3%)**.

| Thư mục gốc | Đã nạp / tổng file văn phòng |
|---|---|
| QUY TRÌNH H2O WEDDING | 125 / 158 |
| PDCA | 72 / 101 |
| PHÁP LÝ | 44 / 48 |
| QUY TRÌNH H2O STUDIO | 36 / 3.666 |
| HCNS | 6 / 32 |
| BẢNG MỤC TIÊU, LIVESTREAM, SOP NGHIÊN CỨU, BÀI TỐT NGHIỆP | đủ (7/7, 2/2, 2/2, 2/2) |
| **CEO - QUY TRÌNH DOANH NGHIỆP** | **0 / 2.651** |
| **7. He thong MTCV chi tiet** | **0 / 182** |
| **THUYH2O MAKEUP ACADEMY** | **0 / 107** |

Kết luận: các bộ nhỏ đã nạp gần đủ; ba thư mục lớn nhất chưa nạp (hoặc chỉ nạp rất ít).

## 3. Chất lượng chưng cất (337 trang có chữ trích)

- Đủ nội dung (>= 400 ký tự): **294 (87%)**. Mỏng (100 đến 400): 33. Gần như rỗng (< 100): 10.
- Hỏng phông khi trích PDF (`/Uhorn.tilde`...): chỉ 1 trang rõ (bìa lưu trình QLNS), 2 trang chữ rời từng ký tự.
- **Mất chữ tiếng Việt thành dấu `?`: 37 file** (20 ở Nhan Su, 9 ở Nhan Su - Makeup, còn lại rải rác). Nguyên nhân thường là file `.doc` cũ mã hoá TCVN3/VNI. Các bản mô tả công việc nhân sự bị ảnh hưởng nặng nhất.
- 21 trang có phần "Tóm tắt" chỉ là dòng đầu của chính đoạn trích (không phải tóm tắt thật).
- Toàn vẹn nguồn: 324 file gốc được tham chiếu, đường dẫn còn đúng hầu hết; chỉ 6 trang trích dẫn đường dẫn không còn (một số là tên rút gọn, không phải đường dẫn).

## 4. Cấu trúc và tra cứu

- `wiki/index.md` liệt kê 775 / 927 trang (83%). Brain lệch nhiều nhất: **ThuyH2O - Hoc Viec: 11 / 151 trang**. Joyce đọc index trước khi trả lời, nên trang không có trong index khó được tìm ra.
- ThuyH2O - Hoc Viec: 144 trang thiếu `created` / `source` trong frontmatter.
- Liên kết `[[...]]` gãy thật: khoảng 66 (49 cái ở Ca Nhan - Thuy trỏ tới thư mục Apple Notes thay vì file; 14 cái ở ThuyH2O Studio trong `memory/conversations`).
- 57 nguồn "processed" không có `wiki_links`; 35 nguồn trỏ tới trang wiki không tồn tại.
- Trùng lặp: chỉ file khung giống hệt nhau giữa các brain (`_session-handoff.md` x52, `index.md`...), và 1 cặp trang khảo sát nhân viên y hệt ở hai brain ThuyH2O.
- File ảnh lớn chưa có chữ tra cứu: 35 ảnh PNG (291 MB), nhiều nhất ở H2O Studio (bảng giá, logo). Nội dung trong ảnh Joyce không tìm kiếm được.

## 5. Luật của repo

- Gạch dài (em dash, cấm toàn hệ thống): **201 file** (92 wiki, 109 sources, vài file khác). Phần lớn là văn bản gốc chép nguyên (Apple Notes, tài liệu doc).
- 17 skill `h2o-y-tuong` có mô tả 151 đến 153 ký tự (giới hạn 150, phần thừa bị cắt im lặng).
- `group` rỗng: 0. Agent/workflow đặt sai thư mục cũ (`Joyce/agents`): 0.

## 6. Dữ liệu nhạy cảm

- **Không thấy** API key, token, JWT, mật khẩu hay số CCCD thật (4 cảnh báo ban đầu đều là báo nhầm).
- Số tài khoản ngân hàng: xuất hiện trong 16 file (kịch bản tư vấn bán hàng, một ghi chú "STK"). Có vẻ là số tài khoản công ty cố ý đưa cho khách; cần chủ xác nhận.
- Lương: cấu trúc lương 3P, mẫu hợp đồng lao động có mức lương nằm ở brain `Nhan Su` và `Ke Toan`. Brain chỉ mở cho nhân viên được gán đúng phòng (cơ chế phạm vi brain theo phòng ban trong `main.py`). Brain `ThuyH2O - Hoc Viec` không chứa số lương (đúng quyết định của chủ: chưa nhắc lương).
- Brain không nằm trong git, nên không bị đẩy lên GitHub; sửa hay xoá là không hoàn tác được.

## 7. Việc nên làm (xếp theo giá trị)

1. Nạp tiếp 3 thư mục chưa phủ (CEO - QUY TRÌNH DOANH NGHIỆP, MTCV, MAKEUP ACADEMY) theo từng đợt nhỏ, có kiểm tra chất lượng sau mỗi đợt.
2. Trích lại 37 file mất chữ tiếng Việt bằng bộ chuyển mã đúng (LibreOffice hoặc antiword kèm bảng mã), ưu tiên 20 file Nhan Su.
3. Bổ sung `ThuyH2O - Hoc Viec/wiki/index.md` cho 140 trang chưa có, và điền `created` / `source` còn thiếu.
4. Viết lại 21 phần "Tóm tắt" bị sao chép; điền chữ cho 10 trang rỗng.
5. Thay gạch dài bằng gạch nối ở `wiki/` (sources là bản chép gốc, tuỳ chủ).
6. Rút gọn mô tả skill `h2o-y-tuong` xuống dưới 150 ký tự (sửa ở mẫu rồi cập nhật 17 bản).
7. OCR các ảnh bảng giá lớn ở H2O Studio để Joyce tra cứu được.
