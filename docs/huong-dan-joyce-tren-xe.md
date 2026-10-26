# Joyce trên xe hơi (Tầng 1)

Dùng Joyce qua điện thoại + Bluetooth xe. Joyce nói qua loa xe, nghe qua mic
điện thoại. Không cần app mới, không đụng màn hình xe.

## Link tự bay vào Telegram (đã có sẵn)

Mỗi lần máy tính khởi động:

```
logon -> task JoyceOS-Boot (tre 5 phut) -> server len
-> tunnel_notify.py mo tunnel -> link trycloudflare moi
-> gui vao Telegram (moi chat_id trong whitelist) + chuong Joyce
```

Anh chỉ việc mở Telegram trên điện thoại, bấm link mới nhất. Link
trycloudflare đổi mỗi lần chạy nhưng không sao - link mới luôn nằm chờ
trong tele.

Muốn link rơi vào **nhóm** tele: thêm chat_id của nhóm vào danh sách
chat_id trong Cai dat -> Telegram (phay giua cac id). Script gui cho tat
ca id trong list.

Muốn link **cố định vĩnh viễn** thay vì đổi mỗi lần: cần named tunnel
(tai khoan Cloudflare + domain) - lam rieng khi can.

## Làm 1 lần đầu (ở nhà)

1. Mở link tunnel trên Chrome/Safari điện thoại → đăng nhập Joyce.
2. Thêm vào màn hình chính (Add to Home Screen) để chạy như app,
   ẩn thanh địa chỉ.
3. Bấm nút mic 1 lần để điện thoại xin quyền micro → cho phép.

## Kết nối xe VinFast Lux SA 2.0

Lux SA KHÔNG có Android Auto (VinFast chỉ bổ sung Apple CarPlay cho iPhone
qua bản cập nhật sau). Tầng 1 không cần Android Auto - Bluetooth là đủ,
cả 3 bản Lux SA đều có sẵn + dàn 13 loa.

Ghép Bluetooth (làm 1 lần, đứng yên ~2 phút):

1. Điện thoại: Cài đặt → Bluetooth → BẬT.
2. Màn hình 10.4" của xe: mục Điện thoại/Cài đặt → Bluetooth →
   tìm/ghép thiết bị mới → chọn điện thoại của anh → xác nhận mã
   trên cả 2 màn hình.
3. Cho phép âm thanh đa phương tiện (media audio) và cuộc gọi.
4. Joyce không phải cuộc gọi điện - tiếng đi theo kênh NHẠC (A2DP),
   nên trên xe chọn nguồn phát là Bluetooth như khi nghe nhạc.

Cổng USB trong hộp tựa tay chỉ để sạc + đọc nhạc file - cắm sạc được
nhưng không đưa gì lên màn hình xe.

## Mỗi lần lên xe

1. Máy tính để tự khởi động Joyce (hoặc double-click `joyce-xe-hoi.bat`
   để lấy link ngay không chờ 5 phút).
2. Trên xe: điện thoại tự nối lại Bluetooth (đã ghép từ trước).
3. Mở Telegram → bấm link Joyce mới nhất → bấm mic → nói chuyện.
   Tiếng Joyce phát qua loa xe; mic điện thoại nghe anh nói.
4. Để điện thoại trên giá đỡ gần người lái - mic nghe rõ hơn.
5. Màn hình điện thoại tự giữ sáng suốt cuộc gọi (Screen Wake Lock).
6. Joyce nói ra loa điện thoại thay vì loa xe → kiểm tra trong cài đặt
   Bluetooth của điện thoại: thiết bị Lux SA đã bật "âm thanh đa phương
   tiện" chưa, và nguồn nhạc trên xe đang là Bluetooth.

## Khi bị lỗi

- **Không nghe/nói được**: mở lại trang Joyce và bấm mic lại (trình duyệt
  cắt mic khi đổi app hoặc khoá máy).
- **Link chết**: máy tính tắt/ngủ hoặc tunnel tắt. Bật lại máy hoặc chạy
  `joyce-xe-hoi.bat`. Cờ `tools\tunnel-off.flag` = chủ cố ý tắt tunnel,
  xoá nó nếu muốn mở lại.
- **Đổi link cũ trong tele**: luôn lấy link mới nhất, link cũ của lần
  chạy trước không dùng lại được.

## Sẽ làm tiếp (chưa làm)

- Tầng 2: kênh Telegram để Android Auto đọc/trả lời tin nhắn Joyce trên
  chính màn hình xe.
- Tầng 3: app Android Automotive native cài thẳng lên đầu DVD VinFast.
