---
name: Lái trình duyệt web (Web Pilot)
description: Điều khiển Chrome thật bằng bảng phần tử đánh số - đọc số liệu, điền form, bấm nút trên các trang không có API (dashboard, CRM, admin, trang cần đăng nhập). Dùng khi cần làm việc trên web mà không có MCP/API nào.
group: Cong cu
---

# Web Pilot - lái web bằng cách CHỌN, không generate

Plugin `web-pilot` biến trang web thành bảng phần tử đánh số. Việc của bạn là chọn số,
không phải viết selector/code trang (cấm - hay sai và dễ bị lạm dụng).

## Vòng lặp bắt buộc

```
web_pilot_open(url)        → bảng ELEMENTS + text trang
      ↓
ĐỌC bảng → chọn element + op (bạn tự viết text khi TYPE_TEXT)
      ↓
web_pilot_act(element, op) → bảng ELEMENTS MỚI (trang đã đổi)
      ↓  lặp lại cho đến khi xong
TỰ KIỂM kết quả thật       → URL mới? dữ liệu cần đã xuất hiện trong TEXT?
web_pilot_close()
```

## Nguyên tắc an toàn (không được phá)

1. **Guard**: mỗi act được kiểm trang còn y nguyên trước khi chạm. Báo `stale` =
   trang đã đổi → snapshot lại, chọn element từ bảng MỚI. Không lặp hành động cũ.
2. **DONE không phải bằng chứng** - sau khi submit/đăng/gửi, phải kiểm trang thật:
   URL đổi? dòng xác nhận xuất hiện? Không thấy = chưa xong, đừng báo thành công.
3. **Trang đăng nhập**: gặp form login/captcha → DỪNG, bảo người dùng đăng nhập tay
   1 lần trong cửa sổ Chrome của plugin (profile giữ lâu dài). Không tự gõ mật khẩu.
4. **Tiền/hành động khó đảo** (thanh toán, đặt hàng, đăng bài, gửi tin): làm đến bước
   CUỐI trước nút xác nhận → tóm tắt sắp làm gì → chờ người bảo "làm tiếp" mới bấm.
5. Một phiên = một mục tiêu. Kẹt >3 lần (act không đổi trang) → dừng, báo thật.

## Ba chế độ trình duyệt

- **Mặc định**: plugin tự mở Chrome profile riêng (đăng nhập giữ lâu dài, không đụng
  Chrome bạn đang dùng). Lần đầu vào trang cần login → đăng nhập tay MỘT lần.
- **`attach: true`**: lái Chrome đang mở của bạn (mở bằng `chrome.exe
  --remote-debugging-port=9222`) - dùng sẵn mọi đăng nhập của bạn.
- **`headless: true`**: chạy ẩn (máy chủ/VPS hoặc tác vụ nền không cần nhìn).

## Công thức đọc số liệu (việc hay gặp nhất)

`web_pilot_open(dashboard_url)` → đọc `text` trong kết quả → thiếu thì
`web_pilot_snapshot(full_text=true)` lấy tới 20k ký tự → trích số liệu cần báo.
Đọc thuần không cần `web_pilot_act` - snapshot là đủ.

## Công thức điền form

1. TYPE_TEXT vào từng ô (text bạn tự soạn theo mục tiêu).
2. SELECT option bằng mã `n:m` trong bảng.
3. Kiểm lại bảng cuối (giá trị ô hiện trong cột `đang="…"`).
4. Bấm nút submit/Enter → verify trang kết quả.

## Ví dụ làm được

- Mở webapp CRM/album nội bộ → đọc số đơn hôm nay, đơn chờ, báo lại.
- Vào trang admin → điền form tạo mục mới.
- Vào dashboard ads/analytics không có MCP → đọc chỉ số chiến dịch.
- Mở trang bất kỳ → bóc danh sách/bảng số liệu để tổng hợp.

## Báo cáo

Xong việc: nói ngắn đã làm gì, kết quả THẬT kiểm được (URL, số liệu đọc ra, dòng
xác nhận), và chỗ nào kẹt nếu có. Không nói "đã xong" khi chưa verify.
