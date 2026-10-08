# Bầu trời tri thức: thiết kế chi tiết

Chủ repo đề xuất 2026-10-08, chốt phạm vi cùng ngày. Tài liệu này là bản thiết kế để code theo,
và là chỗ tra lại sau này khi muốn đổi một chi tiết. Đi kèm `docs/dev/2026-10-tinh-cau-h2o.md`
(thiết kế quả tinh cầu): đọc file đó trước nếu chưa biết renderer vẽ thế nào.

Mã nguồn là sự thật cuối cùng. Chỗ nào tài liệu và mã lệch nhau thì sửa tài liệu.

---

## 1. Ý tưởng trong một đoạn

Mỗi tài liệu kiến thức trong brain là một thiên thể quanh quả tinh cầu. Loại thiên thể nói
kiến thức đang ở giai đoạn nào: **đá vụn** gần dải ngân hà là tài liệu thô chưa chưng cất,
**chấm trên ba vành quỹ đạo** là tri thức vận hành dùng hằng ngày, **các vì sao** quanh địa cầu
là kiến thức đã chưng cất. Tìm một từ khoá (ví dụ "Báo giá") thì các thiên thể liên quan va
vào nhau thành một vụ **Big Bang**, rồi nở ra thành **chòm sao** tinh cầu nhỏ để chọn; bấm một
tinh cầu là hiện thẻ **Đọc nhanh** gồm các đầu mục có sẵn trong tài liệu.

Câu chuyện khép kín với hiệu ứng đã có: đá vụn bị hố đen hút vào để chưng cất, tia sáng bắn về
đúng địa chỉ H2O Studio · ThuyH2O Makeup trên Trái Đất, và một ngôi sao mới sinh ra.

---

## 2. Quyết định đã chốt (2026-10-08)

| Câu hỏi | Chốt |
|---|---|
| Bầu trời hiện kiến thức của ai? | **Admin ở brain chủ** (Brain Default) thấy bầu trời GỘP mọi phòng ban. **Admin mở riêng brain một phòng** thì chỉ thấy trời của phòng đó. **Nhân viên** thấy trời của brain đang mở, trong phạm vi phòng được gán. |
| Đọc nhanh lấy nội dung từ đâu? | **Các đầu mục có sẵn trong tài liệu**, rút bằng code, không gọi AI. Không tốn lượt, bấm là hiện ngay. |
| Làm theo thứ tự nào? | Viết tài liệu này trước, rồi code theo giai đoạn (mục 9). |

"Brain chủ" nhận theo đường dẫn: gốc brain của request trùng `_default_brain_dir()`. Không so
theo tên hiển thị vì tên đổi được.

Phạm vi nhân viên KHÔNG tự viết lại ở đây: endpoint đi qua `_brain_root`, mà `_brain_root` đã
ép mọi brain vào phạm vi phòng của nhân viên (`_STAFF_SCOPE`, `_scope_root`). Nhân viên gửi
đường dẫn Brain Default lên thì nhận về brain mặc định của chính họ, không bao giờ là trời gộp.
Trời gộp chỉ bật khi `_STAFF_SCOPE.get()` rỗng (admin) VÀ gốc là brain chủ.

---

## 3. Thiên thể nào là tài liệu nào

| Thiên thể | Lấy từ | Ý nghĩa |
|---|---|---|
| **Đá vụn** (vành đai quanh hố đen, gần dải ngân hà) | `sources/**`, `inbox/**` (mọi file, kể cả .pdf/.docx) | Nguyên liệu thô, chưa chưng cất |
| **Vành 1** (trong cùng, 1,42R) | `skills/*/SKILL.md`, trừ 6 skill hệ thống | Kỹ năng riêng của brain |
| **Vành 2** (giữa, 1,66R) | `workflows/*.md` | Quy trình Joyce tự chạy |
| **Vành 3** (ngoài, 1,92R) | `memory/facts/*.md` | Trí nhớ về doanh nghiệp và người dùng |
| **Sao** (vòm trời quanh địa cầu) | MỌI `wiki/**/*.md` | Kiến thức đã chưng cất. Trang là quy trình (tag `quy-trinh`, hoặc tên bắt đầu "Quy trình") mang cờ `proc` và vẽ thành sao bốn cánh |

