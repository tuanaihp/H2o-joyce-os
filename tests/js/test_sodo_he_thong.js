/* Trang Sơ đồ hệ thống (dashboard/sodo.js) - "AI engineer's map" của Joyce.

       node tests/js/test_sodo_he_thong.js

   Chạy THẬT render() trong vm với fetch/document giả theo đúng shape của các
   endpoint thật (/settings, /agents, /kanban, /loops, /api/joyce/v1/overview*...).
   Kiểm: đủ 8 khối số liệu, tầng hiệu suất phòng ban đọc board kanban thật, một
   nguồn chết không làm sập trang, đăng ký rail/dispatch/script tag, i18n đủ. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const SODO = D("sodo.js");
const CON = D("console.js");
const INDEX = D("index.html");
const UIA = D("ui-actions.js");
const TARGETS = fs.readFileSync(path.join(__dirname, "..", "..", "server", "ui_targets.py"), "utf8");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));

const fails = [];
const check = (name, cond) => { console.log((cond ? "ok   " : "FAIL ") + name); if (!cond) fails.push(name); };

// ---- môi trường giả: t() đọc vi.json THẬT để lộ key thiếu ----
function makeCtx(canned) {
  const el = { _h: "", btns: [],
    set innerHTML(v) { this._h = v; },
    get innerHTML() { return this._h; },
    querySelectorAll(sel) {
      if (sel !== "[data-go]") return [];
      const out = [];
      const re = /data-go="([^"]+)"/g; let m;
      while ((m = re.exec(this._h))) out.push({ dataset: { go: m[1] }, onclick: null });
      return out;
    } };
  const win = {
    t: (k, v) => {
      let s = VI[k];
      if (s == null) return "THIEU_I18N:" + k;   // thiếu key phải lộ ngay trong HTML
      if (v) for (const kk in v) s = s.replaceAll("{" + kk + "}", v[kk]);
      return s;
    },
    ic: () => "<i/>",
    currentBrainPath: () => "E:\\brains\\Brain Default",
    JoyceNav: { go() {} },
  };
  const doc = { createElement: () => ({ set textContent(v) {}, }), head: { appendChild() {} } };
  const ctx = {
    window: win, document: doc, console,
    fetch: async (u) => {
      const p = u.split("?")[0];
      const d = canned[p];
      if (!d) return { ok: false, status: 404, json: async () => ({}) };
      if (d.__status) return { ok: false, status: d.__status, json: async () => ({}) };
      return { ok: true, status: 200, json: async () => d };
    },
  };
  vm.createContext(ctx);
  vm.runInContext(SODO, ctx);
  return { ctx, el, win };
}

const FULL = {
  "/settings": { model: { main: { provider: "anthropic-cli", model: "opus" },
    providers: [{ id: "anthropic-cli", label: "Claude Code", configured: true, is_main: true },
                { id: "codex-cli", label: "Codex", configured: false }] } },
  "/agents": { agents: [{ slug: "ky-su-harness", name: "Ky su Cai tien", role: "Propose PPC" },
                        { slug: "giam-dinh-harness", name: "Giam dinh", role: "Compose PPC" }] },
  "/skills": { skills: [{ slug: "cham-diem-tuong-phan", name: "Cham diem tuong phan" }] },
  "/workflows": { workflows: [{ slug: "tu-cai-tien-agent", name: "Tu cai tien", status: "active", steps: [1, 2, 3] },
                              { slug: "wf-tat", name: "Wf tat", status: "off", steps: [] }] },
  "/loops": { loops: [{ slug: "dinh-duong-bai-hoc", name: "Dinh duong bai hoc", enabled: true, mode: "full",
                        next_run: 1800000000 }], running: false, running_slug: "" },
  "/kanban": { orchestration: "auto", counts: { triage: 1 },
    operations: { queue: [{}], active: [{}], attention: [] }, dispatcher: { running: true, workers: [] }, completed_24h: 5 },
  "/mcp/list": { servers: [{ name: "zalo" }] },
  "/plugins": { plugins: [{ slug: "datetime-vn", enabled: true }, { slug: "tat", enabled: false }] },
  "/tools/registry": { tools: [{ fn: "joyce_task" }, { fn: "zalo_send" }] },
  "/memory/stats": { facts: 12 },
  "/api/joyce/v1/overview": { memory: { wiki: 46, sources: 30 },
    harness: { pending_n: 1, pending: [{ target: "ky-su-harness", verdict: "win" }],
               lessons_total: 20, learn_log_days: 16, applied_n: 2, last_run: "2026-10-22" } },
  "/api/joyce/v1/overview/departments": { ok: true,
    units: [{ id: "h2o", ten: "H2O Studio" }],
    khois: [{ id: "sx", ten: "Sản xuất" }, { id: "bh", ten: "Bán hàng" }],
    phong: [
      { id: "p1", ten: "San Xuat - Makeup", agent: "Truong phong Makeup", agent_slug: "tp-makeup",
        khoi_id: "sx", status: "good", nhan_vien: 4, nguon: 12, wiki: 8,
        tasks: { done24: 5, open: 3, review: 0, blocked: 0, running: 1, queue: 2 } },
      { id: "p2", ten: "Ban Hang - Sales Vay", agent: "Truong sales vay", agent_slug: "tsv",
        khoi_id: "bh", status: "risk", nhan_vien: 2, nguon: 4, wiki: 3,
        tasks: { done24: 1, open: 7, review: 1, blocked: 2, running: 0, queue: 5 } },
      { id: "p3", ten: "Phong chua gan brain", agent: "", agent_slug: "", khoi_id: "bh",
        status: "nobrain", has_brain: false, nhan_vien: 1, nguon: 0, wiki: 0, tasks: null },
    ] },
};

async function main() {
  // ---- render đủ dữ liệu ----
  {
    const { ctx, el } = makeCtx(FULL);
    await ctx.window.JoyceSoDo.render(el);
    const h = el.innerHTML;
    check("đủ 8 thẻ hệ thống", (h.match(/sd-card c\d/g) || []).length === 8);
    check("thẻ Models hiện engine+model chính", h.includes("anthropic-cli") && h.includes("opus"));
    check("provider chính đánh dấu sao + configured", h.includes("Claude Code ★") && h.includes("Codex"));
    check("thẻ Agents hiện tên+vai trò", h.includes("Ky su Cai tien") && h.includes("Propose PPC"));
    check("board auto hiện đúng trạng thái", h.includes(VI["sodo.board.auto"]));
    check("harness hiện số bài học + đề xuất chờ", h.includes("20") && h.includes(VI["sodo.loop_dd"]));
    check("evals: giám định + skill sẵn sàng + verdict WIN", h.includes("WIN") && h.includes("sẵn sàng"));
    check("ops: loop bật + dispatcher + done24", h.includes("Dispatcher") || h.includes(VI["sodo.dispatch"]));
    check("tầng phòng ban: tên phòng + agent + trạng thái", h.includes("San Xuat - Makeup") && h.includes("Truong phong Makeup"));
    check("phòng risk đếm đúng kẹt", h.includes("risk") && h.includes("kẹt"));
    check("khối gom đúng tên", h.includes("Sản xuất") && h.includes("Bán hàng"));
    check("không rò key i18n", !h.includes("THIEU_I18N"));
    check("nút Mở trang đi đúng 6 hướng", ["models", "camnang", "tools", "staff", "kanban", "selfimprove", "departments"]
      .every(g => h.includes(`data-go="${g}"`)));
    check("dòng chảy vòng đời đủ 7 bước", (h.match(/sd-arr/g) || []).length === 6);
    // ---- bản 1.3.26: sơ đồ + sức khoẻ + trạng thái ----
    check("sơ đồ luồng: 7 nút, mỗi nút trỏ tới một khối", (h.match(/class="sd-node c\d"/g) || []).length === 7 &&
      (h.match(/data-jump="\d"/g) || []).length >= 15);
    check("thanh sức khoẻ: có trạng thái tổng + 8 chip khối", h.includes("sd-health") && (h.match(/class="sd-pill /g) || []).length === 8);
    check("mỗi khối có con số lớn + đèn trạng thái", (h.match(/class="sd-kpi"/g) || []).length === 8 && (h.match(/class="sd-dot sd-st-/g) || []).length >= 8);
    check("việc cần chú ý nói đúng dữ liệu: phòng kẹt + đề xuất chờ", h.includes("1 phòng ban có việc đang kẹt") && h.includes("1 đề xuất cải tiến đang chờ duyệt"));
    check("không có nguồn lỗi thì không báo 'không tải được'", !h.includes(VI["sodo.down"]));
    check("phòng việc kẹt xếp lên đầu khối Bán hàng, thanh tiến độ có mặt", h.indexOf("Ban Hang - Sales Vay") > 0 && h.includes("sd-bar"));
    check("bộ lọc phòng ban Tất cả / Cần chú ý", h.includes('data-f="all"') && h.includes('data-f="attn"'));
    check("không dùng em dash trong HTML", !h.includes("—"));
    check("màu chỉ dùng token theme, không còn --tx/--bd/--tx2 không ai định nghĩa", !/var\(--(tx2?|bd|bg2|bg3)/.test(SODO));
  }
  // ---- 1.3.39: chuẩn Joyce Harness, ba tầng A/B/C, đèn theo số thật từ /work/factory -> harness ----
  {
    const c4 = JSON.parse(JSON.stringify(FULL));
    const o = (k, state, v) => ({ k, state, v: v || {} });
    c4["/work/factory"] = { ok: true, stages: {}, agents: [], autonomy: {}, harness: { version: "1.0.0", ok: 9, total: 14,
      tiers: [
        { id: "A", items: [o("cache", "ok"), o("guard", "ok", { n: 3 }), o("trim", "ok", { n: 80000 }), o("perm", "ok"), o("brake", "ok", { n: 30 })] },
        { id: "B", items: [o("agents", "ok", { n: 3, s: 2 }), o("shared", "ok", { n: 9 }), o("evals", "off", { n: 0 }), o("scope", "off", { n: 0, m: 3 })] },
        { id: "C", items: [o("self", "ok", { n: 61, m: 61 }), o("judge", "ok", { w: 2, k: 1, i: 0 }), o("gate", "warn", { n: 1, e: 0 }),
                           o("registry", "ok", { n: 3, o: 3, s: 0 }), o("routes", "warn", { c: 0, p: 2, u: 6, n: 8 }), o("runs", "ok", { n: 4, v: 1, u: 2, i: 0 }), o("week", "ok", { a: 1, h: 2, q: 0, o: 0, f: 0 }), o("writer", "ok", { d: 0, c: 3, x: 0 }), o("canary", "warn", { n: 0, r: 0, l: 2 }), o("telemetry", "off", { ready: 0, n: 0 }), o("budget", "off", { n: 500000, m: 1000000 })] }],
      phases: [{ k: "0A", state: "ok" }, { k: "0B", state: "warn" }, { k: "1", state: "off" }] } };
    const { ctx, el } = makeCtx(c4);
    await ctx.window.JoyceSoDo.render(el);
    const h = el.innerHTML;
    check("harness: có khối Joyce Harness với ba tầng", h.includes("sd-hx") && (h.match(/class="sd-hx-col"/g) || []).length === 3
      && h.includes(VI["sodo.hx.tA"]) && h.includes(VI["sodo.hx.tC"]));
    check("harness: đủ 20 thành phần, mỗi cái một đèn", (h.match(/class="sd-hx-r /g) || []).length === 20);
    check("harness (A01): đèn bằng chứng canary XÁM và nói thẳng chưa có dữ liệu, không xanh",
      h.includes(VI["sodo.hx.telemetry"]) && h.includes(VI["sodo.hx.telemetry.m"]) && !h.includes(VI["sodo.hx.telemetry.m_ok"])
      && /sd-hx-r sd-st-off[^]*?Bằng chứng canary/.test(h));
    check("harness (A01): canary cần xem hiện số \"cần xem\" và đèn vàng", h.includes("2 cần xem") && /sd-hx-r sd-st-warn[^]*?Canary và lật lại/.test(h));
    check("harness: số thật đi vào chữ (9 bản gốc, 1 chờ chủ, 61/61 brain)", h.includes("9 bản gốc") && h.includes("1 chờ chủ duyệt") && h.includes("61/61"));
    check("harness: số lớn có dấu chấm nghìn", h.includes("500.000") && h.includes("1.000.000"));
    check("harness: thứ chưa làm hiện đèn xám, cổng có việc chờ hiện vàng", h.includes("sd-hx-r sd-st-off") && h.includes("sd-hx-r sd-st-warn"));
    check("harness: điểm tổng và giai đoạn rollout", h.includes(">9/14</b>") && h.includes("Giai đoạn 0A"));
    check("harness: không rò key i18n", !h.includes("THIEU_I18N"));
  }
  {
    const { ctx, el } = makeCtx(FULL);
    await ctx.window.JoyceSoDo.render(el);
    check("không có harness trong /work/factory thì không vẽ khối rỗng", !el.innerHTML.includes("sd-hx-grid") && !el.innerHTML.includes(VI["sodo.hx.sect"]));
  }
  // ---- một nguồn lỗi: khối liên quan báo "Không tải được", các khối khác vẫn bình thường ----
  {
    const c3 = JSON.parse(JSON.stringify(FULL));
    delete c3["/mcp/list"]; delete c3["/tools/registry"];
    const { ctx, el } = makeCtx(c3);
    await ctx.window.JoyceSoDo.render(el);
    const h = el.innerHTML;
    check("nguồn lỗi: khối Tools báo Không tải được, không giả vờ trống", h.includes(VI["sodo.down"]) && h.includes("mcp, tools"));
    check("nguồn lỗi: vẫn đủ 8 thẻ và các khối khác còn số liệu", (h.match(/sd-card c\d/g) || []).length === 8 && h.includes("Ky su Cai tien"));
  }
  // ---- hệ thống mới tinh: Board tắt, chưa có model/agent thì phải nói thẳng ----
  {
    const { ctx, el } = makeCtx({ "/settings": { model: { main: {}, providers: [] } }, "/agents": { agents: [] },
      "/kanban": { orchestration: "off", operations: {}, dispatcher: { running: false } }, "/mcp/list": { servers: [] },
      "/tools/registry": { tools: [{}] }, "/skills": { skills: [] }, "/workflows": { workflows: [] }, "/loops": { loops: [] },
      "/plugins": { plugins: [] }, "/memory/stats": { facts: 0 }, "/api/joyce/v1/overview": { memory: {}, harness: {} } });
    await ctx.window.JoyceSoDo.render(el);
    const h = el.innerHTML;
    check("mới tinh: báo chưa chọn model + Board tắt + chưa có MCP/agent",
      h.includes(VI["sodo.att.no_model"]) && h.includes(VI["sodo.att.board_off"]) && h.includes(VI["sodo.att.no_mcp"]) && h.includes(VI["sodo.att.no_agent"]));
    check("mới tinh: trạng thái tổng là 'Có vấn đề cần xử lý'", h.includes(VI["sodo.health.bad"]));
  }
  // ---- nhân viên thường: departments 403, phần còn lại vẫn vẽ ----
  {
    const c2 = JSON.parse(JSON.stringify(FULL));
    c2["/api/joyce/v1/overview/departments"] = { __status: 403 };
    const { ctx, el } = makeCtx(c2);
    await ctx.window.JoyceSoDo.render(el);
    check("departments 403: trang vẫn đủ 8 thẻ, không sập", (el.innerHTML.match(/sd-card c\d/g) || []).length === 8);
  }
  // ---- mọi endpoint chết: trang vẫn dựng skeleton ----
  {
    const { ctx, el } = makeCtx({});
    await ctx.window.JoyceSoDo.render(el);
    const h = el.innerHTML;
    check("mọi API chết: vẫn render 8 thẻ + flow", (h.match(/sd-card c\d/g) || []).length === 8 && h.includes("sd-flow"));
    check("không rò key i18n khi trống", !h.includes("THIEU_I18N"));
  }
  // ---- đăng ký hệ thống ----
  check("console.js có icon + rail item + dispatch sodo",
    CON.includes('sodo: "workflow"') && CON.includes('"selfimprove", "sodo", "webhooks"') &&
    CON.includes("window.JoyceSoDo.render(el)"));
  check("lệnh UI và giọng nói mở được trang sodo",
    UIA.includes('"selfimprove", "sodo", "webhooks"') &&
    TARGETS.includes('"selfimprove", "sodo", "webhooks"') &&
    TARGETS.includes('"so do": "sodo"'));
  check("index.html nạp sodo.js", INDEX.includes("/static/sodo.js?v="));
  check("nhãn trang đủ vi+en", !!VI["page.sodo.label"] && !!EN["page.sodo.label"]);
  const keys = [...new Set((SODO.match(/t\("(sodo\.[a-z_.]+)"/g) || []).map((m) => m.slice(3, -1))
    .concat(Object.values({ a: "sodo.kpi.engines", b: "sodo.kpi.wiki", c: "sodo.kpi.tools", d: "sodo.kpi.agents", e: "sodo.kpi.wf",
      f: "sodo.kpi.lessons", g: "sodo.kpi.win", h: "sodo.kpi.loops", i: "sodo.s.ok", j: "sodo.s.warn", k: "sodo.s.bad", l: "sodo.s.off",
      m: "sodo.s.err", n: "sodo.health.ok", o: "sodo.health.warn", p: "sodo.health.bad", q: "sodo.open.dept" })))];
  check("mọi khoá sodo.* dùng trong sodo.js có trong vi.json và en.json", keys.every((k) => k in VI && k in EN));
  check("giá trị vi/en không dùng em dash", Object.keys(VI).filter((k) => k.startsWith("sodo.")).every((k) => !VI[k].includes("—") && !(EN[k] || "").includes("—")));

  if (fails.length) { console.log("\nĐỎ " + fails.length + " mục"); process.exit(1); }
  console.log("\nTất cả xanh.");
}
main().catch((e) => { console.log("FAIL chạy test:", e); process.exit(1); });
