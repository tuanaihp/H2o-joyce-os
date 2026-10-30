/* Tab Thu vien skill: bao cao chi doc, du bo loc, khong thay doi brain.

   node tests/js/test_skill_library_ui.js
*/
const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..", "..");
const UI = fs.readFileSync(path.join(ROOT, "dashboard", "skill-library.js"), "utf8");
const CSS = fs.readFileSync(path.join(ROOT, "dashboard", "skill-library.css"), "utf8");
const CONSOLE = fs.readFileSync(path.join(ROOT, "dashboard", "console.js"), "utf8");
const INDEX = fs.readFileSync(path.join(ROOT, "dashboard", "index.html"), "utf8");
const VI = JSON.parse(fs.readFileSync(path.join(ROOT, "dashboard", "i18n", "vi.json"), "utf8"));
const EN = JSON.parse(fs.readFileSync(path.join(ROOT, "dashboard", "i18n", "en.json"), "utf8"));
const fails = [];
function check(name, ok, extra) {
  console.log((ok ? "ok   " : "FAIL ") + name + (!ok && extra ? " [" + extra + "]" : ""));
  if (!ok) fails.push(name);
}

check("tab Thu vien dung dau va tab brain hien tai dung sau", /slib\.tab\.library[\s\S]*?slib\.tab\.current/.test(CONSOLE));
check("mo trang Ky nang thi tai Thu vien mac dinh", /id === "skills" && window\.JoyceSkillLibrary[\s\S]*?JoyceSkillLibrary\.open/.test(CONSOLE));
check("UI chi goi route audit, khong goi route sua skill", /\/skill-library\/audit/.test(UI) && !/\/skills\/(toggle|delete|group)/.test(UI));
check("co bon bo loc tim, nhom, nganh va trang thai", /#slibQ/.test(UI) && /#slibGroup/.test(UI) && /#slibTag/.test(UI) && /#slibStatus/.test(UI));
check("hien ban pho bien va ban moi sua", /s\.majority_sha/.test(UI) && /s\.newest_sha/.test(UI) && /s\.newest_brains/.test(UI));
check("mau co bien khong bi bao nham la ban sao lech", /var changed = !s\.template &&/.test(UI));
check("hien brain chua khop quy tac", /report\.unmatched_brains/.test(UI));
check("CSS dung token theme, khong khoa nen trang", /var\(--panel-bg\)/.test(CSS) && /var\(--text\)/.test(CSS) && !/(background|color)\s*:\s*(#fff|white)\b/i.test(CSS));
check("tai JS va CSS cua Thu vien truoc console", INDEX.indexOf("skill-library.js?v=1") > 0 && INDEX.indexOf("skill-library.js?v=1") < INDEX.indexOf("console.js?v=216") && INDEX.includes("skill-library.css?v=1"));

const used = [...new Set([...UI.matchAll(/t\("(slib\.[a-z0-9_.-]+)"/g)].map((m) => m[1]))];
const missing = used.filter((k) => !VI[k] || !EN[k]);
check("moi khoa slib dung trong JS co du Viet va Anh", missing.length === 0, missing.join(", "));
const vik = Object.keys(VI).filter((k) => k.startsWith("slib.")).sort();
const enk = Object.keys(EN).filter((k) => k.startsWith("slib.")).sort();
check("hai file i18n co cung tap khoa slib", JSON.stringify(vik) === JSON.stringify(enk));
check("placeholder tim kiem bat dau bang chu hoa", /^[A-ZĐT]/.test(VI["slib.filter.search"]) && /^[A-Z]/.test(EN["slib.filter.search"]));

if (fails.length) {
  console.log("\nFAIL - test_skill_library_ui: " + fails.join(", "));
  process.exit(1);
}
console.log("\nOK - test_skill_library_ui");
