# Quản trị skill toàn hệ thống - thiết kế

## Vấn đề

Skill hiện được chép riêng vào từng brain. Nhiều bản cùng slug không có nguồn gốc duy nhất,
khó biết bản nào mới, skill hợp phòng nào và bản nào đã lệch nội dung. Skill Learn chỉ cài vào
một brain đang chọn, chưa có kho lâu dài và chưa có cơ chế phân bổ có thể kiểm chứng, quay lui.

## Mục tiêu

- Có kho gốc dùng chung tại `<STATE_DIR>/skill-library/`, mỗi skill giữ cả gói và metadata.
- Phân loại skill theo một trong 10 nhóm việc cố định và các thẻ ngành tự do.
- Phân bổ một chiều từ kho vào `skills/` của từng brain theo gói lõi, nhóm việc và chuyên ngành.
- Giữ nguyên hợp đồng `skills:` của agent và đường đọc hiện tại của `skill_router`.
- Có thử nghiệm, phiên bản, kiểm chứng, quay lui và nhật ký duyệt trước khi nhân rộng.

## Phạm vi theo giai đoạn

1. Sửa lối mở từ Skill Learn để tới đúng skill hoặc plugin.
2. Kiểm kê chỉ đọc toàn bộ brain, xuất JSON và màn xem. Dừng để chủ repo duyệt số liệu.
3. Dựng kho, đồng bộ và màn Phân bổ. Chỉ migrate thật `Marketing - Makeup`.
4. Đổi Skill Learn thành cửa nhập kho, thêm gợi ý phòng ban và agent.
5. Thêm phiên bản, nhân theo đợt, quay lui, diff, số lượt dùng và nhật ký quản trị.

## Quyết định chính

- Kho nằm ngoài mọi brain, tại `<STATE_DIR>/skill-library/`.
- Metadata để ở sidecar, không chèn khóa riêng vào frontmatter `SKILL.md` nếu không cần.
- Ghi kho theo kiểu atomic và có khóa tiến trình.
- `group` luôn có giá trị. Nhóm việc dùng khóa ASCII cố định, nhãn hiển thị qua i18n.
- Brain nhận bản phái sinh một chiều. Bản đã tách riêng không bị đồng bộ ghi đè.
- Mọi lượt nhân bản dùng gói bất biến, kiểm chứng trước và giữ bản trước để quay lui.
- AI chỉ đề xuất. Mặc định skill mới chưa được cài vào brain nào.

## Ánh xạ phòng ban

- `Ban Hang*`: `ban-hang`
- `CSKH*`: `cskh`
- `Marketing*`: `marketing`
- `Nghien Cuu*`: `nghien-cuu`
- `San Xuat*`: `san-xuat`
- `Ke Toan*`: `ke-toan`
- `Nhan Su*`: `nhan-su`
- `H2O Studio`, `ThuyH2O*`: `dieu-hanh`
- `Ca Nhan*`: `ca-nhan`
- Skill hệ thống dùng chung: `cong-cu`

Brain không khớp quy tắc phải nằm trong báo cáo chờ quyết định, không tự đoán.

## Rủi ro và rào an toàn

- Bước kiểm kê không ghi vào `brains/` và không ghi state thật.
- Test đặt `JOYCE_STATE_DIR` sang thư mục tạm trước khi import module server.
- Trước mọi thay đổi thật dưới `brains/` phải kiểm đường dẫn, sao lưu và kiểm chứng sau ghi.
- Migrate thật chỉ áp dụng cho `Marketing - Makeup` sau khi chủ repo duyệt báo cáo kiểm kê.
- Hash nội dung phải chuẩn hóa khác biệt CRLF và LF khi hợp đồng yêu cầu so nội dung logic.
- Plugin nhập từ Skill Learn luôn `enabled: false`.
- Gọi model chỉ đi qua `_skill_learn_ask` và task `skill-learn`, không mở thêm đường có công cụ.

## Không làm trong cổng đầu

- Không dựng kho và không migrate brain trước khi báo cáo bước kiểm kê được duyệt.
- Không sửa frontmatter agent ở brain khác.
- Không bật plugin, tự khởi động cùng máy hoặc gửi dữ liệu ra ngoài.
