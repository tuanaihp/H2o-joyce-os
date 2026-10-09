---
name: Lập kế hoạch
description: Lập kế hoạch việc lớn theo spec, plan rồi task, mỗi task có bước kiểm. Dùng khi việc chạm nhiều bước hoặc kéo dài nhiều phiên.
description_en: "Plan a large piece of work as spec, then plan, then tasks, each task with a check. Use when the work spans several steps or several sessions."
group: Productivity
---

# LẬP KẾ HOẠCH - việc lớn đi qua spec → plan → task

## Khi nào dùng

- Việc có từ ba bước trở lên, hoặc phải làm qua nhiều lượt chat.
- Việc đổi cấu trúc thư mục, định dạng file, hoặc cách ghi trong brain.
- Người dùng nói "lên kế hoạch", "chia việc", "làm từng bước" hoặc "viết lộ trình".

Việc nhỏ (một câu trả lời, một file, một lần sửa) thì không dùng skill này.

## Ba bước

1. **Spec**: mô tả vấn đề, phạm vi, điều KHÔNG làm, quyết định chính và lý do, rủi ro.
   Dừng lại cho người dùng xác nhận trước khi sang bước 2.
2. **Plan**: chia spec thành task nhỏ. Mỗi task ghi rõ việc cụ thể và cách kiểm xong.
3. **Task**: làm từng task theo thứ tự, đánh dấu `[x]` ngay khi xong. Việc phát sinh thì thêm
   vào plan, không làm lặng lẽ.

## Mẫu plan

```markdown
# <Tên việc> - kế hoạch

Trạng thái: đang làm / xong / bỏ

## Mục tiêu
<một đến ba câu: xong thì người dùng thấy gì khác>

## Ràng buộc
- <điều không được đổi>

## Các task
- [ ] T1 - <việc cụ thể>
  - Kiểm: <cách biết đã xong>
- [ ] T2 - ...

## Ngoài phạm vi
- <thứ dễ bị kéo theo nhưng không làm>
```

## Quy tắc

- Mỗi task phải có bước kiểm có thể lặp lại. "Đã làm" không đủ.
- Đổi hướng giữa chừng thì sửa plan trước, rồi mới làm tiếp.
- Đầu mỗi lượt chat mới, đọc lại plan để biết đang ở task nào, không hỏi lại từ đầu.
- Không dùng dấu gạch dài (em dash) trong plan.
