# Prompt cho Codex: dựng BẢN DEMO "Thiên hà phòng ban"

Dán nguyên phần dưới vạch ngang vào Codex, chạy trong repo `E:\CLAUDECODE\H2O-JOYCE-OS`.

---

Bạn là kỹ sư frontend làm việc trong repo H2O Joyce OS (`E:\CLAUDECODE\H2O-JOYCE-OS`). Nhiệm vụ: dựng
một **bản demo xem trước** cho tính năng "Thiên hà phòng ban" để chủ dự án duyệt giao diện. Đây CHỈ là
demo, chưa đụng vào app thật.

## 1. Đọc trước khi làm

1. `docs/dev/2026-10-thien-ha-phong-ban.md`: thiết kế đầy đủ, đã được chủ duyệt (mục 11 là các quyết
   định đã chốt). Demo phải bám đúng tài liệu này.
2. `docs/dev/2026-10-tinh-cau-h2o.md`: cách quả tinh cầu hiện tại được vẽ (renderer
   `dashboard/brain-planet.js`, lộ ra `window.JoycePlanet`), mục 3 là API của renderer.
3. `docs/dev/2026-10-bau-troi-tri-thuc.md`: bầu trời tri thức, hố đen xoáy bồi tụ, Big Bang, sao băng.
4. `CLAUDE.md` mục "Dev conventions" và `docs/quy-uoc-dev.md`: luật màu / giao diện tối, cấm ký tự
   gạch ngang dài.

## 2. Phạm vi demo

Làm một trang độc lập, KHÔNG sửa file nào đang có của app:

