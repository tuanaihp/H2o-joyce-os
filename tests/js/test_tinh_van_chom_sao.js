/* Tinh vân kiểu chòm sao (dashboard/brain-constellation.js, 1.3.24).
     node tests/js/test_tinh_van_chom_sao.js
   Canh: gom thư mục, bố cục không đè lõi / không chồng nhau, nhánh sáng đúng theo việc thật,
   quả cầu đúng brain đang mở, nối dây vào app.js / index.html / CSS / từ điển. */
const fs = require("fs");
const path = require("path");
const ROOT = path.join(__dirname, "..", "..");
const doc = (p) => fs.readFileSync(path.join(ROOT, p), "utf8");
const fails = [];
function check(ten, ok) { console.log((ok ? "ok   " : "FAIL ") + ten); if (!ok) fails.push(ten); }

const SRC = doc("dashboard/brain-constellation.js");
const C = require(path.join(ROOT, "dashboard/brain-constellation.js"));
const G = C.GEOM;

// 1) Gom thư mục
const nodes = [];
const F = { wiki: 12, facts: 18, sources: 8, agents: 4, skills: 11, ".claude": 9, "07 - Learn Log": 3, attachments: 5 };
for (const [f, c] of Object.entries(F)) for (let i = 0; i < c; i++) nodes.push({ id: f + i, path: "brain/" + f + "/n" + i + ".md" });
nodes.push({ id: "goc", path: "brain/README.md" });
nodes.push({ id: "sau", path: "brain/wiki/y-tuong/x.md" });
const g = C.groupFolders(nodes);
const by = Object.fromEntries(g.folders.map((x) => [x.key, x]));
check("gom theo thư mục GỐC (wiki/y-tuong/x.md tính vào wiki)", by.wiki && by.wiki.count === 13);
check("bỏ thư mục ẩn (.claude) và attachments", !by[".claude"] && !by.claude && !by.attachments);
check("bỏ tiền tố số '07 - '", !!by["learn log"] && by["learn log"].name === "Learn Log");
check("note nằm thẳng ở gốc không thuộc nhánh nào", g.total === 13 + 18 + 8 + 4 + 11 + 3);
check("lớp: agents/skills là vận hành, wiki là tri thức", by.agents.layer === "ops" && by.skills.layer === "ops" && by.wiki.layer === "know");
const nhieu = [];
for (let k = 0; k < 20; k++) for (let i = 0; i <= k; i++) nhieu.push({ path: `b/f${k}/n${i}.md` });
nhieu.push({ path: "b/loops/a.md" });
const g2 = C.groupFolders(nhieu);
check("tối đa 12 nhánh thư mục, nhánh vận hành ít note vẫn giữ", g2.folders.length === 12 && g2.folders.some((x) => x.key === "loops"));

// 2) Bố cục
const mcps = Array.from({ length: 12 }, (_, i) => ({ id: "m" + i, label: "M" + i, enabled: i % 2 === 0 }));
const L = C.layout(g2.folders, mcps);
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
check("không nút nào đè lên lõi (ngoài vòng cách ly)", L.every((n) => Math.hypot(n.x - G.AX, n.y - G.AY) >= G.MINR - 0.01));
let minD = 1e9; L.forEach((a, i) => L.forEach((b, j) => { if (i < j) minD = Math.min(minD, dist(a, b)); }));
check("các nút không chồng lên nhau (cách nhau >= 24)", minD >= 24);
check("MCP tối đa 10 nút, nút chưa bật là live=false (vẽ nét đứt)", L.filter((n) => n.layer === "mcp").length === 10 && L.find((n) => n.key === "m1").live === false);
check("mọi nút nằm trong khung vẽ", L.every((n) => n.x > 8 && n.x < G.VW - 8 && n.y > 8 && n.y < G.VH - 8));
check("khe đáy chừa cho chữ trạng thái: không nút thư mục nào ngay dưới lõi",
  L.filter((n) => n.layer !== "mcp").every((n) => !(Math.abs(n.x - G.AX) < 40 && n.y > G.AY)));