Hai điều chỉnh sau khi chạy thử trên dữ liệu thật (2026-10-08, 47 brain, 1010 tài liệu):

- **Skill hệ thống không tính** (`system_sync.is_system_skill`): mỗi brain mang một bản sao của
  6 skill hệ thống, tính vào thì thành 276 chấm giống hệt nhau trên vành 1.
- **Wiki quy trình vẫn là sao**: wiki H2O lúc viết có 214 trên 222 trang là quy trình. Đưa chúng
  lên vành 2 như bản nháp đầu thì vòm trời chỉ còn 8 sao và vành 2 chật cứng. Hình bốn cánh đủ
  để phân biệt mà không làm trống bầu trời.

Bỏ qua: file và thư mục ẩn, `Joyce/` (file hệ thống tự sinh), và các trang quản trị wiki
(`index.md`, `log.md`, `_open-questions.md`, `_session-handoff.md`, mọi tên bắt đầu bằng `_`).

**Màu theo thương hiệu** (`h2o_departments.phong_by_brain` rồi `brand_of_phong`): H2O Studio màu
xanh số (`PAL.cyan`), ThuyH2O màu hồng tím (`PAL.magenta`), brain chủ và brain không thuộc phòng
nào màu vàng (`PAL.gold`). Brand thứ ba trở đi lấy màu kế tiếp trong `PAL` theo thứ tự brand.

**Cỡ** theo độ quan trọng đo được, không đoán: số liên kết `[[...]]` trỏ tới tài liệu (đếm trong
cùng phạm vi) cộng số liên kết nó trỏ đi, kẹp log. Tài liệu sửa trong 7 ngày gần nhất nháy nhẹ.

---

## 4. Bố cục trên màn hình

Mọi vị trí **cố định theo tài liệu**: lấy từ băm (FNV-1a 32 bit) của `brain + "/" + path`. Cùng
một tài liệu luôn nằm đúng một chỗ, dùng lâu người dùng nhớ được "báo giá nằm ở góc kia". Thêm
tài liệu mới không làm các thiên thể cũ nhảy chỗ.

- **Vành quỹ đạo**: góc `a = băm % 2π`, chạy chậm cùng chiều với hạt trang trí hiện có
  (`ringPt(i, a)`), nên hưởng luôn thanh trượt Cỡ vành quỹ đạo và Cỡ chấm trên vành.
- **Sao**: rải trên một vỏ cầu bán kính 2,3R đến 3,4R quanh tâm hành tinh, toạ độ khung nhìn
  (xoay theo camera như vành). Vĩ độ ưu tiên nửa trên (`lat` từ -0,35 đến 1,2 rad) để "bên trên
  địa cầu là các vì sao". Kinh độ chia theo **cung của phòng ban**: mỗi brain một cung, nên kiến
  thức một phòng tụ lại thành một vùng trời.
- **Đá vụn**: vành đai elip quanh hố đen (`geo.bh`), bán kính 0,10 đến 0,24 lần cạnh ngắn màn
  hình, trôi chậm quanh hố, mỗi viên là một đa giác 5 đến 7 cạnh méo (đá, không phải chấm tròn).
- Thiên thể nằm sau đĩa hành tinh thì bị che, như vành quỹ đạo (`hidden`).

**Trần số lượng** (máy yếu tự giảm): sao 1500 / 900 / 300, vành 600 / 400 / 150, đá vụn 600 /
350 / 120 theo hồ sơ high / balanced / safe; `reduced` không vẽ thiên thể chuyển động. Vượt
trần thì giữ theo cỡ (quan trọng trước), phần còn lại vẫn có trong dữ liệu để tìm kiếm, chỉ
không vẽ thường trực. Máy chủ trả số đếm thật để giao diện nói rõ "đang hiện 1500 trên 2340".

---

## 5. Thẻ Đọc nhanh

Bấm một thiên thể: thẻ DOM nổi cạnh điểm bấm (giống tooltip vệ tinh, nhưng giữ lại tới khi bấm
ra ngoài hoặc Esc). Nội dung:

