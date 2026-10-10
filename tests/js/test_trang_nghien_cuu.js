/* Trang NGHIÊN CỨU (plan 1.3.7, T3): nối dây đủ, khoá i18n đủ cả hai ngôn ngữ, chỉ đọc, không tô màu cứng.

     node tests/js/test_trang_nghien_cuu.js

   Canh bằng đọc mã nguồn (không chạy DOM): thanh bên, dispatch trong console.js, danh sách trang ở
   ui-actions.js và ui_targets.py, module nghien-cuu.js, và hai từ điển i18n. */
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..", "..");
const doc = (p) => fs.readFileSync(path.join(ROOT, p), "utf8");
const KHONG_CO = [];
function check(ten, ok) {
  console.log((ok ? "ok   " : "FAIL ") + ten);
  if (!ok) KHONG_CO.push(ten);
}

const console_js = doc("dashboard/console.js");
const ui_actions = doc("dashboard/ui-actions.js");
const ui_targets = doc("server/ui_targets.py");
const index_html = doc("dashboard/index.html");
const module_js = doc("dashboard/nghien-cuu.js");
const css = doc("dashboard/console.css");
const vi = JSON.parse(doc("dashboard/i18n/vi.json"));
const en = JSON.parse(doc("dashboard/i18n/en.json"));

// ---- 1. Nối dây trong console.js
const railItems = console_js.match(/const RAIL_ITEMS = \[([\s\S]*?)\]\.map/);
check("RAIL_ITEMS có mục nghiencuu", !!railItems && railItems[1].includes('"nghiencuu"'));
const navLuc = console_js.match(/id: "nang_luc"[^\n]*ids: \[([^\]]*)\]/);
check("nhóm Năng lực trên thanh bên có nghiencuu", !!navLuc && navLuc[1].includes('"nghiencuu"'));
const anNV = console_js.match(/const RAIL_AN_NHAN_VIEN = new Set\(\[([\s\S]*?)\]\);/);
check("nhân viên không thấy nghiencuu trên thanh bên", !!anNV && anNV[1].includes('"nghiencuu"'));
check("VIEW_ICON có biểu tượng cho nghiencuu", /nghiencuu: "sparkles"/.test(console_js));
check("renderPage gọi JoyceNghienCuu.render", console_js.includes('id === "nghiencuu"') &&
  console_js.includes("window.JoyceNghienCuu.render(el)"));
const viewMeta = console_js.match(/const VIEW_META = Object\.fromEntries\(\[([^\]]*)\]/);
check("VIEW_META có nghiencuu", !!viewMeta && viewMeta[1].includes('"nghiencuu"'));

// ---- 2. Danh sách trang đồng bộ ba chỗ (ui-actions.js, ui_targets.py, index.html)
const pagesUi = ui_actions.match(/var PAGES = \[([\s\S]*?)\];/);
check("ui-actions.js PAGES có nghiencuu", !!pagesUi && pagesUi[1].includes('"nghiencuu"'));
const pagesSrv = ui_targets.match(/PAGES = \(([\s\S]*?)\)/);
check("ui_targets.py PAGES có nghiencuu", !!pagesSrv && pagesSrv[1].includes('"nghiencuu"'));
check("ui_targets.py ALIASES nhận 'nghien cuu'", ui_targets.includes('"nghien cuu": "nghiencuu"'));
check("index.html nạp nghien-cuu.js", index_html.includes("/static/nghien-cuu.js"));

// ---- 3. Module trang: sáu khu, chỉ đọc, không tô màu cứng
check("module expose JoyceNghienCuu.render", /window\.JoyceNghienCuu = \{ render \}/.test(module_js));
for (const khu of ["tong_quan", "radar", "pipeline", "thu_vien", "quy_trinh", "nhat_ky"]) {
  check(`module vẽ khu ${khu}`, module_js.includes(`khu("${khu}"`));
}
check("module chỉ đọc: chỉ GET /nghien-cuu", module_js.includes('fetch("/nghien-cuu"') &&
  !/method\s*:/.test(module_js) && !/\bPOST\b/.test(module_js));
