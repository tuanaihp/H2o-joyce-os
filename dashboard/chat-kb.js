/* chat-kb.js - mục lục tri thức của brain ngay trong khung chat.

   Khi #chatArea trống (chat mới / vừa đổi brain): đọc wiki/index.md của brain đang
   chọn qua /files/read rồi vẽ các nhóm (## heading) thành chip. Bấm chip = ĐIỀN SẴN
   câu hỏi vào ô chat rồi focus - KHÔNG tự gửi (người dùng đọc lại rồi Enter).
   Khi transcript có tin/bubble nào: tự gỡ panel để nhường chỗ.

   Cơ chế: MutationObserver trên #chatArea - file này tự lo vòng đời panel, không cần
   móc vào app.js hay chat-render. Brain nào có wiki/index.md theo format wiki schema
   đều hiện; brain chưa có thì không hiện gì (transcript :empty giữ câu mời mặc định).

   Ghi chu: KHONG dung ky tu em dash o bat ky dau. */
(function () {
  "use strict";

  // Chữ lấy từ từ điển. Trong trình duyệt là window.t; dưới node (test require file
  // này) đọc thẳng vi.json - cùng mẹo chat-ask.js.
  function tw(khoa, bien) {
    if (typeof window !== "undefined" && window.t) return window.t(khoa, bien);
    try {
      var s = require("./i18n/vi.json")[khoa] || khoa;
      return String(s).replace(/\{(\w+)\}/g, function (m, ten) {
        return (bien && bien[ten] != null) ? String(bien[ten]) : m;
      });
    } catch (e) { return khoa; }
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function brain() {
    try { return window.JoyceSessions ? window.JoyceSessions.brain() : "brain"; }
    catch (e) { return "brain"; }
  }

  function ic(ten) {
    try { return (typeof window !== "undefined" && window.ic) ? window.ic(ten) : ""; }
    catch (e) { return ""; }
  }

  // Parse wiki/index.md -> {cats:[{name, pages:[{rel, base}]}], flat:[{rel, base}]}.
  // `flat` = link gốc không nằm dưới nhóm ## nào (index kiểu phẳng của brain phòng).
  // Cùng luật lọc với camnang.js/sessions-ui.js: bỏ _, index, log, sources/ và trùng.
  function parseIndex(md) {
    var cats = [], cur = null, flat = [], flatSeen = {};
    String(md || "").split(/\r?\n/).forEach(function (line) {
      var mH = line.match(/^##\s+(.+)/);
      if (mH) { cur = { name: mH[1].trim(), pages: [], seen: {} }; cats.push(cur); return; }
      var ms = line.match(/\[\[([^\]]+)\]\]/g);
      if (!ms) return;
      ms.forEach(function (x) {
        var rel = x.slice(2, -2).split("|")[0].trim();
        if (!rel || rel === "index" || rel === "log" || rel[0] === "_"
            || rel.indexOf("sources/") === 0 || rel[rel.length - 1] === "/") return;
        var base = rel.split("/").pop();
        if (cur) {
          if (!cur.seen[rel]) { cur.seen[rel] = 1; cur.pages.push({ rel: rel, base: base }); }
        } else if (!flatSeen[rel]) { flatSeen[rel] = 1; flat.push({ rel: rel, base: base }); }
      });
    });
    return { cats: cats.filter(function (c) { return c.pages.length > 0; }), flat: flat };
  }

  // HTML catalog: tiêu đề + chip nhóm (tên + số trang) + chip trang phẳng nếu có.
  // Gọn vì nằm trong khung chat: nhóm nhiều thì gọn theo chip, trang phẳng cũng chip.
  function renderHtml(parsed) {
    var cats = (parsed && parsed.cats) || [], flat = (parsed && parsed.flat) || [];
    var tong = flat.length + cats.reduce(function (s, c) { return s + c.pages.length; }, 0);
    return '<div class="chat-kb"><div class="chat-kb-h"><span class="chat-kb-i">'
      + ic("book-open") + '</span><b>' + esc(tw("camnang.kb_t")) + '</b>'
      + '<span class="chat-kb-n">' + esc(tw("chat.kb_pages", { n: tong })) + '</span>'
      + '<button type="button" class="chat-kb-more" title="' + esc(tw("chat.kb_more_tip")) + '">'
      + esc(tw("chat.kb_more")) + '</button></div>'
      + '<div class="chat-kb-d">' + esc(tw("chat.kb_d")) + '</div>'
      + '<div class="chat-kb-chips">'
      + cats.map(function (c) {
        return '<button type="button" class="chat-kb-chip" data-kb="' + esc(c.name) + '">'
          + esc(c.name) + ' <b>' + c.pages.length + '</b></button>';
      }).join("")
      + flat.map(function (p) {
        return '<button type="button" class="chat-kb-page" data-kbp="' + esc(p.base) + '">'
          + esc(p.base) + '</button>';
      }).join("")
      + '</div></div>';
  }

  // Điền sẵn câu hỏi vào ô chat rồi focus - KHÔNG gửi (người dùng đọc lại rồi Enter).
  function dienCau(cau) {
    var inp = document.getElementById("chatInput");
    if (!inp) return;
    inp.value = cau;
    inp.dispatchEvent(new Event("input", { bubbles: true }));
    inp.focus();
  }

  // Đồng bộ panel theo trạng thái transcript: trống -> vẽ (nếu có wiki), có con
  // khác -> gỡ. Gọi bởi observer mỗi khi childList đổi.
  function syncKb() {
    var area = document.getElementById("chatArea");
    if (!area) return;
    var kb = area.querySelector(":scope > .chat-kb");
    var other = area.querySelector(":scope > *:not(.chat-kb)");
    if (other) { if (kb) kb.remove(); return; }
    if (kb) return;
    var brainNow = brain();
    fetch("/files/read?brain=" + encodeURIComponent(brainNow)
        + "&path=" + encodeURIComponent("wiki/index.md"))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!area.isConnected) return;
        // Tin/bubble đã xuất hiện trong lúc fetch, hoặc vừa đổi brain -> bỏ kết quả.
        if (area.querySelector(":scope > *")) return;
        if (brain() !== brainNow) return;
        var parsed = parseIndex(d && d.content);
        if (!parsed.cats.length && !parsed.flat.length) return;
        area.insertAdjacentHTML("afterbegin", renderHtml(parsed));
      })
      .catch(function () {});
  }

  if (typeof document !== "undefined") {
    var boot = function () {
      var area = document.getElementById("chatArea");
      if (!area) { setTimeout(boot, 500); return; }
      new MutationObserver(syncKb).observe(area, { childList: true });
      syncKb();
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();

    // Bấm chip nhóm -> điền câu hỏi theo nhóm; bấm "xem đầy đủ" -> mở trang Cẩm nang.
    document.addEventListener("click", function (e) {
      var t = e.target;
      var chip = t.closest ? t.closest(".chat-kb-chip") : null;
      if (chip) { dienCau(tw("chat.kb_ask", { ten: chip.dataset.kb || "" })); return; }
      var pg = t.closest ? t.closest(".chat-kb-page") : null;
      if (pg) { dienCau(tw("camnang.kb_ask", { ten: pg.dataset.kbp || "" })); return; }
      var more = t.closest ? t.closest(".chat-kb-more") : null;
      if (more) {
        try {
          var nav = window.Alpine && Alpine.store("nav");
          if (nav && nav.go) nav.go("camnang");
        } catch (err) {}
      }
    });
  }

  if (typeof window !== "undefined") {
    window.JoyceChatKB = { refresh: syncKb, parseIndex: parseIndex, renderHtml: renderHtml };
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { parseIndex: parseIndex, renderHtml: renderHtml };
  }
})();
