# Quả tinh cầu H2O: thiết kế chi tiết và hướng dẫn code

Ghi chú 1.0.2: dự án đã tách thành H2O Joyce OS (E:\CLAUDECODE\H2O-JOYCE-OS); các số phiên bản 0.65.x bên dưới là lịch sử trước khi tách.

Tài liệu này ghi lại TOÀN BỘ cách quả tinh cầu ở màn Joyce (lớp "Lõi nước") được dựng ra: kiến
trúc, toán, shader từng tầng, lớp vẽ 2D, tương tác, hiệu năng, và tab chỉnh giao diện mới (Cài
đặt -> Giao diện Joyce -> Quả tinh cầu, bản 0.65.38). Mục đích: đọc xong là code lại được từ đầu,
hoặc biết chính xác sửa dòng nào để đổi một chi tiết.

Mã nguồn là sự thật cuối cùng. Tên hàm và tên biến trong tài liệu khớp với mã tại thời điểm viết
(2026-10-07); số dòng không ghi vì nó trôi.

---

## 1. Bản đồ file

| File | Vai trò |
|---|---|
| `dashboard/brain-planet.js` | Toàn bộ renderer: shader WebGL2, lớp 2D, thiên văn, tương tác, hồ sơ chất lượng, bộ tham số giao diện. Lộ ra `window.JoycePlanet`. |
| `dashboard/vn-geo.js` | Dữ liệu bản đồ Việt Nam nhúng sẵn (`window.JoyceVNGeo`): đường bờ, đảo, Hoàng Sa, Trường Sa, 15 đô thị, ghim H2O Studio, khung bao. Sinh một lần, không sửa tay. |
| `dashboard/hud.js` | "Người nuôi" tinh cầu: dựng khoang HUD, đọc trạng thái THẬT của Joyce và đẩy vào renderer, panel telemetry hai bên, ngăn kéo dự án, khung hologram khi gọi, thời tiết kinh doanh, trạng thái nạp dữ liệu, hoà giao diện tinh cầu từ máy chủ. |
| `dashboard/brain-v2.js` | Công tắc "Lõi nước / Tinh vân" phía trên khoang não (gọi `window.JoyceHud`). |
| `dashboard/style.css` | `#planetStage` phủ kín khoang, vị trí canvas, tooltip, khung hologram, ngăn kéo. |
| `dashboard/console.js` | Trang Cài đặt -> tab `appearance` -> tab con Quả tinh cầu (`renderAppearancePage`, `renderPlanetLook`). |
| `dashboard/console.css` | Kiểu của tab Giao diện Joyce (lớp `.look-*`). |
| `server/main.py` | `_PLANET_*` + `_loc_tinh_cau`: lọc từng khoá khi lưu `settings.dashboard.planet`. |
| `tests/js/test_tinh_cau_alien.js` | Interface renderer, trạng thái thật, an toàn, hiệu năng, mặt trời/mặt trăng, hologram. |
| `tests/js/test_planet_astro.js` | Thiên văn giờ thật bằng mốc đã biết (trưa VN, xuân phân, hạ chí, trăng tròn). |
| `tests/js/test_tinh_cau_tuy_bien.js` | Bộ tham số giao diện, shader + uniform mới, tab Cài đặt. |
| `tests/js/test_tinh_cau_cham.js` | Cảm ứng: chụm/mở hai ngón zoom, kéo hai ngón xoay, chạm đúp, touchpad, Safari. |
| `tests/js/test_gio_nui_lua_voi_rong.js` | Gió chỉ quanh/giữa mây, núi lửa + sông dung nham, vòi rồng thấp + 5 màu + sét theo màu. |
| `tests/js/test_song_dung_nham.js` | Sông dung nham: tốc độ chảy, thanh tốc độ, khói bám đường dung nham vừa chảy qua. |
| `tests/js/test_mat_trang.js` | Bề mặt trăng: hình chú Cuội + cây đa, ánh đất ở phần tối, hướng sáng theo pha, tốc độ. |
| `tests/python/test_tinh_cau_tuy_bien.py` | Lưu/đọc lại qua `/settings`, chặn rác, bảng khoá máy chủ khớp renderer. |

Thứ tự nạp trong `index.html`: `vn-geo.js` -> `brain-planet.js` -> `hud.js` (test canh việc
`brain-planet.js` đứng trước `hud.js`). Mỗi lần sửa file, tăng `?v=` của nó trong `index.html` để
trình duyệt bỏ bản cache.

---

## 2. Kiến trúc ba lớp

```
 #planetStage (phủ kín khoang não, position:absolute; inset:0)
 ├─ canvas.planet-gl   WebGL2: MỘT fragment shader vẽ cả vũ trụ + hành tinh (không lưới tam giác)
 ├─ canvas.planet-ov   Canvas 2D phủ lên: vành quỹ đạo, hạt, vệ tinh, mặt trăng, nhãn, hiệu ứng
 └─ div.planet-tip     DOM: tooltip vệ tinh
 (hud.js thêm: hai cột panel, khung hologram, ngăn kéo dự án, nút gọi ẩn cho bàn phím)
```

Vì sao như vậy:

- **Một shader phủ toàn màn** thay cho Three.js + lưới cầu. Mỗi điểm ảnh tự tính giao tia với
  hình cầu (ray-sphere) nên có pháp tuyến thật, ánh sáng thật, thị sai thật cho các lớp bên trong,
  không có răng cưa của lưới tam giác. Không texture ngoài, không thư viện. Three.js chỉ thêm
  ~600KB mà không thêm gì cho mắt.
- **Lớp 2D** cho những thứ cần chữ, cần bấm được, hoặc là đường mảnh (vành quỹ đạo, nhãn, tia
  sét, hạt dung nham). Vẽ 2D rẻ và chính xác từng điểm ảnh.
- **DOM** cho tooltip (chữ sắc, đọc được bằng trình đọc màn hình).

Canvas WebGL vẽ hình tam giác phủ màn duy nhất `(-1,-1), (3,-1), (-1,3)` (to hơn màn hình, cắt
gọn bởi khung nhìn), shader chạy cho mọi điểm ảnh. Đầu ra là màu **premultiplied alpha** để
vũ trụ trong suốt chồng lên nền trang (`premultipliedAlpha: true`).

---

## 3. API của renderer

```js
var r = JoycePlanet.create(opts);   // tạo, chưa vẽ
r.mount(el);                        // gắn 3 lớp vào el, chọn hồ sơ chất lượng, chạy vòng lặp
r.setJoyceState("THINKING");        // 8 trạng thái, xem mục 9
r.setAudioAmplitude(0..1);          // mức âm đã làm trơn (mic hoặc loa)
r.setProjects([{id, name, status, role: "sun"|"moon"|undefined, url, ms, ...}]);
r.setInCall(true|false);            // tinh cầu hạ xuống nhường chỗ khung hologram
r.setWeather("nang"|"nang_nhe"|"nhieu_may"|"mua"|"giong"|"bao"|"loc_xoay");
r.setIngest({active, items:[tên file]});   // hố đen hút tài liệu
r.setQuality("high"|"balanced"|"safe"|"reduced"|null);
r.zoom(z); r.pause(); r.resume(); r.resize(); r.destroy();
r.planetGeom();  r.moonInfo();  r.quality();  r.state();
```