- `dashboard/demo/thien-ha.html` (mở được ở `http://localhost:7777/static/demo/thien-ha.html` khi Joyce
  đang chạy, và mở thẳng bằng file:// cũng phải chạy).
- `dashboard/demo/thien-ha.js` (toàn bộ logic demo).
- `dashboard/demo/thien-ha-data.json` (dữ liệu, xem mục 3).
- `tools/demo_thien_ha_data.py` (script sinh file dữ liệu).

Được phép nạp `../brain-planet.js` và `../vn-geo.js` bằng thẻ `<script>` để dùng lại renderer tinh cầu
(Trái Đất và tinh cầu phòng ban khi đã bay tới). KHÔNG sửa `brain-planet.js`. Nếu thấy cần thêm API
vào renderer, ghi lại thành đề xuất trong báo cáo cuối, đừng tự sửa.

## 3. Dữ liệu thật cho demo

Viết `tools/demo_thien_ha_data.py`, chạy bằng `.venv\Scripts\python.exe`, đọc dữ liệu thật rồi ghi
`dashboard/demo/thien-ha-data.json`:

- Sơ đồ phòng ban: `server/h2o_departments.py` (`list_all()`: 11 khối, 44 phòng; mỗi phòng có
  `khoi_id`, `ten`, `brain`; mỗi khối có `brand`). Thương hiệu: `brands()` (`h2o`, `thuyh2o`).
- Số liệu mỗi brain: `server/knowledge_sky.py`, gọi `_quet_brain(Path(brains/<brain>), <brain>)` cho
  từng brain trong `brains/`, đếm theo `kind` (`star`, `orbit`, `debris`) và số tài liệu sửa trong 7
  ngày (`_mtime`). Đặt `knowledge_sky._deps` như trong `tests/python/test_bau_troi_tri_thuc.py`.
- Đầu ra mỗi phòng: `{brain, ten, khoi_id, khoi_ten, brand, docs, raw, recent7}`; thêm hai brain chung
  thương hiệu (`H2O Studio`, `ThuyH2O Studio`) và `Brain Default` (đánh dấu `role: "earth"`).
- Số việc kẹt: chưa có nguồn rẻ, cho demo sinh giả 0-2 theo băm tên brain và ghi rõ trong JSON là
  `"stuck_demo": true`.

## 4. Demo phải cho thấy được

Bám mục 2 đến 7 của tài liệu thiết kế:

1. **Mở trang**: Trái Đất (Brain Default) ở giữa, y như màn Joyce hiện tại (dùng `JoycePlanet.create`
   + `mount` + `setKnowledge` với dữ liệu giả nhỏ là đủ).
2. **Lăn chuột ra xa** (và nút "Thiên hà" ở góc trên) chuyển mượt sang **tầng Thiên hà**: Trái Đất thu
   thành chấm sáng có nhãn "Bạn đang ở đây"; 44 tinh cầu phòng ban hiện ra.
3. **Bố cục**: hai cánh tay xoắn (H2O Studio xanh lam, ThuyH2O hồng tím), brain chung thương hiệu là
   ngôi sao lớn đầu mỗi cánh, 11 cụm theo khối có vầng tinh vân mờ cùng màu, tên khối hiện khi rê.
   Vị trí cố định theo băm tên brain.
4. **Kiểu tinh cầu theo khối**: đúng bảng mục 4 (bảng màu + chi tiết nhận diện: vành Kế Toán, mây
   Nhân Sự, bão Marketing, dung nham Bán Hàng / Sản Xuất, tinh thể Nghiên Cứu, đại dương CSKH, băng Vệ
   Sinh, ăng ten Truyền Thông, vành giấy Văn Thư, kim tuyến ThuyH2O). Phòng cùng khối lệch sắc độ nhẹ.
   Vẽ 44 tinh cầu bằng **ảnh canvas 2D dựng sẵn một lần** (cầu có ánh sáng + nhiễu bề mặt), không dùng
   WebGL cho từng cái.
5. **Tín hiệu sống** (mục 5): to nhỏ theo `docs`, sáng theo `recent7`, nhấp nháy đỏ khi có việc kẹt,
   hố đen nhỏ cạnh tinh cầu khi `raw > 0`. Rê chuột hiện thẻ nhỏ: tên phòng, số tài liệu, việc kẹt.
6. **Bấm một tinh cầu**: camera bay tới trong khoảng 1,2 giây, tinh cầu đó ra giữa màn; đổi renderer
   sang bảng màu của khối (`JoycePlanet.setLook({palette})` có sẵn: ocean, emerald, amethyst, sunset,
   ice, lava, gold, abyss). CHÚ Ý: `setLook` ghi vào localStorage `joyce.planetLook` dùng chung với
   app thật, nên demo phải lưu `JoycePlanet.getLook()` lúc mở trang và trả lại khi rời trang / quay về
   Trái Đất, không thì giao diện tinh cầu thật của chủ bị đổi theo. Góc trên có "← Thiên hà" và "← Trái Đất". Trong demo, "đổi brain" chỉ cần
   hiện dòng "Đã chuyển sang brain: <tên>" (bản thật mới đổi khung chat và VAULT).
7. **Tìm từ thiên hà**: ô tìm nhỏ trên trang demo; gõ "báo giá" thì các tinh cầu có tài liệu khớp
   sáng lên kèm số kết quả (demo được phép khớp theo tên brain / khối, hoặc thêm vào JSON danh sách
   tiêu đề tài liệu mỗi brain để khớp thật).

## 5. Luật bắt buộc

- Chú thích code bằng **tiếng Việt có dấu**, giải thích VÌ SAO, đúng giọng các file trong `dashboard/`.
- **Không dùng ký tự gạch ngang dài (U+2014)** ở bất kỳ đâu: code, chú thích, chữ trên giao diện.
- Màu nền / chữ của phần giao diện HTML (nút, thẻ, ô tìm) dùng token theme trong `dashboard/style.css`
  (`--bg`, `--text`, `--text2`, `--surface-1`, `--hairline`, `--accent`...), không tô màu cứng; trang
  demo nạp `../style.css` để có token. Màu trong canvas (vũ trụ) được tự chọn.
- Không emoji trên giao diện.
- Chạy được trên máy yếu: trần số hạt / hiệu ứng, `prefers-reduced-motion` thì bỏ hiệu ứng bay.
- Không thêm thư viện ngoài, không gọi mạng ngoài.

## 6. Git

- Làm trên nhánh mới `demo/thien-ha-phong-ban`, KHÔNG commit vào `main`, KHÔNG sửa `VERSION` /
  `CHANGELOG.md`, KHÔNG merge.
- Commit cuối kèm thông điệp mô tả ngắn bằng tiếng Việt không dấu như các commit hiện có.

## 7. Kiểm tra trước khi báo xong

1. Chạy `tools/demo_thien_ha_data.py`, kiểm tra JSON đủ 44 phòng + 2 brain chung + Brain Default.
2. `node --check dashboard/demo/thien-ha.js`.
3. Mở trang bằng Chrome chạy ngầm và chụp ảnh ba trạng thái: Trái Đất, tầng Thiên hà, sau khi bay tới
   một phòng (ví dụ "Ke Toan - Thu"). Lưu ảnh vào `dashboard/demo/shots/`. Lưu ý Chrome chạy ngầm vẽ
   rất ít khung hình với WebGL giả lập: nếu hiệu ứng không kịp chạy, thêm tham số URL để nhảy thẳng
   tới trạng thái cần chụp (ví dụ `?tang=thienha`, `?vao=Ke Toan - Thu`).
4. Tự xem lại ảnh: tinh cầu không đè lên nhau, chữ đọc được, hai cánh tay thiên hà rõ, khác biệt giữa
   các khối thấy được bằng mắt.

## 8. Báo cáo cuối

Viết ngắn bằng tiếng Việt: đã làm gì, mở demo ở đâu, ảnh chụp ở đâu, phần nào trong thiết kế chưa
làm được hoặc làm khác đi và vì sao, và đề xuất API cần thêm vào `brain-planet.js` cho bản thật.
