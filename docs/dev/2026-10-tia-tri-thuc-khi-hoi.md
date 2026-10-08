# Tia tri thức khi hỏi Joyce: thiết kế chi tiết

Chủ repo đề xuất 2026-10-08: "khi anh hỏi Joyce về bất kỳ điều gì thì đều có hiệu ứng lấy kiến
thức từ dữ liệu rồi bắn tia sáng về H2O". Chủ duyệt ý tưởng, yêu cầu lưu thiết kế trước rồi làm
cả ba bước A, B, C; chủ duyệt sau.

Đi kèm `docs/dev/2026-10-bau-troi-tri-thuc.md` (bầu trời tri thức: thiên thể nào là tài liệu
nào) và `docs/dev/2026-10-tinh-cau-h2o.md` (renderer). Mã nguồn là sự thật cuối cùng.

---

## 1. Nguyên tắc: chỉ diễn đúng việc Joyce thật sự làm

Hiệu ứng KHÔNG phải trang trí cho đẹp. Mỗi sợi sáng ứng với MỘT lần Joyce thật sự đọc một tài
liệu hoặc gọi một nguồn dữ liệu trong lượt trả lời đó. Joyce trả lời mà không đọc gì (kiến thức
chung) thì không có sợi nào: chỉ một nhịp sáng nhẹ ở lõi địa cầu. Nhìn bầu trời là biết câu trả
lời có dựa trên tài liệu của H2O hay không, và dựa trên tài liệu nào.

Nguồn sự thật: khung `tool_call` mà máy chủ gửi xuống khung chat trong mỗi lượt (chính là dữ
liệu đang hiện thành các dòng "Đọc file: …" trong khối tiến trình).

---

## 2. Nhịp diễn một câu hỏi

| Lúc | Trong lượt chat | Trên bầu trời |
|---|---|---|
| Gửi câu hỏi | khung `status` đầu tiên của lượt | Từ ghim H2O Studio phát ra **vòng sóng quét** lan khắp bầu trời như radar, lặp mỗi 2,4 giây tới khi có câu trả lời. Sao mờ đi một chút. |
| Joyce đọc một tài liệu | `tool_call` có đường dẫn file khớp một thiên thể | Thiên thể đó **bừng sáng** (vòng sáng nhấp nháy) và một **sợi chỉ sáng** cong chạy từ nó về ghim H2O, hạt sáng trôi dọc sợi về phía H2O. Đọc file thô chưa chưng cất thì sợi đi từ viên đá vụn quanh hố đen. |
| Joyce gọi nguồn dữ liệu ngoài | `tool_call` là công cụ MCP / plugin / web | Tia đi từ **vệ tinh hoặc Mặt Trời** của đúng app đó (vd `h2o-legacy` → H2O Legacy). Nguồn không có thiên thể riêng (Facebook, Zalo, Internet...) đi từ một **cổng** ở mép trái khung, có ghi tên nguồn. |
| Bắt đầu trả lời | khung `stream` đầu tiên (hoặc `response` nếu không stream) | Các sợi **co về** H2O trong 0,7 giây, rồi ghim H2O **loé sáng** (quầng + vòng sóng): kiến thức đã về tới nơi. Không có sợi nào thì chỉ một nhịp sáng nhẹ ở lõi địa cầu. |
| Trả lời xong | `response` / `turn_done` / `error` | Thiên thể đã dùng còn **sáng thêm 10 giây** rồi trở lại bình thường. Bấm vào vẫn mở thẻ tóm tắt như thường. |
| Dưới câu trả lời | khi vẽ bong bóng trả lời | Hàng chip **"Nguồn tri thức"**: mỗi tài liệu đã đọc một chip, bấm là mở file (kể cả file ở brain phòng khác). |

Ghim H2O khuất sau địa cầu thì đích là mép địa cầu gần nhất phía ghim (cùng luật với tia sáng
sau khi nạp dữ liệu).

---

## 3. Ghép lệnh gọi công cụ với thiên thể (bước A)

**Đường dẫn file**: máy chủ gửi kèm trường `files` trong `tool_call` (tool_label.tep: mọi giá
trị dạng đường dẫn trong `file_path`, `notebook_path`, `path`, `paths`, kể cả trong `arguments`
JSON lồng, đầy đủ không rút gọn). Máy chủ cũ chưa có `files` thì trình duyệt bóc từ `detail`
(chỉ còn 3 đoạn cuối, vẫn đủ ghép phần lớn trường hợp).

**Ghép** (hud.js `ghepThienThe`): chuẩn hoá gạch chéo, bỏ tiền tố "…/", hạ chữ thường. Một thiên
thể khớp khi đường dẫn kết thúc bằng `/<path trong brain>` hoặc bằng chính nó. Nhiều brain cùng
có file trùng đường dẫn thì ưu tiên brain có tên nằm trong đường dẫn, rồi brain đang mở.
`X.docx.txt` ghép về thiên thể `X.docx` (cùng một tài liệu, xem mục 9.2 thiết kế bầu trời).
Đường dẫn không khớp thiên thể nào (CLAUDE.md, MEMORY.md, file code...) thì BỎ, không bịa sợi.

## 4. Nguồn dữ liệu ngoài (bước B)

Công cụ cục bộ (Read, Write, Edit, Bash, Glob, Grep, Task, TodoWrite, các `joyce_*` quản trị...)
không tính là nguồn ngoài. Còn lại:
- `WebSearch`, `WebFetch` → cổng **Internet**.
- `mcp__<máy chủ>__<tool>` hoặc `<máy chủ>__<tool>` → tên máy chủ. Plugin theo tiền tố: `fb_` →
  Facebook, `zalo_` → Zalo, `crm_` → CRM.