`opts` (tuỳ chọn, đều có giá trị mặc định an toàn):

| opts | Ý nghĩa |
|---|---|
| `insets()` | Hàm trả `{left,right,top,bottom}` px mà hai cột panel đang chiếm, để camera tự co. |
| `onPlanetClick()` | Bấm vào hành tinh (hud.js: gọi Joyce, bấm nút mic). |
| `onSatelliteClick(project)` | Bấm vệ tinh / mặt trời / mặt trăng (hud.js: mở ngăn kéo dự án). |
| `onBackgroundClick()` | Bấm khoảng trống trên vũ trụ (đóng ngăn kéo). |
| `onQuality(p)` | Báo khi tự hạ chất lượng vì FPS thấp. |
| `labels: false` | Không vẽ nhãn (ô xem trước trong Cài đặt). |
| `tips: false` | Không hiện tooltip. |
| `wheel: false` | Lăn chuột không phóng to (để trang Cài đặt cuộn được). |
| `dark: true` | Luôn vẽ kiểu nền tối dù trang đang ở giao diện sáng. |

Hàm cấp module (dùng chung mọi renderer): `JoycePlanet.getLook / setLook / hydrateLook /
normLook / lookInfo`, các bảng `LOOK_DEFAULT, LOOK_NUM, LOOK_BOOL, LOOK_ENUM, PALETTES, SCENES`,
và `moonPhase, moonPhaseKey, MOON_KEYS, astro{...}` (lộ ra cho test).

---

## 4. Hệ toạ độ, camera và bố cục

### 4.1 Ba hệ toạ độ

- **Màn hình (px)**: gốc góc trên-trái, `y` hướng xuống. Shader dùng `gl_FragCoord` (gốc dưới-trái),
  nên mọi toạ độ đưa vào shader đổi `y -> H - y` và nhân `dprGL`.
- **Khung nhìn (view)**: đơn vị = bán kính hành tinh, tâm hành tinh là gốc, `x` sang phải, `y`
  lên trên, `z` hướng về phía người xem. Điểm ảnh `p = (fragCoord - uC) / uR`, trên đĩa thì
  `n = (p.x, p.y, sqrt(1 - |p|²))` chính là pháp tuyến bề mặt.
- **Địa lý (geo)**: gắn chặt với Trái Đất. `y` = trục cực Bắc, `z` = (vĩ 0, kinh 0), `x` = (vĩ 0,
  kinh 90 Đông). `geoVec(lat, lon) = (cos la sin lo, sin la, cos la cos lo)`.

Ma trận `Gm = viewMat(lat, lon)` biến khung nhìn -> địa lý sao cho điểm `(lat, lon)` nằm giữa đĩa,
Bắc hướng lên: `G = Ry(lon) · Rx(-lat)`. Chiều ngược (địa lý -> nhìn) là `toView(G, v) = Gᵀ v`.
Trong shader: `g = uGeo * n` (uGeo = G, nạp cột theo cột), rồi
`latD = degrees(asin(g.y))`, `lonD = degrees(atan(g.x, g.z))`.

### 4.2 Bố cục (`layout()`)

- Bán kính gốc `base = max(46, min(availH*0.27, max(byW, availH*0.17)))` với
  `byW = (availW/2 - 40) / 1.92`: vành quỹ đạo ngoài cùng (1,92R) cộng chỗ cho nhãn phải lọt
  giữa hai cột telemetry; sàn 17% chiều cao để khoang hẹp không ra "hòn bi".
- `R = base * zoom * (1 - 0.22*callK)`; tâm `cy = top + availH*(0.47 + 0.19*callK)`: đang gọi thì
  tinh cầu nhỏ lại và hạ xuống. `par` (thị sai theo chuột) đẩy tâm vài px.
- Góc nhìn địa lý nội suy theo zoom qua ba mốc: `VIEW_HOME (14.5, 108.4)` thấy trọn Việt Nam +
  Hoàng Sa + Trường Sa; `VIEW_VN (15.6, 106.6)` khi zoom 1,4-3,2; `VIEW_NEAR (20.87, 106.6)` Hải
  Phòng khi zoom 4,5-9. Kéo chuột cộng `cam.yaw` (kinh độ) và `cam.pitch` (vĩ độ).
- Mặt Trời: đặt theo HƯỚNG thật của Mặt Trời trong khung nhìn (`Lv = toView(Gm, sunG)`), khoảng
  cách `R*(0.92 + 1.58*smooth(-0.95, 0.05, Lv.z))`: đêm ở Việt Nam thì Mặt Trời lùi ra SAU quả
  cầu (quầng ló quanh mép), ngày thì ra cạnh khung. Bán kính đĩa `base*0.22*sunSize`, không theo
  zoom (Mặt Trời ở rất xa). Kẹp trong khung để không lấn cột panel.
- Hố đen: góc trên-phải `(86%, 15%)`, bán kính `base*(0.085 + 0.08*gal)*(1 + 0.18*ingest)`.
- Ngân Hà rõ dần khi lùi xa: `gal = 1 - smooth(0.42, 1.0, zoom)`.

### 4.3 Bốn tầng zoom

`ZMIN = 0.32`, `ZMAX = 12`, bước lăn 1,087 (sau zoom 2 là 1,14): Ngân Hà (~0,35) -> Hệ Mặt Trời
(~0,6) -> Trái Đất (1) -> cận cảnh Việt Nam (2-3,4) -> Hải Phòng. Vành dữ liệu tan dần từ zoom
1,5-2,3 (`ringFade`), lõi lặn dần 1,8-3,6 (`uCore`) để không che bản đồ.

---

## 5. Thiên văn theo giờ thật

- **Mặt Trời** (`astro`, `sunGeo`): công thức rút gọn của Almanac. `n` = số ngày từ J2000,
  `L = 280.460 + 0.9856474n`, `g = 357.528 + 0.9856003n`,
  `λ = L + 1.915 sin g + 0.020 sin 2g`, độ nghiêng `ε = 23.439 - 0.0000004n`,
  `GMST = 280.46061837 + 360.98564736629n`. Hoàng đạo -> xích đạo -> (RA, Dec) -> điểm ngay dưới
  Mặt Trời `(Dec, RA - GMST)` -> `geoVec`. Sai số < 0,01 độ.
- **Pha trăng** (`moonPhase`): tháng giao hội 29,530588853 ngày, mốc trăng mới
  2000-01-06 18:14 UTC. `phase = tuổi/tháng` (0 = non, 0,5 = tròn), `illum = (1 - cos 2π·phase)/2`.
- **Vị trí Mặt Trăng** (`moonGeo`): kinh độ hoàng đạo = Mặt Trời + 360·phase (góc ly giác suy từ
  pha thật), vĩ hoàng đạo `5.145·sin F`, `F = 93.272 + 13.22935n`. Nhờ vậy vị trí và pha luôn khớp.
