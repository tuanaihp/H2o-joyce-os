/* Việc hằng ngày trong khung chat (dashboard/viec-mau.js). Chạy tay / CI:
       node tests/js/test_viec_mau.js
   Không cần trình duyệt: test phần thuần (ghép lệnh, kiểm ô bắt buộc, chia nhóm, khoá ô) và các
   hợp đồng tĩnh (khay nằm trong HTML, đi theo khung chat, đủ khoá i18n, màu chỉ dùng token). */
const fs = require("fs");
const path = require("path");
const ROOT = path.join(__dirname, "..", "..");
const read = (p) => fs.readFileSync(path.join(ROOT, p), "utf8");

let fails = [];
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) fails.push(name);
}

const vm = require("../../dashboard/viec-mau.js");
const src = read("dashboard/viec-mau.js");

// ---- ghép lệnh ----
const viec = {
  title: "Tu van", sop: "wiki/quy-trinh.md", route: "auto",
  prompt: "Soan tin cho {khach} ve {dich_vu}. Ghi chu: {ghi_chu}",
  inputs: [{ key: "khach", label: "Khach", required: true }, { key: "dich_vu", label: "DV" }, { key: "ghi_chu", label: "GC" }],
};
const lenh = vm.ghepLenh(viec, { khach: "  Mai ", dich_vu: "Makeup" });
check("thay đúng giá trị và cắt khoảng trắng thừa", lenh.indexOf("cho Mai ve Makeup.") >= 0);
check("ô bỏ trống thành rỗng, không để lộ {khoá}", lenh.indexOf("{") < 0 && lenh.indexOf("Ghi chu: ") >= 0);
check("việc có SOP thì dặn đọc trang SOP trước", lenh.indexOf("wiki/quy-trinh.md") >= 0 && lenh.indexOf("wiki/quy-trinh.md") < lenh.indexOf("Soan tin"));
check("việc không có SOP thì không có lời dặn", vm.ghepLenh({ prompt: "x {a}", sop: "" }, { a: "1" }) === "x 1");
check("route wf: thành lệnh /workflow-<slug>", vm.ghepLenh({ prompt: "x", route: "wf:bao-cao-tuan" }, {}) === "/workflow-bao-cao-tuan x");
check("route agent: thành lệnh /agent-<slug>", vm.ghepLenh({ prompt: "x", route: "agent:giam-dinh" }, {}) === "/agent-giam-dinh x");
check("giá trị có dấu { } không bị ghép đệ quy", vm.ghepLenh({ prompt: "{a} {b}" }, { a: "{b}", b: "z" }) === "{b} z");

// ---- ô bắt buộc ----
check("báo thiếu ô bắt buộc còn trống", vm.thieu(viec, { khach: "   " }).join() === "Khach");
check("đủ ô bắt buộc thì không báo", vm.thieu(viec, { khach: "Mai" }).length === 0);
check("việc không có ô nhập thì không bao giờ thiếu", vm.thieu({ inputs: [] }, {}).length === 0);

// ---- chia nhóm ----
const g = vm.chiaNhom([{ group: "A", slug: "1" }, { group: "B", slug: "2" }, { group: "A", slug: "3" }]);
check("chia nhóm giữ thứ tự xuất hiện đầu tiên", g.map((x) => x.name).join() === "A,B");
check("việc cùng nhóm gom lại dù không liền nhau", g[0].items.map((i) => i.slug).join() === "1,3");
check("danh sách rỗng cho nhóm rỗng", vm.chiaNhom([]).length === 0 && vm.chiaNhom(null).length === 0);

// ---- khoá ô nhập từ nhãn ----
check("nhãn có dấu thành khoá không dấu", vm.khoaO("Tên khách") === "ten_khach");
check("nhãn đ/Đ", vm.khoaO("Đối tượng") === "doi_tuong");
check("nhãn bắt đầu bằng số vẫn ra khoá hợp lệ", /^[a-z][a-z0-9_]*$/.test(vm.khoaO("3 goi")));
check("nhãn trống vẫn ra khoá hợp lệ", /^[a-z][a-z0-9_]*$/.test(vm.khoaO("")));
check("trùng khoá thì thêm hậu tố", vm.khoaO("Tên khách", ["ten_khach"]) === "ten_khach_2");
check("khoá không vượt 20 ký tự", vm.khoaO("mot nhan that la dai dong dai dang", []).length <= 20);

