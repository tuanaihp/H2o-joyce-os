/* CRM van hanh (dashboard/crm.js). Chay tay / CI:
       node tests/js/test_crm.js
   Khong can trinh duyet: test phan thuan va cac hop dong tinh (trang co trong rail, nhan vien chi thay
   khi duoc cap quyen, du khoa i18n vi/en, mau chi dung token, khong gach dai). */
const fs = require("fs");
const path = require("path");
const ROOT = path.join(__dirname, "..", "..");
const read = (p) => fs.readFileSync(path.join(ROOT, p), "utf8");

let fails = [];
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) fails.push(name);
}

const crm = require("../../dashboard/crm.js");
const src = read("dashboard/crm.js");
const con = read("dashboard/console.js");
const html = read("dashboard/index.html");
const vi = JSON.parse(read("dashboard/i18n/vi.json"));
const en = JSON.parse(read("dashboard/i18n/en.json"));

// ---- phan thuan
check("dinh dang tien kieu Viet", crm.dinhDangTien(12000000) === "12.000.000" && crm.dinhDangTien(0) === "0" && crm.dinhDangTien("abc") === "0");
check("tien am giu dau", crm.dinhDangTien(-1500) === "-1.500");
check("han: tre / hom nay / sap toi / khong han / da xong",
  crm.trangThaiHan({ tre_han: true }) === "late" && crm.trangThaiHan({ hom_nay: true }) === "today"
  && crm.trangThaiHan({ due: "2026-12-01" }) === "soon" && crm.trangThaiHan({}) === ""
  && crm.trangThaiHan({ done: 1, tre_han: true }) === "");
const cot = crm.chiaTheoGiaiDoan([{ key: "a", label: "A", kind: "open", deals: [{ value: 5 }, { value: "7" }] }, { key: "b", label: "B", kind: "won" }]);
check("cot pipeline: dem va cong tien, cot rong van co", cot[0].count === 2 && cot[0].total === 12 && cot[1].count === 0 && cot[1].total === 0);
check("danh sach rong khong vo", crm.chiaTheoGiaiDoan(null).length === 0);
check("chu cai dau avatar", crm.chuCaiDau("Lan Anh") === "LA" && crm.chuCaiDau("Nam") === "NA" && crm.chuCaiDau("") === "?");
check("nhan su kien biet loai la thi tra nguyen", crm.nhanSuKien("khong_biet") === "khong_biet" && crm.nhanSuKien("tao") === vi["crm.ev_create"]);

// ---- hop dong tinh
check("crm.js duoc nap trong index.html", html.indexOf("/static/crm.js") > html.indexOf("/static/conversations.js") && html.indexOf("/static/conversations.js") > 0);
check("trang crm co trong RAIL_ITEMS, nhom Nang luc, VIEW_META va co ham ve",
  /"conversations", "crm", "files"/.test(con) && /"conversations", "crm", "skills"/.test(con)
  && /"conversations", "crm", "learn"/.test(con) && /if \(id === "crm"\) return renderCrm\(el\)/.test(con));
check("nhan vien an muc CRM tru khi duoc cap quyen (_coQuyenCrm)", /nv && id === "crm" && !_coQuyenCrm\(\)/.test(con)
  && /quyen\.indexOf\("crm"\) >= 0/.test(con));
check("form nhan vien co o chon quyen CRM (khong / chi xem / day du) va gui quyen", /id="stFCrm"/.test(con) && /value="crm_xem"/.test(con)
  && /quyen: el\.querySelector\("#stFCrm"\)\.value \|\| "-"/.test(con));
check("nhan vien chi xem cung thay muc CRM", /quyen\.indexOf\("crm_xem"\) >= 0/.test(con));
check("che do chi xem khoa moi dieu khien ghi", /function khoaGhi\(\)/.test(src) && /S\.me\.chi_xem\) khoaGhi\(\)/.test(src));
check("nut xoa va khach da xoa chi hien cho quan ly hoac admin", /S\.me\.admin \|\| S\.me\.quan_ly\) \? '<button class="crm-btn dng" data-a="delete"/.test(src)
  && /S\.me\.admin \|\| S\.me\.quan_ly\) \? '<button class="crm-btn" data-a="trash"/.test(src));
