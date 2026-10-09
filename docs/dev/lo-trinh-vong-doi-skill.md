# Lộ trình vòng đời skill: học từ Javis, trạng thái trong Joyce

Javis có đặc tả "Đo skill + Chuẩn viết skill" (2026-07-16) mô tả bốn hệ con theo thứ tự
phụ thuộc. Tài liệu này ghi lại thứ tự đó và trạng thái THẬT trong Joyce, kiểm tra bằng code,
không theo mô tả.

| Hệ con | Nội dung (theo Javis) | Trạng thái trong Joyce | Bằng chứng |
|---|---|---|---|
| A. Vòng đời skill | Đo skill nào thật sự được dùng, trạng thái, hiển thị | Đã có | `server/skill_usage.py` (telemetry một chiều: `use_count > 0` là chắc chắn có dùng) |
| B. Chuẩn viết skill | Hạn mức description, chuẩn viết, skill là package | Một phần | Trần description 150 ký tự (`SKILL_DESC_MAX`); skill package có `references/`, `scripts/` được mirror (`system_sync.mirror_skills`). Bộ chuẩn viết riêng: chưa thấy |
| C. Curator gộp | Gộp các skill chồng chéo, dựa trên A và B | Có pipeline, chưa đối chiếu hết | `server/learn.py` có curator (`_curator_scope`, gộp việc nền theo mẻ) |
| D. `/learn` từ nguồn | Học trực tiếp từ tài liệu nguồn | Có pipeline, chưa đối chiếu hết | `/learn/enable`, `server/learn.py`, staging trong `Joyce/learn-staging/` |

## Thứ tự và lý do

Javis ghi rõ: C phụ thuộc cả A lẫn B. Không có telemetry thì curator gộp mù (không biết skill
nào đang sống), không có chuẩn viết thì không biết gộp về hình gì. D độc lập, làm sau cũng được.

Joyce đã làm A, nên C đứng trên nền có thật. Trước khi làm thêm gì cho C, cần làm rõ hai điều:

1. Chuẩn viết (B) còn thiếu phần nào so với trần description và cấu trúc package.
2. Curator (C) hiện làm gì với dữ liệu telemetry: đọc `Joyce/skill-usage.json` hay chưa.

## Việc chưa kiểm chứng

Trạng thái C và D ở trên là "có pipeline", không phải "đủ như đặc tả". Muốn ghi "xong" thì
phải đối chiếu từng tiêu chí của đặc tả với code và test, rồi mới cập nhật bảng này.
