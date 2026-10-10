# Process Factory cho Joyce - spec

Trạng thái: **chờ chủ repo duyệt** (chưa viết plan, chưa code). Ngày: 2026-10-11.
Nguồn: đề xuất "Phương án vận hành chốt cho Joyce" và phân tích trong phiên 10/10 - 11/10.
Liên quan: `brains/Brain Default/sources/joyce-operating-loop-2-spec-v1.md` (Operating Loop 2.0).

## Vấn đề

- Ý tưởng concept, quy trình mới và sửa quy trình cũ đang đi chung một luồng
  (`xu-ly-y-tuong-moi` ghi vào `wiki/y-tuong/`). Không có chỗ phân loại, nên kết quả bị trộn.
- Joyce chưa có khái niệm SOP đang hiệu lực. Các trang SOP đã nhập
  (`San Xuat - Hinh Anh/wiki/`) có `status: active` và mã hiệu, nhưng không có quy tắc nào
  ngăn sửa trực tiếp hay đánh dấu bản cũ. Chưa brain nào có `wiki/quy-trinh/`.
- Concept mới vào bảng bán mà chưa thử. Lỗi ở khâu chuẩn bị sẽ lặp lại với mọi khách mua concept đó.

## Phạm vi (làm, theo thứ tự)

Mỗi mục là một lát nhỏ, làm và kiểm xong rồi mới sang mục sau.

1. **Chọn loại đề xuất ở cổng ý tưởng**: ý tưởng concept, quy trình mới, hay sửa quy trình cũ.
   Ghi loại vào frontmatter của kết quả. Đây là phần đáng làm nhất: gần như không tốn thêm
   thời gian và ngăn wiki bị trộn.
2. **SOP đang hiệu lực chỉ đổi qua Change Request.** Bản cũ chuyển thành `SUPERSEDED`, không xoá.
   Dùng trường `status` có sẵn, thêm `version` và `supersedes`.
3. **Concept mới thử 1-3 bộ chụp trước khi vào bảng bán.** Dùng cờ PILOT, không thêm trạng thái
   ngoài DRAFT, PILOT, ACTIVE, SUPERSEDED. Chậm có chủ đích: bảo vệ tiền chụp và uy tín.
4. **Duyệt theo rủi ro, số người duyệt tối thiểu.** Việc trong một phòng chỉ cần trưởng phòng.
   Chỉ thêm người khi ảnh hưởng phòng khác. Tránh chuỗi duyệt nhiều người vì đó là chỗ nghẽn lớn nhất.
5. **Radar xu hướng dạng bản tin tuần** (do lịch nhắc chạy, không phải trang).
   **Thư viện concept dạng bảng**, làm khi đã có số booking theo concept.

### Sáu khu đề xuất trước đó được xử lý thế nào

| Khu | Cách làm | Lý do |
|---|---|---|
| Tổng quan theo trạng thái | Không làm riêng, dùng trang Việc | Kanban đã đếm theo cột |
| Radar xu hướng | Bản tin tuần | API engine không có web search; Xiaohongshu thường cần đăng nhập |
| Pipeline ý tưởng | Kanban có sẵn, thêm nhãn loại đề xuất | Cột "Chờ duyệt" đã có |
| Thư viện concept | Bảng, sau khi có số booking | Chưa có nguồn số booking |
| Quy trình liên quan | Lọc theo `status` trong `wiki/index.md` | Thông tin đã có trong frontmatter |
| Nhật ký quyết định | Dùng `wiki/log.md` và `wiki/y-tuong/` | Đã ghi sẵn |

## Không làm (ngoài phạm vi)

- **Trang Nghiên cứu sáu khu.** Bốn khu đã có chỗ; hai khu còn lại thiếu dữ liệu. Đây là điểm
  chủ repo cần chốt (xem bên dưới) vì đã có yêu cầu làm trang.
- Thư mục `workflows/` ở gốc repo. Lõi workflow đi kèm app như system skill, chỉ Admin phát hành.
  Mỗi brain vẫn giữ `workflows/` phẳng riêng.
