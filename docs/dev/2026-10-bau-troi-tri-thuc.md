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

Từ khoá lấy từ ô VAULT ở cột trái (`#vaultSearch`): bấm Enter hoặc ngừng gõ 700ms thì
console.js bắn sự kiện `joyce:vault-search {q}` (cùng từ khoá không bắn lại; xoá ô / Esc bắn
`q` rỗng). Không nổ theo từng chữ gõ.

Kết quả KHÔNG lấy từ danh sách của ô VAULT: ô đó chỉ tìm trong brain đang mở, còn bầu trời của
admin ở brain chủ là mọi phòng. hud.js hỏi `/knowledge/search` (cùng phạm vi, cùng phân loại với
`/knowledge/sky` vì dùng chung `_tat_ca`) rồi gọi `R.focusKnowledge({q, hits, total})`. Danh sách
dòng ở ô VAULT vẫn là của brain đang mở; rê chuột hai chiều chỉ nối được những dòng thuộc brain đó
(sự kiện `joyce:vault-hover` / `joyce:sky-hover`, khớp theo đường dẫn trong brain).

Biên đạo (bản 1.0.6). Bản 1.0.5 đầu tiên kéo mọi kết quả về MỘT điểm rồi nở thành vòng cung
tinh cầu xanh trơn; chủ xem xong (2026-10-08) đổi lại: tinh cầu **giữ nguyên chỗ** và phóng to
tại chỗ, bề mặt là **đá lồi lõm** có màu dải ngân hà, nổ **tại chỗ** khi các thiên thể quanh nó lao
vào, nổ **lửa vàng** trước rồi **xanh chưng cất** có tia sáng (hai ảnh mẫu chủ gửi), và **ánh Mặt
Trời** chiếu dần: khớp nhất sáng nhất.

| Thời điểm (giây) | Diễn ra |
|---|---|
| 0 đến 0,3 | Bầu trời tối lại, thiên thể không liên quan mờ đi. |
| 0,3 đến 1,1 | Mỗi kết quả: tối đa 5 thiên thể ĐANG HIỆN gần nó nhất (trong 140px) lao vào theo đường cong, nóng đỏ dần; thiếu thì thêm mảnh đá cho đủ 4. Thiên thể đã lao vào bị ẩn khỏi trời nền tới khi thu về. |
| 1,1 đến 1,7 | **Nổ lửa** tại chỗ: lõi trắng, vàng, cam, mép đỏ sẫm, 7 cụm lửa cuộn, 26 tia lửa văng. Chế độ hoà màu `lighter`. |
| 1,6 đến 2,6 | **Nổ xanh chưng cất**: loé trắng xanh, vành đĩa hồng-xanh nghiêng, **hai tia sáng ngược chiều** như chuẩn tinh, sóng xung kích xanh. |
| 1,6 đến 2,7 | Tinh cầu **đá** lớn dần tại chỗ (bán kính 7 đến 24px theo hạng, `easeBack`). Hạng sau trễ 0,035 giây/hạng. |
| 2,0 đến 3,6 | **Nắng chiếu dần**: phía hướng Mặt Trời sáng ấm, phía kia chìm vào đêm; hạng 1 sáng 100%, hạng sau giảm dần (sàn 35%). Một tia nắng từ Mặt Trời tới tinh cầu hạng 1. |
| Sau đó | Đứng chờ chọn. Nhãn chữ cho 3 hạng đầu và cái đang trỏ. Vệt nối tài liệu `[[liên kết]]` nhau. Hạng 13 trở đi là chấm lấp lánh tại chỗ thật, kèm dòng "và N tài liệu nữa". |
| Xoá ô tìm / Esc | Tinh cầu co lại và tan tại chỗ trong 0,8 giây; thiên thể đã lao vào hiện lại. |

Giữ chỗ: vị trí mỗi khung = chỗ THẬT (`knowPos`, trôi theo vành/camera) + độ lệch giãn chỗ tính
một lần lúc bắt đầu (40 vòng đẩy nhau cho đủ khoảng trống `rF + rF + 16`). Chỗ thật rơi vào đĩa
địa cầu (thiên thể sau lưng địa cầu) thì đẩy ra sát mép (`focAvoidEarth`), vì chụp thử thấy vụ nổ
nằm đè lên mặt địa cầu.

