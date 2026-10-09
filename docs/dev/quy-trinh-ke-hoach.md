# Quy trình kế hoạch cho việc lớn: spec → plan → task

Học từ Javis (`docs/superpowers/` của bản javis-os, 2026-07): việc lớn đi qua ba bước, mỗi
bước là một file trong `docs/dev/`. Việc nhỏ (sửa một lỗi, đổi một chữ) không cần bước nào.

## Khi nào cần

- Thay đổi chạm từ hai module trở lên, hoặc đổi hợp đồng giữa server và dashboard.
- Có thay đổi dữ liệu trong brain (cấu trúc thư mục, định dạng file, cách ghi).
- Việc mất hơn một buổi và có thể làm lệch quy ước của repo.

## Ba bước

1. **Spec** (`docs/dev/YYYY-MM-<chủ-đề>-design.md`): vấn đề, phạm vi, điều KHÔNG làm, quyết
   định chính và lý do, rủi ro. Chờ chủ repo duyệt trước khi viết plan.
2. **Plan** (`docs/dev/YYYY-MM-DD-<chủ-đề>-plan.md`): chia spec thành các task nhỏ, mỗi task
   có bước kiểm tra cụ thể. Mẫu bên dưới.
3. **Task**: làm từng task theo thứ tự, đánh dấu `[x]` ngay khi xong. Task nào phát sinh
   việc mới thì thêm vào plan, không làm lặng lẽ.

## Mẫu plan

```markdown
# <Tên việc> - kế hoạch

Spec: `docs/dev/<file-spec>.md` · Trạng thái: đang làm / xong / bỏ

## Mục tiêu
<một đến ba câu: xong thì người dùng thấy gì khác>

## Ràng buộc chung
- Không đổi hợp đồng API cũ (liệt kê endpoint bị ảnh hưởng)
- i18n: mọi key mới có cả vi và en; không em dash
- <ràng buộc riêng của việc này>

## Các task
- [ ] T1 - <việc cụ thể, file cụ thể>
  - Kiểm: <lệnh hoặc bước tay để biết xong>
- [ ] T2 - ...
  - Kiểm: ...

## Ngoài phạm vi
- <những thứ dễ bị kéo theo nhưng không làm trong việc này>
```

## Quy tắc khi làm

- Mỗi task kết thúc bằng một bước kiểm có thể lặp lại (test, lệnh gọi endpoint, hoặc bước
  tay ghi rõ). "Đã sửa" không đủ.
- Không gộp hai task vào một commit chỉ vì tiện. Một commit một việc, dễ lùi.
- Plan đã duyệt mà phải đổi hướng thì sửa plan trước, rồi mới sửa code.
- Đóng việc: cập nhật trạng thái trong plan và thêm mục CHANGELOG nếu người dùng thấy khác.
