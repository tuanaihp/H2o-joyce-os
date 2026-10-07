/* Trang Hôm nay + dải Chờ duyệt (Workstation Experience Layer, Phase 1).

       node tests/js/test_trang_hom_nay.js

   Gói tai-lieu-update-tu-openai định vị Joyce là EXPERIENCE LAYER: chỉ đọc + tổng
   hợp nguồn có sẵn, không tạo store nghiệp vụ mới. Ba lỗi thầm lặng file này canh:

   1. **Trang Today phải được đăng ký đủ 4 chỗ** (icon, rail item, nhóm, dispatch) -
      thiếu một chỗ là trang "tồn tại mà không mở được" hoặc hiện key trần.

   2. **"Chờ duyệt" gộp vào trang Việc, KHÔNG tách rail riêng** - cột review của
      kanban đã là inbox phê duyệt sẵn; một trang thứ hai là hai view cho một thực
      thể và chúng sẽ lệch nhau ngay lần sửa đầu tiên.

   3. **Pulse là feed có href** - mọi cảnh báo phải dẫn tới trang xử lý (bấm "app
      down" -> Dự án), item chỉ-đọc-không-đi-được là log, không phải tín hiệu. */
const fs = require("fs");
const path = require("path");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const ROOT = path.join(__dirname, "..", "..");
const D = (f) => fs.readFileSync(path.join(ROOT, "dashboard", f), "utf8");
const CON = D("console.js");
const PY = fs.readFileSync(path.join(ROOT, "server", "joyce_today.py"), "utf8");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));

const fails = [];
const check = (name, cond) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) fails.push(name); };

// ============================================================
// 1. Trang đăng ký đủ chỗ trong console.js
// ============================================================
check("VIEW_ICON có today", /VIEW_ICON\s*=\s*\{[^}]*today:\s*"sun"/s.test(CON));
check("RAIL_ITEMS chứa 'today'", /RAIL_ITEMS\s*=\s*\[[^\]]*"today"/s.test(CON));
check("RAIL_GROUPS có nhóm hom_nay trỏ today",
  /id:\s*"hom_nay"[\s\S]*?ids:\s*\[\s*"today"\s*\]/.test(CON));
check("nhóm hom_nay đứng ĐẦU (entry point)",
  CON.indexOf('id: "hom_nay"') < CON.indexOf('id: "bo_nao"'));
check("VIEW_META có today", /VIEW_META\s*=\s*Object\.fromEntries\(\[\s*"today"/.test(CON));
check("dispatch renderPage -> renderToday", /id === "today"\)[\s\S]*?return renderToday\(el\)/.test(CON));
check("có hàm renderToday", /async function renderToday\(el\)/.test(CON));

// Nhóm mới phải bung được trong railGroups() thật, không chỉ là chữ trong source.
{
  const railCtx = { ICON: {}, GICON: {}, t: k => k };
  vm.createContext(railCtx);
  vm.runInContext(
    CON.slice(CON.indexOf("  const RAIL_ITEMS ="), CON.indexOf("  // Nhãn nhóm chứa")) +
    "\nglobalThis.groups = railGroups();", railCtx);
  const g = railCtx.groups.find(x => x.items.some(i => i.id === "today"));
  assert.ok(g, "nhóm chứa today không tồn tại");
  // deepEqual trên mảng cross-realm (vm context) luôn fail - so từng phần tử.
  assert.equal(g.items.length, 1);
  assert.equal(g.items[0].id, "today");
}

// ============================================================
// 2. Backend: hai endpoint tồn tại + Pulse bọc lỗi từng nguồn
// ============================================================
check("endpoint /api/joyce/v1/today", PY.includes('"/api/joyce/v1/today"'));
check("endpoint /api/joyce/v1/pulse", PY.includes('"/api/joyce/v1/pulse"'));
check("pulse trả partial + sources_down khi nguồn chết", PY.includes('"sources_down"'));
check("mỗi nguồn bọc try/except riêng", PY.includes('_log_pulse_error("kanban"') && PY.includes('_log_pulse_error("inbox"'));
check("pulse item có href", PY.includes('"href"'));

// ============================================================
// 3. Dải Chờ duyệt trong trang Việc (không tách rail)
// ============================================================
check("strip #knApprove trong renderKanban", /id="knApprove"/.test(CON));
check("strip nạp từ cột review của board", /d\.columns\s*&&\s*d\.columns\.review/.test(CON));
check("review có nút Từ chối (data-act=todo -> về lại hàng chờ)",
  /t\.status === "review"[\s\S]*data-act="todo"/.test(CON));
check("KHÔNG có rail item 'approvals' tách riêng", !/"approvals"/.test(CON.match(/RAIL_ITEMS\s*=\s*\[[^\]]*\]/s)[0]));

