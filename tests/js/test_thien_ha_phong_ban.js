/* Thiên hà phòng ban (docs/dev/2026-10-thien-ha-phong-ban.md, chủ duyệt 2026-10-08).

       node tests/js/test_thien_ha_phong_ban.js

   Chạy THẬT setGalaxy / gxPos / hitGalaxy trong vm với dữ liệu dạng /knowledge/galaxy: bố cục cố
   định theo tên, các phòng trong cụm không đè nhau, tinh cầu đang mở mang bảng màu khối (không ghi
   vào cài đặt giao diện), tầng zoom thiên hà, bay tới gọi đổi brain đúng lúc. Cộng hợp đồng nối dây
   hud.js (đổi luôn brain đang mở, nút Thiên hà / Trái Đất, tìm từ thiên hà). */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const PLANET = D("brain-planet.js");
const HUD = D("hud.js");
const STYLE = D("style.css");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));
const SKY = fs.readFileSync(path.join(__dirname, "..", "..", "server", "knowledge_sky.py"), "utf8");

const fails = [];
const check = (name, cond) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) fails.push(name); };
function fn(name) {
  // Thụt lề LINH HOẪT (1.3.55): GX_PAL/gxPal/GX_KHOI_MAU hoist lên cấp IIFE để pet.js đọc
  // chung (window.JoycePlanet.BAN), nên giờ hàm nằm ở cả 2 lề. Bắt bằng \s+ thay vì đếm cứng.
  const s = PLANET.search(new RegExp("\\n +function " + name + "\\("));
  if (s < 0) { check("có hàm " + name, false); return ""; }
  let i = PLANET.indexOf("{", s), d = 0;
  for (; i < PLANET.length; i++) { if (PLANET[i] === "{") d++; else if (PLANET[i] === "}" && --d === 0) break; }
  return PLANET.slice(s, i + 1);
}
const hang = (k) => { const m = new RegExp("var " + k + " = ([\\s\\S]+?);\\n").exec(PLANET); check("đọc được " + k, !!m); return m ? "var " + k + " = " + m[1] + ";" : ""; };

let NOW = 1000;
const ctx = {
  Math, performance: { now: () => NOW }, window: {},
  clamp: (v, a, b) => (v < a ? a : v > b ? b : v),
  smooth: (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); },
  PALETTES: { ocean: { rim: [0, 1, 1] }, gold: { rim: [1, 1, 0] }, emerald: { rim: [0, 1, 0] } },
  LD: { pal: { rim: [9, 9, 9] } },
  geo: { cx: 700, cy: 380, R: 30, base: 190, bh: { x: 1200, y: 100, r: 14 } }, W: 1400, H: 760,
  cam: { zoom: 0.16, tzoom: 0.16, tyaw: 0, tpitch: 0 }, tip: { hidden: false },
};
vm.createContext(ctx);
vm.runInContext([hang("GX_STYLE"), hang("GX_PAL"), hang("GX_KHOI_MAU"), hang("gal"),
  ...["hashRnd", "strHash", "galAngle", "gxPal", "setGalaxy", "setGalaxyCur", "gxLevel", "gxScale", "gxPos", "gxRad",
    "hitGalaxy", "flyTo", "drawFly", "galaxyHits", "curPal"].map(fn)].join("\n"), ctx);

const khoi = [["ke-toan", 3], ["nhan-su", 9], ["marketing", 3], ["ban-hang", 3], ["san-xuat", 6], ["nghien-cuu", 4], ["cskh", 3],
  ["ve-sinh", 3], ["xu-ly-truyen-thong", 3], ["van-thu-va-quy-trinh", 1], ["thuyh2o", 6]];
