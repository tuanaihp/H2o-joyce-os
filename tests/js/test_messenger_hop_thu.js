/* Hộp thư Messenger trong Cẩm nang > Fanpage (dashboard/messenger-inbox.js, 1.3.40).

       node tests/js/test_messenger_hop_thu.js

   Chạy THẬT mount() và các hành động trong vm với fetch giả theo đúng shape của route thật.
   Không có jsdom trong repo, nên "hộp" giả chỉ ghi lại chuỗi innerHTML và trả phần tử giả cho
   những chỗ code cần ô nhập. Kiểm: vẽ đủ Trang, chế độ, hướng dẫn cài đặt; thoát HTML; mở hộp thư
   gọi đúng route SẴN CÓ của Hộp thư; Gợi ý và Gửi; tự động phải xác nhận; i18n đủ vi và en. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const SRC = D("messenger-inbox.js");
const CAM = D("camnang.js");
const INDEX = D("index.html");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));
const fails = [];
const check = (n, c, d) => { console.log((c ? "ok   " : "FAIL ") + n); if (!c) { fails.push(n); if (d) console.log("       " + d); } };

function makeCtx(canned, opts) {
  opts = opts || {};
  const goi = [];
  const textarea = { value: "", focus() {} };
  const inbox = { _h: "", set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h; }, querySelector() { return null; }, querySelectorAll() { return []; } };
  const nutDraft = { disabled: false }, nutSend = { disabled: false }, note = { style: {}, className: "", textContent: "" };
  const box = { _h: "", isConnected: true,
    set innerHTML(v) { this._h = v; }, get innerHTML() { return this._h; },
    querySelectorAll() { return []; },
    querySelector(sel) {
      if (sel === "#miInbox") return inbox;
      if (sel === "#miText") return textarea;
      if (sel === "#miDraft") return nutDraft;
      if (sel === "#miSend") return nutSend;
      if (sel === "#miNote") return note;
      if (sel.startsWith("[data-agent=")) return { value: opts.agent || "" };
      return null;
    } };
  const win = { t: (k, v) => { let s = VI[k]; if (s == null) return "THIEU_I18N:" + k; if (v) for (const kk in v) s = s.replaceAll("{" + kk + "}", v[kk]); return s; },
    ic: (n) => "<i data-ic=" + n + "/>", confirm: () => opts.xacNhan !== false };
  const doc = { createElement: () => ({ set textContent(v) {} }), head: { appendChild() {} }, hidden: false };
  const ctx = { window: win, document: doc, console, navigator: {}, URLSearchParams,
    setInterval: () => 0, clearInterval() {},
    fetch: async (u, o) => {
      const body = o && o.body ? Object.fromEntries(new URLSearchParams(o.body.toString())) : null;
      goi.push({ u, method: (o && o.method) || "GET", body });
      const k = (o && o.method === "POST" ? "POST " : "") + u.split("?")[0];
      const d = canned[k];
      if (d == null) return { ok: false, status: 404, json: async () => ({ ok: false, error: "404 " + k }) };
      if (d.__status) return { ok: false, status: d.__status, json: async () => d.body };
      return { ok: true, status: 200, json: async () => d };
    } };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { ctx, box, inbox, win, goi, textarea, note, J: ctx.window.JoyceMessengerInbox };
}

const ST = { ok: true, ket_noi: true, conn_id: "c1", webhook_url: "https://joyce.example.vn/webhooks/messenger", verify_token: "joyce-abc",
  canh_bao_dia_chi: "", co_app_secret: true, quyen_nhan_tin: null,
  pages: [
    { page_id: "111", name: "Lamary Bridal", bat: true, che_do: "cho_gui", account_id: "acc_1", bot_id: "bot_1", agent: "truong-sales-vay-cuoi", account_key: "messenger:acc_1" },
    { page_id: "222", name: "Trang <img src=x onerror=alert(1)>", bat: false, che_do: "cho_gui", account_id: "", bot_id: "", agent: "", account_key: "" }] };
const CONV = { id: 7, customer_id: 31, title: "Chị Lan", last_message: "Em ơi cho chị xem mẫu", last_message_at: 1790000100, unread_count: 2, mode: "ai" };
const MSGS = [{ id: 1, sender_type: "customer", sender_name: "Chị Lan", text: "Chị muốn hỏi giá <b>gói cưới</b>", created_at: 1790000000 },
              { id: 2, sender_type: "human", text: "Dạ em gửi bảng giá ạ", created_at: 1790000050 }];
const CANNED = () => ({
  "/social/facebook/messenger/status": ST,
  "/conversations": { ok: true, items: [CONV] },
  "/conversations/7/messages": { ok: true, messages: MSGS, conversation: CONV },
  "POST /conversations/7/read": { ok: true },
  "POST /conversations/7/ai-reply": { ok: true, text: "Dạ em gửi chị bảng giá gói cưới ạ.", draft: true },
  "POST /conversations/7/reply": { ok: true },
  "POST /social/facebook/messenger/enable": { ok: true, da_dang_ky_webhook: true },
  "POST /social/facebook/messenger/mode": { ok: true },
  "POST /social/facebook/messenger/disable": { ok: true },
  "POST /social/facebook/messenger/permissions": { ok: true },
  "POST /crm/hop-thu/nhap": { ok: true, contact: { id: 5 } },
});

async function main() {
  // ---- vẽ ban đầu
  {
    const { box, J } = makeCtx(CANNED());
    await J.mount(box, { brain: "brain", agents: [{ slug: "truong-sales-vay-cuoi", name: "Trưởng Sales Váy Cưới" }] });
    const h = box.innerHTML;
    check("vẽ đủ hai Trang, Trang đã bật có chế độ và nút Mở", h.includes("Lamary Bridal") && h.includes(VI["mi.mode_wait"]) && h.includes(VI["mi.mode_auto"]) && h.includes('data-act="open"'));
    check("Trang chưa bật có chọn trợ lý và nút Bật hộp thư", h.includes('data-act="enable"') && h.includes("Trưởng Sales Váy Cưới"));
    check("mặc định Chờ tôi gửi đang chọn, Tự động chưa chọn", /<button type="button" class="on" data-act="mode" data-mode="cho_gui"/.test(h) && !/class="auto on"/.test(h));
    check("hướng dẫn cài đặt có địa chỉ webhook và mã xác minh", h.includes("https://joyce.example.vn/webhooks/messenger") && h.includes("joyce-abc") && h.includes('data-act="perm"'));
    check("năm bước hướng dẫn", (h.match(/<li>/g) || []).length === 5);
    check("tên Trang chứa HTML được thoát, không chèn được thẻ", !h.includes("<img src=x") && h.includes("&lt;img src=x"));
    check("không rò key i18n", !h.includes("THIEU_I18N"));
    check("không dùng em dash", !h.includes("—"));
    check("chưa mở hộp thư thì không vẽ khung hội thoại", !h.includes("mi-box"));
  }
  // ---- thiếu secret và cảnh báo địa chỉ
  {
    const c = CANNED();
    c["/social/facebook/messenger/status"] = { ...ST, co_app_secret: false, canh_bao_dia_chi: "Địa chỉ localhost: Meta không gọi vào được." };
    const { box, J } = makeCtx(c);
    await J.mount(box, { agents: [] });
    check("thiếu App Secret thì nói thẳng", box.innerHTML.includes(VI["mi.no_secret"]));
    check("cảnh báo địa chỉ không gọi được hiện ra", box.innerHTML.includes("Địa chỉ localhost"));
  }
  // ---- chưa kết nối Facebook
  {
    const c = CANNED();
    c["/social/facebook/messenger/status"] = { ok: true, ket_noi: false, pages: [] };
    const { box, J } = makeCtx(c);
    await J.mount(box, {});
    check("chưa kết nối Facebook Trang thì báo, không vẽ danh sách Trang", box.innerHTML.includes(VI["mi.no_conn"]) && !box.innerHTML.includes("mi-pages"));
  }
  // ---- mở hộp thư, gợi ý, gửi
  {
    const { box, inbox, goi, textarea, J } = makeCtx(CANNED());
    await J.mount(box, { brain: "brain", agents: [] });
    await J._act("open", { pid: "111" });
    const lay = goi.find((x) => x.u.startsWith("/conversations?"));
    check("mở hộp thư gọi route SẴN CÓ, lọc đúng kênh và tài khoản của Trang", !!lay && lay.u.includes("channel=messenger") && lay.u.includes("account_id=messenger%3Aacc_1"), lay && lay.u);
    check("danh sách hội thoại hiện tên khách, tin cuối, số chưa đọc", inbox.innerHTML.includes("Chị Lan") && inbox.innerHTML.includes("Em ơi cho chị xem mẫu") && inbox.innerHTML.includes('class="u">2<'));
    check("chưa chọn hội thoại thì nhắc chọn", inbox.innerHTML.includes(VI["mi.pick_conv"]));
    // chọn hội thoại: nạp tin rồi vẽ khung chat (đường thật của nhấp chuột là wireList, ở đây gọi trực tiếp)
    J._state.conv = J._state.convs[0];
    const r = await (await makeCtx(CANNED()).ctx.fetch("/conversations/7/messages?limit=100")).json();
    J._state.msgs = r.messages;
    await J._act("close-noop", {});
    await J._act("open", { pid: "111" });   // lần hai: đóng
    check("bấm Mở lần hai thì đóng hộp thư", !inbox.innerHTML.includes("mi-box"));
    await J._act("open", { pid: "111" });   // mở lại, hội thoại đã bị xoá lúc đóng
    J._state.conv = J._state.convs[0];
    J._state.msgs = r.messages;
    textarea.value = "";
    await J._act("draft", {});
    check("Gợi ý trả lời gọi ai-reply ở chế độ draft", goi.some((x) => x.u === "/conversations/7/ai-reply" && x.body && x.body.mode === "draft"));
    check("bản nháp đổ vào ô soạn, CHƯA gửi", textarea.value.includes("bảng giá gói cưới") && !goi.some((x) => x.u === "/conversations/7/reply"));
    await J._act("send", {});
    const gui = goi.find((x) => x.u === "/conversations/7/reply");
    check("Gửi gọi reply với đúng nội dung ô soạn", !!gui && gui.body.text.includes("bảng giá gói cưới"));
    check("gửi xong thì ô soạn được xoá", textarea.value === "");
    textarea.value = "   ";
    const n = goi.length;
    await J._act("send", {});
    check("ô soạn trống thì không gửi", !goi.slice(n).some((x) => x.u === "/conversations/7/reply"));
  }
  // ---- đưa khách vào CRM (chưng cất hội thoại)
  {
    const { box, inbox, goi, note, J } = makeCtx(CANNED());
    await J.mount(box, { brain: "Ban Hang - Thu", agents: [] });
    await J._act("open", { pid: "111" });
    J._state.conv = J._state.convs[0];
    J._state.msgs = MSGS;
    await J._act("open", { pid: "111" });
    await J._act("open", { pid: "111" });
    J._state.conv = J._state.convs[0];
    await J._act("crm", {});
    const r = goi.find((x) => x.u === "/crm/hop-thu/nhap");
    check("nút CRM gọi route CRM sẵn có với đúng khách và phòng", !!r && r.body.customer_id === "31" && r.body.brain === "Ban Hang - Thu");
    check("nút CRM báo Joyce sẽ đề xuất hồ sơ chờ duyệt", note.textContent === VI["mi.crm_done"]);
    const c = CANNED();
    c["POST /crm/hop-thu/nhap"] = { __status: 403, body: { ok: false, error: "Chỉ quản lý hoặc chủ nhập khách từ hộp thư" } };
    const x = makeCtx(c);
    await x.J.mount(x.box, { brain: "b", agents: [] });
    await x.J._act("open", { pid: "111" });
    x.J._state.conv = x.J._state.convs[0];
    await x.J._act("crm", {});
    check("không đủ quyền CRM thì hiện đúng lý do của server", x.note.textContent.includes("Chỉ quản lý"));
  }
  // ---- bật hộp thư
  {
    const { box, goi, J } = makeCtx(CANNED(), { agent: "" });
    await J.mount(box, { agents: [{ slug: "tsv", name: "TSV" }] });
    await J._act("enable", { pid: "222" });
    check("bật mà chưa chọn trợ lý thì nhắc, không gọi server", !goi.some((x) => x.u.endsWith("/messenger/enable")) && box.innerHTML.includes(VI["mi.need_agent"]));
    J._state.chon["222"] = "tsv";
    await J._act("enable", { pid: "222" });
    const en = goi.find((x) => x.u.endsWith("/messenger/enable"));
    check("chọn trợ lý rồi thì gọi enable với đúng Trang và trợ lý", !!en && en.body.page_id === "222" && en.body.agent_slug === "tsv");
  }
  // ---- tự động phải xác nhận
  {
    const a = makeCtx(CANNED(), { xacNhan: false });
    await a.J.mount(a.box, { agents: [] });
    await a.J._act("mode", { pid: "111", mode: "tu_dong" });
    check("từ chối xác nhận thì KHÔNG gọi server bật tự động", !a.goi.some((x) => x.u.endsWith("/messenger/mode")));
    const b = makeCtx(CANNED(), { xacNhan: true });
    await b.J.mount(b.box, { agents: [] });
    await b.J._act("mode", { pid: "111", mode: "tu_dong" });
    const m = b.goi.find((x) => x.u.endsWith("/messenger/mode"));
    check("xác nhận rồi thì gọi mode kèm xac_nhan", !!m && m.body.mode === "tu_dong" && m.body.xac_nhan === "1");
    await b.J._act("mode", { pid: "111", mode: "cho_gui" });
    const m2 = b.goi.filter((x) => x.u.endsWith("/messenger/mode")).pop();
    check("quay về Chờ tôi gửi không cần xác nhận", m2.body.mode === "cho_gui" && !m2.body.xac_nhan);
  }
  // ---- lỗi server hiện cho chủ, chữ chủ gõ không mất
  {
    const c = CANNED();
    c["POST /conversations/7/reply"] = { __status: 400, body: { ok: false, error: "Quá 24 giờ kể từ tin cuối của khách" } };
    const { box, textarea, note, J } = makeCtx(c);
    await J.mount(box, { agents: [] });
    await J._act("open", { pid: "111" });
    J._state.conv = J._state.convs[0];
    textarea.value = "Chị ơi còn đó không";
    await J._act("send", {});
    check("quá 24 giờ: lỗi của server hiện ra, chữ chủ gõ KHÔNG bị xoá", note.textContent.includes("24 giờ") && textarea.value === "Chị ơi còn đó không");
  }
  // ---- đăng ký hệ thống và i18n
  check("camnang.js gắn panel và gọi JoyceMessengerInbox.mount", CAM.includes('id="cnFbInbox"') && CAM.includes("JoyceMessengerInbox.mount"));
  check("index.html nạp messenger-inbox.js TRƯỚC camnang.js", INDEX.indexOf("messenger-inbox.js") > 0 && INDEX.indexOf("messenger-inbox.js") < INDEX.indexOf("camnang.js"));
  const keys = [...new Set((SRC.match(/t\("(mi\.[a-z0-9_]+)"/g) || []).map((m) => m.slice(3, -1)).concat(["camnang.fb_inbox", "camnang.fb_inbox_d"]))];
  const thieu = keys.filter((k) => !(k in VI && k in EN));
  check("mọi khoá mi.* dùng trong file có trong vi.json và en.json", keys.length > 30 && thieu.length === 0, thieu.join(","));
  const xau = Object.keys(VI).filter((k) => k.startsWith("mi.")).filter((k) => /—|<[a-z\/]/i.test(VI[k]) || /—|<[a-z\/]/i.test(EN[k] || ""));
  check("giá trị vi/en không có em dash, không có thẻ HTML", xau.length === 0, xau.join(","));
  check("không dùng em dash trong mã nguồn", !SRC.includes("—"));

  if (fails.length) { console.log("\nĐỎ " + fails.length + " mục"); process.exit(1); }
  console.log("\nTất cả xanh.");
}
main().catch((e) => { console.log("FAIL chạy test:", e); process.exit(1); });
