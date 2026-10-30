# Quản trị skill toàn hệ thống - kế hoạch

Spec: `docs/dev/2026-10-quan-tri-skill-design.md` · Trạng thái: đang làm

## Mục tiêu

Cho anh nhìn đúng skill vừa cài, sau đó kiểm kê chính xác toàn bộ bản skill hiện có và dừng ở
cổng duyệt trước khi tạo kho hoặc thay đổi bất kỳ brain nào.

## Ràng buộc chung

- Không ghi vào `brains/` trong bước 0 và bước 1.
- Test server dùng `JOYCE_STATE_DIR` và brain tạm trước khi import module.
- i18n Việt và Anh có cùng tập khóa, mọi lệnh `t()` dùng khóa literal.
- Không dùng em dash. Không dùng icon ngoài `dashboard/icons.manifest.json`.
- Mỗi bước có phiên bản riêng, test xanh rồi mới merge fast-forward vào `main`.

## Các task

- [x] T0.1 - Truyền trang đích và slug từ thẻ đã cài trong Skill Learn.
  - Kiểm: test JS xác nhận nút ghi đúng slug và điều hướng qua Alpine nav.
- [x] T0.2 - Trang Kỹ năng và Plugin nhận mục chờ, cuộn tới và làm nổi bật đúng thẻ.
  - Kiểm: test JS chạy mã thật với DOM giả cho cả skill và plugin.
- [x] T0.3 - Chạy test liên quan, test i18n, kiểm tra giao diện hai theme, phát hành 1.3.50.
  - Kiểm: test xanh, `main` fast-forward, origin cập nhật, `/health` trả 200 với PID mới.
- [x] T1.1 - Viết bộ kiểm kê chỉ đọc `server/skill_library_audit.py`.
  - Kiểm: test với cây brain tạm có bản phổ biến, bản khác nội dung, mtime và brain lạ.
- [x] T1.2 - Xuất báo cáo JSON và route quản trị chỉ đọc.
  - Kiểm: TestClient dùng state tạm, route table cập nhật và route staff bị chặn.
- [x] T1.3 - Thêm màn báo cáo chỉ đọc trong tab Thư viện.
  - Kiểm: test JS, i18n Việt và Anh, giao diện tối và sáng.
- [x] T1.4 - Chạy kiểm kê thật, phát hành bước 1 rồi dừng ở cổng duyệt.
  - Kiểm: báo số brain, file, slug, bản lệch, bản mới nhất và brain không khớp quy tắc.
- [ ] T2 - Dựng kho, đồng bộ, màn Phân bổ và dry-run; chỉ migrate thật `Marketing - Makeup`.
  - Kiểm: sao lưu, so sánh agent trước sau, `_verify`, router và rollback.
- [ ] T3 - Đổi Skill Learn thành cửa nhập kho và thêm gợi ý nơi dùng.
  - Kiểm: giữ nguyên toàn bộ rào duyệt, rủi ro, plugin tắt và dọn bản cài hỏng.
- [ ] T4 - Thêm phiên bản, rollout, rollback, diff, số lượt dùng và nhật ký quản trị.
  - Kiểm: canary phòng mẫu đạt trước khi nhân rộng và có đường quay lui một nút.

## Ngoài phạm vi hiện tại

- T2, T3 và T4 chưa được thực hiện trước khi anh duyệt số liệu thật của T1.4.
- Không sửa nội dung skill hiện có trong lúc kiểm kê.
