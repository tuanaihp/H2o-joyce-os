/* Tab LỘ TRÌNH (1.3.9): nối dây đủ, khoá i18n đủ hai ngôn ngữ, không tô màu cứng, vẽ đúng ba màn.

     node tests/js/test_trang_lo_trinh.js

   Canh bằng đọc mã nguồn và chạy module trong sandbox (không DOM): thanh bên, dispatch trong
   console.js, danh sách trang ở ui-actions.js và ui_targets.py, module lo-trinh.js, i18n. */
const fs = require("fs");
const path = require("path");
const vm = require("node:vm");

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
const module_js = doc("dashboard/lo-trinh.js");
const css = doc("dashboard/console.css");
const vi = JSON.parse(doc("dashboard/i18n/vi.json"));
const en = JSON.parse(doc("dashboard/i18n/en.json"));
const manifest = JSON.parse(doc("dashboard/icons.manifest.json"));

// ---- 1. Nối dây trong console.js
const railItems = console_js.match(/const RAIL_ITEMS = \[([\s\S]*?)\]\.map/);
check("RAIL_ITEMS có mục lotrinh", !!railItems && railItems[1].includes('"lotrinh"'));
const navLuc = console_js.match(/id: "nang_luc"[^\n]*ids: \[([^\]]*)\]/);
check("nhóm Năng lực trên thanh bên có lotrinh", !!navLuc && navLuc[1].includes('"lotrinh"'));
const anNV = console_js.match(/const RAIL_AN_NHAN_VIEN = new Set\(\[([\s\S]*?)\]\);/);
check("học viên và nhân viên THẤY lotrinh (không nằm trong danh sách ẩn)", !!anNV && !anNV[1].includes('"lotrinh"'));
check("VIEW_ICON có biểu tượng cho lotrinh", /lotrinh: "clipboard-check"/.test(console_js));
const tatCaIcon = Object.values(manifest.groups || {}).flat();
check("biểu tượng clipboard-check có trong icons.manifest.json", tatCaIcon.includes("clipboard-check"));
check("renderPage gọi JoyceLoTrinh.render", console_js.includes('id === "lotrinh"') &&
  console_js.includes("window.JoyceLoTrinh.render(el)"));
const viewMeta = console_js.match(/const VIEW_META = Object\.fromEntries\(\[([^\]]*)\]/);
check("VIEW_META có lotrinh", !!viewMeta && viewMeta[1].includes('"lotrinh"'));

// ---- 2. Danh sách trang đồng bộ ba chỗ
const pagesUi = ui_actions.match(/var PAGES = \[([\s\S]*?)\];/);
check("ui-actions.js PAGES có lotrinh", !!pagesUi && pagesUi[1].includes('"lotrinh"'));
const pagesSrv = ui_targets.match(/PAGES = \(([\s\S]*?)\)/);
check("ui_targets.py PAGES có lotrinh", !!pagesSrv && pagesSrv[1].includes('"lotrinh"'));
check("ui_targets.py ALIASES nhận 'lo trinh'", ui_targets.includes('"lo trinh": "lotrinh"'));
check("index.html nạp lo-trinh.js trước console.js",
  index_html.indexOf("/static/lo-trinh.js") > 0 && index_html.indexOf("/static/lo-trinh.js") < index_html.indexOf("/static/console.js"));

