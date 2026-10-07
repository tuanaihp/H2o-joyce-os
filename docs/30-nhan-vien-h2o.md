# Nhân viên H2O: tài khoản riêng, model riêng, quyền riêng

Joyce cho phép mỗi nhân viên H2O có một tài khoản riêng để làm việc trên cùng một máy chủ Joyce: đăng nhập bằng **số điện thoại + mã PIN**, thấy tên mình trên thanh công cụ, chỉ dùng được **những model admin đã cấp**, và có **phiên chat/kênh làm việc riêng** cách ly với admin lẫn đồng nghiệp.

Mục tiêu: một máy Joyce chạy 24/7 làm trung tâm; nhân viên chỉ cần trình duyệt, không cần biết mật khẩu admin, không đụng được vào cấu hình hệ thống.

## Mở ở đâu trong Joyce

Thanh điều hướng bên trái, nhóm **Hệ thống**, mục **Nhân viên** (ngay trên Tài khoản). Chỉ admin mới thấy bảng quản lý đầy đủ.

## Admin: quản lý nhân viên

Trang Nhân viên có bảng danh sách + form thêm/sửa. Mỗi nhân viên gồm:

| Trường | Ý nghĩa |
| --- | --- |
| Tên | Hiện trên chip góc màn hình và trong today viewer |
| SĐT | Tài khoản đăng nhập - duy nhất |
| PIN | 4-8 chữ số; server chỉ lưu bản băm, không lưu PIN thô |
| Chức vụ | CEO / Giám đốc / Trưởng phòng / Chuyên gia / Nhân viên / Học việc - hiện là NHÃN hiển thị, chưa quyết định quyền |
| Model được cấp | Tick từng model hoặc "mọi model của provider". Rỗng hoàn toàn = được dùng tất cả |
| Workspace | Thư mục làm việc riêng, tự tạo khi thêm nhân viên |
| Bật/tắt | Tắt = tài khoản chết ngay, cookie cũ cũng vô hiệu |

Sai PIN nhiều lần bị khoá tạm theo IP - dùng chung cơ chế chống brute-force với đăng nhập admin.

## Nhân viên: đăng nhập và dùng

1. Màn đăng nhập có dòng **"Nhân viên H2O (SĐT + PIN)"** - bấm để đổi ô nhập sang SĐT + PIN.
2. Vào được thì thấy **chip tên mình** trên thanh model. Bấm chip -> xác nhận -> đăng xuất.
3. Bảng chọn model **chỉ liệt kê model được cấp** - không thấy, không gọi được model ngoài danh sách (server chặn, không phải chỉ giấu UI).
4. Phiên chat của nhân viên gắn kênh `staff:<id>` - admin mở bộ lọc phiên sẽ thấy riêng; nhân viên A không đọc/sửa/xoá được phiên của nhân viên B hay của admin (404 cả hai chiều).
5. Mở trang Cài đặt chỉ thấy **thẻ thông tin của chính mình** (tên, vai trò, SĐT, danh sách model được cấp).
6. Nhân viên mới đăng nhập lần đầu được đưa thẳng vào trang **Hôm nay** thay vì màn cockpit.

## Nhân viên KHÔNG làm được gì

Chặn ở tầng server (`_staff_blocked` trong main.py), không phải chỉ giấu nút:

- **Ghi bị cấm** vào: settings, tokens, plugins, MCP, packs, channels, models, brains, reminders, kanban, workflows, agents, skills, loops, projects, inbox, Telegram, Zalo, h2o-staff (không tự quản đồng nghiệp).
- **Đọc cũng cấm luôn**: `/files`, `/vault`, `/ingest` - file vault là sổ của admin.
- Đọc danh sách vẫn được (kanban, agents...) vì team cần nhìn công việc chung.
- WebSocket `/ws` cần staff cookie hợp lệ; API key scope `chat` không vượt qua được đường admin.
- Cùng máy tính (localhost) vẫn là vùng tin cậy cũ - các endpoint agent-local không cần cookie; rào staff áp cho truy cập qua mạng/tunnel.

## Cho dev: nâng cấp đúng chỗ

| Muốn sửa | Đụng vào |
| --- | --- |
| Thêm chức vụ | `ROLES` trong `server/h2o_staff.py` + `<select>` trong `renderStaffPage` (console.js) + i18n `staff.role_*` |
| Đổi danh sách API staff bị cấm | `_STAFF_DENY` / `_STAFF_DENY_ALL` trong `server/main.py` (~dòng 16218) |
| Đăng nhập / phiên staff | `server/h2o_staff.py` (`create`, `login`, `staff_by_token`, `revoke`); cookie `h2o_staff` |
| Chống brute-force PIN | `h2o_staff.login` dùng chung `_login_fail`/`_login_ok` của auth admin trong main.py |
| Lọc model theo quyền | ACL enforce trong luồng `/chat` (main.py) + `dashboard/model-picker.js` đọc `window.__h2oStaff` |
| Chip tên + logout | `initAuthGate` trong `dashboard/app.js` (~dòng 4125) |
| Trang quản trị Nhân viên | `renderStaffPage` + `_staffSelfCard` trong `dashboard/console.js`; i18n `page.staff.*`, `staff.*` |
| Workspace riêng | `staff_workspaces/` dưới state dir (gitignore sẵn); tạo trong `h2o_staff.create` |

API: `GET/POST /h2o-staff`, `POST /h2o-staff/{id}/update|pin|toggle|delete` (admin), `POST /staff/login`, `GET /staff/me`, `POST /staff/logout` (public 3 đường cuối). Dữ liệu ở `h2o_staff.json` trong state dir - PIN lưu dạng hash+salt, file đã nằm trong `.gitignore`.

Điểm cần nhớ khi nâng cấp: chức vụ hiện chỉ là nhãn - muốn chức vụ lái quyền (vd Học việc chỉ đọc) phải nối vào `_staff_blocked`/`_staff_req` chứ không sửa UI; test ma trận quyền nằm trong `tests/` (xem các test `staff`/`sessions_kenh`).
