# Tab Tinh vân kiểu APEX - đề xuất thiết kế (chờ chủ duyệt)

Ngày 20/10/2026. Phạm vi: CHỈ lớp nhìn **Tinh vân** của khoang não. Tab **Lõi nước** và **3D Joyce** giữ nguyên, không sửa một dòng nào trong `brain-planet.js`, `joyce-humanoid.js`.

## 1. Rà soát repo APEX-UI (`E:\CLAUDECODE\TOOK\APEX-UI-main`)

| Thành phần | Làm gì | Dùng cho Joyce? |
|---|---|---|
| `ReasoningWeb.jsx` | Chòm nút quanh lõi: vòng quỹ đạo chấm, dây cong từ lõi ra từng nút, mạch PCB chạy ra mép, lưới nơ-ron thưa, hạt sáng chạy dọc dây, nút "thở" lệch pha, nút sáng khi được gọi | **Lấy ý tưởng chính** (viết lại bằng JS thuần, SVG) |
| `ApexOrb.jsx` | Vòng vàng quanh lõi: 3 lớp glow, vòng sáng xoay chậm, vòng nét đứt trong, sóng âm lan ra, vạch ngắm | **Lấy** làm khung quanh quả cầu |
| `OrbStatusBar.jsx` | Thanh equalizer + chữ STANDBY dưới đáy | **Lấy**, đổi chữ tiếng Việt |
| `ApexWorld.tsx` | Ghép lớp + thẻ tổng quan khi bấm nút (vai trò, khả năng, ví dụ yêu cầu, trạng thái) | **Lấy kiểu thẻ**, nội dung là dữ liệu thật của brain |
| `ApexCore3D.jsx` | Lõi hạt xanh bằng three.js | **Không** - lõi thay bằng quả cầu brain |
| `ShaderBackground.jsx` | Nền sóng plasma WebGL | **Không** (thêm một WebGL nữa trong khoang não là nặng), dùng nền gradient |
| `ApexOverviewPanel.tsx` | Đồng hồ + thời tiết góc trái | **Không** |

Giấy phép MIT: được dùng lại, kể cả thương mại, phải giữ ghi công. Tên "Apex" và thương hiệu Reznikov **không** thuộc giấy phép, nên giao diện mới không mang chữ Apex nào; đầu file ghi rõ nguồn cảm hứng + giấy phép MIT.

## 2. Bố cục mới

```
   ┌─────────────────────────── khoang não (Tinh vân) ───────────────────────────┐
   │  ●── mạch PCB ──┐                                          ┌── mạch PCB ──● │
   │                 VAN-HANH ◯                      ◯ SOURCES                    │
   │      WIKI ◯ ╲                                        ╱ ◯ _CHO-DUYET          │
   │              ╲      · · · vòng quỹ đạo · · ·        ╱                        │
   │   LEARN-LOG ◯──╲     ╭──────── vòng vàng ───────╮  ╱──◯ AGENTS               │
   │                 ╲   │     ( quả cầu brain    )  │ ╱                          │
   │    SKILLS ◉──────── │       đang mở: Trái Đất ) │────────◉ WORKFLOWS         │
   │                 ╱   │     ( / tinh cầu phòng )  │ ╲                          │
   │     FACTS ◯──╱      ╰───────────────────────────╯  ╲──◉ LOOPS                │
   │            ╱                                         ╲                       │
   │   ┈ Gmail ┈◌                ▁▃▅▇▅▃▁  ĐANG NGHỈ  ▁▃▅▇▅▃▁       ◌┈ Zalo ┈      │
   │                       4 AGENTS · 11 SKILLS · 3 WORKFLOWS                     │
   └──────────────────────────────────────────────────────────────────────────────┘
   ◯ xanh = tri thức   ◉ cam = vận hành   ◌ xám nét đứt = kết nối / công cụ
```

### Lõi giữa: quả cầu của brain đang mở

- **Brain Default** → quả cầu **Trái Đất** (biển + mây), giống tinh cầu Trái Đất ở thiên hà Lõi nước.
- **Brain phòng ban** → tinh cầu đúng phòng đó, cùng bảng màu và đặc trưng như Lõi nước: Kế toán vàng có vành, Nhân sự lục có mây, Marketing cam có bão, Bán hàng/Sản xuất dung nham nứt, Nghiên cứu tím pha lê, CSKH xanh sóng, Vệ sinh băng, Văn thư giấy xám, ThuyH2O hồng lấp lánh.
- **Brain chung của thương hiệu** (H2O Legacy, ThuyH2O) → ngôi sao sáng.
- Quả cầu **tự xoay chậm**, có viền khí quyển; đổi brain ở ô chọn brain là lõi đổi theo ngay.
- Bao quanh là **vòng vàng** kiểu APEX: glow 3 lớp, vạch sáng xoay chậm, 2 vòng nét đứt trong ngược chiều nhau, sóng âm lan ra khi Joyce nói.
- Dưới vòng: thanh equalizer + chữ trạng thái **ĐANG NGHỈ / ĐANG NGHE / ĐANG NGHĨ / ĐANG NÓI** (cùng nguồn trạng thái mà Lõi nước và 3D Joyce đang dùng).

### Nút xung quanh: dữ liệu thật của brain, 3 lớp màu như APEX

| Lớp | Màu | Nút lấy từ đâu |
|---|---|---|
| Tri thức | xanh ngọc, vòng đặc | các thư mục note: `wiki`, `sources`, `facts`, `learn-log`, `memory`, `notes`, `_cho-duyet`, `van-hanh`... (đúng các nhãn đang hiện quanh Tinh vân hôm nay) |
| Vận hành | cam, vòng đặc | `agents`, `skills`, `workflows`, `loops` |
| Kết nối | xám, vòng **nét đứt** khi chưa nối | MCP lấy từ `/mcp/list` (Gmail, Calendar, Zalo, Telegram, POS...), nối rồi thì nét liền |