- **Quỹ đạo trăng hôm nay** (`moonOrbit`): 72 điểm cách 5 độ, vẽ thành đường mờ.
- Khoảng cách KHÔNG theo tỉ lệ thật (trăng ở 1,9R): giữ đúng HƯỚNG và THỜI GIAN, nén khoảng cách.
- Tính lại vị trí 20 giây/lần (Mặt Trời trôi 0,25 độ/phút), pha trăng 10 phút/lần.

`tests/js/test_planet_astro.js` kiểm bằng mốc thật: trưa VN 06/10 Mặt Trời đứng bóng ~102,1°Đ,
xích vĩ ~ -5°; xuân phân xích vĩ ~0; hạ chí ~ +23,4; trăng tròn đối diện Mặt Trời > 170°.

---

## 6. Shader, từng tầng một

Toàn bộ nằm trong `fragSrc(hi)`. `hi = 1` (hồ sơ high) bật voronoi (mạng nơron + thành phố),
fbm 4 octave, cột magma; `hi = 0` dùng 3 octave và bỏ voronoi. Hai bản biên dịch riêng, bản
high biên dịch lười khi cần.

### 6.0 Công cụ nhiễu

```glsl
float h13(vec3 p)  // băm 3D -> 1 số (Dave Hoskins)
float vn(vec3 x)   // value noise 3D, nội suy smoothstep
float fbm(vec3 p)  // tổng 3-4 octave vn, mỗi octave x2,03 tần số, /2 biên độ
vec3  vor(vec3 x)  // voronoi: (khoảng cách gần nhất, gần nhì, id ô) - chỉ HI
mat3 rY(a), rX(a); vec3 rotAx(v, k, a)   // xoay quanh trục Y, X, trục bất kỳ (Rodrigues)
```

### 6.1 Nền vũ trụ (cộng dồn vào `acc`, độ phủ vào `al`)

1. **Thấu kính hố đen**: lấy mẫu nền ở toạ độ bị đẩy ra xa tâm hố,
   `fcb = fc + bv * (2.2 / (|bv|²/r² + 0.35))`. Ánh sao phía sau bị bẻ cong quanh hố.
2. **Tinh vân**: `n1 = fbm(q*1.7, t*0.006)`, màu pha `OCEAN*.55 -> VIOLET` theo n1, cộng
   `MAGENTA` ở vùng n2 cao; đậm gần hành tinh (`exp(-d*0.42)`).
3. **Ngân Hà**: dải chéo góc -0,46 rad, độ dày `0.13 + 0.05·vn`, `band = exp(-y²/w²)`, lõi phình
   vàng `bulge = exp(-|gr - (.42,.02)|² * 14)`, vệt bụi tối kéo dài (`vn` giãn 5x16). Nhân `uGal`.
4. **Bụi sao lớp hai**: lưới 2,6px, ô nào băm > 0,9965 (dày hơn trong dải Ngân Hà) thì có sao,
   nhấp nháy `0.55 + 0.45 sin(t*(1+h*3) + h*40)`.
5. **Sương chân trời**: dải `NAVY` quanh đường chân trời `uHorizon` làm lưới sàn của trang tan dần.

### 6.2 Mặt Trời

```glsl
disk  = 1 - smoothstep(.95, 1.05, sd);                 // sd = khoảng cách / bán kính đĩa
diskC = mix(trắng ấm, uSunC, rìa) * (.82 + .3*granulation);
rays  = pow(.5+.5*sin(ang*9 + vn(...)*5), 5) * exp(-o1*.85);  // 9 tia uốn lượn
cor   = exp(-o1*2.3)*.95 + exp(-o1*.42)*.2;           // vành nhật hoa 2 tầng
sunC  = diskC*disk*1.7*pow(w,.35) + uSunC*(cor + rays*.32)*(1-disk)*w;
beam  = chùm sáng hình nón từ Mặt Trời về hành tinh, rộng dần, gợn nhẹ theo thời gian
```

`w = uSun.w` = cường độ (độ khoẻ H2O Legacy x thanh Cường độ). Đĩa sáng theo `w^0.35` còn quầng
theo `w`: Mặt Trời yếu là quầng tắt mà đĩa vẫn là khối sáng, không ra đĩa xám.

### 6.3 Hố đen + đĩa bồi tụ

- Bóng đen tuyệt đối trong bán kính 1 (che cả nền).
- Đĩa bồi tụ elip nghiêng 0,32 rad, dẹt 0,3: dải `rin = 1.45 .. rout = 4.2`, vân chạy theo góc,
  **Doppler** `dop = .55 + .45 cos(an + .4)` (một bên sáng hơn), nửa sau vẽ trước bóng, nửa trước
  vẽ sau (`fr0 = step(d2.y, 0)`).
- Khi Joyce nạp dữ liệu (`uBH.w`): đĩa sáng lên + **luồng năng lượng xoắn ốc**
  `arm = pow(.5+.5 sin(3·ang + 6·log r + t·4), 7)` màu CYAN->MINT chảy vào tâm.

### 6.4 Khí quyển và vòng trạng thái

`hh = d - 1` (độ cao trên mặt). Khí quyển `exp(-hh*6.5)` sáng hơn về phía nắng, màu
`mix(uPb, uPc, ...)` (bảng màu), viền tím-hồng phía bóng tối. Các vòng trạng thái đều sống ở đây:

| Trạng thái | Hiệu ứng |
|---|---|
| LISTENING | quầng xanh lá-cyan nở theo mức âm |
| SPEAKING | 3 vòng sáng toả ra ngoài theo nhịp |
| CONNECTING | 3 xung chạy ra |
| INTERRUPTING | 3 vòng tím co vào |
| ERROR | loé đỏ ở một vùng mép, nháy |
| RECONNECTING | khí quyển nhạt đi, mảng bề mặt tắt tạm |

### 6.5 Thân hành tinh

```glsl
n = vec3(p, sqrt(1-d²));             // pháp tuyến (khung nhìn)
s = rY(flowT*.05 + yaw) * rX(.38 + pitch) * n;   // toạ độ "vật liệu" xoay theo thời gian
w = (fbm(s*1.6 + t), fbm(...));      // domain warp
oc = fbm(s*2.3 + w*1.3);             // biển xoáy
base = mix(uPa, uPb*.62, oc) -> pha uPc ở đỉnh sóng, x độ sáng bề mặt
cur  = dải hải lưu theo vĩ tuyến: sin(lat*13 + w.x*6.5) cắt ngưỡng .93, màu uPc->uPd
```

**Lớp tinh vân bên trong** (thị sai thật): giao tia nhìn với cầu bán kính 0,8 sau khúc xạ nhẹ
`pr = p*(1 - .14*(1-n.z))`, rồi lấy 4 lớp nhiễu tím, hồng, xanh lá, vàng. Vì bán kính nhỏ hơn
nên khi xoay nó trôi chậm hơn vỏ ngoài: mắt đọc ra chiều sâu.

### 6.6 Lõi Trái Đất (nhìn xuyên nước)

- Nhân ngoài lỏng bán kính `rc = 0.46`, khúc xạ mạnh hơn: `prc = p*(1 - .22*(1-n.z))`, giao tia
  với cầu nhỏ, xoay NGƯỢC chiều vỏ ngoài.