// ---- 3. Module: không tô màu cứng, không em dash, không gọi model
check("module expose JoyceLoTrinh.render", /window\.JoyceLoTrinh = \{ render,/.test(module_js));
check("module không tô màu cứng (hex, white, black)",
  !/#[0-9a-fA-F]{3,8}\b/.test(module_js) && !/:\s*(white|black)\b/.test(module_js));
check("không có em dash trong module", !module_js.includes("—"));
check("module chỉ gọi /lo-trinh, không gọi chat hay model",
  !/fetch\(\s*["'`]\/(chat|api\/chat|engine|models)/.test(module_js) && module_js.includes('goi("/lo-trinh")'));
check("bắt sự kiện chỉ trong trang Lộ trình (khung dùng chung giữa các tab)", module_js.includes('closest(".lt-trang [data-act]")'));

// ---- 4. Mọi khoá i18n có ở cả vi và en
const khoa = new Set([...module_js.matchAll(/(?<![A-Za-z0-9_.])t\("([^"]+)"/g)].map(m => m[1]));
for (const m of module_js.matchAll(/"(lt\.[a-z_.0-9]+)"/g)) khoa.add(m[1]);
for (const k of ["page.lotrinh.label", "page.lotrinh.title", "page.lotrinh.sub"]) khoa.add(k);
const thieu = [...khoa].filter(k => !(k in vi) || !(k in en));
check(`mọi khoá i18n của tab có ở vi và en (${khoa.size} khoá)`, thieu.length === 0);
if (thieu.length) console.log("     thiếu:", thieu.join(", "));
const lt = (d) => Object.entries(d).filter(([k]) => k.startsWith("lt.") || k.startsWith("page.lotrinh."));
check("không có em dash trong khoá lt.* của vi và en", ![...lt(vi), ...lt(en)].some(([, v]) => String(v).includes("—")));

// ---- 5. CSS dùng token
check("console.css có khối .lt-*", /\.lt-khu\s*\{/.test(css) && /\.lt-cau\s*>\s*li\s*\{/.test(css));
check("CSS tab không tô màu cứng", !/\.lt-[a-z-]+[^}]*#[0-9a-fA-F]{3,6}\b/.test(css));

// ---- 6. Chạy thật trong sandbox
function napModule(fetchFn) {
  const win = { t: (k, p) => {
    let s = vi[k] !== undefined ? vi[k] : k;
    for (const [a, b] of Object.entries(p || {})) s = s.split("{" + a + "}").join(String(b));
    return s;
  } };
  const sandbox = { window: win, console, fetch: fetchFn, encodeURIComponent };
  vm.createContext(sandbox);
  vm.runInContext(module_js, sandbox);
  return win.JoyceLoTrinh;
}

const THANG = [{ ma: "hoc-viec", ten: "Học việc", so_bai: 15, so_ngay: 14 }, { ma: "giam-doc", ten: "CO-Giám đốc", so_bai: 0 }];
const TOM_TAT = {
  id: "lt_0123456789", staff_id: "st_a", ten: "<b>Lan</b>", cap_do: "hoc-viec", cap_ten: "Học việc", nhanh: "makeup",
  ngay_bat_dau: "2026-10-10", ngay_hien_tai: 3, so_ngay: 14, trang_thai: "dang_hoc", mentor_ten: "Hoa",
  kien_thuc_tb: 80, bo_bai: 0, rubric_tong: null, de_xuat: "chua_du_du_lieu", ket_luan: null,
  bai_hom_nay: { ngay: 3, tieu_de: "Ngày 3 - Bảo mật", da_nop: false },
};
const TONG_QL = { ok: true, vai: "quan_ly", hom_nay: "2026-10-13", co_brain: true, thang: THANG,
  hoc_vien: [TOM_TAT], cua_toi: [], ung_vien: [{ id: "st_a", ten: "Lan", role: "hoc_viec" }],
  rubric: [{ ma: "ky_thuat", ten: "Kỹ thuật", toi_da: 35 }], must_pass: [{ ma: "ve_sinh", ten: "Vệ sinh" }],
  khao_sat: [{ ma: "thai_do", ten: "Thái độ" }] };
const TONG_HV = { ...TONG_QL, vai: "hoc_viec", hoc_vien: [], ung_vien: [], cua_toi: [TOM_TAT] };

(async () => {
  let html = "";
  const el = { set innerHTML(v) { html = v; }, get innerHTML() { return html; } };

  const m1 = napModule(async () => ({ json: async () => TONG_QL }));
  await m1.render(el);
  check("trưởng phòng thấy khu Kích hoạt và Học viên", html.includes('data-khu="kich_hoat"') && html.includes('data-khu="hoc_vien"'));
  check("thang lộ trình ghi số bài và cấp chưa có bài", html.includes("15 bài học") && html.includes(vi["lt.thang.chua_co_bai"]));
  check("form kích hoạt chỉ cho chọn cấp đã có bài", html.includes('value="hoc-viec"') && !html.includes('value="giam-doc"'));
  check("tên ghi tay bị escape", !html.includes("<b>Lan</b>") && html.includes("&lt;b&gt;Lan"));
  check("thẻ học viên ghi ngày 3/14", html.includes("Ngày 3/14"));

  const m2 = napModule(async () => ({ json: async () => TONG_HV }));
  await m2.render(el);
  check("học viên thấy Lộ trình của tôi, không thấy Kích hoạt", html.includes('data-khu="cua_toi"') && !html.includes('data-khu="kich_hoat"'));
  check("học viên có nút học bài hôm nay", html.includes(vi["lt.nut.hoc_bai_hom_nay"]) && html.includes('data-act="mo-bai"'));

  const m3 = napModule(async () => ({ json: async () => ({ ok: true, vai: "hoc_viec", co_brain: true, thang: THANG, hoc_vien: [], cua_toi: [], ung_vien: [] }) }));
  await m3.render(el);
  check("chưa được kích hoạt thì nói rõ", html.includes(vi["lt.chua_co_lo_trinh"]));

  const m4 = napModule(async () => { throw new Error("mất mạng"); });
  await m4.render(el);
  check("mất mạng thì báo lỗi, không ném lỗi", html.includes(vi["lt.loi.tai"]));

  // Màn bài học: trước khi lộ đáp án và sau khi hết lượt.
  const ve = m1._ve;
  const BAI = { ok: true, ngay: 3, tieu_de: "Ngày 3", loai: "hoc", thoi_luong_phut: 30, muc_tieu: ["Biết <x>"],
    noi_dung: "# Bảo mật\n<script>alert(1)</script>", nguon: [], so_lan: 0, lan_toi_da: 2, diem: null, lan_cuoi: null,
    nop_duoc: true, kiem_tra: [{ hoi: "Khi nào được đăng ảnh?", lua_chon: ["Ngay", "Khi khách đồng ý"] }] };
  const h1 = ve.veBai("lt_0123456789", BAI, null);
  check("bài chưa nộp: có nút nộp, không lộ giải thích", h1.includes('data-act="nop-bai"') && !h1.includes("lt-giai"));
  check("nội dung bài không chạy script khi thiếu bộ đọc markdown", !h1.includes("<script>") && h1.includes("&lt;script&gt;"));
  const KQ = { ok: true, diem: 0, dung: 0, tong: 1, so_lan: 2, het_luot: true,
    chi_tiet: [{ dung: false, chon: 0, dap_an: 1, giai_thich: "Phải có đồng ý." }] };
  const h2 = ve.veBai("lt_0123456789", { ...BAI, so_lan: 2, nop_duoc: false }, KQ);
  check("hết lượt: hiện đáp án và giải thích, khoá nút nộp",
    h2.includes("lt-dap-an") && h2.includes("Phải có đồng ý.") && !h2.includes('data-act="nop-bai"') && h2.includes("lt-sai"));

  // Màn học viên (người chấm): đề xuất dịch đúng lý do.
  const CT = { ok: true, ban_than: false, tom_tat: TOM_TAT, bai: [{ ngay: 0, tieu_de: "Ngày 0", mo: true, co_kiem_tra: true, diem: 90 }],
    kien_thuc: { trung_binh: 90, so_bai: 1, bo_bai: [] }, quan_ly_duoc: true, cham_duoc: true,
    de_xuat: { ket_qua: "can_bo_sung", ly_do: [{ ma: "rubric_65_79", diem: 72 }] }, ket_luan: {}, ngay_nghi: [],
    gate1: {}, khao_sat: {}, rubric: {}, must_pass: {} };
  const h3 = ve.veHocVien(CT);
  check("đề xuất ghi lý do bằng chữ, có điểm", h3.includes("Rubric 72 điểm"));
  check("người quản lý thấy form chấm, ngày nghỉ, kết luận",
    h3.includes('data-form="rubric"') && h3.includes('data-form="nghi"') && h3.includes('data-form="ket-luan"'));
  const h4 = ve.veHocVien({ ...CT, quan_ly_duoc: false });
  check("mentor không thấy form kết luận", !h4.includes('data-form="ket-luan"') && h4.includes('data-form="rubric"'));

  console.log(KHONG_CO.length === 0 ? "\nOK - test_trang_lo_trinh" : `\nĐỎ: ${KHONG_CO.length} - ${KHONG_CO.join(" | ")}`);
  process.exit(KHONG_CO.length ? 1 : 0);
})();