Mặt đá: 6 mẫu 96x96 dựng bằng nhiễu giá trị 3D (bảng hoán vị, không dùng `Math.sin`) + 9 miệng
hố (lòng lõm + vành nổi) + nổi khối nướng sẵn + hai mảng màu hồng/xanh của dải ngân hà. Dựng
MỖI KHUNG MỘT MẪU (`foc.toBuild`) trong lúc trời đang tối: đo trong closure khoảng 9ms một mẫu,
dựng cả 6 cùng lúc là khựng một nhịp. Ánh nắng thật phủ lên lúc vẽ bằng gradient theo hướng
Mặt Trời.

Độ khớp: khớp tên file > khớp tiêu đề wiki > khớp nội dung; cùng loại thì tài liệu nhiều liên
kết hơn đứng trước. Máy yếu (`safe`, `reduced`) bỏ va chạm và vụ nổ: tinh cầu lớn lên và được
nắng chiếu ngay.

Kết quả ngoài phần đang vẽ (vượt trần mục 4) vẫn hiện: chỗ của nó lấy từ băm id như một ngôi sao.

---

## 7. Khép vòng với hố đen (giai đoạn 3, code xong 1.0.6)

- Nạp xong (`ing.beam`), tia sáng bắn từ hố đen về **ghim H2O Studio · ThuyH2O Makeup**
  (`JoyceVNGeo.studio`, Đại Bản, An Dương, Hải Phòng) khi ghim ở nửa thấy được (`studioPt`);
  khuất thì về mép hành tinh gần hố đen nhất như trước.
- hud.js thấy `/brain/nap-status` chuyển từ đang nạp sang xong thì 1,2 giây sau nạp lại bầu trời
  với `fresh=1` (bỏ cache 60 giây). `setKnowledge` so với bầu trời trước: id sao chưa từng có là
  tài liệu VỪA CHƯNG CẤT, mang `born`; mỗi sao mới trễ 0,22 giây sau sao trước.
- Sao mới bay từ ghim H2O Studio lên đúng chỗ cố định của nó trong 1,8 giây (kéo vệt xanh bạc
  hà), loé vòng sáng khi tới nơi rồi thành sao thường. Có sao mới mà tia sáng đã tắt thì bắn lại.
- Nạp lại bầu trời giữ góc đang chạy của chấm vành và đá vụn cũ, không giật về góc ban đầu.
- Lần nạp bầu trời ĐẦU TIÊN không coi gì là sao mới.

## 7a. Bấm thiên thể là mở file (1.0.7)

Chủ báo 2026-10-08: bấm một tinh thể hiện tên quy trình nhưng không dẫn tới file. Gốc: trời gộp
của admin có file ở brain phòng khác, mà nút Mở chỉ hiện khi file thuộc brain đang mở, và trình
sửa file luôn đọc theo brain đang mở. Sửa:
- Hai bước (chủ chốt lại ở 1.0.9, vì 1.0.7 mở cả thẻ lẫn khung file cùng lúc): bấm thiên thể
  (cả tinh cầu kết quả Big Bang) chỉ mở THẺ TÓM TẮT; nút **Mở** trên thẻ mới mở khung file lớn
  (`JoyceFileEditor.open(path, {brain})`), kể cả file ở brain phòng khác.
- `file-editor.js` nhận `opts.brain` để mở file của brain khác brain đang mở.
- Tìm đường dẫn gốc brain theo thứ tự: `brains[].path` của `/knowledge/sky` (chỉ brain trong phạm
  vi), ô chọn brain (`data-brain-name`), rồi `/brains`. Máy chủ chưa khởi động lại vẫn mở được.

## 7b. Hố đen luôn xoay và nhìn sâu vào hố đen (1.0.6)

Chủ yêu cầu 2026-10-08, kèm ảnh mẫu (xoáy bụi xanh có luồng bụi bị hút; đĩa bồi tụ trong xanh
ngoài hồng cam với hai tia phản lực).