// ============================================================
// 4. Badge rail + feature flag + command palette (phần còn lại Phase 1)
// ============================================================
const HTML = D("index.html");
check("nav store có badges + badgeOf", /badges:\s*\{\}[\s\S]*?badgeOf\(id\)/.test(CON));
check("rail item render badge span", HTML.includes("rail-badge") && HTML.includes("badgeOf(it.id)"));
check("poller _pollBadges đọc /api/joyce/v1/pulse", /_pollBadges[\s\S]*?\/api\/joyce\/v1\/pulse/.test(CON));
check("badge Việc = approvals", /b\.kanban = approvals/.test(CON));
check("badge Hôm nay = critical+high", /b\.today = heavy/.test(CON));
check("pulse endpoint trả approvals", PY.includes('"approvals"'));
check("feature flag _wsV1 từ settings.features.workstation_v1", /s\.features && s\.features\.workstation_v1 === false/.test(CON));
check("flag tắt -> today vào RAIL_AN", /RAIL_AN\.add\("today"\)/.test(CON));
check("renderPage gate today theo flag", /id === "today"\) \{\s*if \(!_wsV1\)/.test(CON));
check("⌘K palette build + toggle", /function _cmdkBuild/.test(CON) && /_cmdkToggle/.test(CON));
check("Ctrl+K/Cmd+K binding", /e\.key\.toLowerCase\(\) === "k"/.test(CON));
check("palette lọc bỏ dấu bằng _vtNoAccent", /_cmdkRender[\s\S]*?_vtNoAccent/.test(CON));
check("bấm task Today -> mở drawer kanban", /JoyceKanbanShow\(tid\)/.test(CON));
check("palette có lệnh server (whitelist v1)", /_cmd_nudge/.test(CON)
      && /api\/joyce\/v1\/commands/.test(CON) && /orchestration\.auto/.test(CON));
check("palette giấu lệnh server với staff", /!window\.__h2oStaff\)\s*\{[\s\S]*?runCmd/.test(CON));
check("brief LLM fetch lười /brief-ai", /brief-ai\?brain=/.test(CON) && /tdBriefText/.test(CON));

// ============================================================
// 5. i18n: đủ key cả hai ngôn ngữ, không key trần trên rail
// ============================================================
for (const k of ["nav.group.hom_nay", "page.today.label", "page.today.title",
                 "today.p_pulse", "today.p_apps", "today.brief" === "today.brief" ? "today.p_priority" : "",
                 "kanban.approve_strip", "kanban.act_reject",
                 "cmdk.placeholder", "cmdk.empty", "cmdk.cmd_new_task"]) {
  if (!k) continue;
  check(`vi.json có ${k}`, typeof VI[k] === "string" && VI[k].length > 0);
  check(`en.json có ${k}`, typeof EN[k] === "string" && EN[k].length > 0);
}
check("nhãn VI 'Hôm nay'", VI["nav.group.hom_nay"] === "Hôm nay");
check("dải VI 'Chờ duyệt'", VI["kanban.approve_strip"] === "Chờ duyệt");

console.log();
if (fails.length) { console.log("FAIL: " + fails.join(", ")); process.exit(1); }
console.log("PASS trang_hom_nay");
