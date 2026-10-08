/* Tia tri thức khi hỏi Joyce (bước A, B, C).

       node tests/js/test_tia_tri_thuc.js

   Thiết kế: docs/dev/2026-10-tia-tri-thuc-khi-hoi.md. Nguyên tắc: chỉ diễn đúng việc Joyce thật
   sự làm. Chạy thật trong vm: ghép đường dẫn file với thiên thể (A), ghép công cụ với app H2O /
   cổng nguồn ngoài (B), nhịp traceTurn + drawTrace (quét, sợi, co về, loé, sáng thêm 10 giây).
   Cộng hợp đồng nối dây app.js và chip "Nguồn tri thức" (C). */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const PLANET = D("brain-planet.js");
const HUD = D("hud.js");
const APP = D("app.js");
const STYLE = D("style.css");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));

const fails = [];
const check = (name, cond) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) fails.push(name); };
function bocHam(src, name, thut) {
  const s = src.indexOf("\n" + thut + "function " + name + "(");
  if (s < 0) { check("có hàm " + name, false); return ""; }
  let i = src.indexOf("{", s), d = 0;
  for (; i < src.length; i++) { if (src[i] === "{") d++; else if (src[i] === "}" && --d === 0) break; }
  return src.slice(s, i + 1);
}

// ---- A + B: ghép (hud.js) ----
const hctx = {
  D: { know: { bodies: [
    { id: "s1", kind: "star", brain: "ThuyH2O - Noi Quy va Bieu Mau", path: "wiki/Danh sach cop trang diem.md" },
    { id: "s2", kind: "star", brain: "Brain Default", path: "wiki/index-gia.md" },
    { id: "s3", kind: "star", brain: "H2O Studio", path: "wiki/index-gia.md" },
    { id: "d1", kind: "debris", brain: "Ban Hang - Sales Hinh Anh", path: "sources/truoc/2. Quy Trình Tư Vấn Báo Giá Online.docx" },
  ] } },
  brainPath: () => "brain",
  healthList: () => [{ id: "legacy", name: "H2O Legacy", role: "sun" }, { id: "book", name: "H2OBOOK" }],
};
vm.createContext(hctx);
vm.runInContext(["gapKhoa", "chuanDuong", "tenBrainDangMo", "ghepThienThe", "nguonNgoai", "appCuaNguon"].map((n) => bocHam(HUD, n, "  ")).join("\n")
  + "\nvar NGUON_TIEN_TO = { fb: 'Facebook', zalo: 'Zalo', crm: 'CRM', pos: 'POS' };", hctx);
const ids = (files) => hctx.ghepThienThe(files).map((b) => b.id);
check("đường dẫn tuyệt đối ghép đúng thiên thể", ids(["E:\\brains\\ThuyH2O - Noi Quy va Bieu Mau\\wiki\\Danh sach cop trang diem.md"]).join() === "s1");
check("detail rút gọn '…/' vẫn ghép được", ids(["…/ThuyH2O - Noi Quy va Bieu Mau/wiki/Danh sach cop trang diem.md"]).join() === "s1");
check("đường dẫn tương đối trùng nhiều brain: ưu tiên brain đang mở", ids(["wiki/index-gia.md"]).join() === "s2");
check("có tên brain trong đường dẫn thì theo brain đó", ids(["/x/brains/H2O Studio/wiki/index-gia.md"]).join() === "s3");
check("X.docx.txt ghép về X.docx (đá vụn)", ids(["sources/truoc/2. Quy Trình Tư Vấn Báo Giá Online.docx.txt"]).join() === "d1");
check("file không có trên trời thì BỎ (không bịa sợi)", ids(["CLAUDE.md", "memory/MEMORY.md", "server/main.py"]).length === 0);
check("đọc lại cùng file trong một lần không nhân đôi", ids(["wiki/index-gia.md", "wiki/index-gia.md"]).length === 1);
const ng = (t) => JSON.stringify(hctx.nguonNgoai(t));
check("công cụ cục bộ không phải nguồn ngoài", ["Read", "Bash", "Grep", "joyce_task", "Edit"].every((x) => hctx.nguonNgoai(x) === null));
check("WebSearch / WebFetch = Internet", /Internet/.test(ng("WebSearch")) && /Internet/.test(ng("WebFetch")));
check("MCP mcp__<máy chủ>__<tool> -> tên máy chủ", hctx.nguonNgoai("mcp__h2o-legacy__query").key === "h2olegacy");
check("plugin fb_ -> Facebook, zalo_ -> Zalo", /Facebook/.test(ng("fb_page_posts")) && /Zalo/.test(ng("zalo_send_message")));
check("nguồn trùng app H2O -> tia từ thiên thể của app đó", hctx.appCuaNguon("h2olegacy") === "legacy" && hctx.appCuaNguon("h2obook") === "book");
check("nguồn không có thiên thể -> cổng mép trái", hctx.appCuaNguon("facebookpages") === null);

