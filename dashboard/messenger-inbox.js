// Hộp thư Messenger ngay trong Cẩm nang > Fanpage (1.3.40).
//
// Đây là CỬA SỔ thứ hai nhìn vào đúng kho hội thoại của trang Hội thoại, không phải một hộp thư
// riêng: danh sách, tin, soạn nháp ("Gợi ý trả lời"), gửi, tiếp quản đều gọi các route /conversations
// SẴN CÓ. Phần mới duy nhất là bật/tắt từng Trang và chọn chế độ (/social/facebook/messenger/*).
//
// Hai chế độ của một Trang:
//   Chờ tôi gửi (mặc định): tin khách chỉ vào hộp thư; Joyce soạn nháp khi chủ bấm, chủ sửa rồi bấm Gửi.
//   Tự động: Joyce tự trả lời qua Agent của bot. Bật phải xác nhận, vì tin đi THẲNG tới khách.
//
// Luật Meta chủ cần thấy ngay trong giao diện: chỉ trả lời được trong 24 giờ sau tin cuối của khách.
(function () {
  "use strict";
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ic = (n, o) => (window.ic ? window.ic(n, o) : "");
  const t = (k, v) => (window.t ? window.t(k, v) : k);
  const REFRESH_MS = 15000;
  const S = { box: null, brain: "brain", agents: [], st: null, page: null, convs: [], conv: null, msgs: [],
              timer: null, busy: false, note: "", noteBad: false, chon: {} };

  const goi = async (url, data) => {
    const opt = data ? { method: "POST", body: new URLSearchParams(data) } : {};
    const r = await fetch(url, opt);
    let d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    return { ok: r.ok && !(d && d.ok === false), status: r.status, data: d || {} };
  };
  const gio = (giay) => {
    const d = new Date(Number(giay || 0) * 1000);
    if (isNaN(d) || !giay) return "";
    try { return d.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }); }
    catch (e) { return ""; }
  };
  const sao = (txt) => { try { navigator.clipboard.writeText(txt); } catch (e) { /* trình duyệt chặn: chủ tự chép */ } };

  let _css = false;
  function css() {
    if (_css) return; _css = true;
    const st = document.createElement("style");
    st.textContent = `
.mi{display:flex;flex-direction:column;gap:12px;color:var(--text)}
.mi-note{padding:8px 11px;border-radius:10px;border:1px solid var(--line);background:var(--wash);font-size:12px;line-height:1.45;color:var(--text2)}
.mi-note.bad{border-color:var(--danger-ink);color:var(--danger-ink)}
.mi-note.warn{border-color:var(--warn-ink);color:var(--warn-ink)}
.mi-setup{border:1px solid var(--line);border-radius:12px;background:var(--wash);padding:0 12px}
.mi-setup>summary{cursor:pointer;padding:9px 0;font-size:12.5px;font-weight:650}
.mi-kv{display:flex;align-items:center;gap:8px;margin:6px 0}
.mi-kv>span{flex:none;width:96px;font-size:11.5px;color:var(--text3)}
.mi-kv>code{flex:1;min-width:0;overflow-wrap:anywhere;font-size:11.5px;padding:5px 8px;border-radius:8px;background:var(--card);border:1px solid var(--line)}
.mi-steps{margin:6px 0 10px 18px;padding:0;font-size:12px;line-height:1.55;color:var(--text2)}
.mi-btn{display:inline-flex;align-items:center;gap:6px;padding:6px 11px;border-radius:9px;border:1px solid var(--line);background:var(--card);
  color:var(--text);font-size:12px;cursor:pointer}
.mi-btn:hover{border-color:var(--accent);color:var(--accent-ink)}
.mi-btn.pri{background:var(--accent);border-color:var(--accent);color:var(--on-accent,#fff)}
.mi-btn[disabled]{opacity:.5;cursor:default}
.mi-pages{display:flex;flex-direction:column;gap:8px}
.mi-page{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:9px 11px;border:1px solid var(--line);border-radius:12px;background:var(--card)}
.mi-page.on{border-color:var(--accent)}
.mi-pn{flex:1;min-width:140px;display:flex;flex-direction:column}
.mi-pn b{font-size:13px}.mi-pn span{font-size:11px;color:var(--text3)}
.mi-seg{display:inline-flex;border:1px solid var(--line);border-radius:9px;overflow:hidden}
.mi-seg button{padding:5px 10px;border:0;background:var(--card);color:var(--text2);font-size:11.5px;cursor:pointer}
.mi-seg button.on{background:color-mix(in srgb,var(--accent) 16%,var(--card));color:var(--accent-ink);font-weight:650}
.mi-seg button.auto.on{background:color-mix(in srgb,var(--warn-ink) 16%,var(--card));color:var(--warn-ink)}
.mi-sel{padding:5px 8px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--text);font-size:12px;max-width:190px}
.mi-box{display:grid;grid-template-columns:minmax(190px,260px) minmax(0,1fr);border:1px solid var(--line);border-radius:12px;overflow:hidden;
  background:var(--card);min-height:380px}
.mi-list{border-right:1px solid var(--line);overflow:auto;max-height:520px}
.mi-c{display:flex;flex-direction:column;gap:2px;padding:9px 11px;border-bottom:1px solid var(--line);cursor:pointer}
.mi-c:hover,.mi-c.on{background:color-mix(in srgb,var(--accent) 9%,var(--card))}
.mi-c b{font-size:12.5px;display:flex;justify-content:space-between;gap:6px}
.mi-c .u{min-width:18px;text-align:center;border-radius:9px;background:var(--accent);color:var(--on-accent,#fff);font-size:10.5px;padding:0 5px}
.mi-c span{font-size:11.5px;color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mi-c i{font-size:10.5px;color:var(--text3);font-style:normal}
.mi-th{display:flex;flex-direction:column;min-width:0}
.mi-thh{padding:8px 12px;border-bottom:1px solid var(--line);font-size:12.5px;font-weight:650;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.mi-thh small{font-weight:400;color:var(--text3)}
.mi-msgs{flex:1;overflow:auto;max-height:380px;padding:10px 12px;display:flex;flex-direction:column;gap:7px}
.mi-m{max-width:82%;padding:7px 10px;border-radius:12px;font-size:12.5px;line-height:1.45;white-space:pre-wrap;overflow-wrap:anywhere;background:var(--wash)}
.mi-m.k{align-self:flex-start}
.mi-m.r{align-self:flex-end;background:color-mix(in srgb,var(--accent) 16%,var(--card))}
.mi-m small{display:block;margin-top:3px;font-size:10px;color:var(--text3)}
.mi-comp{border-top:1px solid var(--line);padding:9px 12px;display:flex;flex-direction:column;gap:7px}
.mi-comp textarea{width:100%;min-height:64px;resize:vertical;padding:8px 10px;border-radius:10px;border:1px solid var(--line);
  background:var(--wash);color:var(--text);font:inherit;font-size:12.5px}
.mi-act{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.mi-empty{padding:18px;text-align:center;font-size:12px;color:var(--text3)}
@container (max-width:640px){.mi-box{grid-template-columns:minmax(0,1fr)}.mi-list{max-height:200px;border-right:0;border-bottom:1px solid var(--line)}}
@media (max-width:640px){.mi-box{grid-template-columns:minmax(0,1fr)}.mi-list{max-height:200px;border-right:0;border-bottom:1px solid var(--line)}}
`;
    document.head.appendChild(st);
  }

  // ---------------------------------------------------------------- vẽ
  function note() {
    return S.note ? `<div class="mi-note ${S.noteBad ? "bad" : ""}" role="status">${esc(S.note)}</div>` : "";
  }
  function setNote(txt, bad) { S.note = txt || ""; S.noteBad = !!bad; }

  function setupHtml(st, nBat) {
    if (!st.ket_noi) return `<div class="mi-note warn">${esc(t("mi.no_conn"))}</div>`;
    const canh = st.canh_bao_dia_chi ? `<div class="mi-note warn">${esc(st.canh_bao_dia_chi)}</div>` : "";
    const quyen = st.quyen_nhan_tin === true ? esc(t("mi.perm_ok"))
      : st.quyen_nhan_tin === false ? esc(t("mi.perm_missing")) : esc(t("mi.perm_unknown"));
    return `<details class="mi-setup"${nBat ? "" : " open"}><summary>${esc(t("mi.setup"))}</summary>${canh}
      <div class="mi-kv"><span>${esc(t("mi.webhook_url"))}</span><code>${esc(st.webhook_url)}</code>
        <button type="button" class="mi-btn" data-copy="${esc(st.webhook_url)}">${esc(t("mi.copy"))}</button></div>
      <div class="mi-kv"><span>${esc(t("mi.verify_token"))}</span><code>${esc(st.verify_token)}</code>
        <button type="button" class="mi-btn" data-copy="${esc(st.verify_token)}">${esc(t("mi.copy"))}</button></div>
      ${st.co_app_secret ? "" : `<div class="mi-note bad">${esc(t("mi.no_secret"))}</div>`}
      <ol class="mi-steps"><li>${esc(t("mi.s1"))}</li><li>${esc(t("mi.s2"))}</li><li>${esc(t("mi.s3"))}</li>
        <li>${esc(t("mi.s4"))}</li><li>${esc(t("mi.s5"))}</li></ol>
      <div class="mi-act"><span class="mi-note" style="flex:1">${quyen}</span>
        <button type="button" class="mi-btn" data-act="perm">${ic("key")} ${esc(t("mi.add_perm"))}</button>
        <button type="button" class="mi-btn" data-goto="mcp">${esc(t("mi.go_connect"))}</button></div></details>`;
  }

  function pageHtml(p) {
    const ag = S.agents.map((a) => `<option value="${esc(a.slug)}"${S.chon[p.page_id] === a.slug ? " selected" : ""}>${esc(a.name || a.slug)}</option>`).join("");
    const dau = `<div class="mi-pn"><b>${esc(p.name)}</b><span>${esc(p.bat ? t("mi.on") : t("mi.off"))}${p.bat && p.agent ? " · " + esc(p.agent) : ""}</span></div>`;
    if (!p.bat) {
      return `<div class="mi-page" data-pid="${esc(p.page_id)}">${dau}
        <select class="mi-sel" data-agent="${esc(p.page_id)}" aria-label="${esc(t("mi.pick_agent"))}">
          <option value="">${esc(t("mi.pick_agent"))}</option>${ag}</select>
        <button type="button" class="mi-btn pri" data-act="enable" data-pid="${esc(p.page_id)}">${esc(t("mi.enable"))}</button></div>`;
    }
    const auto = p.che_do === "tu_dong";
    return `<div class="mi-page on" data-pid="${esc(p.page_id)}">${dau}
      <div class="mi-seg" role="group" aria-label="${esc(t("mi.mode"))}">
        <button type="button" class="${auto ? "" : "on"}" data-act="mode" data-mode="cho_gui" data-pid="${esc(p.page_id)}">${esc(t("mi.mode_wait"))}</button>
        <button type="button" class="auto ${auto ? "on" : ""}" data-act="mode" data-mode="tu_dong" data-pid="${esc(p.page_id)}">${esc(t("mi.mode_auto"))}</button></div>
      <button type="button" class="mi-btn" data-act="open" data-pid="${esc(p.page_id)}">${ic("messages-square")} ${esc(t("mi.open"))}</button>
      <button type="button" class="mi-btn" data-act="disable" data-pid="${esc(p.page_id)}">${esc(t("mi.disable"))}</button></div>`;
  }

  function draw() {
    const st = S.st;
    if (!st) { S.box.innerHTML = `<div class="mi-empty">${esc(t("mi.loading"))}</div>`; return; }
    const pages = st.pages || [];
    const nBat = pages.filter((p) => p.bat).length;
    S.box.innerHTML = `<div class="mi">${note()}${setupHtml(st, nBat)}
      ${st.ket_noi ? `<div class="mi-pages">${pages.length ? pages.map(pageHtml).join("") : `<div class="mi-empty">${esc(t("mi.no_pages"))}</div>`}</div>` : ""}
      <div id="miInbox"></div></div>`;
    wire();
    drawInbox();
  }

  function convHtml(c) {
    return `<div class="mi-c ${S.conv && S.conv.id === c.id ? "on" : ""}" data-cid="${c.id}" role="button" tabindex="0">
      <b><span style="color:var(--text)">${esc(c.title || c.customer_name || c.external_chat_id)}</span>${c.unread_count ? `<span class="u">${c.unread_count}</span>` : ""}</b>
      <span>${esc(c.last_message || "")}</span><i>${esc(gio(c.last_message_at))}${c.mode === "human" ? " · " + esc(t("mi.taken")) : ""}</i></div>`;
  }
  function msgHtml(m) {
    const khach = m.sender_type === "customer";
    const ai = m.sender_type === "ai";
    return `<div class="mi-m ${khach ? "k" : "r"}">${esc(m.text)}<small>${esc(khach ? (m.sender_name || "") : (ai ? t("mi.by_ai") : t("mi.by_you")))} ${esc(gio(m.created_at))}</small></div>`;
  }

  function drawInbox() {
    const host = S.box.querySelector("#miInbox");
    if (!host) return;
    const p = (S.st.pages || []).find((x) => x.page_id === S.page);
    if (!p) { host.innerHTML = ""; return; }
    host.innerHTML = `<div class="mi-box">
      <div class="mi-list" id="miList">${S.convs.length ? S.convs.map(convHtml).join("") : `<div class="mi-empty">${esc(t("mi.no_conv"))}</div>`}</div>
      <div class="mi-th">${S.conv ? `<div class="mi-thh">${esc(S.conv.title || S.conv.customer_name || "")}<small>${esc(t("mi.window24"))}</small>
          ${S.conv.customer_id ? `<button type="button" class="mi-btn" data-act="crm" style="margin-left:auto">${ic("user")} ${esc(t("mi.crm"))}</button>` : ""}</div>
        <div class="mi-msgs" id="miMsgs">${S.msgs.map(msgHtml).join("")}</div>
        <div class="mi-comp"><textarea id="miText" placeholder="${esc(t("mi.placeholder"))}" aria-label="${esc(t("mi.placeholder"))}"></textarea>
          <div class="mi-act"><button type="button" class="mi-btn" data-act="draft" id="miDraft">${ic("sparkles")} ${esc(t("mi.draft"))}</button>
            <button type="button" class="mi-btn pri" data-act="send" id="miSend">${ic("send")} ${esc(t("mi.send"))}</button>
            <span class="mi-note" id="miNote" style="flex:1;display:${S.note ? "block" : "none"}">${esc(S.note)}</span></div></div>`
        : `<div class="mi-empty">${esc(t("mi.pick_conv"))}</div>`}</div></div>`;
    wireInbox(host);
    const m = host.querySelector("#miMsgs");
    if (m) m.scrollTop = m.scrollHeight;
  }

  // ---------------------------------------------------------------- dữ liệu
  async function napStatus() {
    const r = await goi("/social/facebook/messenger/status?brain=" + encodeURIComponent(S.brain));
    S.st = r.ok ? r.data : { ok: false, ket_noi: false, pages: [] };
    if (!r.ok) setNote((r.data && r.data.error) || t("mi.err_status"), true);
  }
  async function napConvs() {
    const p = (S.st.pages || []).find((x) => x.page_id === S.page);
    if (!p || !p.account_key) { S.convs = []; return; }
    const r = await goi("/conversations?channel=messenger&limit=60&account_id=" + encodeURIComponent(p.account_key));
    S.convs = r.ok ? (r.data.items || []) : [];
    if (S.conv) S.conv = S.convs.find((c) => c.id === S.conv.id) || S.conv;
  }
  async function napTin() {
    if (!S.conv) { S.msgs = []; return; }
    const r = await goi(`/conversations/${S.conv.id}/messages?limit=100`);
    S.msgs = r.ok ? (r.data.messages || []) : [];
    if (S.conv.unread_count) goi(`/conversations/${S.conv.id}/read`, {});
  }
  async function lamMoi(chiHopThu) {
    if (!chiHopThu) await napStatus();
    if (S.page) { await napConvs(); await napTin(); }
    if (chiHopThu && S.box.querySelector("#miInbox")) {
      // nhịp tự làm mới: chỉ vẽ lại danh sách và tin, KHÔNG đụng ô soạn (chủ đang gõ dở)
      const l = S.box.querySelector("#miList");
      const m = S.box.querySelector("#miMsgs");
      if (l) l.innerHTML = S.convs.length ? S.convs.map(convHtml).join("") : `<div class="mi-empty">${esc(t("mi.no_conv"))}</div>`;
      if (m) { const cuoi = m.scrollHeight - m.scrollTop - m.clientHeight < 40; m.innerHTML = S.msgs.map(msgHtml).join(""); if (cuoi) m.scrollTop = m.scrollHeight; }
      wireList();
    } else draw();
  }

  // ---------------------------------------------------------------- hành động
  async function hanhDong(act, d) {
    if (S.busy) return;
    S.busy = true;
    try {
      if (act === "enable") {
        const slug = S.chon[d.pid] || ((S.box.querySelector(`[data-agent="${d.pid}"]`) || {}).value || "");
        if (!slug) { setNote(t("mi.need_agent"), true); return draw(); }
        setNote(t("mi.enabling"));
        draw();
        const r = await goi("/social/facebook/messenger/enable", { page_id: d.pid, agent_slug: slug, brain: S.brain });
        setNote(r.ok ? (r.data.da_dang_ky_webhook ? t("mi.enabled") : t("mi.enabled_no_sub", { loi: r.data.loi_dang_ky || "" })) : (r.data.error || t("mi.err")), !r.ok);
        await napStatus();
        return draw();
      }
      if (act === "disable") {
        if (!window.confirm(t("mi.confirm_off"))) return;
        const r = await goi("/social/facebook/messenger/disable", { page_id: d.pid });
        setNote(r.ok ? t("mi.disabled") : (r.data.error || t("mi.err")), !r.ok);
        if (S.page === d.pid) { S.page = null; S.conv = null; S.convs = []; S.msgs = []; }
        await napStatus();
        return draw();
      }
      if (act === "mode") {
        let data = { page_id: d.pid, mode: d.mode };
        if (d.mode === "tu_dong") {
          if (!window.confirm(t("mi.confirm_auto"))) return;
          data.xac_nhan = "1";
        }
        const r = await goi("/social/facebook/messenger/mode", data);
        setNote(r.ok ? t(d.mode === "tu_dong" ? "mi.auto_on" : "mi.wait_on") : (r.data.error || t("mi.err")), !r.ok);
        await napStatus();
        return draw();
      }
      if (act === "open") {
        S.page = S.page === d.pid ? null : d.pid;
        S.conv = null; S.msgs = []; S.convs = [];
        if (S.page) await napConvs();
        return draw();
      }
      if (act === "crm") {
        // Đưa khách vào CRM của phòng đang xem: từ đó Joyce tự đề xuất cập nhật hồ sơ khi khách nhắn đủ
        // ngưỡng (chờ duyệt), và "Ghi nhớ vào wiki" chưng cất khách thành tri thức của phòng (route CRM sẵn có).
        if (!S.conv || !S.conv.customer_id) return;
        const r = await goi("/crm/hop-thu/nhap", { customer_id: String(S.conv.customer_id), brain: S.brain });
        const n = S.box.querySelector("#miNote");
        const txt = r.ok ? t("mi.crm_done") : (r.data.error || r.data.detail || t("mi.err"));
        setNote(txt, !r.ok);
        if (n) { n.style.display = "block"; n.className = "mi-note" + (r.ok ? "" : " bad"); n.textContent = txt; }
        return;
      }
      if (act === "perm") {
        const r = await goi("/social/facebook/messenger/permissions", {});
        setNote(r.ok ? t("mi.perm_added") : (r.data.error || t("mi.err")), !r.ok);
        return draw();
      }
      if (act === "draft" || act === "send") {
        const ta = S.box.querySelector("#miText");
        const nut = S.box.querySelector(act === "draft" ? "#miDraft" : "#miSend");
        const loi = (x) => { setNote(x, true); const n = S.box.querySelector("#miNote"); if (n) { n.style.display = "block"; n.className = "mi-note bad"; n.textContent = x; } };
        if (nut) nut.disabled = true;
        try {
          if (act === "draft") {
            const r = await goi(`/conversations/${S.conv.id}/ai-reply`, { mode: "draft" });
            if (!r.ok) return loi(r.data.error || t("mi.err"));
            if (r.data.silent || !r.data.text) return loi(t("mi.draft_silent"));
            if (ta) { ta.value = r.data.text; ta.focus(); }
            setNote(t("mi.draft_ready"));
            const n = S.box.querySelector("#miNote");
            if (n) { n.style.display = "block"; n.className = "mi-note"; n.textContent = t("mi.draft_ready"); }
          } else {
            const txt = ta ? ta.value.trim() : "";
            if (!txt) return loi(t("mi.empty_text"));
            const r = await goi(`/conversations/${S.conv.id}/reply`, { text: txt });
            if (!r.ok) return loi(r.data.error || t("mi.err"));
            if (ta) ta.value = "";
            setNote("");
            await lamMoi(true);
          }
        } finally { if (nut) nut.disabled = false; }
      }
    } finally { S.busy = false; }
  }

  // ---------------------------------------------------------------- nối sự kiện
  function wireList() {
    S.box.querySelectorAll("[data-cid]").forEach((n) => {
      const mo = async () => { S.conv = S.convs.find((c) => String(c.id) === n.dataset.cid) || null; setNote(""); await napTin(); drawInbox(); };
      n.onclick = mo;
      n.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); mo(); } };
    });
  }
  function wireInbox(host) {
    wireList();
    host.querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => hanhDong(b.dataset.act, b.dataset)));
  }
  function wire() {
    S.box.querySelectorAll("[data-copy]").forEach((b) => (b.onclick = () => { sao(b.dataset.copy); b.textContent = t("mi.copied"); }));
    S.box.querySelectorAll("[data-goto]").forEach((b) => (b.onclick = () => {
      try { const s = window.Alpine && window.Alpine.store("nav"); if (s && s.go) s.go(b.dataset.goto); } catch (e) { /* không có điều hướng */ }
    }));
    S.box.querySelectorAll("[data-agent]").forEach((s) => (s.onchange = () => { S.chon[s.dataset.agent] = s.value; }));
    S.box.querySelectorAll(".mi-pages [data-act], .mi-setup [data-act]").forEach((b) => (b.onclick = () => hanhDong(b.dataset.act, b.dataset)));
  }

  async function mount(box, opts) {
    if (!box) return;
    css();
    if (S.timer) { clearInterval(S.timer); S.timer = null; }
    const o = opts || {};
    Object.assign(S, { box, brain: o.brain || "brain", agents: o.agents || [], page: null, conv: null, convs: [], msgs: [], note: "", noteBad: false });
    draw();
    await napStatus();
    draw();
    if (typeof setInterval === "function") {
      S.timer = setInterval(() => {
        if (!S.box || !S.box.isConnected) { clearInterval(S.timer); S.timer = null; return; }
        if (typeof document !== "undefined" && document.hidden) return;
        if (S.page && !S.busy) lamMoi(true);
      }, REFRESH_MS);
    }
  }

  // `_act` và `_state` chỉ để test điều khiển được từng hành động mà không cần DOM thật.
  window.JoyceMessengerInbox = { mount, _act: hanhDong, _state: S };
})();