- Dung nham: domain warp 3 kênh `wq`, rồi `vein = pow(1 - |2·fbm - 1|, 9)` (ridged noise = dòng
  chảy mảnh), ô đối lưu `cells`. Màu vỏ nguội `(.32,.06,.01)` -> dung nham `(1,.42,.06)` -> nóng
  trắng `(1,.85,.45)`.
- **Mép sáng** (không viền đen): rìa cầu là chỗ nhìn xuyên lớp magma dày nhất,
  `rimC = pow(1-nc.z, 2.2)` cộng sáng.
- Nhân trong rắn nóng trắng có nhịp đập `(.8 + .2 sin(t*1.7))`.
- Quầng nhiệt toả vào nước `exp(-ou*9)` + **cột magma** (HI) bốc lên từ lõi: nhiễu theo HƯỚNG
  `vn(vec3(dcn*7, ou*7 - t*...))`. Trước 0.65.38 dùng góc `atan` nên có một vệt ngang gãy ở ±π.
- Độ lộ: `vis = (.22 + .28*đêm + .45*hover + .12*nghĩ + .25*phun trào) * uCore * độ rõ`. Lõi
  rõ hơn về đêm, khi rê chuột lên và khi Joyce đang nghĩ (dung nham chảy nhanh hơn).
- Biển phía trên lõi tối bớt theo độ sáng dung nham (`1 - |lavaC|*.35`).

### 6.7 Mạng nơron + thành phố trí tuệ (HI)

Voronoi trên `s*4.6 + w*.35`: cạnh ô (`v.y - v.x < 0.032`) là dây nơron, xung chạy dọc
`pulse = pow(.5+.5 sin(dot(s,(9,7,5)) - t*tốc), 3)`, tốc độ tăng khi nghĩ/nghe. Tâm ô có id > 0,55
là "thành phố" vàng-mint, rõ về đêm.

### 6.8 Ngày, đêm, ánh trăng

`day = smoothstep(-.25, .45, dot(n, L))`, `lit = .25 + .75*sức nắng`. Đường ranh ngày/đêm có
dải nắng vàng `exp(-(ndl*5)²)`. Ánh trăng: `mlt = max(dot(n, uMoonV), 0) * (1-day) * uLk.w`
(độ sáng trăng x phần trăng sáng) phủ ánh bạc lên mặt đêm và mây.

### 6.9 Mây và thời tiết

```glsl
gw = xoắn quanh điểm chân lốc (nếu có lốc)
cq = rY(windPhase*.004) * gw           // mây trôi quanh trục cực; pha gió tích luỹ bên JS
cd = fbm(cq*3.1 + drift)
wv = exp(-góc(g, tâm VN)² / .045)       // trọng số vùng Việt Nam
cov = mây nền + thời tiết kinh doanh*wv*.85 + bão*.95 + lốc*.9
cm = smoothstep(lo, lo+.16, cd), lo = .66 - .42*min(cov, 1.2)
```

- **Bão** (`bao`, `loc_xoay`): cánh mây xoắn ốc vẽ theo toạ độ cực quanh tâm,
  `arm = .5+.5 sin(2θ + 5.5 log(r+.06) - t*1.1)`, mắt bão trống ở giữa.
- **Độ u tối** `dk` = mưa/sét theo thời tiết + thanh "Độ u tối" + lốc, kẹp 0,88. Màu mây
  `mix(trắng xanh, xám chì, dk)`, sáng theo ngày x sức nắng, viền nắng ở đường ranh.
- **Mưa** (shader): vệt rơi trong mây `h13(floor(x/2.5), floor((y + t*520)/11)) > .975`.
- **Chớp**: `uFlash` (thời tiết kinh doanh, chớp đôi ngẫu nhiên) sáng mây vùng VN; `uBolt` (tab
  tùy biến) sáng đúng quanh điểm tia sét đánh xuống.

Bảng thời tiết kinh doanh `WX = { key: [mây, mưa, sét, xoáy] }`: nang `[.06,0,0,0]` ... bao
`[.95,1,.8,1]`, loc_xoay `[.8,.7,1,1]` (tâm xoáy đặt ngay H2O Studio, sigma 0,07).

### 6.10 Việt Nam hologram

`buildVNTexture()` vẽ bản đồ vào 4 canvas 1024², gộp thành MỘT texture RGBA:
R = nền đất liền, G = viền phát sáng (stroke có shadowBlur), B = đèn đô thị (gradient tròn theo
cỡ đô thị), A = Hoàng Sa + Trường Sa (chấm + vành nét đứt ôm quanh quần đảo). Shader tra theo
kinh/vĩ trong khung bao `bbox = [101.5, 6.5, 117.5, 24]`:

```glsl
holo = (CYAN*(G*2.1 + R*.3*scan) + MINT*A*1.8) * flicker * limb;
holo += GOLD*B*(đêm)*1.4;   // đèn đô thị chỉ sáng về đêm
scan = .7 + .3 sin(lat*26 - t*2.4)   // vạch quét chạy dọc
```

Lớp 2D thêm nhãn "VIỆT NAM", "Hoàng Sa (Việt Nam)", "Trường Sa (Việt Nam)" khi R > 800px, và ghim
H2O Studio (Đại Bản, An Dương, Hải Phòng) nhịp vàng + thẻ tên khi R > 420px.

### 6.11 Hoàn thiện

- Tối mép `col *= .6 + .4 n.z`; phản xạ nắng (specular hai thùy 70 và 11) trên pháp tuyến gợn
  sóng; **fresnel** `pow(1-n.z, 3)` màu viền sáng `uPc` + tím-hồng phía bóng.
- Lỗi: một vùng đỏ nháy vạch ngang; nối lại: mảng tắt tạm.
- Ánh xạ tông `1 - exp(-col*1.3)`, rồi cả khung `1 - exp(-acc*1.15)`; xuất premultiplied.

---

## 7. Lớp 2D (`frame()` vẽ theo thứ tự này)

1. (bản safe) `drawSafePlanet`: hành tinh bằng gradient + cung tròn, KHÔNG fillRect cả canvas.
2. `drawMoonPath`: quỹ đạo trăng hôm nay, đoạn sau hành tinh bị bỏ.
3. Nửa SAU: `drawRings(false)`, `drawParticles(false)`, `drawSatDots(false)`, `drawMoon(false)`.
4. `drawLookFx`: hiệu ứng của tab tùy biến (gió, mưa, núi lửa, hạt nóng, lốc, sét).
5. Nửa TRƯỚC: `drawRings(true)`, hạt, vệ tinh, `drawMoon(true)`.
6. `drawGlyphs`: ký hiệu tín hiệu ("0x1F", "λ", "∑"...) nháy kiểu vô tuyến trên vành.
7. `drawVN`, `drawIngest` (hạt tài liệu xoắn vào hố đen + tia sáng về Trái Đất khi nạp xong),
   `drawLabels`.

Những điểm đáng chú ý:

- **Vành quỹ đạo 3D** (`ringPt`): 3 vành bán kính 1,42 / 1,66 / 1,92R, nghiêng 1,20 / 1,07 /
  1,31 rad, lăn -0,20 / 0,17 / -0,06. Điểm góc `a` -> xoay nghiêng -> lăn -> xoay camera -> chiếu
  trực giao. Đoạn có `z < 0` và nằm trong đĩa là bị hành tinh che (`hidden`). Mỗi đoạn vẽ hai nét:
  quầng rộng mờ + lõi mảnh.
- **Mặt trăng thật, có chú Cuội** (0.65.40, `moonSurface` ở cấp module + `drawMoonDisc`):
  - Bản đồ 200² dựng MỘT lần bằng toán (không canvas, test được): biển tối (`MARIA`) là hợp các
    hình tròn/elip/nét có mép mềm, xếp thành **tán cây đa, thân, rễ toả, rễ phụ và chú Cuội ngồi
    co gối dựa gốc cây**, cộng các biển giữ dáng trăng thật (Nguy Hiểm, Phì Nhiêu...). Toạ độ được
    uốn méo bằng nhiễu trước khi tra hình nên mép lượn tự nhiên; tán có kẽ lá (`holes`).
  - Độ phản xạ: cao nguyên ~0,66, biển tối ~0,3. 48 hố (biển tối ít hố hơn) có lòng lõm + vành
    nổi trong bản đồ độ cao; hố Tycho/Copernicus/Kepler có tia sáng toả mờ. Độ dốc (GX, GY) suy
    ra từ bản đồ độ cao, dùng làm pháp tuyến lồi lõm.
  - Chiếu sáng (`moonPixels`): phản xạ **Lommel-Seeliger** `2μ0/(μ0+μ)` (trăng tròn sáng đều
    tới mép như ngoài đời); hướng nắng = `(sin 2πp, 0, -cos 2πp)` xoay theo góc màn hình `rot`;
    ranh ngày đêm mềm. **Phần tối = ánh đất** (Trái Đất hắt sáng), mạnh nhất lúc trăng non, cộng
    độ nổi khối riêng của vành/lòng hố, nên phần tối vẫn đọc ra bề mặt và hình chú Cuội.
  - Trăng luôn **đứng thẳng** (khoá thuỷ triều); chỉ phần sáng xoay theo nắng.
  - Hiệu năng: dựng bản đồ ~110-170ms lúc trình duyệt RẢNH (`requestIdleCallback`), chưa xong thì
    vẽ đĩa phẳng kiểu cũ; ảnh đã chiếu sáng giữ trong bộ đệm theo (cỡ bậc 16px, pha, góc bậc
    1/40 rad, độ sáng, màu), tối đa 320px rồi phóng bằng `drawImage`.
  - Trăng sau hành tinh: khoét đĩa hành tinh khỏi vùng vẽ (`arc(..., true); clip()`).
- **Nhãn chống chồng** (`drawLabels`): Mặt Trời + Mặt Trăng xếp trước, thử lần lượt 4 phía
  (bên cũ, phải, trái, trên, dưới), kẹp trong khung, nhớ phía đã chọn để nhãn không nhảy.
  Biểu tượng mặt trời/trăng vẽ bằng canvas (repo cấm emoji).

---

## 8. Hiệu ứng của tab tùy biến (lớp 2D + shader)

Mọi điểm neo trên bề mặt lưu bằng toạ độ **địa lý** rồi chiếu qua `Gm` mỗi khung, nên kéo xoay
quả cầu thì mưa, lốc, núi lửa đi theo đúng chỗ. Cường độ từng hiệu ứng `fx.*` trôi mềm 0..1 về
công tắc (`fk = dt*1.6`): bật/tắt không giật.

| Hiệu ứng | Lớp 2D | Shader |
|---|---|---|
| Mưa (0.65.41) | **Ô bão**: 2-4 vùng cách nhau >= 0,5 rad trên nửa cầu đang thấy, bán kính 0,12-0,2 rad, trôi về Đông (gió mạnh nhanh x4), lớn lên 4 giây - đứng 12-50 giây - tan 4 giây rồi sinh lại chỗ khác. Mỗi ô: đế mây sẫm + 12-18 cụm mây vồng (elip mờ) nổi cao `cloudLift` = 0,12R; màn mưa 3 dải; 36-110 hạt rơi từ đáy mây xuống đúng điểm đất, toé khi chạm. Ngoài ô KHÔNG mưa | `uRc[4]`/`uRs`: mây trong ô dày (+1,1 độ phủ) + đen (+0,72), vệt mưa chỉ trong ô (`uCl.w*rcW`) |
| Sấm sét | Chỉ sinh TRONG ô bão: 70% tia đánh xuống từ đáy mây, 30% chớp trong mây (khối mây loé). Tia gấp khúc 5 tầng + 2-4 nhánh rẽ rộng, 4-6 tia bò lan trên mặt đất, 3 nét **vàng trắng** (quầng vàng cam, thân vàng nhạt, lõi trắng); toé tia lửa | `uBolt`: chớp sáng mây + mặt đất quanh điểm đánh |
| Gió mạnh (0.65.44) | 8-26 luồng gió ở độ cao mây, CHỈ quanh các đám mây: 65% chạy theo cung tròn lớn từ đám A sang đám B (vồng lên giữa đường, lệch làn tối đa 0,55 bán kính đám), 35% cuộn quanh một đám. Bật riêng gió vẫn có các đám mây (trắng xám, `cloudLevel`); mưa/sét mới làm mây đen (`stormLevel`, `uCo.w`) | pha gió `windT += dt*(1 + 7*gió)`: mây trôi nhanh gấp 8 mà không nhảy cóc |
| Vòi rồng (0.65.41, sửa 0.65.44) | Cao CHỈ từ mặt đất tới đáy khối mây giông mẹ phủ đỉnh (`Ht = clamp(0,2R, 26, 140) x (0,6..1,15)`, tối đa ~0,23R). 5 màu (`tornadoColor`): concept / xanh số / lửa / xám bão / đen tối; xám và tối không phát sáng, nhiều bụi, thân đặc, sét quấn vòi 0,14-0,65 giây/lần và đánh xuống đất quanh chân vòi. Theo ảnh mẫu chủ gửi: 150-520 **hạt sáng** xoắn quanh trục cong (uốn lượn theo thời gian), bán kính `rBot + (rTop-rBot)·f^1,6` (loe ở đỉnh, nhỏ dần xuống chân), hạt bốc lên và loe thành vòng ở đỉnh; vệt cung xoắn + chấm sáng (sprite theo màu concept: Đại dương = xanh số, Dung nham = lửa), bụi đen + mảnh vụn quay lộn; lõi thân tối mờ; mây xoáy trên đỉnh; 3 cánh gió xoắn ốc ở chân + cung gió quanh thân; sét vàng trắng quấn quanh vòi 0,5-1,8 giây/lần. Chạy KHÔNG ngừng: hướng lượn theo nhiễu, ra gần mép thì lái về giữa đĩa, tốc 0,045-0,09 rad/s; to nhỏ (`sz` 0,6-1,35) và cao thấp (`hk` 0,5-1,2) theo nhiễu chậm | `uTor`: vặn trường mây thành xoắn ốc chặt quanh chân vòi |
| Phun trào (0.65.44) | MỘT núi lửa ở Krakatoa (-6,1; 105,4): ống magma từ mép lõi lên chân núi (cục magma dâng chậm), núi hình nón gồ ghề, 4 dòng dung nham chảy xuống sườn, miệng rực, giọt sủi nhẹ (cao tối đa ~0,27 núi), khói trôi theo gió. Sông: 3 dòng chính + nhánh rẽ, bước 0,028 rad, dài tới ~4 rad, lượn nhẹ; hiện dần ~14 bước/giây; to + rực gần núi, nhỏ + nguội đỏ sẫm ở xa (`lavaStyle`); nét đứt chạy dọc = đang chảy | `uCo.z`: lõi chảy nhanh, cột magma to + vươn xa (bỏ khe nứt rải khắp vỏ) |
| Sông dung nham (1.0.2) | Đầu dòng `volc.front` tiến LAVA_RATE 1,6 bước/giây x `lavaSpeed` (0,2-3; mặc định ~1,5 phút một dòng). Lớp bán trong suốt (đất cháy 2,7x, quầng nóng 1,8x, vỏ nguội đứt quãng, vệt sáng) vẽ MỘT nét liền mỗi dòng để chỗ nối không lộ chuỗi hạt; lớp đặc (thân, lõi) vẽ từng đoạn 3 bước: bề rộng `2 x 0,024 rad x R` lan dần trong 14 bước sau đầu dòng, đầu dòng rực vàng trắng. `drawLavaSmoke`: khói đen ở đầu dòng 9/giây + khói âm ỉ dọc 40 bước phía sau 10/giây (theo tốc độ), bốc lên và trôi theo gió, 5 ngọn lửa ở đầu dòng, đốm than; trần 420/240/90 hạt theo hồ sơ máy | - |

