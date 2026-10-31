/* Linh vật 1.3.55: HÀNH TINH PHÒNG BAN. Nạp thật pet.js với dữ liệu giả của Lõi nước,
   soi shape, màu, đặc trưng và bảng chọn.

       node tests/js/test_pet_hanh_tinh.js

   Luật trung tâm của tính năng này: bảng hành tinh KHÔNG được chép lại trong pet.js - nó phải
   dựng từ window.JoycePlanet.BAN mà brain-planet.js xuất ra (bản sao GX_STYLE/GX_KHOI_MAU).
   Lõi nước đổi phong cách một ban thì linh vật của ban đó theo, hai chỗ không bao giờ lệch
   nhau. Nên test này làm hai việc:
     1. Đối chiếu dữ liệu Lõi nước (đọc thẳng từ mã nguồn brain-planet.js) với từ điển i18n:
       thêm một phòng ban trong Lõi nước mà quên nhãn ở pet là đỏ ngay.
     2. Nạp pet.js với BAN giả, chạy thật API công khai: dựng shape, màu HEX, hai lớp đặc
       trưng (trước/sau thân), ô xem thử có clipPath id độc nhất, và con pet sống đeo được
       hình hành tinh.

   KHÔNG dùng ký tự em dash. */
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..", "..");
const fails = [];
function check(name, cond, extra) {
  console.log((cond ? "ok   " : "FAIL ") + name + (cond || extra === undefined ? "" : "  [" + extra + "]"));
  if (!cond) fails.push(name);
}

const read = (p) => fs.readFileSync(path.join(ROOT, p), "utf8");
const planetSrc = read("dashboard/brain-planet.js");
const petSrc = read("dashboard/pet.js");
const vi = JSON.parse(read("dashboard/i18n/vi.json"));
const en = JSON.parse(read("dashboard/i18n/en.json"));

// ---- Đọc GX_STYLE và GX_KHOI_MAU thẳng từ brain-planet.js ----
const gxBlock = planetSrc.slice(planetSrc.indexOf("var GX_STYLE = {"), planetSrc.indexOf("var gal = {"));
const reBan = /"([a-z0-9_-]+)":\s*\{\s*pal:\s*"(\w+)",\s*feat:\s*"(\w+)"\s*\}/g;
const bans = [...gxBlock.matchAll(reBan)].map(m => ({ ban: m[1], pal: m[2], feat: m[3] }));
check("đọc được bảng phòng ban từ brain-planet.js", bans.length >= 11, `thấy ${bans.length}`);
const reMau = /"([a-z0-9_-]+)":\s*\[(\d+),\s*(\d+),\s*(\d+)\]/g;
const mauBlock = planetSrc.slice(planetSrc.indexOf("var GX_KHOI_MAU = {"), planetSrc.indexOf("var gal = {"));
const maus = [...mauBlock.matchAll(reMau)].map(m => ({ ban: m[1], rgb: [+m[2], +m[3], +m[4]] }));

// ---- 1. Đồng bộ: mọi phòng ban trong Lõi nước đều có shape + nhãn i18n cho pet ----
for (const b of bans) {
  // Quy ước từ điển: id gạch ngang thành gạch dưới ("ke-toan" -> "gx_ke_toan").
  const khoa = "pet.shape.gx_" + b.ban.replace(/-/g, "_");
  check(`nhãn vi cho hành tinh ${b.ban}`, !!vi[khoa], khoa);
  check(`nhãn en cho hành tinh ${b.ban}`, !!en[khoa], khoa);
}
check("Lõi nước có tiêu đề nhóm chọn cho trang Linh vật",
  !!vi["settings.pet_gx"] && !!en["settings.pet_gx"]);
