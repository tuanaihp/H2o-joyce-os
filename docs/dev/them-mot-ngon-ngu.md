# Thêm một ngôn ngữ mới

Mọi thứ về một ngôn ngữ nằm ở MỘT chỗ: sổ đăng ký `server/lang_registry.py`. Không mã nào ngoài sổ
được viết `if lang == "vi"`. Cần biết gì về một ngôn ngữ thì hỏi sổ đăng ký.

Hiện có hai ngôn ngữ giao diện: `vi` (Tiếng Việt, mặc định) và `en` (English).

## Các bước

1. **Đăng ký.** Thêm MỘT mục vào `LANGS` trong `server/lang_registry.py`. Mã gọn, ví dụ `vi`, không phải
   mã BCP-47 đầy đủ như `vi-VN`. Điền tên hiển thị bằng chính ngôn ngữ đó và bằng tiếng Anh.
2. **Bộ từ vựng (tuỳ chọn).** Tạo `server/lexicon/<mã>.py` như `server/lexicon/en.py`. Bước này không bắt
   buộc. Nhưng nếu làm thì làm trọn: nhận diện và sửa lỗi nghe phải có cùng lúc. Làm MỘT NỬA (có từ điển
   nhận diện nhưng thiếu phần sửa, hoặc ngược lại) còn nguy hiểm hơn không làm.
3. **Giao diện (khi tới phần giao diện).** Tạo `dashboard/i18n/<mã>.json` với đủ mọi khoá có trong
   `vi.json`. Thiếu khoá thì bộ test i18n báo đỏ.
4. **Kiểm.** Chạy `tests/python/test_tai_lieu_song_ngu.py` (sổ tay này phải nhắc đúng mọi mã đang có)
   và `node tests/js/test_i18n.mjs`.

Thêm ngôn ngữ thứ N+1 chỉ chạm các file trên. Không sửa file nào khác.

## Trước khi bắt đầu

- Dùng mã gọn trong toàn bộ sổ đăng ký. Đừng đặt tên thư mục hay khoá i18n theo mã BCP-47.
- Không hard-code chuỗi ngôn ngữ trong giao diện hay trong mã server. Mọi chuỗi đi qua khoá i18n.