**Hạt nóng** (`launch`, `drawHot`): dung nham và tia lửa bay trong toạ độ địa lý, trọng lực
`1/r²` hút về tâm (dung nham g = 1,4, tia lửa 1,7), tốc phóng 0,7-1,05R/giây nên vòm cao
0,2-0,65R. Rơi lại mặt đất (`r < 1` và đang đi vào) là tắt. Màu nguội dần trắng vàng -> cam ->
đỏ sẫm, vẽ hai nét (quầng rộng + lõi) chế độ `lighter`. Trần số hạt 520 / 300 / 160 theo hồ sơ.

Trục cột lốc nghiêng thêm về phía trên khung: giữa đĩa pháp tuyến chĩa thẳng vào mắt người xem,
không nghiêng thì cột "cao" chỉ còn là một chấm.

---

## 9. Trạng thái Joyce

Nguồn duy nhất là runtime thật (`hud.js joyceState()`): lớp CSS của `#orbState` do `capNhatOrb()`
ghi từ đạo diễn giọng nói, cờ `in-call` của nút mic, và `__joyceCallState` cho "connecting". Không
có setTimeout giả lập nào. Mỗi trạng thái là một bộ mục tiêu, giá trị thật nội suy mềm về đó
(`k = dt*3.2`), nên đổi nhanh từ nói sang nghe không giật màu:

| Trạng thái | flow | energy | listen | speak | conn | recon | err | intr | quỹ đạo | hạt |
|---|---|---|---|---|---|---|---|---|---|---|
| READY | 1.0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1.0 | 1.0 |
| CONNECTING | 1.3 | .1 | 0 | 0 | 1 | 0 | 0 | 0 | 1.3 | 1.6 |
| LISTENING | 1.2 | .05 | 1 | 0 | 0 | 0 | 0 | 0 | .9 | 1.0 |
| THINKING | 2.8 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1.6 | 2.6 |
| SPEAKING | 1.5 | .2 | 0 | 1 | 0 | 0 | 0 | 0 | 1.1 | 1.4 |
| INTERRUPTING | .4 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | .25 | .3 |
| RECONNECTING | .7 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | .6 | .6 |
| ERROR | .5 | 0 | 0 | 0 | 0 | .2 | 1 | 0 | .5 | .4 |

`flow` nhân vào `flowT` (tốc độ trôi của biển + mạng nơron); `energy` = tinh vân trong sáng lên,
lõi chảy nhanh, xung nơron; v.v. Đang gọi (`setInCall`) thì `callK -> 1`: tinh cầu thu 22% và hạ
xuống, khung hologram của hud.js (ảnh Joyce hoặc ảnh nhân viên) dựng lên phía trên.

**Thiên thể**: H2O Legacy là Mặt Trời (app lỗi thì Mặt Trời lịm, ngả đỏ: offline 0,4, thiếu quyền
0,6, chậm 0,78). Mặt Trăng là một dự án: chủ ghim trong ngăn kéo, không ghim thì mỗi tuần trăng
mới tự chuyển sang dự án kế tiếp. Các app còn lại là vệ tinh hình thoi trên ba vành.

---

## 10. Tương tác

- Rê chuột: thị sai nhẹ, tooltip vệ tinh, hành tinh sáng viền + lõi lộ rõ (`uHover`).
- Bấm hành tinh: chờ 260ms để phân biệt bấm đúp, rồi gọi Joyce. Bấm đúp: về góc nhìn ban đầu.
- Bấm vệ tinh / Mặt Trời / Mặt Trăng: mở ngăn kéo dự án (không mở app ngay). Bấm khoảng trống:
  đóng ngăn kéo. Phím H: Chế độ Quan sát (ẩn mọi khung).
- Kéo: xoay (yaw ±2,8, pitch ±1,1), chậm lại khi phóng gần. Lăn: zoom 4 tầng.
- **Cảm ứng (0.65.39)**: mỗi ngón là một con trỏ trong `pts`. Hai ngón = chụm: zoom = zoom lúc
  bắt đầu x (khoảng cách hiện tại / khoảng cách đầu), kẹp 0,32-12; điểm giữa hai ngón dời thì
  xoay. Đã chụm thì nhấc ngón không tính là bấm; còn một ngón thì kéo tiếp từ ngón đó. Chạm đúp
  (< 320ms, < 36px) về góc nhìn đầu, vì điện thoại không chắc bắn `dblclick`. `pointercancel`
  dọn cử chỉ; ngón đầu của cử chỉ mới (`isPrimary`) xoá con trỏ sót. Chụm touchpad (wheel +
  `ctrlKey`) zoom theo `exp(-deltaY*0,01)`. Safari iOS: chặn `gesturestart/gesturechange` để
  không phóng cả trang. `R.camera()` trả đích zoom/xoay cho test.
- Nút DOM `#planetCallBtn` (ẩn tới khi focus bằng phím): canvas không phải lối duy nhất để gọi.

---

## 11. Hiệu năng và độ bền

| Hồ sơ | Khi nào | Khác biệt |
|---|---|---|
| high | máy >= 4GB RAM và >= 4 nhân | shader HI, DPR tối đa 2, trần 2,6 triệu điểm ảnh |
| balanced | máy yếu, hoặc tự hạ | shader thường, DPR 1,25, trần 1,4 triệu |
| safe | không WebGL2 / mất context / cờ tắt | Canvas 2D thuần (`drawSafePlanet`) |
| reduced | `prefers-reduced-motion` | gần tĩnh, ~8 khung/giây, chỉ đổi màu trạng thái |