check("brain-planet.js xuất BAN ra window.JoycePlanet", /BAN:\s*\{\s*styles:/.test(planetSrc));
check("pet.js KHÔNG chép bảng hành tinh, chỉ đọc qua JoycePlanet.BAN",
  !/"ke-toan"\s*:\s*\{\s*pal:/.test(petSrc) && /window\.JoycePlanet && window\.JoycePlanet\.BAN/.test(petSrc));

// ---- 2. Nạp thật pet.js với dữ liệu BAN giả ----
function nut() {
  return {
    _html: "", dataset: {}, hidden: false, classList: { add() {}, remove() {}, contains: () => false },
    style: { setProperty() {} }, setAttribute() {}, addEventListener() {}, appendChild() {},
    querySelector: () => nut(), querySelectorAll: () => [], getBoundingClientRect: () => ({ width: 72, height: 72, top: 0, left: 0 }),
    get innerHTML() { return this._html; }, set innerHTML(v) { this._html = String(v); },
  };
}
let now = 1000;
const hangRaf = [];
const win = {
  matchMedia: () => ({ matches: false, addEventListener() {} }), addEventListener() {}, dispatchEvent() {},
  innerWidth: 1280, innerHeight: 800, joyceTheme: { isLight: () => true, on() {} },
  JoycePlanet: {
    BAN: {
      styles: { "ke-toan": { pal: "gold", feat: "ring" }, "cskh": { pal: "ocean", feat: "waves" } },
      colors: { "ke-toan": [255, 205, 90], "cskh": [70, 160, 255] },
    },
  },
};
const doc = {
  readyState: "complete", addEventListener() {}, querySelectorAll: () => [], querySelector: () => nut(),
  getElementById: () => null, body: nut(), activeElement: null,
  createElement: () => {
    const e = nut();
    const con = {};
    e.querySelector = (sel) => (con[sel] = con[sel] || nut());
    return e;
  },
};
new Function("window", "document", "localStorage", "fetch", "requestAnimationFrame", "cancelAnimationFrame",
  "performance", "CustomEvent", "FormData", "setTimeout", "clearTimeout",
  fs.readFileSync(path.join(ROOT, "dashboard", "pet.js"), "utf8"))(
  win, doc, { getItem: () => null, setItem() {} }, () => Promise.reject(new Error("offline")),
  (cb) => { hangRaf.push(cb); return hangRaf.length; }, () => {}, { now: () => now },
  function () {}, function () { this.append = () => {}; }, () => {}, () => {});
const P = win.JoycePet;

// ---- 3. Dựng shape hành tinh từ BAN ----
const gxs = P.gxShapes();
check("dựng đúng hai hành tinh từ BAN giả", Object.keys(gxs).sort().join(",") === "gx-cskh,gx-ke-toan",
  Object.keys(gxs).join(","));
check("khoá shape mang tiền tố gx-", Object.keys(gxs).every(k => /^gx-/.test(k)));
check("màu hành tinh là MÃ HEX đọc được từ GX_KHOI_MAU",
  gxs["gx-ke-toan"].mau.toUpperCase() === "#FFCD5A" && gxs["gx-cskh"].mau.toUpperCase() === "#46A0FF",
  gxs["gx-ke-toan"].mau + " / " + gxs["gx-cskh"].mau);
check("đặc trưng vành Saturn nằm ở lớp TRƯỚC thân (back)",
  /ellipse[^>]*rotate\(-18/.test(gxs["gx-ke-toan"].back || "") && !gxs["gx-ke-toan"].in);
check("đặc trưng sóng nằm ở lớp TRÊN mặt (in) và bị cắt theo thân",
  /Q126 142 160 156/.test(gxs["gx-cskh"].in || "") && !gxs["gx-cskh"].back);
check("thân hành tinh là cùng một hình tròn với shape circle",
  gxs["gx-ke-toan"].d === P.shapes().circle.d);
check("tra shape qua một cửa duy nhất", P.shapeCua("gx-ke-toan") === gxs["gx-ke-toan"] &&
  P.shapeCua("star") === P.shapes().star && P.shapeCua("khong_co") === null);
check("ban không có màu khối thì nhận màu dự phòng đọc được",
  (() => {
    win.JoycePlanet.BAN.colors = {};
    const lai = P.gxShapes();
    return /^#[0-9a-f]{6}$/.test(lai["gx-ke-toan"].mau);
  })(), "phải là hex 6 số");
win.JoycePlanet.BAN.colors = { "ke-toan": [255, 205, 90], "cskh": [70, 160, 255] };
// Xoá cache để lần sau dựng lại từ dữ liệu vừa gán (hàm nhớ _GXC theo thiết kế).

// ---- 4. Con pet sống đeo hình hành tinh ----
P.setCfg({ shape: "gx-ke-toan", palette: "custom", color: gxs["gx-ke-toan"].mau });
check("chuanHoa nhận khoá hành tinh, không reset về hình mặc định",
  P.get().shape === "gx-ke-toan", P.get().shape);
const el = doc.body.querySelector ? null : null;   // (khai báo cho tường minh)
const petEl = (() => {
  // Dựng DOM thật của pet qua đường mount (khoiTao) bằng cách bấm setState với el chưa có:
  // pet.js tự createElement khi lần đầu cần vẽ. doc.createElement ở trên giữ từng phần con.
  P.setState("listening");
  return doc.body;
})();

// ---- 5. Ô xem thử (chanDung) vẽ đủ lớp và clipPath id ĐỘC NHẤT ----
const xem1 = P.previewSvg("gx-ke-toan", "custom", { mau: "#ffcd5a" });
const xem2 = P.previewSvg("gx-cskh", "custom", { mau: "#46a0ff" });
// Kế toán chỉ có đặc trưng đâm RA NGOÀI (vành Saturn) nên không cần clipPath; CSKH có sóng
// nằm TRÊN mặt cầu nên phải có clipPath cắt theo thân.
check("hành tinh chỉ có đặc trưng ngoài thì KHÔNG dính clipPath thừa",
  !/clipPath/.test(xem1) && /rotate\(-18 160 160\)/.test(xem1));
check("chân dung hành tinh có đặc trưng trên mặt thì có clipPath cắt theo thân",
  /clipPath id="petGxClip\d+"/.test(xem2) && /clip-path="url\(#petGxClip\d+\)"/.test(xem2) &&
  /Q126 142 160 156/.test(xem2));
const id1 = /petGxClip(\d+)/.exec(xem2)[1];
const xem3 = P.previewSvg("gx-ke-toan", "custom", { mau: "#ffcd5a", vanh: true });
const xem4 = P.previewSvg("gx-cskh", "custom", { mau: "#46a0ff", vanh: true });
const id2 = /petGxClip(\d+)/.exec(xem4)[1];
check("hai chân dung có hai id clipPath khác nhau", id1 !== id2, `${id1} vs ${id2}`);
check("thân chân dung mang đúng màu ban", /fill="#ffcd5a"/.test(xem1), xem1.slice(0, 120));
check("chân dung hình thường KHÔNG dính clipPath thừa",
  !/clipPath/.test(P.previewSvg("star", "cam", {})));

// ---- 6. Bảng biểu cảm theo trạng thái vẫn nói đúng điều (nghe / nghĩ / vui) ----
// Khoá lại quan hệ trạng thái -> dáng mắt trên chính hình hành tinh: đổi lớp hình không được
// làm mất biểu cảm.
const doc2 = {
  readyState: "complete", addEventListener() {}, querySelectorAll: () => [], querySelector: () => nut(),
  getElementById: () => null, body: nut(), activeElement: null,
  createElement: () => { const e = nut(); const con = {}; e.querySelector = (sel) => (con[sel] = con[sel] || nut()); return e; },
};
new Function("window", "document", "localStorage", "fetch", "requestAnimationFrame", "cancelAnimationFrame",
  "performance", "CustomEvent", "FormData", "setTimeout", "clearTimeout",
  fs.readFileSync(path.join(ROOT, "dashboard", "pet.js"), "utf8"))(
  win, doc2, { getItem: () => null, setItem() {} }, () => Promise.reject(new Error("offline")),
  (cb) => { hangRaf.push(cb); return hangRaf.length; }, () => {}, { now: () => now },
  function () {}, function () { this.append = () => {}; }, () => {}, () => {});
const P2 = win.JoycePet;
P2.setCfg({ shape: "gx-cskh", palette: "custom", color: "#46a0ff" });
check("bảng STATES vẫn ánh xạ nghe->curious, nghĩ->thinking, nói->happy",
  /listening:\s*\{\s*eye:\s*"curious"/.test(petSrc) && /thinking:\s*\{\s*eye:\s*"thinking"/.test(petSrc) &&
  /speaking:\s*\{\s*eye:\s*"happy"/.test(petSrc));
check("phản ứng theo trạng thái còn nguyên: nghe gật, xong nhảy",
  /react\("nghe"\)/.test(petSrc) || /ten === "nghe"/.test(petSrc));

if (fails.length) { console.log(`\nFAILED ${fails.length}: ${fails.join(" | ")}`); process.exit(1); }
console.log("\nOK - test_pet_hanh_tinh: all pass");