// ---- nhịp traceTurn + drawTrace (brain-planet.js) ----
let NOW = 1000;
const c = new Proxy({}, { get(_, k) { return k === "createRadialGradient" || k === "createLinearGradient" ? () => ({ addColorStop() {} }) : () => {}; }, set() { return true; } });
const k1 = { b: { id: "s1" }, col: [0, 231, 255], v: [0, 2, 0.5] };
const pctx = {
  performance: { now: () => NOW }, Math, window: { JoyceVNGeo: { studio: { lat: 20.88, lon: 106.59 } } },
  clamp: (v, a, b) => (v < a ? a : v > b ? b : v), rgba: () => "", PAL: { gold: [1, 1, 1], mint: [2, 2, 2] },
  geo: { cx: 400, cy: 300, R: 150 }, W: 800, H: 600, profile: "high", opts: {},
  know: { byId: { s1: k1 } }, sats: [{ p: { id: "legacy" }, pt: { x: 700, y: 500 } }], sun: null, moon: null,
  cam: { yaw: 0, pitch: 0 }, Gm: [1, 0, 0, 0, 1, 0, 0, 0, 1],
  studioPt: () => ({ x: 420, y: 280 }), toView: () => [0, 0, 1], geoVec: () => [0, 0, 1], ringPt: () => ({ x: 0, y: 0 }),
};
vm.createContext(pctx);
vm.runInContext(["trMoi", "trPin", "trSatPos", "traceTurn", "trStart", "trCurve", "drawTrace", "knowPos", "camRot", "bez"]
  .map((n) => bocHam(PLANET, n, "    ")).join("\n") + "\nvar TR_MAX = 24, TR_GROW = 0.5, TR_BACK = 0.7, TR_GLOW = 10000;\nvar tr = trMoi();", pctx);
const info = () => pctx.tr;
pctx.traceTurn("start");
check("gửi câu hỏi: bắt đầu quét", info().on && !info().tAns);
pctx.traceTurn("source", { id: "s1" }); pctx.traceTurn("source", { id: "s1" });
pctx.traceTurn("source", { id: "khong-co" });
pctx.traceTurn("gate", { kind: "sat", id: "legacy" }); pctx.traceTurn("gate", { kind: "edge", label: "Facebook" });
check("mỗi nguồn một sợi, id lạ bị bỏ", info().threads.length === 3 && info().threads.map((x) => x.kind).join() === "src,sat,edge");
check("sợi từ vệ tinh của app bắt đầu đúng chỗ vệ tinh", JSON.stringify(pctx.trStart(info().threads[1])) === '{"x":700,"y":500}');
const ve = (s) => { for (let i = 0; i < s * 30; i++) { NOW += 33; pctx.drawTrace(c, NOW); } };
ve(1);
pctx.traceTurn("answer");
pctx.traceTurn("source", { id: "s1x" });
check("đã trả lời thì không mọc sợi mới", info().threads.length === 3 && !!info().tAns);
ve(0.8);
pctx.traceTurn("done");
check("xong: thiên thể đã dùng sáng thêm ~10 giây", info().used.length === 1 && info().glowUntil - NOW > 9000);
pctx.traceTurn("done");
check("done lặp không vỡ", !info().on);
for (let i = 0; i < 30; i++) pctx.traceTurn("source", { id: "s1" });
check("thiếu 'start' vẫn an toàn (tự mở lượt mới)", info().on && info().threads.length === 1);
pctx.traceTurn("start");
for (let i = 0; i < 40; i++) pctx.traceTurn("gate", { kind: "edge", label: "n" + i });
check("tối đa 24 sợi một lượt", info().threads.length === 24);

// ---- nối dây ----
check("app.js báo nhịp: start ở status đầu lượt, tool ở mỗi tool_call, answer ở stream đầu, done ở response/lỗi",
  /if \(isActive && t && !t\.triThuc\) \{ t\.triThuc = true; veTriThuc\("start"\); \}/.test(APP)
  && /if \(isActive\) veTriThuc\("tool", \{ tool: data\.tool \|\| "", files: _tep \}\);/.test(APP)
  && /if \(!t\.triThucTraLoi\) \{ t\.triThucTraLoi = true; veTriThuc\("answer"\); \}/.test(APP)
  && /veTriThuc\("answer"\); veTriThuc\("done"\);/.test(APP) && (APP.match(/veTriThuc\("done"\)/g) || []).length >= 2);
check("máy chủ cũ chưa có files: bóc từ detail nếu giống đường dẫn", /const tepCuaLenh = \(d\) =>/.test(APP));
check("chip Nguồn tri thức gắn dưới câu trả lời", /window\.JoyceTriThuc\.chips\(msgEl, t\.tep\)/.test(APP) && /window\.JoyceTriThuc = \{ ghep: ghepThienThe, nguon: nguonNgoai, chips: chipNguon \};/.test(HUD));
check("bấm chip mở file (đúng brain)", /bt\.addEventListener\("click", function \(\) \{ moFileTriThuc\(b\); \}\);/.test(HUD));
check("chip dùng token theme", /\.jv-nguon button \{[^}]*var\(--surface-1\)/.test(STYLE) && !/\.jv-nguon[^{]*\{[^}]*#[0-9a-f]{3,6}/i.test(STYLE));
check("tia tri thức vẽ sau hố đen nạp, trước nhãn", PLANET.indexOf("drawTrace(c, now);") > PLANET.indexOf("drawIngest(c, now, ddt);")
  && PLANET.indexOf("drawTrace(c, now);") < PLANET.indexOf("if (opts.labels !== false) drawLabels(c);"));
check("R.traceTurn lộ ra", /R\.traceTurn = traceTurn;/.test(PLANET));
check("đủ chữ vi + en", VI["hud.k_sources"] && EN["hud.k_sources"]);

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nOK - test_tia_tri_thuc: tất cả pass");