const data = {
  earth: { key: "Brain Default", path: "/b/Brain Default", docs: 14 },
  stars: [{ key: "H2O Studio", brand: "h2o", docs: 8 }, { key: "ThuyH2O Studio", brand: "thuyh2o", docs: 5 }],
  khoi: khoi.map(([id]) => ({ id, ten: id, brand: id === "thuyh2o" ? "thuyh2o" : "h2o" })),
  phong: [].concat(...khoi.map(([id, n]) => Array.from({ length: n }, (_, i) => ({
    key: id + "-" + i, path: "/b/" + id + "-" + i, ten: id + " " + i, khoi: id, brand: id === "thuyh2o" ? "thuyh2o" : "h2o",
    docs: i * 3, raw: i % 2, recent7: i, agents: i % 4, stuck: i === 1 ? 1 : 0 })))),
  others: 0,
};
ctx.setGalaxy(data, "Brain Default");
check("đủ 44 phòng + 2 ngôi sao + Trái Đất", ctx.gal.nodes.length === 47 && ctx.gal.clusters.length === 11);
check("Trái Đất là Brain Default ở lõi, đang được chọn", ctx.gal.cur.key === "Brain Default" && ctx.gal.cur.gx === 0 && ctx.gal.cur.gy === 0);
check("Trái Đất không đổi bảng màu", ctx.gal.palOverride === null && ctx.curPal() === ctx.LD.pal);
const vt = JSON.stringify(ctx.gal.nodes.map((n) => [n.key, n.gx, n.gy]).sort());
const dao = JSON.parse(JSON.stringify(data)); dao.phong.reverse();
ctx.setGalaxy(dao, "Brain Default");
check("vị trí phòng cố định, không phụ thuộc thứ tự dữ liệu",
  ctx.gal.nodes.filter((n) => n.role === "dept").every((n) => JSON.parse(vt).some(([k, x, y]) => k === n.key && Math.abs(x - n.gx) < 1e-9 && Math.abs(y - n.gy) < 1e-9)));
ctx.setGalaxy(data, "Brain Default");
// không đè nhau trong một cụm (đo trên màn ở tầng thiên hà)
let de = 0;
ctx.gal.clusters.forEach((cl) => {
  const ns = ctx.gal.nodes.filter((n) => n.cluster === cl);
  for (let i = 0; i < ns.length; i++) for (let j = i + 1; j < ns.length; j++) {
    const a = ctx.gxPos(ns[i]), b = ctx.gxPos(ns[j]);
    if (Math.hypot(a.x - b.x, a.y - b.y) < (ctx.gxRad(ns[i]) + ctx.gxRad(ns[j])) * 0.9) de++;
  }
});
check("các phòng trong một cụm không đè nhau", de === 0);
let cumGan = 0;
for (let i = 0; i < ctx.gal.clusters.length; i++) for (let j = i + 1; j < ctx.gal.clusters.length; j++) {
  const a = ctx.gal.clusters[i], b = ctx.gal.clusters[j];
  if (Math.hypot(a.gx - b.gx, a.gy - b.gy) < 1.6) cumGan++;
}
check("các cụm khối cách nhau (không chồng cụm)", cumGan === 0);
const to = ctx.gal.nodes.filter((n) => n.key === "nhan-su-8")[0], nho = ctx.gal.nodes.filter((n) => n.key === "nhan-su-0")[0];
check("phòng nhiều tài liệu to hơn", ctx.gxRad(to) > ctx.gxRad(nho));
check("tầng zoom: 1 ở 0,16, 0 ở tầng tinh cầu", Math.abs(ctx.gxLevel() - 1) < 1e-9 && (ctx.cam.zoom = 1, ctx.gxLevel() === 0));
ctx.cam.zoom = 0.16;
// bấm trúng
ctx.gal.hitPts = ctx.gal.nodes.filter((n) => n.role === "dept").map((n) => { const p = ctx.gxPos(n); return { x: p.x, y: p.y, r: ctx.gxRad(n) + 6, n }; });
const kt = ctx.gal.nodes.filter((n) => n.key === "ke-toan-1")[0], pk = ctx.gxPos(kt);
check("bấm trúng tinh cầu phòng ban", ctx.hitGalaxy(pk.x + 1, pk.y) === kt);
// vào phòng: bảng màu khối, tâm thiên hà dời theo
ctx.setGalaxyCur("ke-toan-1");
check("vào phòng Kế Toán: tinh cầu mang bảng màu vàng kim của khối", ctx.curPal() === ctx.PALETTES.gold);
check("tâm thiên hà dời về phòng đang mở", Math.abs(ctx.gxPos(kt).x - ctx.geo.cx) < 1e-6 && Math.abs(ctx.gxPos(kt).y - ctx.geo.cy) < 1e-6);
ctx.setGalaxyCur("thuyh2o-0");
check("ThuyH2O dùng bảng màu hồng riêng", ctx.curPal() === ctx.GX_PAL.pink);
ctx.setGalaxyCur("Brain Default");
// bay tới: gọi đổi brain đúng một lần, giữa lúc màn tối nhất, rồi zoom vào tinh cầu mới
let goi = 0;
const c = new Proxy({}, { get(_, k) { return k.startsWith("create") ? () => ({ addColorStop() {} }) : () => {}; }, set() { return true; } });
ctx.flyTo(kt, () => goi++);
for (let i = 0; i < 90; i++) { NOW += 16; ctx.drawFly(c); }
check("bay tới: đổi brain đúng một lần, rồi zoom từ xa vào", goi === 1 && ctx.cam.tzoom === 1 && ctx.gal.fly === null);
ctx.galaxyHits({ "ke-toan-1": 4, "cskh-0": 1 });
check("tìm từ thiên hà: ghi số kết quả theo phòng", ctx.gal.hitsMax === 4);
ctx.galaxyHits(null);

