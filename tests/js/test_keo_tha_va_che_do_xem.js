/* Kéo thả tinh thể và 3 chế độ xem (1.3.3).

       node tests/js/test_keo_tha_va_che_do_xem.js

   Kiểm tra: kéo thả cập nhật vị trí, chế độ xem quỹ đạo/tam giác bố trí đúng, chuyển mode
   có hoạt ảnh, nút UI có mặt, i18n đủ khoá. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const PLANET = D("brain-planet.js");
const HUD = D("hud.js");
const STYLE = D("style.css");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));

const fails = [];
const check = (name, cond) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) fails.push(name); };

// ---- nối dây brain-planet.js ----
check("có hàm focHitItem", /function focHitItem\(x, y\)/.test(PLANET));
check("có hàm focViewLayout", /function focViewLayout\(mode, items\)/.test(PLANET));
check("foc có viewMode, dragIt, dragLand", /viewMode: 0, viewT0: 0, viewFrom: null, dragIt: null, dragLand: 0/.test(PLANET));
check("R.setFocViewMode lộ ra", /R\.setFocViewMode = function/.test(PLANET));
check("R.focViewMode lộ ra", /R\.focViewMode = function/.test(PLANET));
check("knowledgeFocus trả viewMode", /viewMode: foc\.viewMode/.test(PLANET));

// ---- kéo thả tinh thể ----
check("onDown nhận diện focHitItem", /focHitItem\(p\.x, p\.y\)/.test(PLANET));
check("onDown ghi dragIt + _dragX/_dragY", /foc\.dragIt = fi/.test(PLANET));
check("onMove cập nhật _dragX/_dragY khi focDrag", /fi2\._dragX = fi2\.px/.test(PLANET));
check("onUp: kéo xong ghi dragged + _userX/_userY", /fi3\.dragged = true/.test(PLANET));
check("onUp: không kéo (click) gọi onKnowledgeClick", /opts\.onKnowledgeClick && opts\.onKnowledgeClick\(kh3\.b/.test(PLANET));
check("drawKnowFocus: dragIt mờ các tinh thể khác", /foc\.dragIt && it !== foc\.dragIt\) a \*= 0\.55/.test(PLANET));
check("drawKnowFocus: hạ cánh scale 1.1->1.0", /foc\.dragLand && it === foc\._landed/.test(PLANET));

// ---- kéo nhóm vòng trong (quỹ đạo) ----
check("kéo tinh thể vòng trong dời cả nhóm (orbit)", /fi2\._vring === 0/.test(PLANET));
check("kéo tinh thể tam giác dời cả nhóm (triangle)", /fi2\._vtri != null/.test(PLANET) && /oi\._vtri === tg/.test(PLANET));

// ---- chế độ xem ----
check("vẽ vòng tròn quỹ đạo (mode 1)", /vRadii = \[80 \* vsc, 160 \* vsc, 240 \* vsc\]/.test(PLANET));
check("vẽ tam giác chòm sao (mode 2)", /vtR \* 0\.866/.test(PLANET));
check("nét đứt cho khung hình chế độ xem", /c\.setLineDash\(\[6, 4\]\)/.test(PLANET));
check("hoạt ảnh chuyển mode 600ms", /clamp\(\(now - foc\.viewT0\) \/ 600/.test(PLANET));

// ---- nối dây hud.js ----
check("hud.js: có div #fvCtl", /id="fvCtl"/.test(HUD));
check("hud.js: 3 nút fv-btn với data-fv 0,1,2",
  /data-fv="0"/.test(HUD) && /data-fv="1"/.test(HUD) && /data-fv="2"/.test(HUD));
check("hud.js: bấm nút gọi setFocViewMode", /planet\.setFocViewMode\(m\)/.test(HUD));
check("hud.js: focViewReset ẩn fvCtl khi đóng tìm kiếm", /function focViewReset\(\)/.test(HUD));
check("hud.js: tìm có kết quả thì hiện fvCtl", /fc\.hidden = !_timHits\.length/.test(HUD));
check("hud.js: repaintTitles dịch data-title-tk", /data-title-tk/.test(HUD) && /el\.dataset\.titleTk/.test(HUD));

// ---- CSS ----
check("CSS: .fv-ctl dùng token theme",
  /\.fv-ctl \{[^}]*position: absolute/.test(STYLE) && /\.fv-btn \{[^}]*var\(--surface-1\)/.test(STYLE));
check("CSS: .fv-active nổi bật", /\.fv-btn\.fv-active \{/.test(STYLE));
check("CSS: ẩn khi chế độ Quan sát", /brain-overlays-hidden .fv-ctl/.test(STYLE));
check("CSS: peek-b hiện fv-ctl khi rê chuột dưới", /hud-peek-b .fv-ctl/.test(STYLE));
check("hud.js: mousemove bật hud-peek-b khi gần đáy", /hud-peek-b.*r\.height - 100/.test(HUD));
check("hud.js: touchstart bật peek vùng đáy", /touchstart[\s\S]*?hud-peek-b/.test(HUD));

// ---- i18n ----
var fvKeys = ["planet.fv_sky", "planet.fv_orbit", "planet.fv_tri"];
check("đủ chữ vi cho chế độ xem", fvKeys.every(function (k) { return VI[k]; }));
check("đủ chữ en cho chế độ xem", fvKeys.every(function (k) { return EN[k]; }));

// ---- kéo dịch thiên hà (pan) ----
check("gal có panX, panY", /panX: 0, panY: 0/.test(PLANET));
check("gxPos cộng panX/panY", /gal\.panX \|\| 0\)/.test(PLANET) && /gal\.panY \|\| 0\)/.test(PLANET));
check("kéo ở tầng thiên hà: pan thay vì xoay", /gxLevel\(\) > 0\.5\) \{\s*\n\s*gal\.panX \+= p\.x/.test(PLANET));
check("chạm đúp reset pan", /gal\.panX = 0; gal\.panY = 0;\s*\n\s*\}/.test(PLANET));
check("bay tới reset pan", /gal\.panX = 0; gal\.panY = 0;\s*\n\s*var p = gxPos\(n\)/.test(PLANET));
check("nhãn Bạn đang ở đây dịch theo pan", /geo\.cx \+ \(gal\.panX \|\| 0\)/.test(PLANET));

// ---- kéo tinh cầu/khối thiên hà ----
check("onDown nhận diện hitGalaxy cho gxDrag", /gal\.dragNode = isClus \? null : gh2/.test(PLANET));
check("onDown ghi gxDrag flag", /gxDrag: true/.test(PLANET));
check("onMove: gxDrag chuyển delta screen sang galaxy unit", /drag\.gxDrag && \(gal\.dragNode \|\| gal\.dragCluster\)/.test(PLANET));
check("onMove: gxDrag cập nhật _dox/_doy", /tgt\._dox = \(tgt\._dox \|\| 0\) \+ gdx/.test(PLANET));
check("onMove: gxDrag cursor grabbing", /ovCv\.style\.cursor = "grabbing"/.test(PLANET));
check("onUp: gxDrag xoá dragNode/dragCluster", /gal\.dragNode = null; gal\.dragCluster = null/.test(PLANET));
check("onUp: gxDrag không kéo thì gọi onGalaxyClick", /wasGxDrag[\s\S]*?opts\.onGalaxyClick/.test(PLANET));
check("gxPos cộng cluster offset", /n\.cluster && n\.cluster\._dox/.test(PLANET));
check("hover cursor grab cho galaxy node", /gh && gxLevel\(\) > 0\.5 \? "grab"/.test(PLANET));

// ---- không em dash ----
check("không em dash trong brain-planet.js", !/[—]/.test(PLANET));
check("không em dash trong hud.js", !/[—]/.test(HUD));

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nOK - test_keo_tha_va_che_do_xem: tất cả pass");