// 3) Nhánh sáng theo việc thật
const LN = C.layout(g.folders, [{ id: "zalo1", label: "Zalo", enabled: true, slug: "zalo" }, { id: "gm", label: "Gmail", enabled: true, slug: "gmail" }]);
const nguon = (tool) => { const p = String(tool).split("__"); return p.length >= 3 ? { key: p[1] } : null; };
check("đọc wiki/... -> nhánh WIKI", JSON.stringify(C.targetsFor({ tool: "Read", files: ["wiki/huong-dan.md"] }, LN, nguon)) === '["f:wiki"]');
check("đường dẫn tuyệt đối Windows vẫn khớp", C.targetsFor({ files: ["E:\\x\\brain\\facts\\a.md"] }, LN, nguon).includes("f:facts"));
check("gọi Skill -> nhánh SKILLS", C.targetsFor({ tool: "Skill" }, LN, nguon).includes("f:skills"));
check("gọi mcp__zalo__send -> nút Zalo", C.targetsFor({ tool: "mcp__zalo__send_message" }, LN, nguon).includes("m:zalo1"));
check("công cụ không liên quan -> không bịa nhánh nào", C.targetsFor({ tool: "Bash", files: ["/tmp/x.txt"] }, LN, nguon).length === 0);

// 4) Quả cầu đúng brain đang mở
const gal = { earth: { key: "Brain Default", ten: "Brain Default" }, phong: [{ key: "Ke Toan", ten: "Kế toán", khoi: "ke-toan" }], stars: [{ key: "H2O Legacy", brand: "h2o" }] };
check("Brain Default -> Trái Đất", C.sphereFor(gal, "Brain Default").kind === "earth" && C.sphereFor(gal, "Brain Default").style === "_earth");
check("brain phòng -> tinh cầu đúng khối (Kế toán vàng có vành)", C.sphereFor(gal, "Ke Toan").style === "ke-toan" && C.buildSurface("ke-toan", 1).ring === true);
check("brain thương hiệu -> ngôi sao", C.sphereFor(gal, "H2O Legacy").kind === "star");
const sf = C.buildSurface("_earth", 7);
check("bề mặt Trái Đất dựng được, giá trị hợp lệ", sf.TW === 256 && sf.base.every((v) => v >= 0 && v <= 1.01));

// 5) Nối dây
const APP = doc("dashboard/app.js"), IDX = doc("dashboard/index.html"), CSS = doc("dashboard/style.css");
check("app.js phát joyce:graph-data sau khi nạp /graph", APP.includes('new CustomEvent("joyce:graph-data"'));
check("app.js báo note mới (joyce:graph-add)", APP.includes('new Event("joyce:graph-add")'));
check("app.js đẩy trạng thái + mức âm sang chòm sao", APP.includes("window.JoyceTinhVan.setState(state)") && APP.includes("window.JoyceTinhVan.setLevel(voice.getLevel())"));
check("index.html nạp brain-constellation.js sau graph.js, trước app.js",
  IDX.indexOf("/static/graph.js") < IDX.indexOf("/static/brain-constellation.js") && IDX.indexOf("/static/brain-constellation.js") < IDX.indexOf("/static/app.js"));
check("index.html có nút #tvModeBtn có data-i18n-aria", /id="tvModeBtn"[^>]*data-i18n-aria="tv\.mode_to_note"/.test(IDX));
check("CSS: chòm sao che đồ thị note; Lõi nước bật thì ẩn chòm sao",
  CSS.includes(".hud-center.tv-chom #graph2d") && CSS.includes(".hud-center.hud-on .bc-layer"));
check("chuyển Mạng note khi bấm timelapse ở chòm sao", SRC.includes("#graphTimelapseBtn") && SRC.includes("setMode('note')"));
check("nhớ lựa chọn chòm sao / Mạng note", SRC.includes("joyce.tvMode"));

// 6) Từ điển + an toàn
const vi = JSON.parse(doc("dashboard/i18n/vi.json")), en = JSON.parse(doc("dashboard/i18n/en.json"));
const keys = [...new Set((SRC.match(/tt\('(tv\.[a-z_]+)'/g) || []).map((m) => m.slice(4, -1))
  .concat(["tv.st_idle", "tv.st_listen", "tv.st_think", "tv.st_speak", "tv.mode_to_note", "tv.mode_to_chom", "tv.layer_ops", "tv.layer_know", "tv.mcp_on", "tv.mcp_off"]))];
check("mọi khoá tv.* có trong vi.json và en.json", keys.every((k) => k in vi && k in en));
check("ghi công APEX-UI (MIT), không dùng tên Apex trên giao diện", SRC.includes("MIT") && SRC.includes("APEX-UI") && !/tt\([^)]*[Aa]pex/.test(SRC));
check("không em dash", !SRC.includes("\u2014") && !Object.values(vi).concat(Object.values(en)).some((v) => String(v).includes("\u2014")));
check("tôn trọng giảm chuyển động", SRC.includes("prefers-reduced-motion"));

console.log(fails.length ? "\n" + fails.length + " FAIL" : "\nTẤT CẢ PASS");
process.exit(fails.length ? 1 : 0);
