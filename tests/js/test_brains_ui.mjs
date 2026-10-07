// Test logic dọn folder ngoài (📁) của brains-ui.js - mock DOM tối thiểu + fetch + localStorage.
// Chạy: node dashboard/test_brains_ui.mjs
// Kịch bản = đúng bug thật: 📁 "brain" (đã xoá khỏi đĩa) + 📁 trùng path 1 não thật phải bị dọn,
// 📁 folder ngoài hợp lệ (D:\My Bullet Journal) phải GIỮ.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC = fs.readFileSync(path.join(__dirname, "../../dashboard/brains-ui.js"), "utf8");

const fails = [];
const check = (name, cond) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) fails.push(name); };

const REAL = [
  { name: "Brain Default", path: "D:\\Project\\Joyce-OS\\brains\\Brain Default", notes: 90, is_default: true },
  { name: "My Bullet Journal", path: "D:\\Project\\Joyce-OS\\brains\\My Bullet Journal", notes: 576 },
  { name: "Ngọc Thu Phạm", path: "D:\\Project\\Joyce-OS\\brains\\Ngọc Thu Phạm", notes: 111 },
];
// Server: path nào còn là thư mục.
const EXISTS = {
  "D:\\Project\\Joyce-OS\\brain": { exists: false, is_dir: false },          // 📁 brain: đã xoá
  "D:\\My Bullet Journal": { exists: true, is_dir: true },                    // 📁 ngoài hợp lệ
};

// ---- Mock Option ----
class Opt {
  constructor(value = "", text = "") { this.value = value; this.textContent = text; this.dataset = {}; this._parent = null; }
  get nextSibling() { const a = this._parent?._kids; if (!a) return null; const i = a.indexOf(this); return i >= 0 && i + 1 < a.length ? a[i + 1] : null; }
  remove() { const a = this._parent?._kids; if (a) { const i = a.indexOf(this); if (i >= 0) a.splice(i, 1); } this._parent = null; }
}
class Frag { constructor() { this._kids = []; } appendChild(o) { this._kids.push(o); return o; } }

// ---- Mock Select ----
class Select {
  constructor() { this._kids = []; this._value = "brain"; }
  _all() { return this._kids; }
  _match(o, sel) {
    if (sel === "option[data-brain]") return o.dataset.brain !== undefined;
    if (sel === "option[data-custom]") return o.dataset.custom !== undefined;
    if (sel === 'option[value="brain"]') return o.value === "brain";
    // Thư mục ngoài giờ nằm trong <optgroup> (thẻ <option> không nhận được icon
    // nên dùng nhóm để phân biệt). Mock này chỉ dựng Opt phẳng, không dựng
    // optgroup, nên đúng là không khớp gì - trả false thay vì ném lỗi.
    if (sel === "optgroup") return false;
    if (sel === "optgroup[data-brain-group]") return false;   // nhóm phòng ban H2O: mock không dựng nhóm
    throw new Error("selector chưa mock: " + sel);
  }
  querySelectorAll(sel) { return this._kids.filter((o) => this._match(o, sel)); }
  querySelector(sel) { return this._kids.find((o) => this._match(o, sel)) || null; }
  appendChild(node) {
    const kids = node instanceof Frag ? node._kids : [node];
    for (const k of kids) { k._parent = this; this._kids.push(k); }
    if (node instanceof Frag) node._kids = [];
    return node;
  }
  insertBefore(node, ref) {
    const kids = node instanceof Frag ? node._kids : [node];
    let idx = ref ? this._kids.indexOf(ref) : -1;
    if (idx < 0) idx = this._kids.length;
    for (const k of kids) k._parent = this;
    this._kids.splice(idx, 0, ...kids);
    if (node instanceof Frag) node._kids = [];
    return node;
  }
  get options() { return this._kids; }
  get selectedIndex() { return this._kids.findIndex((o) => o.value === this._value); }
  get value() { return this._value; }
  set value(v) { this._value = v; }
  dispatchEvent() { return true; }
}

const sel = new Select();
// Trạng thái khởi đầu: default + 2 option 📁 (như app.js đã render từ localStorage).
const def = new Opt("brain", "🧠 Brain Default"); sel.appendChild(def);
const c1 = new Opt("path:D:\\Project\\Joyce-OS\\brain", "📁 brain"); c1.dataset.custom = "1"; sel.appendChild(c1);
const c2 = new Opt("path:D:\\My Bullet Journal", "📁 My Bullet Journal"); c2.dataset.custom = "1"; sel.appendChild(c2);
const c3 = new Opt("path:D:\\Project\\Joyce-OS\\brains\\My Bullet Journal", "📁 My Bullet Journal"); c3.dataset.custom = "1"; sel.appendChild(c3); // TRÙNG não thật

// localStorage khởi đầu (3 entry, có 1 trùng não thật)
const store = {
  "joyce.brains": JSON.stringify([
    { name: "brain", path: "D:\\Project\\Joyce-OS\\brain" },
    { name: "My Bullet Journal", path: "D:\\My Bullet Journal" },
    { name: "My Bullet Journal", path: "D:\\Project\\Joyce-OS\\brains\\My Bullet Journal" },
  ]),
  "joyce.graphSource": "brain",
};