check("module không tô màu cứng (hex, white, black)",
  !/#[0-9a-fA-F]{3,8}\b/.test(module_js) && !/:\s*(white|black)\b/.test(module_js));

// ---- 4. Mọi khoá t() của module có trong cả hai từ điển
// Khoá cố định trong mã, bỏ các tiền tố động (kết thúc bằng dấu chấm, ghép với biến sau đó).
const khoaCoDinh = [...module_js.matchAll(/t\("([^"]+)"/g)].map(m => m[1]).filter(k => !k.endsWith("."));
const khoaTheoTien = [];
for (const khu of ["tong_quan", "radar", "pipeline", "thu_vien", "quy_trinh", "nhat_ky"]) khoaTheoTien.push("nc.khu." + khu);
for (const giai of ["moi", "phan-tich", "ban-nhap", "ra-soat", "cho-duyet", "pilot", "hoat-dong", "gac"]) khoaTheoTien.push("nc.giai_doan." + giai);
for (const loai of ["concept", "quy-trinh-moi", "sua-quy-trinh"]) khoaTheoTien.push("nc.loai." + loai);
for (const k of ["nc.sop.active", "nc.sop.superseded"]) khoaTheoTien.push(k);
const tatCa = [...new Set([...khoaCoDinh, ...khoaTheoTien, "page.nghiencuu.title", "page.nghiencuu.sub"])];
const thieu = tatCa.filter(k => !(k in vi) || !(k in en));
check(`mọi khoá i18n của trang có ở vi và en (${tatCa.length} khoá)`, thieu.length === 0);
if (thieu.length) console.log("     thiếu:", thieu.join(", "));

// ---- 5. Khoá không có chữ em dash (quy ước dự án)
const co_emdash = [vi, en].some(d => Object.values(d).some(v => String(v).includes("—")));
check("không có em dash trong vi.json và en.json", !co_emdash);
check("không có em dash trong module nghien-cuu.js", !module_js.includes("—"));

// ---- 6. CSS của trang dùng token, có trong console.css
check("console.css có khối .nc-*", /\.nc-khu\s*\{/.test(css) && /\.nc-pipeline\s*\{/.test(css));
check("CSS trang không tô màu cứng", !/\.nc-[a-z-]+[^}]*#[0-9a-fA-F]{3,6}\b/.test(css));

// ---- 7. Chạy thật: nạp module trong sandbox, đưa JSON mẫu, kiểm HTML sinh ra
const vm_mod = require("node:vm");

async function chayTrang(json, { loiMang = false } = {}) {
  const win = { t: (k) => (vi[k] !== undefined ? vi[k] : k) };
  let html = "";
  const el = { set innerHTML(v) { html = v; }, get innerHTML() { return html; } };
  const sandbox = {
    window: win, console,
    fetch: async () => {
      if (loiMang) throw new Error("mất mạng");
      return { json: async () => json };
    },
  };
  vm_mod.createContext(sandbox);
  vm_mod.runInContext(module_js, sandbox);
  await win.JoyceNghienCuu.render(el);
  return html;
}

const MAU = {
  ok: true, co_brain: true, brain: "Nghien Cuu - Concept Hinh Anh", hom_nay: "2026-10-11",
  tong_quan: { y_tuong_tong: 2, theo_giai_doan: {}, sop_active: 1, sop_superseded: 0, sop_qua_han: 1,
               change_request_mo: 1, pilot_dang_chay: 1 },
  pipeline: { cot: [
    { giai_doan: "moi", the: [{ slug: "x", tieu_de: "<img src=x onerror=alert(1)>", loai: "concept", ngay: "2026-10-10" }] },
    { giai_doan: "phan-tich", the: [] }, { giai_doan: "ban-nhap", the: [] }, { giai_doan: "ra-soat", the: [] },
    { giai_doan: "cho-duyet", the: [] }, { giai_doan: "pilot", the: [] }, { giai_doan: "hoat-dong", the: [] },
  ] },
  thu_vien: { concept: [{ slug: "a", tieu_de: "Váy trắng", giai_doan: "pilot", booking: null }], nguon_booking: false },
  quy_trinh: { sop: [{ slug: "chup", tieu_de: "Chụp album", status: "active", phien_ban: "2",
                       ngay_ra_soat: "2026-09-01", qua_han: true, thay_the: "" }],
               change_request: [{ slug: "sua", tieu_de: "Sửa lọc ảnh", giai_doan: "cho-duyet" }] },
  radar: { muc: [] }, nhat_ky: { muc: [{ ngay: "2026-10-07", loai: "y-tuong", tieu_de: "Váy trắng" }] },
};

(async () => {
  const html = await chayTrang(MAU);
  for (const khu of ["tong_quan", "radar", "pipeline", "thu_vien", "quy_trinh", "nhat_ky"]) {
    check(`render sinh đủ khu ${khu}`, html.includes(`data-khu="${khu}"`));
  }
  check("tiêu đề ghi tay bị escape, không chèn thẻ <img>", !html.includes("<img") && html.includes("&lt;img"));
  check("booking chưa có hiện 'chưa nối nguồn', không bịa số", html.includes("chưa nối nguồn"));
  check("SOP quá hạn có nhãn đến hạn rà soát", html.includes("đến hạn rà soát 2026-09-01"));
  check("radar rỗng có câu nói rõ chưa có bản tin", html.includes(vi["nc.radar.trong"]));
  const thieu = await chayTrang({ ok: true, co_brain: false });
  check("brain chưa có thì báo thiếu brain, không vẽ sáu khu", thieu.includes(vi["nc.thieu_brain"]) && !thieu.includes("data-khu="));
  const loi = await chayTrang({ ok: false, error: "staff_denied" });
  check("server trả lỗi thì báo lỗi, không trắng trang", loi.includes(vi["nc.loi"]));
  const mang = await chayTrang(null, { loiMang: true });
  check("mất mạng thì báo lỗi, không ném lỗi", mang.includes(vi["nc.loi"]));

  console.log(KHONG_CO.length === 0 ? "\nOK - test_trang_nghien_cuu" : `\nĐỎ: ${KHONG_CO.length} - ${KHONG_CO.join(" | ")}`);
  process.exit(KHONG_CO.length ? 1 : 0);
})();