- **Độ to nút** theo số note của thư mục (thư mục lớn gần lõi hơn, như "Chief of staff" của APEX); nhãn ghi `14 note · 15%` như hiện nay.
- Nút không có note nào thì mờ, nhãn nhỏ (giống nút "Drive" chưa dựng của APEX).
- Bố trí cố định theo tên thư mục, mở lại vẫn đúng chỗ cũ; có vòng cách ly quanh lõi để không nút nào đè lên quả cầu.

### Dây nối và chuyển động

- Mỗi nút có **dây cong** nối về lõi; nút gần nhau có một dây mảnh nối ngang (mỗi nút 1 hàng xóm gần nhất, không rối).
- **3 vòng quỹ đạo chấm** quanh lõi, **mạch PCB** chạy ngang ra hai mép với chấm sáng ở đầu, vài nơ-ron mờ nhấp nháy lấp khoảng trống.
- Lúc nghỉ: hạt sáng mờ trôi chậm từ lõi ra các nút; mỗi nút thở theo nhịp riêng.
- **Joyce làm việc thật thì sáng đúng nhánh**: khi Joyce đọc/ghi một file (`tool_call` có đường dẫn, đã có sẵn sự kiện `joyce:avatar-act`), nhánh của thư mục chứa file đó sáng lên, dòng hạt chạy từ lõi ra nút, nút phình sáng; gọi skill thì nhánh SKILLS sáng, dùng MCP Gmail thì nhánh Gmail sáng. Hai nhánh cùng sáng trong một lượt thì hiện dây nối tạm giữa chúng ("đang phối hợp").
- Joyce nghĩ/nói thì cả mạng **chạy nhanh hơn** và hạt dày hơn, nghỉ thì chậm lại.

### Tương tác

- **Rê chuột** lên nút: nút và dây của nó sáng, phần còn lại mờ đi.
- **Bấm nút** → mở **thẻ tổng quan** kiểu APEX (kéo thả được, Esc để đóng):
  - Thư mục note: số note, % vault, **5 note mới sửa gần nhất** (bấm là mở note như hiện nay), ô tìm trong thư mục.
  - Agents/Skills/Workflows/Loops: danh sách tên + mô tả ngắn, bấm mở file.
  - Kết nối MCP: trạng thái, số công cụ, nút đến trang Kết nối.
- **Bấm quả cầu** → thẻ của brain: tên, số note, số kết nối, lần nạp tri thức gần nhất.
- Thanh thống kê AGENTS · SKILLS · WORKFLOWS ở đáy giữ nguyên.

## 3. Giữ lại những gì Tinh vân cũ đang làm được

Đồ thị cũ (mỗi note một chấm) có vài tính năng chủ đang dùng: xem từng note và liên kết, **timelapse** bộ não lớn dần, chấm mới nảy ra khi Joyce ghi note, tìm note. Đề xuất: thêm một nút nhỏ góc phải **"Mạng note"** để chuyển qua lại giữa chòm mới và đồ thị cũ (đồ thị cũ giữ nguyên `graph.js`). Mặc định mở **chòm kiểu APEX**.

## 4. Kỹ thuật

- File mới `dashboard/brain-constellation.js` (JS thuần, không React, không three.js): lớp SVG cho dây/nút/vòng + một canvas nhỏ cho quả cầu xoay (dựng ảnh bề mặt một lần theo bảng màu phòng, mỗi khung chỉ lấy mẫu lại, ~5 ms).
- Bảng màu và đặc trưng các phòng chép sang file mới (không import ngược vào `brain-planet.js`) để Lõi nước không bị đụng.
- Dữ liệu: `/graph` (đang gọi sẵn) gom theo thư mục; `/knowledge/galaxy` để biết brain đang mở là Trái Đất / phòng nào / ngôi sao; `/mcp/list` cho lớp kết nối; số agents/skills/workflows lấy từ ô thống kê sẵn có.
- Hiệu năng: chỉ vẽ khi tab Tinh vân đang mở; đứng yên thì hạ nhịp vẽ; máy yếu bỏ mạch PCB và nơ-ron; tôn trọng "giảm chuyển động" của hệ điều hành.
- Điện thoại (khoang não cao ~228 px): bỏ mạch PCB, chỉ hiện nhãn nút lớn, lõi co nhỏ.
- Nền sáng/tối: dùng bảng màu ngày của APEX cho giao diện sáng (đường nét mảnh không glow, như bản in).
- Truy cập: danh sách nút ẩn bằng nút bấm thật để dùng bàn phím, như APEX làm.

## 5. Không làm

- Không đổi tab Lõi nước, 3D Joyce, thiên hà phòng ban.
- Không dùng tên/brand "Apex", không chép nền shader WebGL, không đồng hồ thời tiết.
- Không thêm thư viện mới.

## 6. Cần chủ chốt trước khi làm

1. **Lõi giữa**: quả cầu của **brain đang mở** (đổi brain là đổi quả cầu) - hay luôn là Trái Đất?
2. **Đồ thị note cũ**: giữ làm nút chuyển "Mạng note" (đề xuất) - hay bỏ hẳn?
3. **Lớp kết nối MCP** (nút xám nét đứt như Drive/Email/Calendar của APEX): có hiện không?

## 7. Kiểm thử khi làm

Test JS cho bố cục (nút không đè lõi, không đè nhau, đúng màu lớp, nhánh sáng theo `tool_call`), chụp Playwright hai tông sáng/tối + khung điện thoại, đo CPU lúc đứng yên. Tăng phiên bản theo `docs/quy-uoc-dev.md`, cập nhật hai CHANGELOG.