- FPS trung bình < 30 trong 2 cửa sổ 90 khung liên tiếp -> hạ một bậc (high -> balanced -> safe).
- `webglcontextlost` -> `preventDefault`, về safe; `restored` -> chọn lại hồ sơ.
- Ẩn tab (`visibilitychange`) dừng vẽ; `pause()` khi rời lớp Lõi nước.
- `destroy()`: huỷ RAF, gỡ mọi listener, ngắt ResizeObserver, thả context (`WEBGL_lose_context`).
- Cờ `joyce_alien_intelligence_planet_v1 = "0"` (localStorage hoặc `?...=0` trên URL) ép bản safe.

---

## 12. Tab Giao diện Joyce -> Quả tinh cầu

### 12.1 Luồng dữ liệu

```
 Cài đặt (console.js)                 brain-planet.js                     máy chủ
 kéo thanh trượt ──> JoycePlanet.setLook(patch) ──> look (module) ──> mọi renderer đọc mỗi khung
                         │ ghi localStorage "joyce.planetLook"
                         └ bắn sự kiện "joyce:planet-look"
 hẹn 0,7s ──> POST /settings section=dashboard {planet: look} ──> _loc_tinh_cau lọc từng khoá
         └──> GET /settings đọc lại, so khớp ──> "Đã lưu cho mọi máy" hoặc cảnh báo
 hud.js lúc khởi động: GET /settings ──> JoycePlanet.hydrateLook(dashboard.planet)
```

**Khung xem trước kéo giãn (0.65.42)**: trang dùng hết bề ngang, ba cột (cột chỉnh | vạch kéo |
khung). Kéo vạch dọc đặt `--look-ctl` (cột chỉnh 340px trở lên, khung 300px trở lên), mép dưới đặt
`--look-h` (220px tới cao màn trừ 120px; điện thoại tối đa 60% chiều cao), bấm đúp vạch hoặc nút
góc khung = phóng tối đa / trả về, bàn phím: mũi tên (Shift = bước lớn), Enter. Cỡ nhớ ở
localStorage `joyce.lookPreviewSize` (theo máy). Renderer tự vẽ lại theo cỡ mới (ResizeObserver).

Tinh cầu ở màn Joyce và ô xem trước trong Cài đặt là HAI renderer đọc CÙNG một bộ tham số, nên
kéo một thanh là cả hai đổi. Máy chủ là nguồn sự thật cho mọi máy (nhân viên cũng đọc được
`GET /settings`); localStorage chỉ để mở trang là có ngay. Ô xem trước được dọn qua `_pageLeave`
khi rời trang, và tự huỷ khi rời DOM (lối dọn thứ hai cho đường vẽ lại không qua `navigateTo`).

### 12.2 Bảng tham số

| Khoá | Khoảng | Mặc định | Tác động |
|---|---|---|---|
| `sunPower` | 0,1-2 | 1 | `uSun.w` (đĩa, quầng, chùm sáng) + `uLk.x` sức nắng lên mặt ngày |
| `sunSize` | 0,6-1,8 | 1 | bán kính đĩa Mặt Trời |
| `sunColor` | #rrggbb | #ffd46b | `uSunC`; sự cố Legacy vẫn đè 70% màu báo lỗi |
| `moonMode` | auto / manual | auto | theo lịch thật hay tự chỉnh |
| `moonFull` | 0-1 | 1 | phần trăng sáng khi tự chỉnh -> pha `acos(1 - 2f)/2π` |
| `moonGlow` | 0-2 | 1 | quầng + độ sáng đĩa trăng, ánh trăng lên mặt đêm |
| `moonSize` | 0,6-1,8 | 1 | cỡ đĩa trăng (cả vùng bấm và chỗ đặt nhãn) |
| `palette` | ocean, emerald, amethyst, sunset, ice, lava, gold, abyss, custom | ocean | `uPa..uPd` |
| `seaColor`, `rimColor` | #rrggbb | #064cff, #00e7ff | concept tự chọn |
| `surface` | 0,4-1,8 | 1 | độ sáng biển (`uLk.z`) |
| `atmo` | 0-2 | 1 | khí quyển + fresnel (`uLk.y`) |
| `clouds` | 0-1 | 0,3 | mây nền `uCl.x = clouds*0.55` (0,3 -> 0,165 ~ hằng 0,16 cũ) |
| `cloudDark` | 0-1 | 0 | độ u tối mây (`uCl.y`) |
| `rain`, `lightning`, `wind`, `tornado`, `eruption` | bật/tắt | tắt | mục 8 |
| `coreVis` | 0-2 | 1 | độ lộ của lõi qua nước |
| `coreGlow` | 0-2 | 1 | độ phát sáng dung nham + tầm quầng nhiệt |
| `orbits` | bật/tắt | bật | vành + hạt + ký hiệu (vệ tinh dự án vẫn ở lại vì là dữ liệu) |

Mặc định tái tạo đúng giao diện trước khi có tab (test canh: bảng `ocean` = hằng
`OCEAN/CYAN/MINT` của shader, mây nền ~0,16).

### 12.3 Thêm một tham số mới (checklist)

1. `brain-planet.js`: thêm khoá vào `LOOK_NUM` / `LOOK_COLOR` / `LOOK_BOOL` / `LOOK_ENUM`.
2. Dùng nó: trong JS (`look.x`) hoặc thêm uniform (khai trong `fragSrc`, thêm tên vào danh sách
   `getUniformLocation`, nạp trong `frame()`).
3. `server/main.py`: thêm vào `_PLANET_SO` / `_PLANET_MAU` / `_PLANET_BAT` / `_PLANET_CHON`
   (quên là người dùng kéo, thấy đổi, F5 mất; `test_tinh_cau_tuy_bien.py` sẽ đỏ).
4. `console.js` `renderPlanetLook`: thêm `truot(...)` hoặc `congTac(...)`.
5. Chuỗi `look.*` vào `i18n/vi.json` + `en.json` (không em dash, không xưng "anh", bản Anh không
   dấu Việt).

### 12.4 Thêm một kiểu giao diện mới (tab con khác)

Thêm một dòng vào `LOOK_SUBS` trong `console.js` (`{ nhan, icon, ve: (host) => renderXxx(host) }`)
và viết hàm vẽ. Hàm vẽ nào giữ tài nguyên (WebGL, timer) thì gán `_pageLeave` để được dọn.

---

## 13. Muốn đổi X thì sửa Y

