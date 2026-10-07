# Nhật ký phiên bản — H2O Joyce OS

## [1.0.2] - 2026-10-07
### Cải thiện
- **Sông dung nham chảy chậm và lan rộng như dòng sông thật**: đầu dòng bò tới từ từ (khoảng 1,5 phút một dòng), phía sau tràn rộng ra, hai bên là dải đất cháy sẫm, mặt dung nham có mảng vỏ nguội trôi chậm.
- **Chảy tới đâu cháy tới đó**: lửa bập bùng ở đầu dòng, khói đen cuồn cuộn bốc lên và trôi theo gió dọc đường dung nham vừa chảy qua, có đốm than âm ỉ phía sau.
- **Thanh Tốc độ dòng dung nham** trong Cài đặt → Giao diện Joyce → Quả tinh cầu (thẻ Lõi tinh cầu), từ 0,2 lần tới 3 lần.

## [1.0.1] - 2026-10-07
### Thêm mới
- **Nhóm Tổng quan** đứng đầu thanh bên, gồm 5 trang: **Bảng điều hành**, Hôm nay, **Phòng ban**, **Lịch & kế hoạch**, **Báo cáo**. Hôm nay giữ nguyên, chỉ chuyển vào nhóm này.
- **Bảng điều hành**: brief buổi sáng, 6 chỉ số việc, hàng đợi ưu tiên, nhịp vận hành theo lĩnh vực, sức khoẻ phòng ban, lịch hôm nay, sức khoẻ hệ thống và hoạt động gần đây. Toàn số thật, chưa nối nguồn thì nói thẳng, không bịa số.
- **Phòng ban**: từng phòng của từng thương hiệu, phòng có việc kẹt lên đầu; bấm vào là mở brain của phòng hoặc hỏi Joyce. **Lịch** gom nhắc hẹn mọi brain trong 7 ngày. **Báo cáo** dẫn tới đúng chỗ giữ số liệu hoặc nhờ Joyce viết.
- Nói "mở tổng quan", "mở báo cáo"... bằng giọng nói cũng tới đúng trang.

## [1.0.0-h2o] — 2026-10-07

### Bản phát hành nội bộ đầu tiên của H2O
- Fork độc lập từ Joyce OS (MIT), giữ nguyên LICENSE và ghi công tác giả gốc.
- Tách toàn bộ phụ thuộc hạ tầng ngoài: không kiểm tra bản mới, không kho gói ngoài,
  không telemetry; tài liệu đọc nội bộ qua /static/docs/view.html.
- Bảng điều khiển theo phòng ban H2O (46 brain), trang Cẩm nang với tab con:
  Tổng quan, Phòng ban, Fanpage, Zalo.
- Skill nghiệp vụ đầu tiên: phân loại lead, kế hoạch nội dung, review hiệu quả,
  comment → lead, chăm sóc sau dịch vụ.