// ---- tự gắn ô vào lệnh ----
const noi = vm.themO("Soan tin cho {khach}", [{ key: "khach", label: "Khach" }, { key: "goi", label: "Goi chup" }]);
check("ô chưa được nhắc tới thì tự nối dòng 'Nhãn: {khoá}'", noi.indexOf("Goi chup: {goi}") >= 0);
check("ô đã có trong lệnh thì không nối lại", noi.split("{khach}").length === 2);

// ---- hợp đồng tĩnh ----
const html = read("dashboard/index.html");
const con = read("dashboard/console.js");
check("khay #vmTray có trong index.html, mặc định ẩn", /id="vmTray"[^>]*hidden/.test(html) || /hidden[^>]*id="vmTray"/.test(html));
check("viec-mau.js được nạp sau composer-plus.js", html.indexOf("/static/viec-mau.js") > html.indexOf("/static/composer-plus.js") && html.indexOf("/static/composer-plus.js") > 0);
check("khay đi theo khung chat sang trang Trò chuyện (CHAT_NODE_IDS)", /CHAT_NODE_IDS = \[[^\]]*"vmTray"/.test(con));
check("khay nằm trước ô nhập để chip ở ngay trên composer", html.indexOf('id="vmTray"') < html.indexOf('id="hudVoice"'));

const vi = JSON.parse(read("dashboard/i18n/vi.json"));
const en = JSON.parse(read("dashboard/i18n/en.json"));
const dung = new Set();
src.replace(/tw\("([a-z_.0-9]+)"/g, (m, k) => { dung.add(k); return m; });
src.replace(/tw\(la_moi \? "([a-z_.0-9]+)" : "([a-z_.0-9]+)"|tw\((?:chung_cat[^"]*|r && r\.ok)\s*\?\s*"([a-z_.0-9]+)"\s*:\s*"([a-z_.0-9]+)"/g, (m, a, b, c, d) => {
  [a, b, c, d].filter(Boolean).forEach((k) => dung.add(k)); return m;
});
["vm.title", "vm.send", "vm.done", "vm.learn", "vm.add_tip", "vm.sop_hint", "vm.menu"].forEach((k) => dung.add(k));
const thieuVi = [...dung].filter((k) => !(k in vi));
const thieuEn = [...dung].filter((k) => !(k in en));
check(`đủ khoá vi cho ${dung.size} khoá vm.*` + (thieuVi.length ? " THIẾU: " + thieuVi.join() : ""), thieuVi.length === 0);
check("đủ khoá en" + (thieuEn.length ? " THIẾU: " + thieuEn.join() : ""), thieuEn.length === 0);
check("khoá vm.* cuối cùng khớp giữa vi và en", Object.keys(vi).filter((k) => k.startsWith("vm.")).sort().join() === Object.keys(en).filter((k) => k.startsWith("vm.")).sort().join());

const dau = String.fromCharCode(0x2014);
check("không dùng gạch dài ở file mã, vi, en", src.indexOf(dau) < 0 && !Object.keys(vi).some((k) => k.startsWith("vm.") && vi[k].indexOf(dau) >= 0)
  && !Object.keys(en).some((k) => k.startsWith("vm.") && en[k].indexOf(dau) >= 0));
const cssPhan = (src.match(/s\.textContent = \[([\s\S]*?)\]\.join/) || [])[1] || "";
check("có đoạn CSS để soi", cssPhan.length > 500);
check("CSS chỉ dùng token theme, không tô cứng #hex hay white/black", !/#[0-9a-fA-F]{3,8}\b/.test(cssPhan) && !/(?<![-\w])(white|black)(?![-\w])/.test(cssPhan));
const bien = new Set((cssPhan.match(/var\(--[a-z0-9-]+/g) || []).map((x) => x.slice(4)));
const style = read("dashboard/style.css");
const chuaDinhNghia = [...bien].filter((v) => style.indexOf(v + ":") < 0);
check("mọi biến CSS dùng đều đã định nghĩa trong style.css" + (chuaDinhNghia.length ? ": " + chuaDinhNghia.join() : ""), chuaDinhNghia.length === 0);

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nTẤT CẢ OK");
