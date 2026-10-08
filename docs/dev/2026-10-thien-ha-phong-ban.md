# Thiên hà phòng ban: ý tưởng chi tiết

Chủ repo đề xuất 2026-10-08: thu nhỏ tinh cầu thì thấy khoảng không bao la, nên đặt các **tiểu
tinh cầu phòng ban** rải rác ở xa. Mỗi loại có màu sắc, kích thước riêng. Bấm vào một tinh cầu thì
màn hình chỉ còn tinh cầu phòng ban đó với hố đen của nó, nạp / tìm kiến thức y như Trái Đất hiện
tại. Chọn brain phòng ban ở ô chọn brain cũng bay tới đúng tinh cầu đó.

Ý tưởng đã được chủ duyệt 2026-10-08 (mục 11). Chưa code: bước đầu là bản demo của Codex. Đi kèm `2026-10-tinh-cau-h2o.md` (renderer) và
`2026-10-bau-troi-tri-thuc.md` (bầu trời tri thức, hố đen, Big Bang).

---

## 1. Ý tưởng trong một đoạn

Trái Đất là brain đang mở. Lùi xa thêm một tầng zoom là **Thiên hà H2O**: 44 tinh cầu phòng ban
xếp thành **11 cụm sao theo khối** (Kế Toán, Nhân Sự, Marketing...), mỗi cụm có màu và kiểu bề mặt
riêng, nằm trên hai cánh tay xoắn của dải ngân hà: cánh **H2O Studio** (xanh lam) và cánh
**ThuyH2O** (hồng tím). Tinh cầu càng nhiều kiến thức càng to, phòng có việc kẹt thì nhấp nháy đỏ,
phòng đang nạp tài liệu thì hố đen nhỏ cạnh nó xoáy sáng. Bấm một tinh cầu là bay tới: tinh cầu đó
thành trung tâm màn hình, có bầu trời tri thức, hố đen, Big Bang, sợi sáng khi hỏi Joyce, y hệt Trái
Đất bây giờ, chỉ khác là toàn bộ dữ liệu là của phòng đó.

---

## 2. Bốn tầng zoom (mở rộng tầng hiện có)

| Tầng | Zoom | Thấy gì |
|---|---|---|
| Cận cảnh Việt Nam | 2 - 12 | như hiện tại |
| Tinh cầu | ~1 | như hiện tại: tinh cầu đang mở + bầu trời tri thức + hố đen |
| Hệ Mặt Trời | ~0,6 | như hiện tại, thêm: vài tinh cầu phòng ban gần nhất ló ở rìa khung |
| **Thiên hà H2O** (mới) | 0,12 - 0,32 | tinh cầu đang mở thu thành một chấm sáng có vòng chỉ "Bạn đang ở đây"; 44 tinh cầu phòng ban hiện rõ, gom theo cụm |

Lăn chuột ra xa qua mốc 0,32 là trượt mượt vào tầng Thiên hà (không chuyển trang). Có thêm nút
**"Thiên hà"** nhỏ ở góc trên (cạnh nút Lõi nước / Tinh vân) cho người không quen lăn chuột.

---

## 3. Bố cục thiên hà

- **Hai cánh tay xoắn** của dải ngân hà (cùng góc nghiêng với dải ngân hà hiện tại): cánh H2O
  Studio đi về một phía, cánh ThuyH2O đi về phía kia. Brain chung của thương hiệu (`H2O Studio`,
  `ThuyH2O Studio`) là **ngôi sao lớn** đứng đầu mỗi cánh, các cụm khối nằm dọc cánh của mình.
- **Mỗi khối là một cụm sao**: các phòng trong khối nằm gần nhau, có vầng tinh vân mờ cùng màu
  khối bao quanh, tên khối hiện mờ ở giữa cụm khi rê chuột vào.
- **Brain chủ** (Brain Default) là Trái Đất, ở gần lõi thiên hà.
- Vị trí **cố định** theo tên brain (băm như thiên thể tri thức): dùng lâu sẽ nhớ "Kế Toán ở phía
  trên-trái". Thêm phòng mới thì nó tự mọc vào cụm khối của nó, phòng cũ không nhảy chỗ.

## 4. Mỗi khối một kiểu tinh cầu

Tận dụng sẵn 8 bảng màu bề mặt mà shader đã có (ocean, emerald, amethyst, sunset, ice, lava,
gold, abyss) cộng một chi tiết nhận diện vẽ 2D:

| Khối (số phòng) | Bảng màu | Chi tiết nhận diện | Ý nghĩa |
|---|---|---|---|
| Kế Toán (3) | gold | vành đai vàng như sao Thổ | dòng tiền quay vòng |
| Nhân Sự (9) | emerald | mây trắng dày, nhiều mặt trăng nhỏ | con người, đông nhất |
| Marketing (3) | sunset | bão xoáy cam như sao Mộc | lan toả, ồn ào |
| Bán Hàng (3) | lava | vệt nứt dung nham sáng | nóng, chốt đơn |
| Sản Xuất (6) | lava tối + khói | núi lửa nhỏ phun | xưởng làm ra sản phẩm |
| Nghiên Cứu (4) | amethyst | tinh thể nhô trên mặt, lấp lánh | ý tưởng, concept |
| CSKH (3) | ocean | đại dương lặng, vệt sóng sáng | chăm sóc, mềm |
| Vệ Sinh (3) | ice | băng trắng sạch, chóp sáng | sạch sẽ |
| Xử Lý Truyền Thông (3) | abyss | vệ tinh ăng ten nhỏ quay quanh, sóng tín hiệu | theo dõi tín hiệu |
| Văn Thư & Quy Trình (1) | ice xám | vành giấy mảnh nhiều lớp | lưu trữ |
| ThuyH2O (6) | amethyst hồng | quầng hồng phấn, lấp lánh như kim tuyến | thương hiệu makeup |

Các phòng trong cùng khối dùng chung bảng màu nhưng lệch sắc độ một chút theo băm tên, để nhận ra
từng phòng.

## 5. Kích thước, độ sáng, tín hiệu sống

Tất cả lấy từ dữ liệu thật, không trang trí:

- **Kích thước** theo số tài liệu kiến thức của phòng (log, kẹp từ nhỏ tới to gấp 3).
- **Độ sáng** theo hoạt động 7 ngày (tài liệu mới sửa, hội thoại của nhân viên phòng).
- **Nhấp nháy đỏ nhẹ** khi phòng có việc kẹt trên bảng Việc (cùng nguồn với trang Phòng ban).
- **Hố đen nhỏ cạnh tinh cầu** khi phòng còn tài liệu thô chưa chưng cất; xoáy sáng khi phòng đang
  nạp; nạp xong có sao băng nhỏ rơi vào tinh cầu phòng đó.
- **Mặt trăng nhỏ** = số trợ lý (agent) của phòng; **vành** = phòng có quy trình.
- Rê chuột: thẻ nhỏ "Kế Toán - Thu · 24 tài liệu · 2 việc kẹt · nạp gần nhất 3 giờ trước".

## 6. Bấm vào một tinh cầu phòng ban

1. **Bay tới** (khoảng 1,2 giây): camera lao qua thiên hà, tinh cầu phòng ban lớn dần ra giữa
   màn, Trái Đất lùi lại thành chấm sáng phía sau.
2. **Đổi brain thật**: ô chọn brain chuyển sang brain phòng đó (đúng cơ chế trang Phòng ban đang
   dùng), nên khung chat, VAULT, Tệp tin, bầu trời tri thức đều đổi theo.
3. **Màn hình còn tinh cầu phòng ban + hố đen của nó**: shader dùng bảng màu của khối, bầu trời tri
   thức là của phòng đó (đã có sẵn: admin mở brain phòng thì chỉ thấy trời phòng đó), hố đen hút
   đúng tài liệu thô của phòng.
4. Mọi thứ đang có **chạy y nguyên**: Big Bang khi tìm ở ô VAULT, sợi sáng khi hỏi Joyce, sao băng
   khi nạp xong, bấm hố đen để nhìn sâu, thẻ Đọc nhanh.
5. Góc trên có đường về: **"← Thiên hà"** và **"← Trái Đất"**. Nút Quay lại chung của hệ thống
   cũng lùi đúng về chỗ trước.

Chọn brain phòng ban ở **ô chọn brain** (thay vì bấm trên thiên hà) cũng chạy đúng hiệu ứng bay tới
đó, để hai đường vào cho cùng một kết quả.

## 7. Tìm kiếm từ thiên hà