check("bo lang nghe gan tren goc rieng, khong gan len khung dung chung", /document\.createElement\("div"\)/.test(src) && /el\.addEventListener\("click"/.test(src)
  && !/host\.addEventListener/.test(src));

// ---- i18n
const dung = new Set();
src.replace(/tw\("(crm\.[a-z_0-9]+)"/g, (m, k) => { dung.add(k); return m; });
const dong = {
  "crm.tab_": ["contacts", "pipeline", "todos", "proposals", "segments"],
  "crm.mode_": ["off", "duyet", "auto"],
  "crm.seg_": ["can_cham_hom_nay", "dang_theo", "chua_co_co_hoi", "than_thiet", "nguoi_lau_khong_cham"],
  "crm.p_": ["nhu_cau", "ngan_sach", "han", "phan_doi", "buoc_tiep", "tom_tat"],
  "crm.ev_": ["create", "edit", "deal", "todo", "dept", "extract", "approve", "wiki", "delete", "restore"],
};
Object.keys(dong).forEach((p) => dong[p].forEach((x) => dung.add(p + x)));
["crm.need_restart", "crm.guide_title", "crm.guide_body", "crm.all_depts", "crm.pick_dept", "crm.trash", "crm.trash_back", "crm.restore", "crm.restored", "crm.trash_empty", "crm.thr_pre", "crm.thr_post", "crm.f_name", "crm.f_phone", "crm.f_email", "crm.f_company", "page.crm.label", "page.crm.title", "page.crm.sub", "staff.crm_grant", "staff.crm_hint", "staff.crm_none", "staff.crm_view", "staff.crm_full", "crm.dept_on", "crm.dept_on_saved", "crm.read_only", "crm.no_dept"].forEach((k) => dung.add(k));
dung.delete("crm.f_"); dung.delete("crm.tab_"); dung.delete("crm.mode_"); dung.delete("crm.seg_"); dung.delete("crm.p_"); dung.delete("crm.ev_");
const thieuVi = [...dung].filter((k) => !(k in vi));
const thieuEn = [...dung].filter((k) => !(k in en));
check(`du khoa vi cho ${dung.size} khoa` + (thieuVi.length ? " THIEU: " + thieuVi.join() : ""), thieuVi.length === 0);
check("du khoa en" + (thieuEn.length ? " THIEU: " + thieuEn.join() : ""), thieuEn.length === 0);
const mine = (o) => Object.keys(o).filter((k) => k.startsWith("crm.") || k.startsWith("page.crm.") || k.startsWith("staff.crm_")).sort().join();
check("khoa crm.* khop giua vi va en", mine(vi) === mine(en));
const dau = String.fromCharCode(0x2014);
const co = (o) => Object.keys(o).filter((k) => /crm/.test(k)).some((k) => o[k].indexOf(dau) >= 0);
check("khong dung gach dai o file ma, vi, en", src.indexOf(dau) < 0 && !co(vi) && !co(en));
check("tham so {path} cua crm.remembered co o ca hai ngon ngu", vi["crm.remembered"].indexOf("{path}") >= 0 && en["crm.remembered"].indexOf("{path}") >= 0);

// ---- CSS
const css = (src.match(/s\.textContent = \[([\s\S]*?)\]\.join/) || [])[1] || "";
check("co doan CSS de soi", css.length > 1500);
check("CSS chi dung token theme, khong to cung #hex hay white/black", !/#[0-9a-fA-F]{3,8}\b/.test(css) && !/(?<![-\w])(white|black)(?![-\w])/.test(css));
const bien = new Set((css.match(/var\(--[a-z0-9-]+/g) || []).map((x) => x.slice(4)));
const style = read("dashboard/style.css");
const chua = [...bien].filter((v) => style.indexOf(v + ":") < 0 && v !== "--danger-wash");
check("moi bien CSS dung deu da dinh nghia trong style.css" + (chua.length ? ": " + chua.join() : ""), chua.length === 0);
check("van tieng Viet khong nam trong chuoi cua ma (chu qua tw)", !/["'`][^"'`\n]*[À-ỹ][^"'`\n]*["'`]/.test(src.split("\n").filter((l) => !/^\s*(\/\*|\*|\/\/)/.test(l)).join("\n")));

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nTAT CA OK");