- Năm skill mới. Gộp vào `h2o-y-tuong` và một skill soạn SOP. Phát hành là một bước workflow.
- Vòng đời 13 trạng thái.
- Mười KPI. Giữ ba chỉ số đo được ngay: thời gian ra quyết định, số lần người phải chạm vào một
  thay đổi SOP, số SOP quá hạn rà soát.
- Khoá cả thư mục `skills/`, `.claude/`, `memory/`. App đồng bộ `.claude/skills` từ `skills/`.
  Nếu làm khoá, chỉ khoá từng SOP có trạng thái ACTIVE.
- Sửa dữ liệu trong `brains/` khi chưa có plan đã duyệt. Thư mục này không nằm trong git nên
  không hoàn tác được bằng git.

## Quyết định chính và lý do

- **Không tạo trang mới ở giai đoạn này.** Bốn trong sáu khu đã có chỗ. Trang mới sẽ thêm việc
  bảo trì trước khi dữ liệu chính (booking, nguồn web) có.
- **Cổng ý tưởng dùng lại luồng có sẵn.** Task tiền tố `[Ý tưởng]` đã tự chạy (`server/tasks.py`)
  và đã có workflow `xu-ly-y-tuong-moi`. Thêm loại bằng tiền tố hoặc một trường trong task, không
  dựng màn hình mới. Cách cụ thể sẽ chốt ở plan.
- **Pilot ở brain `Nghiên Cứu - Concept Hình Ảnh` trước.** Các phòng khác làm sau khi quy trình chạy ổn.
- **Chỉ số pilot dùng số liệu có sẵn** trong `server/h2o_departments.py`: tỉ lệ ảnh khách yêu cầu
  sửa (Nhân Sự Photoshop), đánh giá khách (Nhân Sự Hình Ảnh). Thời gian chuẩn bị và chi phí một bộ
  ghi tay trong biên bản pilot.

## Rủi ro

- Ghi nhận bị bỏ quên, bảng trạng thái sai sau vài tuần. Giảm: ít trạng thái, mỗi bước có một người chịu trách nhiệm.
- Thêm vòng duyệt làm chậm. Giảm: duyệt L1 chỉ cần trưởng phòng; đo thời gian trước và sau khi bật.
- Pilot dùng khách thật. Phải báo trước và thống nhất giá; không dùng khách chưa đồng ý.
- Chưa kiểm tra quyền ghi theo từng file của nhân viên. Cần xem code quyền trước khi hứa khoá SOP.

## Cần chủ repo chốt trước khi viết plan

1. **Có làm trang Nghiên cứu sáu khu không?** Đề xuất: không, giai đoạn này. Nếu chủ muốn có, cho biết
   khu nào làm trước; spec sẽ sửa lại.
2. **Brain pilot.** Đề xuất: `Nghiên Cứu - Concept Hình Ảnh`.
3. **Cách chọn loại đề xuất.** Tiền tố trong task, hay trường trong form? Đề xuất: tiền tố (ít code nhất).
4. **Ai được đề nghị Change Request, ai duyệt L1.** Đề xuất: mọi nhân viên đề nghị; trưởng phòng duyệt.

## Mẫu frontmatter cho SOP (wiki/quy-trinh/)

```yaml
---
type: wiki
status: active            # active (đang hiệu lực) | superseded (đã thay thế)
phien_ban: 2              # tăng khi đổi qua Change Request
ngay_ra_soat: 2026-12-01  # đến ngày này phải rà soát; quá hạn thì trang báo
thay_the: chup-album-v1   # slug bản cũ, nếu có (bản cũ giữ nguyên, status: superseded)
---
```

Quy tắc: SOP có `status: active` không sửa trực tiếp, muốn đổi thì tạo ý tưởng `loai: sua-quy-trinh`.
Khi bản mới được duyệt, bản cũ đổi `status: superseded` và không xoá. Mã hiệu và lần ban hành
của SOP gốc (ví dụ CG.CN.0003, lần 01) giữ nguyên trong thân trang.

## Bước tiếp theo

Sau khi chủ duyệt spec: viết plan theo mẫu trong `docs/dev/quy-trinh-ke-hoach.md`, rồi làm
T1 = mục 1 ở brain pilot. Mỗi task kết thúc bằng một bước kiểm lặp lại được.