**Luôn xoay** (`drawBHSwirl`, vẽ trước thiên thể): 260/150/70 hạt bụi trong ĐÚNG mặt phẳng đĩa bồi
tụ của shader (nghiêng 0,32 rad, dẹt 0,3), góc tốc `0,42 / r^1,2` (trong nhanh, ngoài chậm), trôi
vào tâm 0,05 bán kính/giây rồi sinh lại ở rìa. 90/50/24 hạt chảy theo một luồng cong từ trên-trái
xa vào rìa đĩa, tới nơi thì kéo một hạt xoáy về rìa. Ba cung sáng quanh miệng hố xoay chậm để
mắt thấy rõ hố đang quay. Hạt nửa xa rơi vào bóng hố thì bỏ (lớp 2D nằm trên shader). Đang nạp
dữ liệu: nhanh gấp 3,5, trôi vào nhanh hơn, sáng hơn.

**Nhìn sâu** (`openBlackHole`, `drawBHView`, vẽ trên cùng): bấm trong 1,8 bán kính hố đen. Màn
mở tròn từ hố đen ra cả khung. Trong đó:
- Hố đen lớn (bán kính 0,1 cạnh ngắn), vành photon, đĩa bồi tụ 700/400/160 vệt (trong trắng xanh,
  ra ngoài hồng rồi cam), nửa gần đè lên bóng hố, nửa xa bị che. Hai tia phản lực tím xanh vuông
  góc với đĩa. Dải tinh vân xanh bị hút vào từ góc trên-trái.
- 26/20/12 tinh thể dữ liệu thô mang đúng tên file trong `sources/`, `inbox/` (đang nạp thì ưu
  tiên tên file đang nạp) xoáy dần vào, sàn 0,36 để không lọt vào bóng hố. Cứ 1,4-2,2 giây (nhanh
  hơn khi đang nạp) hai tinh thể trong cùng lao vào nhau trong 0,45 giây rồi **nổ lửa** (0,6 giây),
  **nổ xanh** (1 giây), rồi một **tia kiến thức** đã chưng cất bay vào tâm và vọt theo tia phản lực.
  Tinh thể mới thay chỗ ở vòng ngoài.
- Chữ: tiêu đề, số tài liệu thô đang chờ (hoặc tên file đang chưng cất), lối ra. Nhãn tên tinh
  thể thưa (vòng ngoài, tối đa 6, cách nhau đủ xa).
- Ra: bấm bất kỳ đâu, hoặc Esc. Đang mở thì lăn chuột không phóng quả cầu, rê chuột không hiện
  chú thích.

Lỗi bắt được khi chụp thử bằng Chrome chạy ngầm (2026-10-08), ghi lại để khỏi lặp:
- Gradient vành photon bắt đầu từ 0,95 bán kính thì canvas tô màu điểm dừng đầu cho cả phần
  bên trong: lòng hố thành đĩa màu be. Phải bắt đầu từ tâm và trong suốt tới mép bóng.
- Nửa gần của đĩa là nửa PHÍA DƯỚI trên màn (sin > 0 khi y hướng xuống); lấy ngược thì nửa xa
  vẽ đè lên hố.

## 8. Kiến trúc và API

### 8.1 Máy chủ (`server/knowledge_sky.py`, mount qua `register(app, deps)`)