// ---- Globals ----
const btns = {};
global.document = {
  getElementById: (id) => id === "graphSource" ? sel : (btns[id] || (btns[id] = { addEventListener() {} })),
  createElement: () => new Opt(),
  createDocumentFragment: () => new Frag(),
};
global.localStorage = { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); } };
global.window = {};
global.Event = class { constructor(t) { this.type = t; } };
global.fetch = async (url) => {
  if (url === "/brains") return { json: async () => ({ dir: "D:\\...", brains: REAL }) };
  if (url.startsWith("/path/exists?path=")) {
    const p = decodeURIComponent(url.split("path=")[1]);
    const r = EXISTS[p] || { exists: false, is_dir: false };
    return { ok: true, json: async () => ({ path: p, ...r }) };
  }
  throw new Error("fetch chưa mock: " + url);
};

// ---- Nạp module (IIFE tự chạy loadBrains(null,true)) ----
eval(SRC);

// loadBrains async → chờ microtask lắng
await new Promise((r) => setTimeout(r, 50));

// ---- Assert ----
const customVals = sel.querySelectorAll("option[data-custom]").map((o) => o.value);
const brainNames = sel.querySelectorAll("option[data-brain]").map((o) => o.dataset.brainName);
const stored = JSON.parse(store["joyce.brains"]);

check("📁 'brain' (đã xoá) bị gỡ khỏi menu", !customVals.includes("path:D:\\Project\\Joyce-OS\\brain"));
check("📁 trùng não thật bị gỡ khỏi menu", !customVals.includes("path:D:\\Project\\Joyce-OS\\brains\\My Bullet Journal"));
check("📁 folder ngoài hợp lệ được GIỮ", customVals.includes("path:D:\\My Bullet Journal"));
check("chỉ còn ĐÚNG 1 option 📁", customVals.length === 1);
check("localStorage còn ĐÚNG 1 entry", stored.length === 1 && stored[0].path === "D:\\My Bullet Journal");
check("🧠 não thật (không default) render đủ 2", brainNames.length === 2 && brainNames.includes("My Bullet Journal") && brainNames.includes("Ngọc Thu Phạm"));
check("option default cập nhật nhãn kèm note", def.textContent.includes("Brain Default") && def.textContent.includes("90"));

// ---- Test 2: fail-safe khi endpoint 404 (server chưa restart) → KHÔNG xoá gì ----
const sel2 = new Select();
sel2.appendChild(new Opt("brain", "🧠 Brain Default"));
const d1 = new Opt("path:D:\\mot\\folder", "📁 folder"); d1.dataset.custom = "1"; sel2.appendChild(d1);
const store2 = { "joyce.brains": JSON.stringify([{ name: "folder", path: "D:\\mot\\folder" }]), "joyce.graphSource": "brain" };
global.document.getElementById = (id) => id === "graphSource" ? sel2 : (btns[id] || (btns[id] = { addEventListener() {} }));
global.localStorage = { getItem: (k) => (k in store2 ? store2[k] : null), setItem: (k, v) => { store2[k] = String(v); } };
global.fetch = async (url) => {
  if (url === "/brains") return { json: async () => ({ brains: [REAL[0]] }) };
  if (url.startsWith("/path/exists")) return { ok: false, status: 404, json: async () => ({ error: "not found" }) };
  throw new Error("fetch chưa mock: " + url);
};
eval(SRC);
await new Promise((r) => setTimeout(r, 50));
const stored2 = JSON.parse(store2["joyce.brains"]);
check("fail-safe: endpoint 404 → GIỮ nguyên entry (không xoá nhầm)", stored2.length === 1 && sel2.querySelectorAll("option[data-custom]").length === 1);

// ---- Test 3: tài khoản nhân viên (scoped) -> giấu brain mặc định + nút tạo/xoá, tự chọn phòng đầu ----
const sel3 = new Select();
const def3 = new Opt("brain", "Brain Default"); sel3.appendChild(def3);
const store3 = { "joyce.brains": "[]", "joyce.graphSource": "brain" };
const btns3 = { newBrainBtn: { style: {}, addEventListener() {} }, delBrainBtn: { style: {}, addEventListener() {} } };
global.document.getElementById = (id) => id === "graphSource" ? sel3 : (btns3[id] || (btns3[id] = { addEventListener() {} }));
global.localStorage = { getItem: (k) => (k in store3 ? store3[k] : null), setItem: (k, v) => { store3[k] = String(v); } };
global.fetch = async (url) => {
  if (url === "/brains") return { json: async () => ({ scoped: true, brains: [
    { name: "San Xuat - Makeup", label: "Phòng Makeup", path: "D:/b/San Xuat - Makeup", notes: 3, is_default: false },
    { name: "Marketing - Makeup", label: "Marketing Makeup", path: "D:/b/Marketing - Makeup", notes: 1, is_default: false },
  ] }) };
  if (url.startsWith("/path/exists")) return { ok: true, json: async () => ({ exists: false, is_dir: false }) };
  throw new Error("fetch chưa mock: " + url);
};
eval(SRC);
await new Promise((r) => setTimeout(r, 50));
check("nhân viên: brain mặc định bị giấu", def3.hidden === true && def3.disabled === true);
check("nhân viên: giấu nút tạo/xoá brain", btns3.newBrainBtn.style.display === "none" && btns3.delBrainBtn.style.display === "none");
check("nhân viên: tự chọn phòng đầu tiên", sel3.value === "path:D:/b/San Xuat - Makeup" && store3["joyce.graphSource"] === sel3.value);
check("nhân viên: nhãn là tên phòng có dấu", sel3.querySelectorAll("option[data-brain]")[0].textContent.startsWith("Phòng Makeup"));