- Tiêu đề, loại thiên thể, phòng ban (tên brain), ngày sửa.
- **3 đến 6 gạch đầu dòng** rút từ tài liệu (mục 5.1).
- Nút: **Mở** (mở trình sửa file, chỉ khi tài liệu thuộc brain đang mở), **Hỏi Joyce** (điền
  sẵn câu hỏi về tài liệu vào ô chat, không tự gửi, giống câu mẫu ở Cẩm nang), **Đóng**.

### 5.1 Rút đầu mục (không AI)

Thứ tự ưu tiên, lấy nguồn đầu tiên cho ra ít nhất 2 mục:

1. Frontmatter `tom_tat` hoặc `summary` (danh sách hoặc chuỗi) nếu tài liệu tự khai.
2. Tiêu đề markdown `#`, `##`, `###` (bỏ tiêu đề trùng tên file).
3. Gạch đầu dòng cấp 1 (`- `, `* `, `1. `) trong 60 dòng đầu.
4. **Dòng tiêu đề trần** của tài liệu chuyển từ .docx: dòng đứng riêng, 4 đến 70 ký tự, không
   kết thúc bằng dấu chấm, không phải số trần hay mã hiệu, có ít nhất 2 từ. (Wiki H2O phần lớn
   là .docx chuyển sang nên không có `#`; mục này là để chúng vẫn có đầu mục.)
5. Ba câu đầu của phần thân.

Mỗi mục cắt còn 90 ký tự, bỏ mục trùng. Không đọc quá 200KB đầu file. Tài liệu không phải văn
bản (.pdf, .docx trong `sources/`) chỉ có tiêu đề + đường dẫn + gợi ý "chưa chưng cất, nhờ
Joyce chưng cất".

---

## 6. Tìm kiếm: Big Bang và chòm sao (giai đoạn 2)

Nguồn kết quả: chính ô VAULT ở cột trái (`#vaultSearch`). Tìm xong (bấm Enter, hoặc ngừng gõ
700ms) thì danh sách kết quả đẩy sang tinh cầu bằng `R.focusKnowledge({q, ids})`. Không nổ theo
từng chữ gõ.

Biên đạo khoảng 2,5 giây:

| Thời điểm | Diễn ra |
|---|---|
| 0 đến 0,3s | Bầu trời tối lại 60%, thiên thể không liên quan mờ còn 15%. |
| 0,3 đến 1,1s | Thiên thể liên quan (đá vụn, chấm, sao) bị kéo theo đường cong về **điểm hội tụ** phía trước-trên hành tinh, nhanh dần. |
| 1,1 đến 1,4s | **Va chạm**: loé trắng ở điểm hội tụ, vòng sóng xung kích lan ra, 40 đến 80 mảnh văng (dùng lại bộ hạt nóng `launch`). |
| 1,4 đến 2,5s | **Nở thành chòm sao**: tối đa 12 kết quả đầu thành tinh cầu nhỏ (bán kính 6 đến 18px theo độ khớp) xếp vòng cung quanh địa cầu, nhấp nháy theo màu concept bề mặt (`look.palette`). Tài liệu nào `[[liên kết]]` tới nhau thì nối bằng vệt sáng mảnh. Phần còn lại là chấm lấp lánh, kèm dòng "và N tài liệu nữa". |
| Sau đó | Đứng yên chờ chọn. Rê chuột lên dòng kết quả ở ô VAULT thì tinh cầu tương ứng sáng lên, và ngược lại. |
| Xoá ô tìm / Esc | Chòm sao thu nhỏ rồi bay ngược về chỗ cũ trong 0,8s. |

Độ khớp: khớp tên file > khớp tiêu đề wiki > khớp nội dung; cùng loại thì tài liệu nhiều liên
kết hơn đứng trước. Máy yếu (`safe`, `reduced`) bỏ hội tụ và vụ nổ, chỉ làm sáng kết quả.

Kết quả tìm được ngoài phần đang vẽ (vượt trần mục 4) vẫn được nở thành tinh cầu: chòm sao lấy
từ danh sách kết quả chứ không chỉ từ thiên thể đang hiện.

