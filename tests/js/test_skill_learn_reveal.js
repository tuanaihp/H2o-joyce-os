/* Nút mở trang từ Skill Learn phải tới đúng skill hoặc plugin vừa cài.

   node tests/js/test_skill_learn_reveal.js
*/
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.join(__dirname, "..", "..");
const SL = fs.readFileSync(path.join(ROOT, "dashboard", "skill-learn.js"), "utf8");
const CSS = fs.readFileSync(path.join(ROOT, "dashboard", "skill-learn.css"), "utf8");
const STUDIO = fs.readFileSync(path.join(ROOT, "dashboard", "studio.js"), "utf8");
const CONSOLE = fs.readFileSync(path.join(ROOT, "dashboard", "console.js"), "utf8");
const INDEX = fs.readFileSync(path.join(ROOT, "dashboard", "index.html"), "utf8");

const fails = [];
function check(name, ok) {
  console.log((ok ? "ok   " : "FAIL ") + name);
  if (!ok) fails.push(name);
}

const added = [], removed = [];
let scrolled = null;
const details = { open: false };
const card = {
  dataset: { slug: "viet-email" }, offsetWidth: 100,
  classList: {
    add: (x) => added.push(x),
    remove: (x) => removed.push(x),
  },
  closest: (sel) => sel === "details" ? details : null,
  scrollIntoView: (opts) => { scrolled = opts; },
};
const other = { dataset: { slug: "khac" } };
const sandbox = {
  window: { requestAnimationFrame: (fn) => fn() },
  document: {},
  setTimeout: (fn) => fn(),
  console,
};
vm.runInNewContext(SL, sandbox, { filename: "skill-learn.js" });
const target = sandbox.window.JoyceSkillLearnTarget;

check("có bộ truyền mục đích dùng chung", !!target);
target.set("skills", "viet-email");
check("peek chỉ trả mục của đúng trang", target.peek("plugins") === null && target.peek("skills").slug === "viet-email");
check("không xoá mục chờ khi thẻ chưa được vẽ", target.reveal("skills", { querySelectorAll: () => [other] }) === false && !!target.peek("skills"));
check("tìm đúng data-slug và mở details cha", target.reveal("skills", { querySelectorAll: () => [other, card] }) === true && details.open);
check("cuộn thẻ vào giữa màn hình", scrolled && scrolled.block === "center");
check("thêm lớp làm nổi bật rồi tự dọn", added.includes("sl-target-flash") && removed.includes("sl-target-flash"));
check("đã mở xong thì xoá mục chờ", target.peek("skills") === null);

check("nút Skill Learn mang cả trang và slug", /data-act="goto"[\s\S]*?data-page=[\s\S]*?data-slug=/.test(SL));
check("bấm nút ghi mục chờ trước khi điều hướng", /targetSet\(b\.dataset\.page, b\.dataset\.slug\);[\s\S]*?Alpine\.store\("nav"\)\.go/.test(SL));
check("trang Kỹ năng bỏ lọc, chọn đúng trang phân trang rồi reveal", /mucCanMo[\s\S]*?_skState\.cat = "ALL"[\s\S]*?Math\.floor\(viTri \/ SK_MOI_TRANG\)[\s\S]*?reveal\("skills", panel\)/.test(STUDIO));
check("thẻ plugin có data-slug và trang Plugin gọi reveal", /div\.dataset\.slug = p\.slug;/.test(CONSOLE) && /reveal\("plugins", wrap\)/.test(CONSOLE));
check("lớp nổi bật dùng token theme", /\.sl-target-flash[\s\S]*?var\(--accent\)/.test(CSS) && /var\(--accent-wash\)/.test(CSS));
check("cache JS và CSS Skill Learn cùng tăng", /skill-learn\.css\?v=6/.test(INDEX) && /skill-learn\.js\?v=6/.test(INDEX));

if (fails.length) {
  console.log("\nFAIL - test_skill_learn_reveal: " + fails.join(", "));
  process.exit(1);
}
console.log("\nOK - test_skill_learn_reveal");