Đang ở tầng Thiên hà mà gõ từ khoá ở ô VAULT (ví dụ "Báo giá"):
- Các tinh cầu phòng ban có tài liệu khớp **sáng lên** và hiện số kết quả trên đầu (ví dụ "Bán
  Hàng - Sales Hình Ảnh · 4"); phòng không có thì mờ đi.
- Bấm một tinh cầu đang sáng thì bay tới đó và **Big Bang diễn luôn** với đúng từ khoá, khỏi gõ lại.

## 8. Phân quyền

- **Admin** thấy cả thiên hà 44 phòng.
- **Nhân viên** chỉ thấy tinh cầu các phòng được gán (sáng rõ) cùng hai ngôi sao thương hiệu; các
  phòng khác chỉ là đốm sao mờ không tên, không bấm được. Máy chủ quyết, như bầu trời tri thức.

## 9. Kỹ thuật (để ước lượng)

- **Một shader WebGL duy nhất** vẫn chỉ vẽ tinh cầu đang mở (đổi bảng màu khi bay tới phòng khác).
  44 tinh cầu ở xa là **ảnh dựng sẵn bằng canvas 2D** (cầu có ánh sáng, nhiễu bề mặt theo bảng màu
  khối, chi tiết nhận diện), giống cách dựng mặt đá tinh cầu kiến thức, nên máy yếu vẫn chạy.
- Máy chủ thêm `/knowledge/galaxy`: mỗi brain phòng một dòng (khối, thương hiệu, số tài liệu, số tài
  liệu thô, hoạt động 7 ngày, số việc kẹt, đang nạp hay không), cache 60 giây; tìm từ thiên hà dùng
  lại `/knowledge/search` với phạm vi gộp.
- Hiệu ứng bay tới: nội suy zoom + vị trí camera trong 1,2 giây, đổi brain ở giữa lúc bay (lúc màn
  đang mờ nhất) để không thấy giật khi dữ liệu nạp lại.

## 10. Lộ trình đề xuất

| Giai đoạn | Nội dung |
|---|---|
| 1. Bản đồ thiên hà | Tầng zoom Thiên hà, 44 tinh cầu ảnh dựng sẵn theo khối, cụm + hai cánh tay, rê chuột ra thẻ, bấm là đổi brain và bay tới, nút về Trái Đất |
| 2. Tinh cầu phòng ban sống | Bảng màu theo khối khi vào phòng, kích thước / độ sáng / việc kẹt / hố đen nhỏ từ dữ liệu thật, mặt trăng = trợ lý |
| 3. Tìm kiếm và nạp xuyên thiên hà | Tìm từ thiên hà sáng tinh cầu có kết quả, bấm là Big Bang luôn; sao băng rơi vào đúng tinh cầu phòng đang nạp |

## 10b. Trạng thái: code xong 1.3.0 (2026-10-08)

Chủ không ưng bản demo của Codex, bảo bỏ demo và làm thẳng theo thiết kế này. Cả ba giai đoạn ở
mục 10 làm cùng lúc (trừ sao băng rơi đúng tinh cầu phòng đang nạp: hố đen nhỏ của phòng đã có,
sao băng riêng từng phòng để sau).

- Máy chủ `knowledge_sky.dung_thien_ha` + `GET /knowledge/galaxy`: Trái Đất (brain chủ), ngôi sao
  thương hiệu, mỗi phòng `{docs, raw, proc, recent7, agents, stuck, khoi, brand, path}`. Việc kẹt
  đọc thẳng `kanban.sqlite3` (status blocked) chỉ đọc. Nhân viên: chỉ phòng được gán, còn lại là
  `others` (đốm mờ), không thấy Trái Đất. Phạm vi nhân viên truyền vào qua `register(..., scope_fn)`
  (KHÔNG `import main` trong module: máy chủ chạy main.py trực tiếp, import lại là chạy lại cả máy chủ).
- Renderer: `ZMIN` 0,32 -> 0,12; `gxLevel()` = 1 - smooth(0,24; 0,42; zoom). Bố cục đơn vị thiên
  hà nhân `base x zoom x 1,55`, xoay theo `galAngle()`. Cụm khối xoắn ốc quanh Trái Đất (mỗi cụm
  +0,75 rad, +0,83 đơn vị); phòng trong cụm xếp hoa hướng dương (góc vàng), sắp theo tên trước để
  thứ tự dữ liệu không làm đổi chỗ (test bắt được). Ảnh tinh cầu 96px dựng sẵn, mỗi khung tối đa 2.
- Tinh cầu đang mở là phòng ban thì shader dùng bảng màu khối qua `curPal()` (không ghi
  `joyce.planetLook` của người dùng). Thêm bảng `pink` (ThuyH2O) và `paper` (Văn Thư).
- `flyTo`: 1,2 giây, tinh cầu lớn dần ra giữa, màn tối nhất lúc 0,55 thì gọi hud.js đổi brain
  (ô chọn brain + sự kiện change, đúng cơ chế trang Phòng ban), rồi zoom 0,38 -> 1 vào tinh cầu mới.
  Chọn brain ở ô chọn cũng diễn `arrive()`. Nút "Thiên hà" và "← Trái Đất" dưới công tắc Lõi nước.
- Tìm ở tầng thiên hà: `/knowledge/search?brain=brain` (phạm vi gộp), đếm kết quả theo brain, tinh
  cầu sáng + số; bấm vào thì tới nơi Big Bang luôn với từ khoá đó.

## 11. Quyết định đã chốt (2026-10-08)

| Câu hỏi | Chốt |
|---|---|
| Trái Đất là brain nào? | **Brain Default** (brain chủ), như hiện tại. |
| Bấm tinh cầu phòng ban thì sao? | **Đổi luôn brain đang mở**: khung chat, VAULT, Tệp tin, bầu trời tri thức đổi theo brain phòng đó. |
| Bảng kiểu tinh cầu theo khối (mục 4) | Giữ nguyên, không đổi khối nào. |
| Làm theo thứ tự nào? | Codex dựng **bản demo xem trước** theo `docs/dev/2026-10-thien-ha-prompt-codex.md`; chủ xem xong mới làm bản thật theo lộ trình mục 10. |