---

## 7. Khép vòng với hố đen (giai đoạn 3)

- Nạp xong (`ing.beam`), tia sáng hiện đang bắn về mép hành tinh gần hố đen nhất. Đổi đích về
  **ghim H2O Studio** (`JoyceVNGeo.studio`, Hải Phòng) khi ghim đang ở nửa thấy được; khuất thì
  giữ mép như cũ.
- Khi tia chạm đất, các tài liệu vừa chưng cất (so danh sách thiên thể trước và sau khi nạp) hiện
  thành sao mới: loé, rồi bay từ điểm chạm lên đúng vị trí cố định của chúng trên vòm trời.
- Đá vụn tương ứng tài liệu nguồn đã chưng cất mờ đi và biến mất ở lần nạp bầu trời kế tiếp.

---

## 8. Kiến trúc và API

### 8.1 Máy chủ (`server/knowledge_sky.py`, mount qua `register(app, deps)`)

```
GET /knowledge/sky?brain=<gốc brain>
 -> {ok, scope: "all"|"brain", brains: [{key, name, brand, color}],
     bodies: [{id, kind, ring, brain, path, title, size, recent}],
     counts: {star, orbit, debris, total}}
GET /knowledge/quick?brain=<gốc>&src=<key brain>&path=<đường dẫn trong brain>
 -> {ok, title, kind, brain_name, path, updated, bullets: [...], text_file: bool}
```

- `kind`: `star` | `orbit` | `debris`; `ring` 0, 1, 2 cho `orbit`.
- `id` = băm 32 bit dạng hex của `brain + "/" + path`, cũng là hạt giống vị trí phía trình duyệt.
- `brain` trong mỗi thiên thể là **key ngắn** (`b0`, `b1`...) trỏ vào mảng `brains`, để không lặp
  đường dẫn tuyệt đối hàng nghìn lần. Đường dẫn tuyệt đối không ra khỏi máy chủ; `/knowledge/quick`
  nhận key brain + path rồi tự dựng lại và kiểm nằm trong gốc brain (chặn `..`).
- Quét trong threadpool, cache theo (gốc brain, thời điểm sửa mới nhất của các thư mục kiến thức),
  sống 60 giây. 46 brain x vài trăm file quét lại mỗi lần mở là quá đắt.
- Chỉ đọc. Nhân viên đi qua `_brain_root` nên tự bị khoá phạm vi (mục 2).

### 8.2 Renderer (`dashboard/brain-planet.js`)

```js
r.setKnowledge({brains, bodies});      // thay cả bầu trời; giữ vị trí cố định theo id
r.focusKnowledge({q, ids} | null);     // giai đoạn 2: Big Bang + chòm sao; null = thu về
opts.onKnowledgeClick(body, {x, y});   // bấm một thiên thể
```

- Vẽ trong `frame()`: sao và đá vụn ngay sau `drawMoonPath` (nằm sau mọi thứ), chấm tri thức
  trên vành vẽ cùng nhịp `drawParticles` (nửa sau rồi nửa trước) để bị hành tinh che đúng.
- Bắt chuột: sau `hitSat` (vệ tinh ưu tiên), tìm thiên thể gần nhất trong 9px (`hitKnow`). Mỗi
  khung dựng lại danh sách điểm ĐANG HIỆN (`know.hits`) rồi quét thẳng: trần 2700 điểm là vài
  nghìn phép so, dưới 0,1ms mỗi lần rê. Lưới ô chỉ đáng làm nếu trần vượt cỡ 10 nghìn.
- Bấm thiên thể được xét TRƯỚC bấm hành tinh: chấm vành nằm đè lên đĩa hành tinh, xét sau thì
  bấm chấm thành gọi Joyce.
- Công tắc `look.knowledge` (mặc định bật) trong thẻ Khác của tab Quả tinh cầu; tắt thì bầu
  trời trở về như cũ. Thêm khoá thì thêm cả `_PLANET_BAT` trong `main.py` (test canh hai bên).

### 8.3 Người nuôi (`dashboard/hud.js`)

