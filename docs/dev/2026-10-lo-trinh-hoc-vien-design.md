# Tab Lộ trình: kích hoạt, gửi bài và chấm điểm học viên - thiết kế

Trạng thái: chủ studio giao "hoàn thiện toàn bộ" ngày 2026-10-15 · Phiên bản dự kiến: 1.3.9

## Vấn đề

Brain `ThuyH2O - Hoc Viec` đã có đủ khung 9 bậc (spec `2026-10-hoc-viec-chung-cat-brain-design.md`), nhưng:

- **Chưa có bài học thật và chưa có bài kiểm tra có đáp án.** Học việc có lộ trình 14 ngày, rubric,
  gate, must-pass, nhưng trang nhánh Makeup tự ghi "Còn thiếu: danh sách bài cụ thể". Các cấp từ
  Nhân viên trở lên là khung vai trò (KPI, scorecard), không phải giáo trình theo ngày.
- **Chưa có chỗ vận hành.** Trưởng phòng không có nút nào để bắt đầu lộ trình cho một người mới, học
  viên không có chỗ đọc bài và làm bài, điểm không được ghi ở đâu.

Tài liệu nguồn cấp 1 (`1-PROMPT...HOC_VIEC_14_NGAY.md`) mô tả đúng phần nền tảng này: gửi bài theo
ngày, nộp bài, mentor chấm, Gate 1, thi thực hành, phê duyệt cuối. Lần chưng cất đầu cố ý tách phần
đó ra để làm sau khi kiến thức đã nằm đúng chỗ. Đây là phần đó.

## Mục tiêu

1. Trưởng phòng bấm **Kích hoạt lộ trình** cho một nhân viên mới, chọn mentor và ngày bắt đầu.
2. Mỗi ngày đào tạo, bài của ngày đó **tự mở** cho học viên, và nếu có Telegram thì **tự gửi tin**.
3. Học viên đọc bài, làm **bài kiểm tra trắc nghiệm, chấm tự động** ngay khi nộp.
4. Mentor nhập điểm phần phải quan sát bằng mắt: Gate 1, khảo sát tuần, rubric 100 điểm, must-pass.
5. Hệ thống tính **đề xuất kết quả** theo đúng ngưỡng đã có trong brain. Trưởng phòng bấm kết luận.

## Ràng buộc quan trọng nhất: không tốn quota

Chủ studio yêu cầu: "mọi quy trình sau này chỉ cần một AI agent lọc hoặc không cần tốn quota quá
nhiều đã có thể gửi được và đánh giá chấm điểm được". Thiết kế chọn **không gọi model ở bất kỳ bước
vận hành nào**:

| Bước | Cách làm | Gọi model? |
|---|---|---|
| Mở bài theo ngày | Tính từ ngày bắt đầu và ngày nghỉ được duyệt, lúc đọc | Không |
| Gửi tin Telegram | Vòng nền 30 phút, gửi thẳng Bot API, có dấu đã gửi để không gửi trùng | Không |
| Chấm bài trắc nghiệm | So đáp án trong file bài học | Không |
| Chấm rubric, must-pass, khảo sát | Mentor nhập số, server cộng theo trọng số | Không |
| Đề xuất kết quả | Luật cố định theo ngưỡng của brain | Không |

AI chỉ cần khi **soạn hoặc sửa bài học** (một lần, do người dùng nhờ trong chat), không cần mỗi lần
có học viên mới.

## Quyết định chính

### 1. Bài học nằm trong brain, điểm nằm ngoài brain

- **Bài học** là file markdown trong `wiki/hoc-viec/cap-do/<cap>/bai-hoc/`, mỗi ngày một file,
  frontmatter có `ngay`, `tieu_de`, `nhanh`, và danh sách `kiem_tra` (câu hỏi, lựa chọn, đáp án,
  giải thích). Trưởng đào tạo sửa bài như sửa mọi trang wiki, không cần code.