// ---- Test 4: lọc theo THƯƠNG HIỆU (nút não xanh H2O / hồng ThuyH2O) ----
const sel4 = new Select();
sel4.appendChild(new Opt("brain", "Brain Default"));
const sw4 = { hidden: true, innerHTML: "", addEventListener() {}, querySelectorAll: () => [] };
const store4 = { "joyce.brains": "[]", "joyce.graphSource": "brain" };
global.document.getElementById = (id) => id === "graphSource" ? sel4 : id === "brandSwitch" ? sw4 : (btns[id] || (btns[id] = { addEventListener() {} }));
global.localStorage = { getItem: (k) => (k in store4 ? store4[k] : null), setItem: (k, v) => { store4[k] = String(v); } };
// Không có `group`: mock <select> không dựng optgroup (xem chú thích ở mock) - nhóm khối
// là chuyện riêng, ca này chỉ canh bộ lọc thương hiệu.
const B4 = [
  { name: "Brain Default", path: "D:/b/Brain Default", notes: 3, is_default: true },
  { name: "H2O Studio", label: "H2O Studio", path: "D:/b/H2O Studio", notes: 9, brand_id: "h2o", shared: true },
  { name: "San Xuat - Makeup", label: "Phòng Makeup", path: "D:/b/San Xuat - Makeup", notes: 5, brand_id: "h2o" },
  { name: "ThuyH2O Studio", label: "ThuyH2O Studio", path: "D:/b/ThuyH2O Studio", notes: 7, brand_id: "thuyh2o", shared: true },
  { name: "ThuyH2O - Hoc Vien", label: "Học Viên", path: "D:/b/ThuyH2O - Hoc Vien", notes: 4, brand_id: "thuyh2o" },
  { name: "Ca nhan", path: "D:/b/Ca nhan", notes: 2 },
];
global.fetch = async (url) => {
  if (url === "/brains") return { json: async () => ({ brains: B4, brands: [
    { id: "h2o", ten: "H2O Studio", mau: "#22d3ee" }, { id: "thuyh2o", ten: "ThuyH2O", mau: "#f472b6" }] }) };
  if (url.startsWith("/path/exists")) return { ok: true, json: async () => ({ exists: false, is_dir: false }) };
  throw new Error("fetch chưa mock: " + url);
};
eval(SRC);
await new Promise((r) => setTimeout(r, 50));
const names4 = () => sel4.querySelectorAll("option[data-brain]").map((o) => o.dataset.brainName);
check("thương hiệu: hiện cụm nút não khi có 2 brand", sw4.hidden === false && /data-brand="thuyh2o"/.test(sw4.innerHTML) && /--bc:#f472b6/.test(sw4.innerHTML));
check("thương hiệu: mặc định chỉ brain H2O + brain không thuộc brand",
  JSON.stringify(names4().sort()) === JSON.stringify(["Ca nhan", "H2O Studio", "San Xuat - Makeup"]));
window.JoyceBrains.brand("thuyh2o");
check("thương hiệu: bấm hồng -> chỉ còn phòng ThuyH2O + brain không thuộc brand",
  JSON.stringify(names4().sort()) === JSON.stringify(["Ca nhan", "Hoc Vien", "ThuyH2O Studio"].map((n) => n === "Hoc Vien" ? "ThuyH2O - Hoc Vien" : n).sort()));
check("thương hiệu: nhớ lựa chọn brand", store4["joyce.brainBrand"] === "thuyh2o");
// Đang mở một phòng ThuyH2O mà chuyển sang lọc H2O: phòng đang mở vẫn phải còn trong danh sách.
sel4.value = "path:D:/b/ThuyH2O - Hoc Vien";
window.JoyceBrains.brand("h2o");
check("thương hiệu: brain ĐANG MỞ luôn được giữ (không tự đổi brain)",
  names4().includes("ThuyH2O - Hoc Vien") && sel4.value === "path:D:/b/ThuyH2O - Hoc Vien" && !names4().includes("ThuyH2O Studio"));

console.log();
if (fails.length) { console.log(`${fails.length} FAIL: ${fails.join(", ")}`); process.exit(1); }
console.log("TẤT CẢ PASS");