- Tên nguồn (bỏ dấu, chỉ chữ/số) chứa hoặc nằm trong tên / id của một app H2O đang là thiên thể
  (Mặt Trời, Mặt Trăng, vệ tinh) → tia đi từ thiên thể đó. Không khớp → cổng ở mép trái.
- Mỗi nguồn chỉ một tia trong một lượt.

## 5. Chip "Nguồn tri thức" (bước C)

app.js gom `files` của mọi `tool_call` trong lượt (`t.tep`). Lúc vẽ bong bóng trả lời, nếu ghép
được ít nhất một thiên thể thì thêm một hàng chip dưới bong bóng (tối đa 8, thừa thì "+N"), màu
theo token theme. Bấm chip = mở file trong trình xem/sửa lớn (đúng brain của file).

Giới hạn đã biết: hàng chip chỉ có ở lượt vừa trả lời trong phiên đang xem; tải lại trang thì
không vẽ lại (kho phiên chưa lưu danh sách nguồn). Muốn giữ qua F5 thì lưu thêm khối ẩn
`JOYCE_NGUON` vào bản ghi lượt, để lần sau.

## 6. Kiến trúc

```
app.js (khung WS của lượt)  --CustomEvent "joyce:turn-trace" {pha, tool, files}-->  hud.js
hud.js: ghép files -> id thiên thể (D.know), ghép tool -> app/cổng  -->  planet.traceTurn(pha, ...)
brain-planet.js: drawTrace (vẽ trên thiên thể, dưới Big Bang và cảnh nhìn sâu hố đen)
app.js lúc vẽ bong bóng: window.JoyceTriThuc.chips(bong bóng, t.tep)
```

Pha của `traceTurn`: `start` | `source {id}` | `gate {kind: "sat", id} | {kind: "edge", label}` |
`answer` | `done`. Mọi pha đều an toàn khi gọi lặp hoặc sai thứ tự (vd `answer` không có `start`).

## 7. Hiệu năng và máy yếu

Tối đa 24 sợi một lượt (thừa thì bỏ sợi sau), mỗi sợi một đường cong + 3 hạt. Hồ sơ `safe` /
`reduced`: không vòng quét lặp, sợi thẳng không hạt, vẫn có loé ở H2O.

## 7b. Trạng thái

Bước A, B, C code xong ở 1.1.0 (2026-10-08), chờ chủ duyệt. Đã chụp thử bằng Chrome chạy ngầm
với dữ liệu thật (6 tài liệu "báo giá", H2O Legacy, Facebook): vòng quét, sợi từ đá vụn và sao,
tia từ Mặt Trời H2O Legacy, cổng Facebook ở mép trái đều hội tụ về ghim H2O. Test bắt được một
lỗi ghép nhầm: "facebook-pages" chứa "book" (id ngắn của H2OBOOK); giờ chỉ ghép khi trùng hẳn
hoặc phần chứa nhau dài từ 5 ký tự.

Máy chủ chưa khởi động lại thì chưa có trường `files`: trình duyệt bóc đường dẫn từ `detail`
(3 đoạn cuối), vẫn ghép được phần lớn tài liệu.

## 7c. Sửa sau lần chủ thử đầu tiên (1.1.1, 2026-10-08)

Chủ hỏi Joyce (bộ não Codex) "báo giá online gói chụp ảnh ngoại cảnh": chỉ có vòng sóng quét,
không có sợi nào, không có chip. Hai gốc và một bổ sung:
- **Codex đọc file bằng lệnh shell** (`Get-Content '...md'`, `cat`, `sed -n`), không có khoá
  `file_path`. Giờ bóc đường dẫn trong câu lệnh: chuỗi trong nháy, hoặc từ không nháy có gạch
  chéo, kết thúc bằng đuôi tài liệu (máy chủ `tool_label.tep_trong_lenh`, trình duyệt
  `tepTrongChu`). Lệnh tìm (`rg "báo giá" wiki`) không tính là đã đọc.
- **Câu mở đầu chảy về trước khi đọc** ("Em sẽ kiểm tra Wiki..."), bị coi là "đã trả lời" nên
  mọi lệnh đọc sau đó bị bỏ. Giờ lệnh gọi tới sau nhịp `answer` thì mở lại vòng thu thập; chữ
  chảy lại SAU một lệnh gọi mới là `answer` tiếp theo.
- **Tài liệu trích dẫn trong câu trả lời** (`[tên](wiki/x.md)`, `[[wiki/x]]`, đúng dạng Joyce
  ghi ở dòng "Nguồn: ...") cũng là nguồn thật: thành sợi và chip, đẩy vào trước nhịp `answer`.
- Ghép chuẩn hoá Unicode NFC cho tên file tiếng Việt.

## 8. Kiểm thử

`tests/js/test_tia_tri_thuc.js`: ghép đường dẫn (tuyệt đối, tương đối, "…/", `.docx.txt`, file
không có trên trời), phân loại công cụ và ghép app, nhịp `traceTurn` chạy thật trong vm (sóng
quét, sợi, co về, loé, sáng thêm 10 giây), chip nguồn, nối dây app.js. `tests/python/
test_bau_troi_tri_thuc.py`: `tool_label.tep` rút đủ đường dẫn từ mọi dạng tham số.
