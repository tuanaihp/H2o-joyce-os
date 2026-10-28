// Trang Sơ đồ hệ thống - "AI engineer's map" của Joyce.
//
// Vì sao có file này: chủ hệ thống cần MỘT màn nhìn thấy Joyce vận hành ra sao -
// model nào, não đang giữ gì, chạm được vào đâu, ai đang làm, harness học thế
// nào - rồi bấm thẳng tới trang chỉnh. MỌI con số là số thật gọi từ API đang chạy,
// không phải chữ trang trí.
//
// Bố cục (1.3.26):
//   1. Thanh sức khoẻ: mấy khối ổn, và danh sách "cần chú ý" nói thẳng việc phải làm.
//   2. Sơ đồ luồng: 7 bước một lượt việc đi qua hệ thống, mỗi bước hiện số liệu sống,
//      bấm là nhảy tới khối tương ứng.
//   3. Tám khối (Models/Context/Tools/Agents/Multi-agent/Harness/Evals/Ops), mỗi khối
//      có con số lớn, đèn trạng thái, chip, dòng chi tiết và nút "Mở trang".
//   4. Hiệu suất phòng ban: board kanban thật của từng brain, lọc "cần chú ý".
// Nguồn nào không tải được thì khối đó báo "Không tải được" chứ không giả vờ trống.
// Chỉ ĐỌC. Tự làm mới mỗi 60 giây khi trang đang hiện.
//
// Màu CHỈ dùng token của theme (--text, --card, --line, --ok-ink...) nên đúng ở cả hai
// giao diện. Bản đầu dùng --tx/--bd/--tx2 không ai định nghĩa: chữ trắng trên nền trắng.
(function () {
  "use strict";
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ic = (n, o) => (window.ic ? window.ic(n, o) : "");
  const t = (k, v) => (window.t ? window.t(k, v) : k);
  const brain = () => (window.currentBrainPath ? window.currentBrainPath() : "brain");
  const go = (id) => { try { if (window.JoyceNav) return window.JoyceNav.go(id); } catch (e) {} };
  const api = async (u) => { const r = await fetch(u); if (!r.ok) throw new Error(String(r.status)); return r.json(); };
  const so = (n) => Number(n || 0).toLocaleString("vi-VN");
  const REFRESH_MS = 60000;

  // Bảng khoá i18n LITERAL - test_i18n quét t("key") nên không được ghép chuỗi động.
  const OPEN_GO = { models: "sodo.open.models", camnang: "sodo.open.camnang", tools: "sodo.open.tools",
                    staff: "sodo.open.staff", kanban: "sodo.open.kanban", selfimprove: "sodo.open.selfimprove" };
  const BOARD_KEY = { auto: "sodo.board.auto", manual: "sodo.board.manual", off: "sodo.board.off" };
  const VERDICT_KEY = { win: "sodo.verdict.win", keep: "sodo.verdict.keep", inconclusive: "sodo.verdict.inc" };
  const STATE_KEY = { ok: "sodo.s.ok", warn: "sodo.s.warn", bad: "sodo.s.bad", off: "sodo.s.off" };
  const HEALTH_KEY = { ok: "sodo.health.ok", warn: "sodo.health.warn", bad: "sodo.health.bad" };
  const ST_TXT = { good: "ov.st_good", wait: "ov.st_wait", risk: "ov.st_risk", empty: "ov.st_empty",
                   nobrain: "ov.st_nobrain", error: "ov.st_error" };
  // Thứ tự phòng trong khối: việc kẹt lên đầu, phòng chưa gắn brain xuống cuối.
  const ST_ORDER = { risk: 0, wait: 1, good: 2, error: 3, empty: 4, nobrain: 5 };
  const BLOCKS = [
    { n: 1, ic: "cpu", t: "sodo.c1", d: "sodo.c1d", kpi: "sodo.kpi.engines", go: "models" },
    { n: 2, ic: "database", t: "sodo.c2", d: "sodo.c2d", kpi: "sodo.kpi.wiki", go: "camnang" },
    { n: 3, ic: "wrench", t: "sodo.c3", d: "sodo.c3d", kpi: "sodo.kpi.tools", go: "tools" },
    { n: 4, ic: "users", t: "sodo.c4", d: "sodo.c4d", kpi: "sodo.kpi.agents", go: "staff" },
    { n: 5, ic: "git-branch", t: "sodo.c5", d: "sodo.c5d", kpi: "sodo.kpi.wf", go: "kanban" },
    { n: 6, ic: "sparkles", t: "sodo.c6", d: "sodo.c6d", kpi: "sodo.kpi.lessons", go: "selfimprove" },
    { n: 7, ic: "clipboard-check", t: "sodo.c7", d: "sodo.c7d", kpi: "sodo.kpi.win", go: "selfimprove" },
    { n: 8, ic: "settings", t: "sodo.c8", d: "sodo.c8d", kpi: "sodo.kpi.loops", go: "kanban" },
  ];
  // Bước luồng -> khối cung cấp số liệu cho bước đó.
  const FLOW = [
    { k: "sodo.flow.ask", ic: "send", c: 1 }, { k: "sodo.flow.ctx", ic: "database", c: 2 },
    { k: "sodo.flow.agent", ic: "users", c: 4 }, { k: "sodo.flow.tool", ic: "wrench", c: 3 },
    { k: "sodo.flow.result", ic: "square-kanban", c: 8 }, { k: "sodo.flow.learn", ic: "sparkles", c: 6 },
    { k: "sodo.flow.approve", ic: "clipboard-check", c: 7 },
  ];

  // Trạng thái giao diện giữ qua các lần làm mới tự động (bộ lọc phòng ban).
  const ui = { filter: "all", facNote: "", el: null };
  let timer = null;

  let _css = false;
  function injectCss() {
    if (_css) return; _css = true;
    const st = document.createElement("style");
    st.textContent = `
.sd-root{container:sd/inline-size;padding:14px 18px 32px;display:flex;flex-direction:column;gap:14px;color:var(--text);
  --sd-1:var(--info);--sd-2:var(--accent);--sd-3:var(--ok-ink);--sd-4:var(--ov-amber);
  --sd-5:var(--ov-violet);--sd-6:var(--ov-rose);--sd-7:var(--ov-teal);--sd-8:var(--ov-indigo)}
.sd-st-ok{--s:var(--ok-ink)}.sd-st-warn{--s:var(--warn-ink)}.sd-st-bad{--s:var(--danger-ink)}.sd-st-off{--s:var(--text3)}
.sd-top{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:12px;color:var(--text2)}
.sd-brain{padding:3px 10px;border-radius:20px;border:1px solid var(--line);background:var(--wash);color:var(--text)}
.sd-upd{margin-left:auto;color:var(--text3)}
.sd-refresh{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:8px;cursor:pointer;
  border:1px solid var(--line);background:var(--wash);color:var(--text2)}
.sd-refresh:hover{color:var(--accent-ink);border-color:var(--accent)}
.sd-refresh.spin svg{animation:sdSpin .8s linear infinite}
@keyframes sdSpin{to{transform:rotate(360deg)}}
.sd-health{display:grid;grid-template-columns:auto 1fr;gap:12px 16px;align-items:center;padding:14px 16px;border-radius:14px;
  background:var(--card);border:1px solid var(--line);border-left:4px solid var(--s)}
.sd-orb{width:14px;height:14px;border-radius:50%;background:var(--s);box-shadow:0 0 0 5px color-mix(in srgb,var(--s) 22%,transparent)}
.sd-hstate{font-size:16px;font-weight:700}
.sd-hsub{font-size:12px;color:var(--text2);margin-top:2px}
.sd-pills{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:6px}
.sd-pill{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;padding:3px 10px 3px 8px;border-radius:20px;cursor:pointer;
  border:1px solid var(--line);background:var(--wash);color:var(--text)}
.sd-pill:hover{border-color:var(--s)}
.sd-pill i,.sd-dot{width:8px;height:8px;border-radius:50%;background:var(--s);flex:none;display:inline-block}
.sd-att{grid-column:1/-1;list-style:none;display:flex;flex-direction:column;gap:6px;margin:0;padding:0}
.sd-att li{display:flex;align-items:center;gap:10px;font-size:12.5px;padding:7px 10px;border-radius:9px;
  background:color-mix(in srgb,var(--s) 11%,transparent);border:1px solid color-mix(in srgb,var(--s) 30%,transparent)}
.sd-att li svg{color:var(--s);flex:none}
.sd-att li span{flex:1;min-width:0}
.sd-att button{border:0;background:none;color:var(--accent-ink);font-size:12px;cursor:pointer;white-space:nowrap;padding:2px 4px}
.sd-att button:hover{text-decoration:underline}
.sd-sect{font-size:11px;font-weight:700;letter-spacing:.7px;text-transform:uppercase;color:var(--text3);margin:4px 0 -4px}
.sd-flow{display:flex;align-items:stretch}
.sd-node{flex:1 1 0;min-width:0;display:flex;flex-direction:column;align-items:flex-start;gap:3px;padding:10px 11px;border-radius:12px;
  cursor:pointer;text-align:left;font:inherit;color:var(--text);background:var(--card);border:1px solid var(--line);position:relative}
.sd-node:hover{border-color:var(--h);transform:translateY(-1px)}
.sd-node-ic{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;color:var(--h);
  background:color-mix(in srgb,var(--h) 15%,transparent)}
.sd-node b{font-size:12.5px;font-weight:650;line-height:1.25}
.sd-node-in{display:flex;flex-direction:column;gap:2px;min-width:0}
.sd-metric{font-size:11px;color:var(--text2);line-height:1.3;overflow-wrap:anywhere}
.sd-node .sd-dot{position:absolute;top:10px;right:10px}
.sd-arr{--sd-ln:color-mix(in srgb,var(--text3) 65%,transparent);flex:none;width:24px;align-self:center;height:2px;position:relative;background:var(--sd-ln)}
.sd-arr::before{content:"";position:absolute;right:-1px;top:-3px;border:4px solid transparent;border-left:6px solid var(--sd-ln);border-right:0}
.sd-arr::after{content:"";position:absolute;top:-2px;left:0;width:6px;height:6px;border-radius:50%;background:var(--accent);
  animation:sdFlow 2.4s linear infinite}
@keyframes sdFlow{0%{transform:translateX(0);opacity:0}15%{opacity:1}85%{opacity:1}100%{transform:translateX(18px);opacity:0}}
.sd-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
@supports (container-type:inline-size){
  .sd-grid{grid-template-columns:repeat(4,minmax(0,1fr))}
  @container sd (max-width:1099px){.sd-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
  @container sd (max-width:619px){.sd-grid{grid-template-columns:minmax(0,1fr)}}
  @container sd (max-width:819px){
    .sd-flow{flex-direction:column}.sd-node{flex-direction:row;align-items:center;gap:10px}.sd-node .sd-dot{position:static;margin-left:auto}
    .sd-arr{width:2px;height:16px;align-self:center}
    .sd-arr::before{right:-3px;top:auto;bottom:-1px;border:4px solid transparent;border-top:6px solid var(--sd-ln);border-bottom:0}
    .sd-arr::after{display:none}
  }
}
.sd-card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:13px 14px;display:flex;flex-direction:column;
  gap:9px;min-height:170px;position:relative;overflow:hidden;box-shadow:var(--shadow-1)}
.sd-card::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:var(--h)}
.sd-card.sd-flash{animation:sdFlash 1.3s ease-out}
@keyframes sdFlash{0%{box-shadow:0 0 0 3px var(--h)}100%{box-shadow:var(--shadow-1)}}
.sd-h{display:flex;align-items:center;gap:8px}
.sd-ico{width:28px;height:28px;border-radius:9px;display:grid;place-items:center;flex:none;color:var(--h);
  background:color-mix(in srgb,var(--h) 15%,transparent)}
.sd-num{font-size:10.5px;color:var(--text3);font-weight:700;letter-spacing:.5px}
.sd-t{font-weight:700;font-size:14px}
.sd-h .sd-dot{margin-left:auto}
.sd-sub{font-size:11.5px;color:var(--text3);margin-top:-5px}
.sd-kpi{display:flex;align-items:baseline;gap:7px}
.sd-kpi b{font-size:26px;line-height:1;font-weight:750;letter-spacing:-.5px}
.sd-kpi span{font-size:12px;color:var(--text2)}
.sd-chips{display:flex;flex-wrap:wrap;gap:5px}
.sd-chip{font-size:11px;padding:2px 8px;border-radius:20px;border:1px solid var(--line);background:var(--wash);color:var(--text);white-space:nowrap}
.sd-chip.on{border-color:color-mix(in srgb,var(--ok-ink) 55%,transparent);color:var(--ok-ink)}
.sd-chip.off{opacity:.6}
.sd-chip.warn{border-color:color-mix(in srgb,var(--warn-ink) 55%,transparent);color:var(--warn-ink)}
.sd-rows{display:flex;flex-direction:column;gap:6px;flex:1}
.sd-row{display:flex;gap:8px;align-items:flex-start;font-size:12px;line-height:1.35}
.sd-row strong{display:block;font-weight:600}
.sd-row span{color:var(--text2);font-size:11px}
.sd-ri{margin-top:2px;opacity:.75;flex:none;width:14px;height:14px}
.sd-foot{margin-top:auto}
.sd-go{background:none;border:none;color:var(--accent-ink);font-size:12px;cursor:pointer;display:inline-flex;align-items:center;gap:4px;padding:2px 0}
.sd-go:hover{text-decoration:underline}
.sd-empty{font-size:12px;color:var(--text3);font-style:italic}
.sd-bad-src{color:var(--warn-ink)}
.sd-card.c1{--h:var(--sd-1)}.sd-card.c2{--h:var(--sd-2)}.sd-card.c3{--h:var(--sd-3)}.sd-card.c4{--h:var(--sd-4)}
.sd-card.c5{--h:var(--sd-5)}.sd-card.c6{--h:var(--sd-6)}.sd-card.c7{--h:var(--sd-7)}.sd-card.c8{--h:var(--sd-8)}
.sd-node.c1{--h:var(--sd-1)}.sd-node.c2{--h:var(--sd-2)}.sd-node.c3{--h:var(--sd-3)}.sd-node.c4{--h:var(--sd-4)}
.sd-node.c5{--h:var(--sd-5)}.sd-node.c6{--h:var(--sd-6)}.sd-node.c7{--h:var(--sd-7)}.sd-node.c8{--h:var(--sd-8)}
.sd-dept-h{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.sd-filters{display:flex;gap:6px;margin-left:auto}
.sd-f{font:inherit;font-size:11.5px;padding:3px 11px;border-radius:20px;cursor:pointer;border:1px solid var(--line);background:var(--wash);color:var(--text2)}
.sd-f[aria-pressed="true"]{color:var(--accent-ink);border-color:var(--accent);background:color-mix(in srgb,var(--accent) 12%,transparent)}
.sd-sum{display:flex;flex-wrap:wrap;gap:6px}
.sd-khoi{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--card)}
.sd-khoi[hidden]{display:none}
.sd-khoi-h{display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--wash);font-size:12.5px;font-weight:650;cursor:pointer;list-style:none}
.sd-khoi-h::-webkit-details-marker{display:none}
.sd-khoi-h .sd-kt{flex:1}
.sd-khoi-h .sd-kn{font-size:11px;color:var(--text3);font-weight:400}
.sd-prow{display:grid;grid-template-columns:10px minmax(0,1.1fr) minmax(0,1fr) minmax(0,2fr) 100px;align-items:center;gap:10px;width:100%;
  padding:8px 12px;border:0;border-top:1px solid var(--line);background:none;color:var(--text);font:inherit;font-size:12px;cursor:pointer;text-align:left}
.sd-prow[hidden]{display:none}
.sd-prow:hover,.sd-prow:focus-visible{background:var(--wash)}
.sd-pname{font-weight:600}
.sd-pagent{color:var(--text2);font-size:11.5px}
.sd-pstats{color:var(--text2);font-size:11.5px;display:flex;flex-direction:column;gap:4px}
.sd-pstats b{color:var(--text);font-weight:600}
.sd-bar{height:4px;border-radius:3px;background:var(--line);overflow:hidden}
.sd-bar i{display:block;height:100%;background:var(--s);border-radius:3px}
.sd-st{justify-self:end;font-size:10.5px;padding:1px 8px;border-radius:10px;border:1px solid color-mix(in srgb,var(--s) 55%,transparent);color:var(--s);white-space:nowrap}
.sd-prow.good{--s:var(--ok-ink)}.sd-prow.wait{--s:var(--warn-ink)}.sd-prow.risk{--s:var(--danger-ink)}
.sd-prow.empty,.sd-prow.nobrain,.sd-prow.error{--s:var(--text3)}
.sd-prow .sd-dot{background:var(--s)}
@container sd (max-width:819px){
  .sd-prow{grid-template-columns:10px 1fr auto}
  .sd-prow .sd-pagent,.sd-prow .sd-pstats{grid-column:2/-1}
}
/* Tầng nhà máy (factory pipeline) - vòng đời SAU KHI việc xong, lớp OpenAI factory */
.sd-fac{display:flex;flex-direction:column;gap:10px;padding:13px 14px;border-radius:14px;
  background:var(--card);border:1px solid var(--line)}
.sd-fac-h{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.sd-fac-h .sd-t{font-size:14px}
.sd-fac-au{margin-left:auto;display:flex;align-items:baseline;gap:7px}
.sd-fac-au b{font-size:24px;font-weight:750;letter-spacing:-.5px;color:var(--accent-ink)}
.sd-fac-au span{font-size:11.5px;color:var(--text2);max-width:200px;line-height:1.3}
.sd-pipe{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.sd-stage{display:flex;align-items:flex-start;gap:8px;padding:8px 10px;border-radius:10px;
  border:1px solid var(--line);background:var(--wash);position:relative;min-width:0;cursor:pointer}
.sd-stage.on{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 9%,var(--wash))}
.sd-stage .sd-dot{position:absolute;top:8px;right:8px}
.sd-fac-note{border:1px dashed var(--line);border-radius:10px;padding:8px 11px;font-size:11.5px;
  color:var(--text2);line-height:1.45;background:var(--wash)}
.sd-fac-note b{color:var(--text);font-weight:650}
.sd-stage-ic{width:22px;height:22px;border-radius:7px;display:grid;place-items:center;flex:none;
  color:var(--accent-ink);background:color-mix(in srgb,var(--accent) 14%,transparent)}
.sd-stage-in{display:flex;flex-direction:column;gap:1px;min-width:0}
.sd-stage-in b{font-size:11.5px;font-weight:650;line-height:1.2}
.sd-stage-in span{font-size:10.5px;color:var(--text2);line-height:1.3;overflow-wrap:anywhere}
.sd-fac-cap{display:flex;flex-wrap:wrap;gap:5px}
/* Triển khai tự cải tiến */
.sd-dp-list{display:flex;flex-direction:column;gap:8px}
.sd-dp-r{border:1px solid var(--line);border-radius:10px;background:var(--wash);padding:8px 10px;display:flex;flex-direction:column;gap:5px}
.sd-dp-h{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.sd-dp-h b{font-size:12.5px}
.sd-dp-m{font-size:11px;color:var(--text2);line-height:1.4;overflow-wrap:anywhere}
.sd-dp-tg{display:flex;flex-wrap:wrap;gap:6px}
.sd-dp-t{display:inline-flex;align-items:center;gap:5px;font-size:11px;padding:3px 7px;border-radius:8px;border:1px solid var(--line);background:var(--card)}
.sd-dp-act{display:flex;gap:6px;flex-wrap:wrap}
.sd-dp-b{padding:3px 9px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--text);font-size:11px;cursor:pointer}
.sd-dp-b:hover{border-color:var(--accent);color:var(--accent-ink)}
.sd-dp-b[aria-disabled="true"]{opacity:.55;cursor:not-allowed}
.sd-dp-out{margin:0;padding:8px 10px;border:1px dashed var(--line);border-radius:10px;font-size:11px;white-space:pre-wrap;overflow-wrap:anywhere;max-height:240px;overflow:auto;background:var(--wash);color:var(--text2)}
.sd-dp-out.bad{border-color:var(--danger-ink);color:var(--danger-ink)}
/* Chuẩn Joyce Harness: ba cột tầng A/B/C, mỗi dòng một thành phần có đèn */
.sd-hx-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.sd-hx-col{display:flex;flex-direction:column;gap:6px;min-width:0}
.sd-hx-th{display:flex;flex-direction:column;gap:1px;padding:0 2px 2px}
.sd-hx-th b{font-size:12px;font-weight:700}
.sd-hx-th span{font-size:10.5px;color:var(--text3)}
.sd-hx-r{display:flex;align-items:flex-start;gap:8px;padding:8px 26px 8px 10px;border-radius:10px;
  border:1px solid var(--line);background:var(--wash);position:relative;min-width:0}
.sd-hx-r .sd-dot{position:absolute;top:9px;right:9px}
.sd-hx-r.sd-st-off{opacity:.78}
.sd-hx-ic{width:22px;height:22px;border-radius:7px;display:grid;place-items:center;flex:none;
  color:var(--s,var(--accent-ink));background:color-mix(in srgb,var(--s,var(--accent)) 14%,transparent)}
.sd-hx-in{display:flex;flex-direction:column;gap:1px;min-width:0}
.sd-hx-in b{font-size:11.5px;font-weight:650;line-height:1.2}
.sd-hx-in span{font-size:10.5px;color:var(--text2);line-height:1.3;overflow-wrap:anywhere}
@container sd (max-width:819px){.sd-hx-grid{grid-template-columns:minmax(0,1fr)}}
/* Bảng agent hiệu quả */
.sd-ag{display:flex;flex-direction:column;gap:0;border:1px solid var(--line);border-radius:12px;
  overflow:hidden;background:var(--card)}
.sd-ag-h{display:grid;grid-template-columns:10px minmax(0,1.4fr) minmax(0,1.6fr) 110px 60px;
  gap:10px;padding:7px 12px;background:var(--wash);font-size:10.5px;font-weight:700;
  letter-spacing:.5px;text-transform:uppercase;color:var(--text3)}
.sd-ag-r{display:grid;grid-template-columns:10px minmax(0,1.4fr) minmax(0,1.6fr) 110px 60px;
  gap:10px;align-items:center;padding:8px 12px;border-top:1px solid var(--line);font-size:12px}
.sd-ag-r .sd-dot{background:var(--s)}
.sd-ag-name{font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sd-ag-role{color:var(--text2);font-size:11px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sd-ag-stats{color:var(--text2);font-size:11.5px}
.sd-ag-stats b{color:var(--text);font-weight:600}
.sd-ag-bar{height:4px;border-radius:3px;background:var(--line);overflow:hidden}
.sd-ag-bar i{display:block;height:100%;background:var(--s);border-radius:3px}
.sd-ag-score{font-size:11.5px;font-weight:650;color:var(--s);text-align:right}
.sd-ag-r.good{--s:var(--ok-ink)}.sd-ag-r.wait{--s:var(--warn-ink)}.sd-ag-r.risk{--s:var(--danger-ink)}
.sd-ag-r.idle{--s:var(--text3)}
@container sd (max-width:819px){
  .sd-ag-h{display:none}
  .sd-ag-r{grid-template-columns:10px 1fr auto}
  .sd-ag-role,.sd-ag-stats{grid-column:2/-1}
  .sd-fac-au{margin-left:0}
}
@media (prefers-reduced-motion:reduce){.sd-arr::after,.sd-refresh.spin svg,.sd-card.sd-flash{animation:none}.sd-node:hover{transform:none}}
`;
    document.head.appendChild(st);
  }

  const chip = (txt, cls) => `<span class="sd-chip ${cls || ""}">${esc(txt)}</span>`;
  const row = (icon, title, meta) =>
    `<div class="sd-row">${ic(icon, { cls: "sd-ri" })}<div><strong>${esc(title)}</strong>${meta ? `<span>${esc(meta)}</span>` : ""}</div></div>`;

  function card(b, st, kpiN, chipsHtml, rowsHtml, down) {
    const cls = "c" + b.n;
    const stTxt = t(down ? "sodo.s.err" : STATE_KEY[st]);
    const dnChip = down ? chip(t("sodo.down"), "warn") : "";
    return `<section class="sd-card ${cls}" id="sd-c${b.n}">
      <div class="sd-h"><span class="sd-ico">${ic(b.ic)}</span><span class="sd-num">${String(b.n).padStart(2, "0")}</span>
        <span class="sd-t">${esc(t(b.t))}</span><span class="sd-dot sd-st-${down ? "warn" : st}" title="${esc(stTxt)}" role="img" aria-label="${esc(stTxt)}"></span></div>
      <div class="sd-sub">${esc(t(b.d))}</div>
      <div class="sd-kpi"><b>${esc(kpiN)}</b><span>${esc(t(b.kpi))}</span></div>
      ${(dnChip + chipsHtml) ? `<div class="sd-chips">${dnChip}${chipsHtml}</div>` : ""}
      <div class="sd-rows">${rowsHtml || `<div class="sd-empty">${esc(t("sodo.empty"))}</div>`}</div>
      <div class="sd-foot"><button type="button" class="sd-go" data-go="${esc(b.go)}">${esc(t(OPEN_GO[b.go] || "sodo.open.kanban"))} ${ic("chevron-right")}</button></div>
    </section>`;
  }

  // Tầng nhà máy Joyce (OpenAI agentic factory): vòng đời SAU KHI việc xong -
  // CI babysit, risk gate, watcher handhold, Perf/Sevbot, PPC proposal, eval,
  // canary, tự áp, pacing. Mỗi ô là số thật từ /work/factory; ô nào có vấn đề
  // (CI đỏ, eval rớt, canary rollback) chuyển đèn vàng để chủ thấy ngay.
  function facSection(fc) {
    if (!fc) return "";
    const sg = fc.stages || {}, au = fc.autonomy || {};
    const w = sg.watch || {}, cn = sg.canary || {}, pp = sg.proposals || {};
    const vd = sg.verdicts || {};
    const cp = sg.capacity || {};
    const ratio = au.ratio;
    const auTxt = ratio == null ? t("sodo.fac.nodata") : Math.round(ratio * 100) + "%";
    const cnTxt = Object.keys(cn).length
      ? Object.entries(cn).map(([k2, v]) => `${v} ${k2}`).join(" · ")
      : t("sodo.fac.none");
    const ST = [
      { ic: "hammer", k: "sodo.fac.ci", m: `${so(sg.ci_open || 0)} ${t("sodo.fac.pending")}`,
        s: (sg.ci_open || 0) ? "warn" : "ok" },
      { ic: "shield-check", k: "sodo.fac.risk",
        m: `${t("sodo.fac.auto")} ${so(sg.auto_approved || 0)} · ${t("sodo.fac.high")} ${so(sg.escalated || 0)}`, s: "ok" },
      { ic: "eye", k: "sodo.fac.watch",
        m: `${so(w.watching || 0)} ${t("sodo.fac.watching")} · ${so(w.failed || 0)} ${t("sodo.fac.failed")}`,
        s: (w.failed || 0) ? "warn" : "ok" },
      { ic: "activity", k: "sodo.fac.perf",
        m: `${so(sg.perf_cooldowns || 0)} pattern · sev ${so(sg.sev_sent || 0)}`, s: "ok" },
      { ic: "file-diff", k: "sodo.fac.ppc",
        m: `${so(pp.pending || 0)} ${t("sodo.fac.pending")} · ${so(pp.eval_failed || 0)} ${t("sodo.fac.evalfail")} · WIN ${so(vd.win || 0)}/KEEP ${so(vd.keep || 0)}`,
        s: (pp.eval_failed || 0) ? "warn" : "ok" },
      { ic: "flask-conical", k: "sodo.fac.eval",
        m: `${so(sg.evals || 0)} ${t("sodo.fac.evalset")}`, s: (sg.evals || 0) ? "ok" : "off" },
      { ic: "bird", k: "sodo.fac.canary", m: cnTxt,
        s: (cn.reverted || 0) ? "warn" : "ok" },
      { ic: "wand-2", k: "sodo.fac.self",
        m: `${so(pp.applied || 0)} ${t("sodo.fac.applied")}`, s: "ok" },
      { ic: "timer", k: "sodo.fac.pace",
        m: `${so(sg.pacing_deferred || 0)} ${t("sodo.fac.deferred")} · ckpt ${so(sg.checkpoints || 0)}`, s: "ok" },
    ];
    const cells = ST.map(x => `<div class="sd-stage${x.k === ui.facNote ? " on" : ""}" data-note="${esc(x.k)}" title="${esc(t(x.k + ".d"))}"><span class="sd-stage-ic">${ic(x.ic)}</span>
      <span class="sd-stage-in"><b>${esc(t(x.k))}</b><span>${esc(x.m)}</span></span>
      <span class="sd-dot sd-st-${x.s}"></span></div>`).join("");
    const noteHtml = `<div class="sd-fac-note">${ui.facNote
      ? `<b>${esc(t(ui.facNote))}</b>: ${esc(t(ui.facNote + ".d"))}`
      : esc(t("sodo.fac.hint"))}</div>`;
    const caps = [
      chip(t("sodo.fac.cap_done", { n: so(cp.done_24h || 0) }), "on"),
      chip(t("sodo.fac.cap_blocked", { n: so(cp.blocked || 0), p: cp.blocked_pct || 0 }),
           (cp.blocked_pct || 0) >= 30 ? "warn" : ""),
      chip(t("sodo.fac.cap_active", { n: so(cp.active || 0) })),
      chip(t("sodo.fac.cap_art", { n: so(sg.artifacts || 0) })),
    ].join("");
    return `<section class="sd-fac">
      <div class="sd-fac-h"><span class="sd-t">${esc(t("sodo.fac.title"))}</span>
        <span class="sd-sub">${esc(t("sodo.fac.sub"))}</span>
        <div class="sd-fac-au"${ratio == null ? ` title="${esc(t("sodo.fac.nodata_d"))}"` : ""}><b>${esc(auTxt)}</b><span>${esc(t("sodo.fac.autonomy", { d: au.days || 30 }))}</span></div></div>
      <div class="sd-pipe">${cells}</div>
      ${noteHtml}
      <div class="sd-fac-cap">${caps}</div>
    </section>`;
  }

  // Triển khai tự cải tiến (A06, 1.3.42): chủ nhìn được MỖI canary đang ở đâu, nguồn đang chạy bản nào, từng đích ra sao, và quyết
  // định được: xem diff, khôi phục từng đích, đã đọc, tạm dừng. Mọi thao tác gọi /work/factory/action; server mới là nơi kiểm quyền
  // và phiên bản, nút ẩn hay khoá chỉ là gợi ý. Trạng thái "chưa đủ dữ liệu" KHÔNG bao giờ hiện xanh.
  const DP_STATE = { canary: "info", legacy_review: "warn", promoted: "ok", reverted: "warn", superseded: "off", het_han: "warn",
                     partial: "warn", conflict: "warn" };
  const DP_STATE_KEY = { canary: "sodo.dp.s.canary", legacy_review: "sodo.dp.s.legacy_review", promoted: "sodo.dp.s.promoted",
                         reverted: "sodo.dp.s.reverted", superseded: "sodo.dp.s.superseded", het_han: "sodo.dp.s.het_han",
                         partial: "sodo.dp.s.partial", conflict: "sodo.dp.s.conflict" };
  const DP_TG_KEY = { pending: "sodo.dp.t.pending", promoted: "sodo.dp.t.promoted", already: "sodo.dp.t.already", conflict: "sodo.dp.t.conflict",
                      override: "sodo.dp.t.override", missing: "sodo.dp.t.missing", error: "sodo.dp.t.error", restored: "sodo.dp.t.restored" };
  const DP_SRC_KEY = { ban_moi: "sodo.dp.src.ban_moi", da_khoi_phuc: "sodo.dp.src.da_khoi_phuc", khong_chac: "sodo.dp.src.khong_chac" };
  const dpId = () => (window.crypto && window.crypto.randomUUID ? window.crypto.randomUUID() : "a-" + Date.now() + "-" + Math.random().toString(16).slice(2));

  function dpSection(fc) {
    const dp = fc && fc.deployments;
    if (!dp || !Array.isArray(dp.canaries)) return "";
    const ban = dp.canaries.slice().reverse().slice(0, 8);
    const banner = (dp.tam_dung ? `<div class="sd-fac-note">${esc(t("sodo.dp.paused"))}</div>` : "")
      + (dp.telemetry_ready ? "" : `<div class="sd-fac-note">${esc(t("sodo.dp.no_telemetry"))}</div>`);
    const rows = ban.map(c => {
      const st = DP_STATE[c.state] || "off";
      const ev = c.evidence && c.evidence.tasks != null ? t("sodo.dp.evidence", { n: so(c.evidence.tasks), m: so(c.min_tasks || 0) }) : "";
      const tg = (c.dich || []).map(x => {
        const ts = x.state === "promoted" || x.state === "already" || x.state === "restored" ? "ok" : (x.state === "pending" ? "off" : "warn");
        const nut = x.co_the_khoi_phuc
          ? ` <button type="button" class="sd-dp-b" data-dp="diff" data-c="${esc(c.id)}" data-t="${esc(x.target_id)}">${esc(t("sodo.dp.btn.diff"))}</button>`
            + ` <button type="button" class="sd-dp-b" data-dp="restore" data-c="${esc(c.id)}" data-t="${esc(x.target_id)}" data-rev="${esc(c.revision)}">${esc(t("sodo.dp.btn.restore"))}</button>` : "";
        return `<span class="sd-dp-t sd-st-${ts}"><i class="sd-dot sd-st-${ts}"></i>${esc(x.brain)}: ${esc(t(DP_TG_KEY[x.state] || "sodo.dp.t.pending"))}${nut}</span>`;
      }).join("");
      const can = ["canary", "legacy_review", "partial", "conflict", "het_han"].includes(c.state);
      const thieu = (c.thieu || []).slice(0, 4);
      const nutNguon = c.nguon_co_the_khoi_phuc && c.nguon_chay !== "da_khoi_phuc"
        ? `<button type="button" class="sd-dp-b" data-dp="restore" data-c="${esc(c.id)}" data-t="nguon" data-rev="${esc(c.revision)}">${esc(t("sodo.dp.btn.restore_src"))}</button>` : "";
      const ack = can && !c.acknowledged ? `<button type="button" class="sd-dp-b" data-dp="ack" data-c="${esc(c.id)}" data-rev="${esc(c.revision)}">${esc(t("sodo.dp.btn.ack"))}</button>` : "";
      const nhan = can ? `<button type="button" class="sd-dp-b" data-dp="promote" data-c="${esc(c.id)}" data-rev="${esc(c.revision)}" ${thieu.length ? "aria-disabled=\"true\" title=\"" + esc(thieu.join(" · ")) + "\"" : ""}>${esc(t("sodo.dp.btn.promote"))}</button>` : "";
      return `<div class="sd-dp-r sd-st-${st}"><div class="sd-dp-h"><span class="sd-dot sd-st-${st}" role="img" aria-label="${esc(t(DP_STATE_KEY[c.state] || "sodo.dp.s.canary"))}"></span>
          <b>${esc(c.file)}</b><span class="sd-dp-m">${esc(c.brain)} · ${esc(t(DP_STATE_KEY[c.state] || "sodo.dp.s.canary"))} · ${esc(t(DP_SRC_KEY[c.nguon_chay] || "sodo.dp.src.khong_chac"))} · ${esc(c.ung_vien)}</span></div>
        ${ev ? `<div class="sd-dp-m">${esc(ev)}</div>` : ""}${c.ly_do ? `<div class="sd-dp-m">${esc(c.ly_do)}</div>` : ""}
        ${thieu.length ? `<div class="sd-dp-m">${esc(t("sodo.dp.missing"))}: ${esc(thieu.join("; "))}</div>` : ""}
        <div class="sd-dp-tg">${tg}</div><div class="sd-dp-act">${nutNguon}${ack}${nhan}</div></div>`;
    }).join("");
    return `<section class="sd-fac sd-dp"><div class="sd-fac-h"><span class="sd-t">${esc(t("sodo.dp.title"))}</span><span class="sd-sub">${esc(t("sodo.dp.sub"))}</span>
        <button type="button" class="sd-dp-b" style="margin-left:auto" data-dp="pause" data-on="${dp.tam_dung ? "0" : "1"}">${esc(t(dp.tam_dung ? "sodo.dp.btn.resume" : "sodo.dp.btn.pause"))}</button></div>
      ${banner}<div class="sd-dp-list">${rows || `<div class="sd-empty">${esc(t("sodo.dp.none"))}</div>`}</div>
      <pre class="sd-dp-out" id="sdDpOut" hidden></pre></section>`;
  }

  async function dpAct(d) {
    const out = (typeof document !== "undefined" && document.getElementById) ? document.getElementById("sdDpOut") : null;
    const noi = (txt, loi) => { if (out) { out.hidden = false; out.textContent = txt; out.className = "sd-dp-out" + (loi ? " bad" : ""); } return txt; };
    if (d.dp === "diff") {
      const r = await fetch(`/work/factory/diff?canary_id=${encodeURIComponent(d.c)}&target_id=${encodeURIComponent(d.t)}`);
      let j = {}; try { j = await r.json(); } catch (e) {}
      return noi(r.ok ? (j.diff || t("sodo.dp.diff_same")) : (j.error || t("sodo.dp.err")), !r.ok);
    }
    if (d.dp === "restore" && !window.confirm(t("sodo.dp.confirm_restore"))) return "";
    if (d.dp === "promote" && !window.confirm(t("sodo.dp.confirm_promote"))) return "";
    const ly = d.dp === "pause" ? t("sodo.dp.reason_default") : (window.prompt(t("sodo.dp.reason"), t("sodo.dp.reason_default")) || "");
    if (!ly.trim()) return "";
    const body = new URLSearchParams({ action: d.dp, canary_id: d.c || "", target_id: d.t || "", expected_revision: d.rev || "", action_id: dpId(), reason: ly,
                                       on: d.dp === "pause" ? (d.on === "1" ? "1" : "0") : "" });
    const r = await fetch("/work/factory/action", { method: "POST", body });
    let j = {}; try { j = await r.json(); } catch (e) {}
    const msg = r.ok ? t("sodo.dp.done") : (j.dieu_kien_thieu ? t("sodo.dp.not_ready") + ": " + j.dieu_kien_thieu.join("; ") : (j.stale ? t("sodo.dp.stale") : (j.error || t("sodo.dp.err"))));
    noi(msg, !r.ok);
    if (r.ok && ui.el) setTimeout(() => render(ui.el, true), 400);
    return msg;
  }

  // Chuẩn Joyce Harness (1.3.39, docs/dev/Joyce-harness.md): ba tầng A lõi chạy, B bề mặt phòng
  // ban, C vòng cải tiến. Mỗi thành phần một đèn lấy từ /work/factory -> harness (server
  // harness_map.py). Thứ chưa làm thì đèn xám và mô tả nói thẳng là chưa làm.
  const HX_TIER = { A: ["sodo.hx.tA", "sodo.hx.tA.d"], B: ["sodo.hx.tB", "sodo.hx.tB.d"], C: ["sodo.hx.tC", "sodo.hx.tC.d"] };
  const HX = {
    cache: ["sodo.hx.cache", "sodo.hx.cache.m", "sodo.hx.cache.d", "zap"],
    guard: ["sodo.hx.guard", "sodo.hx.guard.m", "sodo.hx.guard.d", "shield"],
    trim: ["sodo.hx.trim", "sodo.hx.trim.m", "sodo.hx.trim.d", "minimize"],
    perm: ["sodo.hx.perm", "sodo.hx.perm.m", "sodo.hx.perm.d", "lock"],
    brake: ["sodo.hx.brake", "sodo.hx.brake.m", "sodo.hx.brake.d", "circle-stop"],
    agents: ["sodo.hx.agents", "sodo.hx.agents.m", "sodo.hx.agents.d", "users"],
    shared: ["sodo.hx.shared", "sodo.hx.shared.m", "sodo.hx.shared.d", "layers"],
    evals: ["sodo.hx.evals", "sodo.hx.evals.m", "sodo.hx.evals.d", "list-checks"],
    scope: ["sodo.hx.scope", "sodo.hx.scope.m", "sodo.hx.scope.d", "key"],
    self: ["sodo.hx.self", "sodo.hx.self.m", "sodo.hx.self.d", "sparkles"],
    judge: ["sodo.hx.judge", "sodo.hx.judge.m", "sodo.hx.judge.d", "eye"],
    gate: ["sodo.hx.gate", "sodo.hx.gate.m", "sodo.hx.gate.d", "shield-alert"],
    week: ["sodo.hx.week", "sodo.hx.week.m", "sodo.hx.week.d", "activity"],
    writer: ["sodo.hx.writer", "sodo.hx.writer.m", "sodo.hx.writer.d", "hard-drive"],
    runs: ["sodo.hx.runs", "sodo.hx.runs.m", "sodo.hx.runs.d", "route"],
    canary: ["sodo.hx.canary", "sodo.hx.canary.m", "sodo.hx.canary.d", "undo-2"],
    telemetry: ["sodo.hx.telemetry", ["sodo.hx.telemetry.m", "sodo.hx.telemetry.m_ok"], "sodo.hx.telemetry.d", "history"],
    budget: ["sodo.hx.budget", "sodo.hx.budget.m", "sodo.hx.budget.d", "hourglass"],
  };
  function hxSection(fc) {
    const hx = fc && fc.harness;
    if (!hx || !Array.isArray(hx.tiers)) return "";
    const fmt = (v) => { const o = {}; for (const k in (v || {})) o[k] = typeof v[k] === "number" ? so(v[k]) : v[k]; return o; };
    const cols = hx.tiers.map(tr => {
      const tk = HX_TIER[tr.id];
      if (!tk) return "";
      const rows = (tr.items || []).map(x => {
        const m = HX[x.k];
        if (!m) return "";
        const st = STATE_KEY[x.state] ? x.state : "off";
        return `<div class="sd-hx-r sd-st-${st}" title="${esc(t(m[2]))}"><span class="sd-hx-ic">${ic(m[3])}</span>
          <span class="sd-hx-in"><b>${esc(t(m[0]))}</b><span>${esc(t(Array.isArray(m[1]) ? m[1][x.state === "ok" ? 1 : 0] : m[1], fmt(x.v)))}</span></span>
          <span class="sd-dot sd-st-${st}" role="img" aria-label="${esc(t(STATE_KEY[st]))}"></span></div>`;
      }).join("");
      return `<div class="sd-hx-col"><div class="sd-hx-th"><b>${esc(t(tk[0]))}</b><span>${esc(t(tk[1]))}</span></div>${rows}</div>`;
    }).join("");
    const phases = (hx.phases || []).map(p => chip(t("sodo.hx.phase", { k: p.k }), p.state === "ok" ? "on" : p.state === "warn" ? "warn" : "")).join("");
    return `<section class="sd-fac sd-hx">
      <div class="sd-fac-h"><span class="sd-t">${esc(t("sodo.hx.title"))}</span>
        <span class="sd-sub">${esc(t("sodo.hx.sub"))}</span>
        <div class="sd-fac-au"><b>${esc(so(hx.ok))}/${esc(so(hx.total))}</b><span>${esc(t("sodo.hx.score", { v: hx.version || "" }))}</span></div></div>
      <div class="sd-hx-grid">${cols}</div>
      <div class="sd-fac-cap">${phases}</div>
      <div class="sd-fac-note">${esc(t("sodo.hx.hint"))}</div>
    </section>`;
  }

  // Bảng agent hiệu quả: agent nào được giao việc và xong tốt, ai chỉ đứng ngoài,
  // ai có proposal WIN (PPC chứng minh nó tốt hơn sau cải tiến). Đây là chỗ chủ nhìn
  // "agent nào đang hiệu quả / cần cải tiến" mà không phải mở từng brain.
  function agentBoard(fc) {
    if (!fc) return "";
    const rows = (fc.agents || []);
    if (!rows.length) return `<div class="sd-empty">${esc(t("sodo.ag.none"))}</div>`;
    const show = rows.slice(0, 8);
    const more = rows.length - show.length;
    const trs = show.map(r => {
      const cls = (r.blocked || 0) > 0 ? "risk" : (r.running || 0) > 0 ? "good"
        : (r.done || 0) > 0 ? "good" : "idle";
      const stat = `<b>${so(r.done || 0)}</b> ${esc(t("sodo.ag.done"))} · <b>${so(r.blocked || 0)}</b> ${esc(t("sodo.ag.blocked"))}` +
        (r.running ? ` · <b>${so(r.running)}</b> ${esc(t("sodo.ag.running"))}` : "") +
        (r.wins ? ` · <b>${so(r.wins)}</b> PPC` : "");
      const pct = r.score == null ? 0 : r.score;
      const scoreTxt = r.score == null ? "-" : pct + "%";
      return `<div class="sd-ag-r ${cls}"><span class="sd-dot"></span>
        <span class="sd-ag-name" title="${esc(r.slug)}">${esc(r.name || r.slug)}</span>
        <span class="sd-ag-role" title="${esc(r.role)}">${esc(r.role || "-")}</span>
        <span class="sd-ag-stats">${stat}</span>
        <span class="sd-ag-score">${esc(scoreTxt)}<span class="sd-ag-bar"><i style="width:${pct}%"></i></span></span></div>`;
    }).join("");
    const moreRow = more > 0 ? `<div class="sd-ag-r idle"><span></span><span class="sd-ag-name">+${more}</span><span></span><span></span><span></span></div>` : "";
    // Bảng toàn số 0 = chưa ai được giao việc riêng: kèm đề xuất hành động thay vì
    // chỉ trưng một bảng trống (đúng tinh thần "chưa có dữ liệu thì phải nói làm gì tiếp").
    const allIdle = rows.every(r => !(r.done || r.blocked || r.running || r.open || r.wins));
    const hint = allIdle ? `<div class="sd-fac-note">${esc(t("sodo.ag.hint"))}</div>` : "";
    return `<div class="sd-dept"><div class="sd-dept-h"><div class="sd-sect">${esc(t("sodo.ag.title"))}</div></div>
      <div class="sd-ag"><div class="sd-ag-h"><span></span><span>${esc(t("sodo.ag.col_name"))}</span>
        <span>${esc(t("sodo.ag.col_role"))}</span><span>${esc(t("sodo.ag.col_stats"))}</span>
        <span>${esc(t("sodo.ag.col_score"))}</span></div>${trs}${moreRow}</div>${hint}</div>`;
  }

  // Tầng hiệu suất: mỗi phòng = một brain có board kanban riêng; trạng thái suy từ việc
  // THẬT (kẹt/chờ duyệt/chạy tốt) do server tính - trang này chỉ vẽ lại đúng con số đó.
  function deptSection(dp) {
    if (!dp) return "";
    if (dp.error === "staff_denied" || dp.ok === false)
      return `<div class="sd-empty">${esc(t("sodo.dept_denied"))}</div>`;
    const phong = dp.phong || [], khois = dp.khois || [];
    if (!phong.length) return `<div class="sd-empty">${esc(t("sodo.dept_none"))}</div>`;
    const stt = { good: 0, wait: 0, risk: 0 };
    phong.forEach(p => { if (stt[p.status] != null) stt[p.status]++; });
    const sum = chip(t("sodo.dept_n", { n: phong.length }), "on") +
      chip(t("ov.st_good") + " " + stt.good, "on") + chip(t("ov.st_wait") + " " + stt.wait, "warn") +
      chip(t("ov.st_risk") + " " + stt.risk, stt.risk ? "warn" : "off");
    const byKhoi = {};
    phong.forEach(p => { (byKhoi[p.khoi_id || "_"] = byKhoi[p.khoi_id || "_"] || []).push(p); });
    const khoiTen = Object.fromEntries(khois.map(k => [k.id, k.ten]));
    const groups = Object.keys(byKhoi).map(kid => {
      const list = byKhoi[kid].slice().sort((a, z) => (ST_ORDER[a.status] ?? 9) - (ST_ORDER[z.status] ?? 9));
      const rows = list.map(p => {
        const c = p.tasks || {};
        const stats = `<b>${so(c.done24)}</b> ${esc(t("sodo.d24"))} · <b>${so(c.open)}</b> ${esc(t("sodo.mo"))}` +
          (c.blocked ? ` · <b>${so(c.blocked)}</b> ${esc(t("sodo.ket"))}` : "") +
          (c.running ? ` · <b>${so(c.running)}</b> ${esc(t("sodo.dangchay"))}` : "");
        const meta2 = [p.nhan_vien ? so(p.nhan_vien) + " NV" : "", p.nguon ? so(p.nguon) + " " + t("sodo.nguon") : ""]
          .filter(Boolean).join(" · ");
        const tot = (c.done24 || 0) + (c.open || 0) + (c.blocked || 0);
        const pct = tot ? Math.round(((c.done24 || 0) / tot) * 100) : 0;
        const attn = p.status === "wait" || p.status === "risk";
        const stCls = esc(p.status || "empty");
        return `<button type="button" class="sd-prow ${stCls}" data-go="departments" data-attn="${attn ? 1 : 0}">
          <span class="sd-dot"></span>
          <span class="sd-pname">${esc(p.ten)}</span>
          <span class="sd-pagent">${esc(p.agent || "-")}</span>
          <span class="sd-pstats"><span>${stats}${meta2 ? " · " + esc(meta2) : ""}</span>
            ${tot ? `<span class="sd-bar" title="${pct}%"><i style="width:${pct}%"></i></span>` : ""}</span>
          <span class="sd-st">${esc(t(ST_TXT[p.status] || "ov.st_empty"))}</span>
        </button>`;
      }).join("");
      const nAttn = byKhoi[kid].filter(p => p.status === "wait" || p.status === "risk").length;
      return `<details class="sd-khoi" open data-attn="${nAttn}"><summary class="sd-khoi-h"><span class="sd-kt">${esc(khoiTen[kid] || kid)}</span>
        <span class="sd-kn">${byKhoi[kid].length} ${esc(t("sodo.phong"))}</span></summary>${rows}</details>`;
    }).join("");
    const f = (k, key) => `<button type="button" class="sd-f" data-f="${k}" aria-pressed="${ui.filter === k ? "true" : "false"}">${esc(t(key))}</button>`;
    return `<div class="sd-dept" data-filter="${esc(ui.filter)}">
      <div class="sd-dept-h"><div class="sd-sect">${esc(t("sodo.dept_title"))}</div>
        <div class="sd-filters">${f("all", "sodo.f.all")}${f("attn", "sodo.f.attn")}</div></div>
      <div class="sd-sum">${sum}</div>${groups}</div>`;
  }

  // Lọc phòng ban theo "cần chú ý": ẩn dòng/khối không khớp, không dựng lại cả trang.
  function applyFilter(el) {
    if (!el.querySelectorAll) return;
    const only = ui.filter === "attn";
    el.querySelectorAll(".sd-prow").forEach(r => { r.hidden = only && r.dataset.attn !== "1"; });
    el.querySelectorAll(".sd-khoi").forEach(k => { k.hidden = only && k.dataset.attn === "0"; });
    el.querySelectorAll(".sd-f").forEach(b => b.setAttribute("aria-pressed", b.dataset.f === ui.filter ? "true" : "false"));
  }

  function jump(el, n) {
    const target = el.querySelector && el.querySelector("#sd-c" + n);
    if (!target) return;
    try { target.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (e) {}
    target.classList.remove("sd-flash"); void target.offsetWidth; target.classList.add("sd-flash");
  }

  async function render(el, silent) {
    injectCss();
    if (timer) { clearInterval(timer); timer = null; }
    if (!silent) el.innerHTML = `<div class="sd-root"><div class="sd-empty">${esc(t("common.loading") || "...")}</div></div>`;
    const b = encodeURIComponent(brain());
    const down = [];
    const J = (name, p) => p.catch(() => { down.push(name); return null; });   // một nguồn chết không làm sập cả trang
    const [st, ag, sk, wf, lp, kb, mcp, pl, tr, mem, ov, dp, fc] = await Promise.all([
      J("settings", api("/settings")), J("agents", api(`/agents?brain=${b}&prompt=0`)), J("skills", api(`/skills?brain=${b}`)),
      J("workflows", api(`/workflows?brain=${b}`)), J("loops", api(`/loops?brain=${b}`)), J("kanban", api(`/kanban?brain=${b}`)),
      J("mcp", api("/mcp/list")), J("plugins", api(`/plugins?brain=${b}`)), J("tools", api(`/tools/registry?brain=${b}`)),
      J("memory", api(`/memory/stats?brain=${b}`)), J("overview", api(`/api/joyce/v1/overview?brain=${b}`)),
      api("/api/joyce/v1/overview/departments").catch(() => null),   // nhân viên thường bị 403: không phải lỗi, chỉ ẩn tầng này
      J("factory", api(`/work/factory?brain=${b}`)),                 // lớp nhà máy: pipeline + agent hiệu quả
    ]);
    const isDown = (...names) => names.some(n => down.includes(n));

    // ---- 01 Models: model chính + các engine đã nối
    let mChips = "", mRows = "", mainTxt = "", nConn = 0, nProv = 0;
    if (st && st.model) {
      const main = st.model.main || {};
      mainTxt = [main.provider, main.model].filter(Boolean).join(" · ");
      mRows += row("cpu", mainTxt || t("sodo.no_model"), t("sodo.main_model"));
      let prov = st.model.providers || [];
      if (!Array.isArray(prov)) prov = Object.values(prov);
      nProv = prov.length; nConn = prov.filter(p => p.configured).length;
      mChips = prov.map(p => chip((p.label || p.id || "?") + (p.is_main ? " ★" : ""), p.configured ? "on" : "off")).join("");
      mRows += row("plug", t("sodo.n_engine", { n: nProv }), nConn + " " + t("sodo.connected"));
    }
    const s1 = !st ? "off" : (!mainTxt || !nConn) ? "bad" : "ok";

    // ---- 02 Context: não brain này đang giữ gì
    const mem2 = (ov && ov.memory) || {};
    const facts = (mem && mem.facts) || mem2.facts || 0;
    const cChips = chip(t("sodo.facts", { n: so(facts) }), "on") +
      chip(t("sodo.wiki_n", { n: so(mem2.wiki) })) + chip(t("sodo.sources_n", { n: so(mem2.sources) }));
    const cRows = row("database", t("sodo.ctx_brain", { b: brain() }), "MEMORY.md + wiki + sources + learn-log");
    const s2 = (facts + (mem2.wiki || 0) + (mem2.sources || 0)) > 0 ? "ok" : "off";

    // ---- 03 Tools
    const tools = (tr && tr.tools) || [];
    const servers = (mcp && mcp.servers) || [];
    const plugins = (pl && pl.plugins) || [];
    const plOn = plugins.filter(p => p.enabled || p.loaded || p.state === "loaded").length;
    const tRows = row("wrench", t("sodo.tools_see", { n: tools.length }), t("sodo.tools_see_d")) +
      row("plug", t("sodo.mcp_n", { n: servers.length }), servers.slice(0, 4).map(s => s.name || s.id).join(" · ")) +
      row("puzzle", t("sodo.plugin_n", { on: plOn, n: plugins.length }), plugins.slice(0, 4).map(p => p.slug || p.name).join(" · "));
    const tChips = chip(t("sodo.mcp_n", { n: servers.length }), servers.length ? "on" : "") +
      chip(t("sodo.plugin_chip", { n: plOn }), plOn ? "on" : "");
    const s3 = !tools.length ? "bad" : servers.length ? "ok" : "warn";

    // ---- 04 Agents
    const agents = (ag && ag.agents) || [];
    const aChips = chip(t("sodo.n_ag", { n: agents.length }), agents.length ? "on" : "");
    const aRows = agents.slice(0, 6).map(a => row("user", a.name || a.slug, a.role || a.group || "")).join("") +
      (agents.length > 6 ? row("ellipsis", "+" + (agents.length - 6), "") : "");
    const s4 = agents.length ? "ok" : "warn";

    // ---- 05 Multi-agent
    const wfs = (wf && wf.workflows) || [];
    const wfOn = wfs.filter(w => w.status === "active");
    const orch = (kb && kb.orchestration) || "";
    const orchCls = orch === "auto" ? "on" : orch === "manual" ? "warn" : "off";
    const ops = (kb && kb.operations) || {};
    const m5 = chip(t("sodo.wf_on", { on: wfOn.length, n: wfs.length }), wfOn.length ? "on" : "") +
      chip(t(BOARD_KEY[orch] || "sodo.board.off"), orchCls);
    const m5r = wfOn.slice(0, 4).map(w => row("git-branch", w.name || w.slug, (w.steps || []).length + " " + t("sodo.steps"))).join("") +
      row("square-kanban", t("sodo.q_counts", { q: (ops.queue || []).length, r: (ops.active || []).length, a: (ops.attention || []).length }),
        t("sodo.done_24h", { n: (kb && kb.completed_24h) || 0 }));
    const s5 = orch === "auto" ? "ok" : "warn";   // thủ công hay tắt đều là "việc không tự chạy"

    // ---- 06 Harness: vòng tự cải tiến
    const hz = (ov && ov.harness) || {};
    const loops = (lp && lp.loops) || [];
    const dinhDuong = loops.find(l => l.slug === "dinh-duong-bai-hoc");
    const hChips = chip(t("sodo.lessons", { n: so(hz.lessons_total) }), hz.lessons_total ? "on" : "") +
      chip(t("sodo.pending_n", { n: so(hz.pending_n) }), hz.pending_n ? "warn" : "") +
      chip(t("sodo.applied", { n: so(hz.applied_n) }));
    const hRows = row("repeat", t("sodo.loop_dd"), dinhDuong ? (dinhDuong.enabled ? t("sodo.st_on") : t("sodo.st_off")) : t("sodo.st_none")) +
      row("sparkles", t("sodo.ppc"), dinhDuong ? "" : t("sodo.ppc_missing")) +
      (hz.last_run ? row("calendar", t("sodo.last_run", { d: hz.last_run }), "") : "");
    const s6 = dinhDuong && dinhDuong.enabled ? "ok" : "warn";

    // ---- 07 Evals: giám định + verdict
    const skl = (sk && sk.skills) || [];
    const hasJudge = agents.some(a => a.slug === "giam-dinh-harness");
    const hasScore = skl.some(s => s.slug === "cham-diem-tuong-phan");
    const verdicts = { win: 0, keep: 0, inconclusive: 0 };
    (hz.pending || []).forEach(p => { if (verdicts[p.verdict] != null) verdicts[p.verdict]++; });
    const eChips = chip(t("sodo.verdict.win") + " " + verdicts.win, "on") +
      chip(t("sodo.verdict.keep") + " " + verdicts.keep) +
      chip(t("sodo.verdict.inc") + " " + verdicts.inconclusive);
    const eRows = row("eye", t("sodo.judge_agent"), hasJudge ? t("sodo.st_ready") : t("sodo.st_none")) +
      row("clipboard-check", t("sodo.score_skill"), hasScore ? t("sodo.st_ready") : t("sodo.st_none")) +
      (hz.pending || []).slice(0, 3).map(p => row("git-branch", p.target || p.file, t(VERDICT_KEY[p.verdict] || "sodo.verdict.none"))).join("");
    const s7 = hasJudge && hasScore ? "ok" : (hasJudge || hasScore) ? "warn" : "off";

    // ---- 08 Ops
    const lpOn = loops.filter(l => l.enabled);
    const nextRun = lpOn.filter(l => l.next_run).sort((a, z) => a.next_run - z.next_run)[0];
    const nextTxt = nextRun ? new Date(nextRun.next_run * 1000).toLocaleString("vi-VN", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" }) : "";
    const dispOn = !!(kb && kb.dispatcher && kb.dispatcher.running);
    const oChips = chip(t("sodo.loops_on", { on: lpOn.length, n: loops.length }), lpOn.length ? "on" : "") +
      chip(t("sodo.dispatch"), dispOn ? "on" : "off");
    const oRows = lpOn.slice(0, 4).map(l => row("repeat", l.name || l.slug,
        l.running ? t("sodo.running") : (l.mode || ""))).join("") +
      (nextTxt ? row("alarm-clock", t("sodo.next_run", { d: nextTxt }), "") : "") +
      row("trending-up", t("sodo.done_24h", { n: (kb && kb.completed_24h) || 0 }), "");
    const s8 = !kb ? "off" : dispOn ? (lpOn.length ? "ok" : "warn") : "warn";

    // ---- gom: trạng thái + con số lớn của từng khối
    const dn = [isDown("settings"), isDown("memory", "overview"), isDown("tools", "mcp", "plugins"), isDown("agents"),
      isDown("workflows", "kanban"), isDown("overview", "loops"), isDown("skills", "agents", "overview"), isDown("loops", "kanban")];
    const stat = [s1, s2, s3, s4, s5, s6, s7, s8].map((s, i) => dn[i] ? "warn" : s);
    const kpi = [nConn, so(mem2.wiki), tools.length, agents.length, wfOn.length, so(hz.lessons_total), verdicts.win, lpOn.length];
    const metric = [mainTxt || t("sodo.no_model"), t("sodo.wiki_n", { n: so(mem2.wiki) }) + " · " + t("sodo.facts", { n: so(facts) }),
      t("sodo.tools_short", { n: tools.length, m: servers.length }), t("sodo.n_ag", { n: agents.length }),
      t("sodo.done_24h", { n: (kb && kb.completed_24h) || 0 }), t("sodo.lessons", { n: so(hz.lessons_total) }),
      t("sodo.pending_n", { n: so(hz.pending_n) }), t("sodo.loops_on", { on: lpOn.length, n: loops.length })];
    const metricOf = [metric[0], metric[1], metric[3] + " · " + t("sodo.wf_on", { on: wfOn.length, n: wfs.length }),
      metric[2], metric[4], metric[5], metric[6], metric[7]];

    // ---- việc cần chú ý: chỉ nói điều CÓ THẬT trong dữ liệu vừa đọc
    const att = [];
    const A = (lv, key, vars, to) => att.push({ lv, text: t(key, vars), go: to });
    if (st && st.model) {
      if (!mainTxt) A("bad", "sodo.att.no_model", null, "models");
      else if (!nConn) A("bad", "sodo.att.no_engine", null, "models");
    }
    if (kb) {
      if (!orch || orch === "off") A("warn", "sodo.att.board_off", null, "kanban");
      else if (orch === "auto" && !dispOn) A("warn", "sodo.att.no_dispatch", null, "kanban");
    }
    const nRisk = ((dp && dp.phong) || []).filter(p => p.status === "risk").length;
    if (nRisk) A("warn", "sodo.att.dept_risk", { n: nRisk }, "departments");
    if (mcp && !servers.length) A("warn", "sodo.att.no_mcp", null, "tools");
    if (ag && !agents.length) A("warn", "sodo.att.no_agent", null, "staff");
    if (down.length) A("warn", "sodo.att.down", { n: down.length, names: down.join(", ") }, "");
    if (hz.pending_n) A("info", "sodo.att.pending", { n: so(hz.pending_n) }, "selfimprove");
    if (lp && !dinhDuong) A("info", "sodo.att.no_loop", null, "selfimprove");
    if (fc && fc.stages) {
      const _pp = fc.stages.proposals || {}, _cn = fc.stages.canary || {};
      if (_pp.eval_failed) A("warn", "sodo.att.evalfail", { n: so(_pp.eval_failed) }, "selfimprove");
      if (_cn.reverted) A("warn", "sodo.att.reverted", { n: so(_cn.reverted) }, "selfimprove");
      if (fc.stages.ci_open) A("warn", "sodo.att.cired", { n: so(fc.stages.ci_open) }, "kanban");
    }
    const rank = { bad: 0, warn: 1, info: 2 };
    att.sort((a, z) => rank[a.lv] - rank[z.lv]);
    const level = att.some(a => a.lv === "bad") || stat.includes("bad") ? "bad"
      : att.some(a => a.lv === "warn") || stat.includes("warn") ? "warn" : "ok";
    const nOk = stat.filter(s => s === "ok").length;

    const pills = BLOCKS.map((bl, i) => `<button type="button" class="sd-pill sd-st-${stat[i]}" data-jump="${bl.n}"><i></i>${esc(t(bl.t))}</button>`).join("");
    const attHtml = att.length ? `<ul class="sd-att">${att.slice(0, 7).map(a => `<li class="sd-st-${a.lv === "info" ? "off" : a.lv}">${ic(a.lv === "info" ? "circle-check" : "triangle-alert")}<span>${esc(a.text)}</span>${a.go ? `<button type="button" data-go="${esc(a.go)}">${esc(t(OPEN_GO[a.go] || (a.go === "departments" ? "sodo.open.dept" : "sodo.open.kanban")))}</button>` : ""}</li>`).join("")}</ul>`
      : `<ul class="sd-att"><li class="sd-st-ok">${ic("circle-check")}<span>${esc(t("sodo.health.none"))}</span></li></ul>`;
    const hhmm = new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

    const flow = FLOW.map((f, i) => `<button type="button" class="sd-node c${f.c}" data-jump="${f.c}">
        <span class="sd-node-ic">${ic(f.ic)}</span>
        <span class="sd-node-in"><b>${esc(t(f.k))}</b><span class="sd-metric">${esc(metricOf[i])}</span></span>
        <span class="sd-dot sd-st-${stat[f.c - 1]}"></span></button>` + (i < FLOW.length - 1 ? `<span class="sd-arr" aria-hidden="true"></span>` : "")).join("");

    el.innerHTML = `<div class="sd-root">
      <div class="sd-top"><span class="sd-brain">${esc(t("sodo.ctx_brain", { b: brain() }))}</span>
        <span class="sd-upd">${esc(t("sodo.updated", { h: hhmm }))}</span>
        <button type="button" class="sd-refresh" data-act="refresh" title="${esc(t("sodo.refresh"))}" aria-label="${esc(t("sodo.refresh"))}">${ic("rotate-cw")}</button></div>
      <section class="sd-health sd-st-${level}" aria-live="polite">
        <span class="sd-orb"></span>
        <div><div class="sd-hstate">${esc(t(HEALTH_KEY[level]))}</div>
          <div class="sd-hsub">${esc(t("sodo.health.sub", { n: nOk, m: BLOCKS.length }))}</div></div>
        <div class="sd-pills">${pills}</div>${attHtml}
      </section>
      <div class="sd-sect">${esc(t("sodo.pipe_title"))}</div>
      <div class="sd-flow">${flow}</div>
      ${fc && fc.harness ? `<div class="sd-sect">${esc(t("sodo.hx.sect"))}</div>` : ""}
      ${hxSection(fc)}
      <div class="sd-sect">${esc(t("sodo.fac.sect"))}</div>
      ${facSection(fc)}
      ${dpSection(fc)}
      <div class="sd-grid">
        ${card(BLOCKS[0], stat[0], kpi[0], mChips, mRows, dn[0])}
        ${card(BLOCKS[1], stat[1], kpi[1], cChips, cRows, dn[1])}
        ${card(BLOCKS[2], stat[2], kpi[2], tChips, tRows, dn[2])}
        ${card(BLOCKS[3], stat[3], kpi[3], aChips, aRows, dn[3])}
        ${card(BLOCKS[4], stat[4], kpi[4], m5, m5r, dn[4])}
        ${card(BLOCKS[5], stat[5], kpi[5], hChips, hRows, dn[5])}
        ${card(BLOCKS[6], stat[6], kpi[6], eChips, eRows, dn[6])}
        ${card(BLOCKS[7], stat[7], kpi[7], oChips, oRows, dn[7])}
      </div>
      ${agentBoard(fc)}
      ${deptSection(dp)}
      </div>`;

    if (!el.querySelectorAll) return;
    el.querySelectorAll("[data-go]").forEach(bt => (bt.onclick = () => go(bt.dataset.go)));
    el.querySelectorAll("[data-jump]").forEach(bt => (bt.onclick = () => jump(el, bt.dataset.jump)));
    el.querySelectorAll("[data-f]").forEach(bt => (bt.onclick = () => { ui.filter = bt.dataset.f; applyFilter(el); }));
    // Chạm 1 ô pipeline -> note bar dưới đổi sang giải thích ô đó (bấm lại để tắt).
    // ui.facNote sống ngoài render nên lựa chọn giữ nguyên qua nhịp tự làm mới.
    el.querySelectorAll("[data-note]").forEach(st => (st.onclick = () => {
      ui.facNote = ui.facNote === st.dataset.note ? "" : st.dataset.note;
      el.querySelectorAll(".sd-stage").forEach(s => s.classList.toggle("on", s.dataset.note === ui.facNote));
      const nb = el.querySelector(".sd-fac-note");
      if (nb) nb.innerHTML = ui.facNote
        ? `<b>${esc(t(ui.facNote))}</b>: ${esc(t(ui.facNote + ".d"))}`
        : esc(t("sodo.fac.hint"));
    }));
    ui.el = el;
    el.querySelectorAll("[data-dp]").forEach(bt => (bt.onclick = () => dpAct(bt.dataset)));
    el.querySelectorAll("[data-act=refresh]").forEach(bt => (bt.onclick = () => {
      bt.classList.add("spin"); render(el, true);
    }));
    applyFilter(el);

    // Tự làm mới khi trang còn hiện; trang đã bị thay bằng trang khác thì tự dừng.
    if (typeof setInterval === "function") {
      timer = setInterval(() => {
        if (!el.isConnected) { clearInterval(timer); timer = null; return; }
        if (typeof document !== "undefined" && document.hidden) return;
        render(el, true);
      }, REFRESH_MS);
    }
  }

  window.JoyceSoDo = { render, _dpAct: dpAct, _dpSection: dpSection };   // _dp*: chỉ để test điều khiển được từng thao tác
})();