- Nạp `/knowledge/sky` khi mount, khi đổi brain, và mỗi 5 phút; đẩy vào `planet.setKnowledge`.
- Thẻ Đọc nhanh (`openKnow`) dùng lại ngăn kéo `#planetCtx` của vệ tinh: cùng chỗ đứng, cùng
  cách đóng (nút x, Esc, bấm khoảng trống), lớp `.pc-know-*` theo token theme.
- Đổi brain: nghe `change` của ô `#graphSource`, và `refresh()` 45 giây gọi `loadKnow(false)`
  (chỉ nạp lại khi brain khác) để bắt cả đường đổi brain không qua ô chọn.
- Giai đoạn 2: nghe ô `#vaultSearch` (console.js phơi kết quả qua sự kiện `joyce:vault-search`).

---

## 9. Lộ trình

| Giai đoạn | Nội dung | Xong khi |
|---|---|---|
| **1. Bản đồ sao thật** (code xong 1.0.4, 2026-10-08) | Endpoint `/knowledge/sky` + `/knowledge/quick`, vẽ sao, chấm vành, đá vụn từ dữ liệu thật, rê chuột hiện tên, bấm hiện thẻ Đọc nhanh, công tắc trong Cài đặt. | Admin ở Brain Default thấy trời gộp, mở brain phòng thì thấy trời phòng đó; bấm một sao đọc được đầu mục. |
| **2. Big Bang** | `focusKnowledge`, biên đạo mục 6, đồng bộ hai chiều với ô VAULT. | Gõ "Báo giá" + Enter thấy nổ và chòm sao, bấm chọn được. |
| **3. Khép vòng** | Tia sáng về ghim H2O Studio, sao mới sinh sau khi nạp. | Nạp một tài liệu, thấy sao mới bay lên chỗ của nó. |

---

### 9.1 Phát hiện khi chạy giai đoạn 1 trên dữ liệu thật (2026-10-08)

47 brain, 1010 tài liệu: 477 đá vụn, 222 sao (214 là quy trình), 15 kỹ năng, 14 trí nhớ, 0
workflow. Đo đầu mục trên 222 trang wiki: 158 trang có từ 2 đầu mục trở lên, **73 trang chỉ còn
trang bìa** (dưới 60 từ: mã hiệu, lần ban hành, ngày ban hành, số trang) và 10 trang không rút
được đầu mục nào. 73 trang đó bị mất nội dung lúc chuyển .docx sang wiki, không phải lỗi của
bầu trời: cần chưng cất lại từ file gốc trong `sources/` thì Đọc nhanh mới có gì để hiện.

## 10. Rủi ro và cách giữ

- **Quá nhiều thiên thể làm rối mắt**: trần ở mục 4, đá vụn và sao mờ hơn vành, chỉ vành và
  chòm sao kết quả được sáng rõ.
- **Chậm khung hình**: thiên thể vẽ bằng `fillRect`/`arc` không gradient (gradient chỉ cho tinh
  cầu chòm sao, tối đa 12); bộ tự hạ chất lượng sẵn có (FPS < 30) vẫn áp dụng.
- **Lộ dữ liệu phòng khác**: phạm vi tính ở máy chủ, trình duyệt không bao giờ nhận đường dẫn
  tuyệt đối; `/knowledge/quick` kiểm path nằm trong gốc brain được phép.
- **Đầu mục rác** từ .docx chuyển đổi (mã hiệu, số trang): luật mục 5.1 bước 4 lọc số trần,
  mã hiệu, dòng một từ; test khoá bằng mẫu thật từ wiki H2O.

## 11. Kiểm thử

- `tests/python/test_bau_troi_tri_thuc.py`: phân loại thiên thể, bỏ file hệ thống, trời gộp chỉ
  cho admin ở brain chủ, nhân viên bị khoá phạm vi, `/knowledge/quick` chặn `..`, rút đầu mục
  (đủ 5 nguồn, mẫu .docx thật).
- `tests/js/test_bau_troi_tri_thuc.js`: vị trí cố định theo id, trần theo hồ sơ, công tắc khớp
  máy chủ, bắt chuột trúng thiên thể, thẻ Đọc nhanh dùng token theme.