- **Điểm, bài nộp, nhận xét về từng người** nằm ở `STATE_DIR/lo_trinh.json`, không vào brain.
  Đúng quyết định đã chốt ở spec chưng cất: dữ liệu cá nhân không vào brain.
- Server **gỡ đáp án** trước khi gửi bài cho học viên. Học viên không đọc được brain Học Việc vì
  phạm vi brain của họ là brain phòng mình.

### 2. Một cấp có bài học thì mới kích hoạt được

Bản này soạn đủ 15 bài (ngày 0 đến 14) cho **Học việc nhánh Makeup**, từ 15 SOP thật của brain
`San Xuat - Makeup`. Các cấp khác hiện là khung vai trò: tab hiện chúng trên thang lộ trình kèm số
bài bằng 0 và nút kích hoạt bị tắt, kèm câu "chưa có bài học". Thêm bài cho cấp nào thì cấp đó tự mở.

### 3. Luật chấm (lấy từ brain, không đặt mới)

- **Rubric 100 điểm** (6 nhóm, trọng số của `rubric-100-diem`): 80 trở lên đạt, 65 đến 79 cần bổ
  sung, dưới 65 trưởng phòng xem xét.
- **Must-pass** (5 điều): trượt một điều thì không bù bằng điểm.
- **Khảo sát tuần** (phần quản lý chấm, 3 tiêu chí thang 10-100): theo `khao-sat-4-tuan`, trung bình
  từ 70 và tuần sau không thấp hơn tuần 1.
- **Bài kiểm tra kiến thức** (mới, đề xuất tạm): trung bình các bài đã đến hạn từ **70%**, và không
  bỏ bài nào. Ghi rõ là tạm trên trang luật chấm của brain.
- Kết quả cuối luôn do **người bấm** (trưởng phòng hoặc quản trị). Hệ thống chỉ đề xuất.

### 4. Ai làm được gì

| Việc | Quản trị | Trưởng phòng (trong phòng mình) | Mentor của học viên | Học viên |
|---|---|---|---|---|
| Kích hoạt lộ trình | Có | Có | Không | Không |
| Thêm ngày nghỉ được duyệt | Có | Có | Không | Không |
| Chấm Gate 1, khảo sát, rubric, must-pass | Có | Có | Có | Không |
| Kết luận cuối | Có | Có | Không | Không |
| Đọc bài, làm bài kiểm tra | Không | Không | Không | Chỉ của mình |

Kiểm quyền ở server, không tin vai trò client gửi lên.

### 5. Gửi tin

Kênh chắc chắn có: **tab Lộ trình của chính học viên** (bài hôm nay nằm trên cùng). Kênh thêm:
Telegram, nếu trưởng phòng điền chat ID của học viên lúc kích hoạt và Joyce đã nối bot Telegram. Tin
gồm tên bài và đường dẫn mở tab. Gửi lỗi thì lần sau thử lại, không làm hỏng dữ liệu học.

## Không làm trong bản này

- Bài học cho Thực tập sinh, CTV và các cấp trên (cần nội dung từ trưởng đào tạo).
- Nộp ảnh hoặc video bằng chứng thực hành ngay trong tab (mentor xác nhận checklist là đủ cho bản đầu).
- Gửi qua Zalo (cần đi qua MCP, không gửi thẳng được như Telegram).
- Tự đổi chức vụ nhân viên khi đạt (trưởng phòng đổi ở trang Nhân viên, như hiện nay).

## Rủi ro

- **Bài do Joyce soạn từ SOP** có thể sai ý người viết SOP. Giảm bằng cách: mỗi câu hỏi trích đúng
  câu trong SOP, mỗi bài ghi nguồn, và trang ghi rõ "trưởng đào tạo rà soát".
- **Ngày bắt đầu sai múi giờ.** Dùng ngày Việt Nam (UTC+7) như phần còn lại của Joyce.
- **Học viên đổi phòng giữa chừng.** Trưởng phòng mới vẫn thấy vì kiểm theo phòng hiện tại của học viên.