// ---- nối dây ----
check("ZMIN hạ xuống 0,12 để có tầng Thiên hà", /var ZMIN = 0\.12, ZMAX = 12;/.test(PLANET));
check("bảng màu phòng ban KHÔNG ghi vào cài đặt giao diện (curPal thay LD.pal ở 3 chỗ)",
  (PLANET.match(/curPal\(\)/g) || []).length >= 4 && !/setLook\(\{ ?palette/.test(PLANET));
check("thiên hà vẽ xa nhất, bay tới vẽ trên cùng",
  PLANET.indexOf("drawGalaxy(c, now, ddt);") < PLANET.indexOf("drawGalRing(c, now, ddt, false);")
  && PLANET.indexOf("drawFly(c);") > PLANET.indexOf("drawBHView(c, now, reduced"));
check("bấm: hố đen > thiên hà > thiên thể", (() => {
  const up = PLANET.slice(PLANET.indexOf("function onUp("), PLANET.indexOf("function onDbl("));
  return up.indexOf("onBlackHole(p.x, p.y)") < up.indexOf("hitGalaxy(p.x, p.y)") && up.indexOf("hitGalaxy(p.x, p.y)") < up.indexOf("hitKnow(p.x, p.y)");
})());
check("hud.js: bấm tinh cầu = bay tới + ĐỔI LUÔN brain đang mở",
  /onGalaxyClick: function \(n\) \{ vaoTinhCau\(n\); \}/.test(HUD) && /planet\.flyTo\(n, function \(\) \{ chuyenBrain\(n\); \}\);/.test(HUD)
  && /sel\.dispatchEvent\(new Event\("change", \{ bubbles: true \}\)\);/.test(HUD));
check("hud.js: chọn brain ở ô chọn cũng vào tinh cầu đó", /if \(!_dangBay && nodeThienHa\(tenBrainDangMo\(\)\)\) planet\.arrive\(\);/.test(HUD));
check("hud.js: tìm ở tầng thiên hà sáng tinh cầu có kết quả; bay tới thì Big Bang luôn",
  /planet\.galaxyLevel\(\) > 0\.5\) \{ timThienHa\(q\); return; \}/.test(HUD) && /if \(_choTim\) \{ var q0 = _choTim;/.test(HUD));
check("nút Thiên hà và ← Trái Đất, theo token theme", /id="gxBtn"/.test(HUD) && /id="gxEarth"/.test(HUD)
  && /\.gx-btn \{[^}]*var\(--surface-1\)/.test(STYLE) && !/\.gx-btn \{[^}]*#[0-9a-f]{3,6}/i.test(STYLE));
check("máy chủ: /knowledge/galaxy, nhân viên chỉ thấy phòng được gán", /@router\.get\("\/knowledge\/galaxy"\)/.test(SKY) && /others \+= 1/.test(SKY));
const khoa = ["planet.gx_btn", "planet.gx_back_earth", "planet.gx_here", "planet.gx_docs", "planet.gx_raw", "planet.gx_stuck", "planet.gx_hits"];
check("đủ chữ vi + en", khoa.every((k) => VI[k] && EN[k]) && !khoa.some((k) => /[–—]/.test(VI[k] + EN[k])));

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nOK - test_thien_ha_phong_ban: tất cả pass");