```
GET /knowledge/sky?brain=<gốc brain>
 -> {ok, scope: "all"|"brain", brains: [{key, name, brand, color}],
     bodies: [{id, kind, ring, brain, path, title, size, recent}],
     counts: {star, orbit, debris, total}}
GET /knowledge/quick?brain=<gốc>&src=<key brain>&path=<đường dẫn trong brain>
 -> {ok, title, kind, brain_name, path, updated, bullets: [...], text_file: bool}
GET /knowledge/search?brain=<gốc>&q=<từ khoá>
 -> {ok, q, scope, total, hits: [{...thiên thể, score, stem, links}]}   (tối đa 60, xếp theo điểm)
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
r.focusKnowledge({q, hits, total} | null);   // giai đoạn 2: Big Bang + chòm sao; null = thu về
r.highlightKnowledge(id | null);             // dòng kết quả ở ô VAULT đang được trỏ
r.knowledgeFocus();                          // trạng thái Big Bang (cho test)
opts.onKnowledgeHover(body | null);          // rê lên thiên thể / tinh cầu nhỏ
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
- Giai đoạn 2: nghe `joyce:vault-search`, hỏi `/knowledge/search`, bỏ kết quả về muộn của từ
  khoá cũ (`_timQ`); nối rê chuột hai chiều với ô VAULT.

---

## 9. Lộ trình

| Giai đoạn | Nội dung | Xong khi |
|---|---|---|
| **1. Bản đồ sao thật** (code xong 1.0.4, 2026-10-08) | Endpoint `/knowledge/sky` + `/knowledge/quick`, vẽ sao, chấm vành, đá vụn từ dữ liệu thật, rê chuột hiện tên, bấm hiện thẻ Đọc nhanh, công tắc trong Cài đặt. | Admin ở Brain Default thấy trời gộp, mở brain phòng thì thấy trời phòng đó; bấm một sao đọc được đầu mục. |
| **2. Big Bang** (code xong 1.0.5, 2026-10-08) | `focusKnowledge`, biên đạo mục 6, đồng bộ hai chiều với ô VAULT. | Gõ "Báo giá" + Enter thấy nổ và chòm sao, bấm chọn được. |
| **3. Khép vòng** (code xong 1.0.6) | Tia sáng về ghim H2O Studio, sao mới sinh sau khi nạp. | Nạp một tài liệu, thấy sao mới bay lên chỗ của nó. |

---

### 9.0 Ghi chú cài đặt giai đoạn 2

- Tìm theo CỤM từ khoá đã gấp (`_khoa_so`: bỏ dấu, chỉ chữ/số): khớp tên/tiêu đề 3 điểm (+0,5
  nếu trọn từ), khớp nội dung 1 điểm + tối đa 1 theo số lần xuất hiện, cộng nửa cỡ thiên thể.
  Nội dung gấp sẵn cache theo mtime: "Báo giá" trên 47 brain mất 1 giây lần đầu, 0,14 giây sau đó.
- Vị trí trên cung: hạng 1 ở đỉnh giữa, các hạng sau toả xen kẽ hai bên. Nhãn chữ chỉ cho 3 hạng
  đầu và tinh cầu đang trỏ, vì 12 nhãn trên một cung 2R chồng lên nhau.
- Đang nổ thì chưa bấm được gì; tinh cầu bấm được khi đã nở quá 60%; đang thu về thì không
  bấm được nữa (test canh cả ba).

### 9.2 Đối chiếu số liệu với đĩa (1.0.8, chủ hỏi 2026-10-08 "có khớp dữ liệu thực tế không")

Đếm lại toàn bộ 1973 file trong 47 brain (bỏ thư mục ẩn):

| Thư mục | File trên đĩa | Thành thiên thể | Vì sao chênh |
|---|---|---|---|
| `wiki/` | 410 | 222 sao (214 quy trình) | 188 = 4 trang quản trị wiki x 47 brain (`index`, `log`, `_open-questions`, `_session-handoff`) |
| `sources/` + `inbox/` | 473 + 4 | 261 đá vụn | **209 file `X.docx.txt` là bản chữ trích từ chính `X.docx`**: trước 1.0.8 đếm đôi thành 477. Giờ gộp làm một (máy chủ `_la_ban_chu` + trình duyệt `gopBanChu`), Đọc nhanh của `.docx` lấy chữ từ bản `.txt` đó |
| `skills/` | 297 SKILL.md | 15 kỹ năng | 282 = 6 skill hệ thống x 47 brain |
| `memory/` | 70 | 14 trí nhớ | chỉ `facts/`; `MEMORY.md` (chỉ mục) và `conversations/` (nhật ký thô) không phải kiến thức |
| `workflows/` | 0 | 0 | chưa brain nào có |
| `Joyce/`, `agents/`, `00 - Dashboard`, `CLAUDE.md`, `AGENTS.md` | 157 + 45 + 47 + 94 | 0 | file hệ thống / vai trò, không phải tài liệu kiến thức |

Tổng 512 tài liệu: H2O Studio 304, ThuyH2O 190, Brain chủ 18. Khối **KHO TRI THỨC** trong khung
TÍN HIỆU GẦN (hud.js `khoTriThucHtml`) hiện đúng các số này, chia theo đúng loại thiên thể.

Trên màn thấy ít hơn tổng là đúng: sao rải trên vỏ cầu quanh địa cầu nên một phần nằm sau lưng
địa cầu (bị che) hoặc ngoài khung, đá vụn quanh hố đen ở góc trên-phải tràn một phần ra mép
trên. Trần vẽ (1500/600/600) lớn hơn số thật nên không thiên thể nào bị cắt.

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