| Muốn | Sửa |
|---|---|
| Tinh cầu to/nhỏ hơn ở trạng thái thường | `byH = availH * 0.27` trong `layout()` |
| Mặt Trời gần/xa hành tinh | `sdist = geo.R * (0.92 + 1.58 * ...)` |
| Thêm/bớt tia Mặt Trời | `sin(ang*9.+...)` (9 tia), mũ `5.` độ sắc |
| Biển xoáy mạnh/nhẹ | hệ số warp `w.xy*1.3` và tần số `s*2.3` trong `oc` |
| Dải hải lưu dày/thưa | `sin(lat*13. + ...)` và ngưỡng `smoothstep(.93,1.,band)` |
| Lõi to/nhỏ | `rc=.46` (và `.22` khúc xạ) |
| Dòng dung nham mảnh/dày | mũ `9.` trong `vein=pow(1.-abs(f1*2.-1.),9.)` |
| Mây trôi nhanh/chậm khi lặng gió | `.004` trong `rY(uCl.z*.004)`; khi gió mạnh: `7` trong `windT` |
| Vành quỹ đạo rộng/nghiêng | bảng `RINGS` (`k`, `incl`, `roll`) |
| Thêm vị trí núi lửa | mảng `VENTS` (vĩ, kinh) |
| Lốc cao/to | `Hh = R * 0.55`, `w = R*(0.016 + 0.12*f^1.7)` |
| Tia sét dài/ngắn, dày/thưa | `len: 0.16 + rand*0.14`, `nextBolt = now + 500 + rand*2300` |
| Mật độ mưa | `160 / 100 / 55` theo hồ sơ trong `drawRain` |
| Thêm concept màu | một dòng trong `PALETTES` + `_PLANET_CHON["palette"]` + `look.pal_*` + `PAL_KEY` trong console.js |
| Thêm cảnh dựng sẵn | `SCENES` + `look.scene_*` + bảng `SCENE` trong console.js |

---

## 14. Code lại từ đầu: lộ trình 10 bước

1. **Khung**: canvas WebGL2 phủ kín, tam giác phủ màn, fragment shader trả màu theo `gl_FragCoord`.
   Vòng `requestAnimationFrame` với `dt` kẹp 0,1 giây. ResizeObserver đặt kích thước theo DPR.
2. **Hình cầu**: `p = (fragCoord - tâm)/R`, `d = |p|`, trong đĩa thì `n = (p, sqrt(1-d²))`.
   Khử răng cưa mép bằng `smoothstep(1-px, 1+px, d)` với `px = 1.6/R`.
3. **Ánh sáng**: `day = smoothstep(-.25, .45, dot(n, L))`, tối mép `(.6 + .4 n.z)`, fresnel
   `pow(1-n.z, 3)`. Đặt `L` từ vị trí Mặt Trời trên màn hình (cùng MỘT vector cho cả hai).
4. **Bề mặt**: fbm + domain warp trên `s = M*n` (M = ma trận xoay theo thời gian). Màu theo nhiễu.
5. **Khí quyển** ngoài thân: `exp(-max(d-1,0)*6.5)`, sáng phía nắng. **Nền**: tinh vân fbm, sao
   theo lưới băm. Cộng dồn `acc/al`, xuất premultiplied, tone map `1 - exp(-x)`.
6. **Lớp trong có thị sai**: giao tia với cầu bán kính nhỏ hơn sau khúc xạ `p*(1 - k(1-n.z))`.
   Đây là mẹo cho cảm giác "nhìn xuyên nước". Lõi dung nham là cùng mẹo với bán kính 0,46.
7. **Thiên văn**: `sunGeo/moonGeo/moonPhase` (mục 5), khung nhìn địa lý `viewMat/toView`.
8. **Lớp 2D**: vành 3D chiếu trực giao + che bởi hành tinh, mặt trăng đúng pha, nhãn.
9. **Dữ liệu thật**: trạng thái Joyce, dự án (vệ tinh), thời tiết kinh doanh, trạng thái nạp. Bảng
   mục tiêu + nội suy mềm cho mọi chuyển trạng thái.
10. **Độ bền**: hồ sơ chất lượng, hạ bậc theo FPS, mất context, giảm chuyển động, dọn khi huỷ.

---

## 15. Kiểm thử

```
node tests/js/test_tinh_cau_alien.js
node tests/js/test_planet_astro.js
node tests/js/test_tinh_cau_tuy_bien.js
JOYCE_REQUIRE_LOGIN=0 python tests/python/test_tinh_cau_tuy_bien.py
```

`JOYCE_REQUIRE_LOGIN=0` chỉ cần trên máy có `.env` bật đăng nhập (CI không có `.env`): không có nó
thì TestClient bị chặn 401 và mọi test lưu cài đặt đỏ dù code đúng.

**Xem tận mắt bằng Chrome không giao diện** (cách đã dùng khi làm 0.65.38): một trang HTML nạp
`vn-geo.js` + `brain-planet.js` bằng `file://`, `JoycePlanet.create({labels:false, ...})`, gắn vào
một div kín trang, rồi chụp:

```
chrome --headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist
       --allow-file-access-from-files --window-size=1000,640 --virtual-time-budget=20000
       --screenshot=out.png "file:///.../harness.html?scene=storm"
```

Ba bẫy của cách này:
- SwiftShader chỉ chạy được vài khung/giây, nên hiệu ứng chuyển động (hạt, lốc) chưa kịp diễn. Cách
  xử lý: ghi đè `performance.now` và `requestAnimationFrame` bằng đồng hồ ảo, tự bơm 60-80 khung,
  mỗi khung 50ms.
- Sau khi bơm phải `r.pause()`: Chrome đổi cỡ cửa sổ ngay trước khi chụp, ResizeObserver đặt lại
  kích thước canvas (xoá trắng), và chỉ renderer đang dừng mới tự vẽ lại một khung tĩnh.
- Headless có bề ngang tối thiểu 500px: muốn thử màn điện thoại thì bó khung cuộn lại (vd 375px)
  thay vì `--window-size=390,...`.
- `quality=high` trên ảnh chụp là bằng chứng shader biên dịch được (lỗi GLSL thì renderer rơi về
  safe và in cảnh báo).

---

## 16. Bẫy đã gặp

- **`atan` gãy ở ±π**: nhiễu theo góc tạo vệt thẳng ở nửa trái. Dùng vector hướng thay góc.
- **Góc quay tăng vô hạn theo thời gian**: `rotate(t * k)` với `k` đổi được (gió) thì đổi `k` làm
  góc nhảy cóc. Tích luỹ pha bên JS (`windT += dt*k`) rồi truyền pha vào shader.
- **Canvas bỏ qua nét dài 0**: muốn vẽ chấm bằng `lineCap: round` thì nét phải dài tối thiểu một
  chút (`x - 0.05`).
- **Đổi cỡ khung khi đang có hạt**: vị trí màn hình cũ lệch tâm mới, khung kế vẽ vệt dài. Đổi cỡ
  thì quên vị trí cũ (`hot[i].sx = null`).
- **Allowlist phía máy chủ**: POST `/settings` lọc từng khoá; khoá mới quên thêm là "lưu thành
  công" mà F5 mất. Vì vậy tab Cài đặt đọc lại `/settings` sau khi lưu và báo thật.
- **i18n**: không em dash; không có chữ "anh" đứng riêng trong vi.json (luật xưng hô của repo đã
  bắt cả "Thạch anh tím", nên concept đó tên là "Tím pha lê"); bản Anh không được còn dấu Việt.
- **`label` lồng `label`**: ô chọn màu dùng `label.pet-swatch-custom` nên hàng bao ngoài phải là `div`.
