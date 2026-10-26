/* viec-mau.js - "Việc hằng ngày" trong khung chat (kế hoạch: docs/dev/2026-10-chat-cong-viec-hang-ngay.md).

   Mỗi brain có danh sách việc mẫu do máy chủ cấp (GET /viec-mau). Ở khung chat trống, một khay
   chip hiện NGAY TRÊN ô nhập: bấm chip -> form ngắn -> ghép lệnh -> gửi vào chat như tin thường.
   Mỗi nhóm kết thúc bằng một nút "+" để tự thêm việc (mọi phòng đều có). Menu "+" của ô chat có
   mục "Việc hằng ngày" dùng chung đúng form này khi đang gõ dở.

   Sau khi một việc mẫu chạy xong (#chatArea hết .busy), file này hiện thanh đề nghị "Đã xong?".
   Bấm thì máy chủ ghi việc vào cột Xong của bảng Công việc + hồ sơ sources/viec-lam/. Rồi nút
   "Ghi nhớ cách làm này" chưng cất NGAY lên wiki. Đếm, ghi sổ, ngưỡng đều do code làm.

   Phần thuần (ghepLenh, thieu, chiaNhom, khoaO, ...) xuất ra cho test node.
   Ghi chu: KHONG dung ky tu em dash o bat ky dau. Chữ giao diện đều qua tw() (khoá vm.*). */
(function () {
  "use strict";

  var TOI_DA_CHIP = 8;          // chip hiển thị mỗi nhóm, còn lại ở "Xem thêm"
  var TOI_DA_O = 5;             // trùng trần của máy chủ (viec_mau.TOI_DA_O)
  var KHOA_GAP = "joyce.vm.gap";

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

  function ic(ten) {
    try { return (typeof window !== "undefined" && window.ic) ? window.ic(ten) : ""; }
    catch (e) { return ""; }
  }

  // ---------------------------------------------------------------- phần thuần
  // Ghép lệnh: thay {khoa} bằng giá trị đã điền; việc có trang SOP thì dặn đọc trang đó trước.
  function ghepLenh(item, values) {
    var v = values || {};
    var than = String((item && item.prompt) || "").replace(/\{(\w+)\}/g, function (m, k) {
      return v[k] == null ? "" : String(v[k]).trim();
    });
    var tienTo = "";
    if (item && item.sop) tienTo += tw("vm.sop_hint", { sop: item.sop }) + "\n\n";
    var route = String((item && item.route) || "auto");
    var lenh = "";
    if (route.indexOf("wf:") === 0) lenh = "/workflow-" + route.slice(3) + " ";
    else if (route.indexOf("agent:") === 0) lenh = "/agent-" + route.slice(6) + " ";
    return lenh + tienTo + than;
  }

  // Tên các ô bắt buộc còn trống.
  function thieu(item, values) {
    var v = values || {};
    return ((item && item.inputs) || []).filter(function (o) {
      return o.required && !String(v[o.key] == null ? "" : v[o.key]).trim();
    }).map(function (o) { return o.label; });
  }

  // [{name, items}] theo thứ tự nhóm xuất hiện lần đầu.
  function chiaNhom(items) {
    var out = [], idx = {};
    (items || []).forEach(function (it) {
      var g = it.group || "";
      if (!(g in idx)) { idx[g] = out.length; out.push({ name: g, items: [] }); }
      out[idx[g]].items.push(it);
    });
    return out;
  }

  function bo(s) {
    return String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .replace(/\u0111/g, "d").replace(/\u0110/g, "D").toLowerCase();
  }

  // Khoá ô nhập từ nhãn người dùng gõ: "Tên khách" -> ten_khach; luôn bắt đầu bằng chữ, không trùng.
  function khoaO(nhan, dung) {
    var k = bo(nhan).replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 20);
    if (!/^[a-z]/.test(k)) k = "o" + (k || "");
    var goc = k, n = 2;
    while ((dung || []).indexOf(k) >= 0) { k = goc.slice(0, 17) + "_" + n; n += 1; }
    return k;
  }

  // Lệnh mà người dùng quên nhắc tới ô nào thì tự nối thêm dòng "Nhãn: {khoá}" cho ô đó.
  function themO(prompt, inputs) {
    var p = String(prompt || "").trim();
    (inputs || []).forEach(function (o) {
      if (p.indexOf("{" + o.key + "}") < 0) p += "\n" + o.label + ": {" + o.key + "}";
    });
    return p;
  }

  function mauPhieu(item) {
    return item || { title: "", group: "", prompt: "", inputs: [] };
  }

  var pure = { ghepLenh: ghepLenh, thieu: thieu, chiaNhom: chiaNhom, khoaO: khoaO, themO: themO,
               TOI_DA_CHIP: TOI_DA_CHIP, TOI_DA_O: TOI_DA_O };
  if (typeof module !== "undefined" && module.exports) module.exports = pure;
  if (typeof document === "undefined") return;

  // ---------------------------------------------------------------- mạng
  function brain() {
    try { return (window.JoyceSessions && window.JoyceSessions.brain()) || "brain"; }
    catch (e) { return "brain"; }
  }
  function getJson(url) {
    return fetch(url, { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }
  function post(url, fields) {
    var fd = new FormData();
    Object.keys(fields || {}).forEach(function (k) { fd.append(k, fields[k]); });
    return fetch(url, { method: "POST", body: fd, credentials: "same-origin" })
      .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
      .catch(function () { return { ok: false, error: "network" }; });
  }
  function chatId() {
    try {
      var id = window.JoyceSessions && window.JoyceSessions.current && window.JoyceSessions.current();
      return id ? "web:" + id : "";
    } catch (e) { return ""; }
  }
  function maNgau() {
    var s = "";
    for (var i = 0; i < 16; i += 1) s += Math.floor(Math.random() * 16).toString(16);
    return s;
  }

  var cache = { brain: null, data: null, cho: null };
  function nap(ep) {
    var b = brain();
    if (!ep && cache.data && cache.brain === b) return Promise.resolve(cache.data);
    if (cache.cho && cache.choBrain === b) return cache.cho;
    cache.choBrain = b;
    cache.cho = getJson("/viec-mau?brain=" + encodeURIComponent(b)).then(function (d) {
      cache.cho = null;
      if (d && d.ok) { cache.brain = b; cache.data = d; }
      return d && d.ok ? d : null;
    });
    return cache.cho;
  }

  // ---------------------------------------------------------------- việc đang chạy
  var chay = null;   // {slug,title,values,key,brain,seenBusy,asked}

  function gui(item, values) {
    var text = ghepLenh(item, values);
    chay = { slug: item.slug, title: item.title, values: values, key: maNgau(), brain: brain(), seenBusy: false, asked: false };
    if (typeof window.JoyceSend === "function") window.JoyceSend(text);
  }

  // ---------------------------------------------------------------- form
  function truongHtml(o, i) {
    var id = "vmf" + i, req = o.required ? ' <span class="vm-req" aria-hidden="true">*</span>' : "";
    var lab = '<label for="' + id + '">' + esc(o.label) + req + "</label>";
    if (o.type === "select") {
      return '<div class="vm-f">' + lab + '<select id="' + id + '" data-k="' + esc(o.key) + '">'
        + '<option value=""></option>' + (o.options || []).map(function (x) {
          return '<option value="' + esc(x) + '">' + esc(x) + "</option>";
        }).join("") + "</select></div>";
    }
    if (o.type === "longtext") {
      return '<div class="vm-f">' + lab + '<textarea id="' + id + '" rows="3" data-k="' + esc(o.key) + '"></textarea></div>';
    }
    return '<div class="vm-f">' + lab + '<input id="' + id + '" type="text" data-k="' + esc(o.key) + '" autocomplete="off"></div>';
  }

  function formHtml(item) {
    return '<form class="vm-form" novalidate>'
      + '<div class="vm-ft"><b>' + esc(item.title) + "</b>"
      + (item.sop ? '<span class="vm-sop" title="' + esc(item.sop) + '">' + ic("book-open") + esc(tw("vm.has_sop")) + "</span>" : "")
      + "</div>"
      + (item.inputs || []).map(truongHtml).join("")
      + '<div class="vm-err" role="alert" hidden></div>'
      + '<div class="vm-fa"><button type="submit" class="vm-go">' + esc(tw("vm.send")) + "</button>"
      + '<button type="button" class="vm-ghost" data-vm="cancel">' + esc(tw("vm.cancel")) + "</button>"
      + '<span class="vm-tools"><button type="button" class="vm-ghost" data-vm="edit">' + esc(tw("vm.edit")) + "</button>"
      + '<button type="button" class="vm-ghost vm-danger" data-vm="del">' + esc(tw("vm.del")) + "</button></span></div>"
      + "</form>";
  }

  function oHtml(o, i) {
    return '<div class="vm-orow" data-k="' + esc(o.key || "") + '" data-type="' + esc(o.type || "text") + '"'
      + (o.options ? ' data-opts="' + esc(JSON.stringify(o.options)) + '"' : "") + ">"
      + '<input type="text" class="vm-olab" value="' + esc(o.label || "") + '" placeholder="' + esc(tw("vm.in_ph")) + '" maxlength="40">'
      + '<label class="vm-oreq"><input type="checkbox"' + (o.required ? " checked" : "") + "> " + esc(tw("vm.in_req")) + "</label>"
      + '<button type="button" class="vm-ghost" data-vm="orm" title="' + esc(tw("vm.in_rm")) + '">&times;</button></div>';
  }

  function editHtml(item, nhomCo, la_moi) {
    var it = mauPhieu(item);
    return '<form class="vm-form vm-edit" novalidate>'
      + '<div class="vm-ft"><b>' + esc(tw(la_moi ? "vm.add_t" : "vm.edit_t")) + "</b></div>"
      + '<div class="vm-f"><label for="vme1">' + esc(tw("vm.f_title")) + '</label><input id="vme1" type="text" data-e="title" maxlength="80" value="' + esc(it.title) + '"></div>'
      + '<div class="vm-f"><label for="vme2">' + esc(tw("vm.f_group")) + '</label><input id="vme2" type="text" data-e="group" maxlength="40" list="vmGroups" value="' + esc(it.group) + '">'
      + '<datalist id="vmGroups">' + nhomCo.map(function (g) { return '<option value="' + esc(g) + '">'; }).join("") + "</datalist></div>"
      + '<div class="vm-f"><label for="vme3">' + esc(tw("vm.f_prompt")) + '</label><textarea id="vme3" rows="4" data-e="prompt">' + esc(it.prompt) + "</textarea>"
      + '<div class="vm-hint">' + esc(tw("vm.f_prompt_hint")) + "</div></div>"
      + '<div class="vm-f"><label>' + esc(tw("vm.f_inputs")) + '</label><div class="vm-olist">' + (it.inputs || []).map(oHtml).join("") + "</div>"
      + '<button type="button" class="vm-ghost" data-vm="oadd">+ ' + esc(tw("vm.in_add")) + "</button></div>"
      + '<div class="vm-err" role="alert" hidden></div>'
      + '<div class="vm-fa"><button type="submit" class="vm-go">' + esc(tw("vm.save")) + "</button>"
      + '<button type="button" class="vm-ghost" data-vm="cancel">' + esc(tw("vm.cancel")) + "</button></div></form>";
  }

  function docOs(form) {
    var dung = [], out = [];
    Array.prototype.forEach.call(form.querySelectorAll(".vm-orow"), function (row) {
      var nhan = row.querySelector(".vm-olab").value.trim();
      if (!nhan || out.length >= TOI_DA_O) return;
      var k = row.getAttribute("data-k") || khoaO(nhan, dung);
      if (dung.indexOf(k) >= 0) k = khoaO(nhan, dung);
      dung.push(k);
      var o = { key: k, label: nhan, type: row.getAttribute("data-type") || "text", required: row.querySelector("input[type=checkbox]").checked };
      if (row.getAttribute("data-opts")) o.options = JSON.parse(row.getAttribute("data-opts"));
      out.push(o);
    });
    return out;
  }

  // Gắn khay/menu: host là phần tử trống, ctx = {close()}. Trả {refresh()}.
  function mount(host, ctx) {
    ctx = ctx || {};
    var data = null, mo = {};

    function baoLoi(form, msg) {
      var e = form.querySelector(".vm-err");
      if (!e) return;
      e.textContent = msg || ""; e.hidden = !msg;
    }

    function veChip() {
      host.classList.remove("vm-formmode");
      var chia = chiaNhom(data.items);
      var n = data.items.length;
      var gap = false;
      try {
        var luu = localStorage.getItem(KHOA_GAP);
        gap = luu == null ? window.innerWidth < 700 : luu === "1";   // điện thoại: thu gọn sẵn
      } catch (e) {}
      var html = ctx.close ? "" : '<div class="vm-head"><span class="vm-hi">' + ic("list-checks") + "</span><b>" + esc(tw("vm.title")) + "</b>"
        + '<span class="vm-n">' + esc(tw("vm.count", { n: n, brain: data.brain || "" })) + "</span>"
        + (ctx.close ? "" : '<button type="button" class="vm-fold" data-vm="fold" aria-expanded="' + (!gap) + '" title="' + esc(tw("vm.fold")) + '">' + ic(gap ? "chevron-down" : "chevron-up") + "</button>")
        + "</div>";
      if (gap && !ctx.close) { host.innerHTML = html; return; }
      html += '<div class="vm-body">';
      if (!chia.length) html += '<div class="vm-empty">' + esc(tw("vm.empty")) + "</div>";
      chia.forEach(function (g) {
        var hien = mo[g.name] ? g.items : g.items.slice(0, TOI_DA_CHIP);
        html += '<div class="vm-g"><div class="vm-gn">' + esc(g.name) + '</div><div class="vm-chips">'
          + hien.map(function (it) {
            return '<button type="button" class="vm-chip" data-vm="run" data-slug="' + esc(it.slug) + '" title="' + esc(it.title) + '">'
              + ic(it.icon || "message-circle") + "<span>" + esc(it.title) + "</span></button>";
          }).join("")
          + (g.items.length > hien.length ? '<button type="button" class="vm-chip vm-more" data-vm="more" data-g="' + esc(g.name) + '">' + esc(tw("vm.more", { n: g.items.length - hien.length })) + "</button>" : "")
          + '<button type="button" class="vm-chip vm-plus" data-vm="add" data-g="' + esc(g.name) + '" title="' + esc(tw("vm.add_tip")) + '" aria-label="' + esc(tw("vm.add_tip")) + '">+</button>'
          + "</div></div>";
      });
      html += '<div class="vm-g"><div class="vm-chips"><button type="button" class="vm-chip vm-plus vm-newg" data-vm="add" data-g="">+ '
        + esc(tw(chia.length ? "vm.new_group" : "vm.add_first")) + "</button></div></div></div>";
      host.innerHTML = html;
    }

    function timViec(slug) {
      return data.items.filter(function (i) { return i.slug === slug; })[0];
    }

    function veForm(item) {
      host.classList.add("vm-formmode");
      host.innerHTML = formHtml(item);
      var f = host.querySelector("form");
      var dau = f.querySelector("input,textarea,select"); if (dau) dau.focus();
      f.addEventListener("submit", function (e) {
        e.preventDefault();
        var values = {};
        Array.prototype.forEach.call(f.querySelectorAll("[data-k]"), function (el) { values[el.getAttribute("data-k")] = el.value; });
        var ts = thieu(item, values);
        if (ts.length) { baoLoi(f, tw("vm.need", { ten: ts.join(", ") })); return; }
        gui(item, values);
        if (ctx.close) ctx.close();
        veChip();
      });
      f.querySelector('[data-vm="cancel"]').addEventListener("click", function () { veChip(); });
      f.querySelector('[data-vm="edit"]').addEventListener("click", function () { veSua(item, false); });
      f.querySelector('[data-vm="del"]').addEventListener("click", function () {
        if (!window.confirm(tw("vm.del_ask", { ten: item.title }))) return;
        post("/viec-mau/delete", { brain: brain(), slug: item.slug }).then(function (r) {
          if (!r || !r.ok) { baoLoi(f, (r && r.error) || tw("vm.fail")); return; }
          lamMoi();
        });
      });
    }

    function veSua(item, laMoi, nhomMacDinh) {
      var it = item ? JSON.parse(JSON.stringify(item)) : { title: "", group: nhomMacDinh || "", prompt: "", inputs: [] };
      host.classList.add("vm-formmode");
      host.innerHTML = editHtml(it, chiaNhom(data.items).map(function (g) { return g.name; }).filter(Boolean), laMoi);
      var f = host.querySelector("form");
      f.querySelector("[data-e=title]").focus();
      f.addEventListener("click", function (e) {
        var b = e.target.closest ? e.target.closest("[data-vm]") : null;
        if (!b) return;
        var act = b.getAttribute("data-vm");
        if (act === "cancel") veChip();
        else if (act === "orm") b.closest(".vm-orow").remove();
        else if (act === "oadd") {
          var lst = f.querySelector(".vm-olist");
          if (lst.children.length >= TOI_DA_O) { baoLoi(f, tw("vm.in_max", { n: TOI_DA_O })); return; }
          lst.insertAdjacentHTML("beforeend", oHtml({ label: "", required: false }, lst.children.length));
          lst.lastElementChild.querySelector(".vm-olab").focus();
        }
      });
      f.addEventListener("submit", function (e) {
        e.preventDefault();
        var inputs = docOs(f);
        var campos = {
          brain: brain(), slug: laMoi ? "" : it.slug, title: f.querySelector("[data-e=title]").value.trim(),
          group: f.querySelector("[data-e=group]").value.trim(), icon: it.icon || "",
          prompt: themO(f.querySelector("[data-e=prompt]").value, inputs), inputs: JSON.stringify(inputs),
          route: it.route || "auto", sop: it.sop || "",
        };
        if (!campos.title) { baoLoi(f, tw("vm.need_title")); return; }
        if (!campos.prompt.trim()) { baoLoi(f, tw("vm.need_prompt")); return; }
        if (!laMoi && it.origin === "seed") campos.hidden = "";
        post("/viec-mau", campos).then(function (r) {
          if (!r || !r.ok) { baoLoi(f, (r && r.error) || tw("vm.fail")); return; }
          lamMoi();
        });
      });
    }

    function lamMoi() {
      return nap(true).then(function (d) {
        if (!d) { host.innerHTML = ""; return; }
        data = d; veChip();
      });
    }

    host.addEventListener("click", function (e) {
      var b = e.target.closest ? e.target.closest("[data-vm]") : null;
      if (!b || !data) return;
      var act = b.getAttribute("data-vm");
      if (act === "run") {
        var it = timViec(b.getAttribute("data-slug"));
        if (!it) return;
        if (!(it.inputs || []).length) { gui(it, {}); if (ctx.close) ctx.close(); return; }
        veForm(it);
      } else if (act === "add") veSua(null, true, b.getAttribute("data-g"));
      else if (act === "more") { mo[b.getAttribute("data-g")] = true; veChip(); }
      else if (act === "fold") {
        try {
          var cu = localStorage.getItem(KHOA_GAP);
          var dangGap = cu == null ? window.innerWidth < 700 : cu === "1";
          localStorage.setItem(KHOA_GAP, dangGap ? "0" : "1");
        } catch (err) {}
        veChip();
      }
    });

    return {
      refresh: function () {
        return nap(false).then(function (d) {
          if (!d) { host.innerHTML = ""; return false; }
          data = d; veChip(); return true;
        });
      },
      lamMoi: lamMoi,
    };
  }

  // ---------------------------------------------------------------- khay trên ô nhập
  var tray = null, tm = null, daNapCho = null;

  function chatTrong() {
    var area = document.getElementById("chatArea");
    if (!area) return false;
    return !area.querySelector(":scope > *:not(.chat-kb)");
  }

  function dongBo() {
    var el = document.getElementById("vmTray");
    if (!el) return;
    if (!chatTrong()) { el.hidden = true; return; }
    if (!tray || tray.host !== el) { tray = { host: el, m: mount(el, null) }; daNapCho = null; }
    var b = brain();
    if (daNapCho === b && !el.hidden) return;
    daNapCho = b;
    tray.m.refresh().then(function (ok) {
      el.hidden = !(ok && chatTrong());
    });
  }

  // ---------------------------------------------------------------- thanh "Đã xong?"
  function viecCuoiCau() {
    var area = document.getElementById("chatArea");
    var bs = area ? area.querySelectorAll(".msg-joyce .bubble") : [];
    var b = bs.length ? bs[bs.length - 1] : null;
    return b ? String(b.innerText || b.textContent || "").trim().slice(0, 8000) : "";
  }

  function hienThanhXong() {
    var area = document.getElementById("chatArea");
    if (!area || !chay) return;
    var viec = chay;
    var bar = document.createElement("div");
    bar.className = "vm-xong";
    bar.innerHTML = '<span class="vm-xi">' + ic("circle-check") + "</span>"
      + '<span class="vm-xt">' + esc(tw("vm.ask_done", { ten: viec.title })) + "</span>"
      + '<button type="button" class="vm-go" data-vx="done">' + esc(tw("vm.done")) + "</button>"
      + '<button type="button" class="vm-ghost" data-vx="no">' + esc(tw("vm.not_yet")) + "</button>";
    area.appendChild(bar);
    try { bar.scrollIntoView({ block: "nearest" }); } catch (e) {}
    bar.addEventListener("click", function (e) {
      var b = e.target.closest ? e.target.closest("[data-vx]") : null;
      if (!b) return;
      var act = b.getAttribute("data-vx");
      if (act === "no") { bar.remove(); return; }
      if (act === "done") {
        b.disabled = true;
        post("/viec-mau/xong", {
          brain: viec.brain, slug: viec.slug, title: viec.title, values: JSON.stringify(viec.values || {}),
          result: viecCuoiCau(), chat_id: chatId(), key: viec.key,
        }).then(function (r) {
          if (!r || !r.ok) { b.disabled = false; bar.querySelector(".vm-xt").textContent = (r && r.error) || tw("vm.fail"); return; }
          bar.innerHTML = '<span class="vm-xi">' + ic("circle-check") + "</span><span class=\"vm-xt\">"
            + esc(tw(r.chung_cat && r.chung_cat.ok ? "vm.done_ok_learn" : "vm.done_ok")) + "</span>"
            + '<button type="button" class="vm-ghost" data-vx="learn">' + esc(tw("vm.learn")) + "</button>"
            + '<button type="button" class="vm-ghost" data-vx="board">' + esc(tw("vm.open_board")) + "</button>";
        });
      } else if (act === "learn") {
        b.disabled = true;
        post("/viec-mau/ghi-nho", { brain: viec.brain, slug: viec.slug, chat_id: chatId() }).then(function (r) {
          bar.querySelector(".vm-xt").textContent = tw(r && r.ok ? "vm.learn_ok" : "vm.learn_none");
          b.remove();
        });
      } else if (act === "board") {
        try { window.Alpine.store("nav").go("kanban"); } catch (err) {}
      }
    });
  }

  function theoDoiBusy() {
    var area = document.getElementById("chatArea");
    if (!area || area.__vmObs) return;
    area.__vmObs = new MutationObserver(function (ms) {
      for (var i = 0; i < ms.length; i += 1) {
        if (ms[i].type === "attributes") {
          if (!chay || chay.asked) continue;
          var busy = area.classList.contains("busy");
          if (busy) chay.seenBusy = true;
          else if (chay.seenBusy) { chay.asked = true; hienThanhXong(); }
        }
      }
      dongBo();
    });
    area.__vmObs.observe(area, { childList: true, attributes: true, attributeFilter: ["class"] });
  }

  // ---------------------------------------------------------------- menu "+" của ô chat
  function dangKyMenu() {
    var reg = window.JoyceComposerMenu;
    if (!reg || !reg.register) return false;
    reg.register({
      id: "viec_mau", order: 25, label: "vm.menu",
      icon: '<svg class="cp-ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6h11M9 12h11M9 18h11M3.5 6l1 1 2-2M3.5 12l1 1 2-2M3.5 18l1 1 2-2"/></svg>',
      panel: function (el, ctx) {
        el.classList.add("vm-menu");
        var m = mount(el, { close: ctx && ctx.close });
        m.refresh();
      },
    });
    return true;
  }

  function css() {
    if (document.getElementById("vm-css")) return;
    var s = document.createElement("style");
    s.id = "vm-css";
    s.textContent = [
      ".vm-tray{margin:0 0 8px;padding:10px 12px;border:1px solid var(--line);border-radius:14px;background:var(--card);max-height:min(34vh,300px);overflow:auto}",
      ".vm-tray[hidden]{display:none}",
      ".vm-tray.vm-formmode{max-height:62vh}",
      ".vm-head{display:flex;align-items:center;gap:8px;color:var(--text);font-size:14px}",
      ".vm-hi{display:inline-flex;color:var(--accent)}",
      ".vm-hi svg{width:16px;height:16px}",
      ".vm-n{color:var(--text3);font-size:12.5px;margin-left:2px;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
      ".vm-fold{border:0;background:transparent;color:var(--text3);cursor:pointer;padding:2px 4px;border-radius:8px}",
      ".vm-fold:hover{color:var(--text);background:var(--wash)}",
      ".vm-fold svg{width:16px;height:16px}",
      ".vm-body{margin-top:8px;display:flex;flex-direction:column;gap:8px}",
      ".vm-gn{font-size:12px;color:var(--text3);margin-bottom:4px;letter-spacing:.2px}",
      ".vm-chips{display:flex;flex-wrap:wrap;gap:6px}",
      ".vm-chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--wash);color:var(--text);",
      "border-radius:999px;padding:6px 12px;font-size:13px;cursor:pointer;line-height:1.2;max-width:100%}",
      ".vm-chip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
      ".vm-chip svg{width:14px;height:14px;flex:none;color:var(--accent)}",
      ".vm-chip:hover,.vm-chip:focus-visible{border-color:var(--accent);outline:none}",
      ".vm-plus{color:var(--accent);border-style:dashed;background:transparent;font-weight:600;padding:6px 12px}",
      ".vm-more{color:var(--text2)}",
      ".vm-empty{color:var(--text2);font-size:13px}",
      ".vm-form{display:flex;flex-direction:column;gap:10px;margin-top:2px}",
      ".vm-ft{display:flex;align-items:center;gap:8px;color:var(--text);font-size:14px}",
      ".vm-sop{display:inline-flex;align-items:center;gap:4px;color:var(--text3);font-size:12px}",
      ".vm-sop svg{width:13px;height:13px}",
      ".vm-f{display:flex;flex-direction:column;gap:4px}",
      ".vm-f label{font-size:12.5px;color:var(--text2)}",
      ".vm-req{color:var(--danger-ink)}",
      ".vm-f input[type=text],.vm-f textarea,.vm-f select{width:100%;box-sizing:border-box;border:1px solid var(--line);border-radius:10px;",
      "padding:8px 10px;background:var(--card);color:var(--text);font:inherit;font-size:14px}",
      ".vm-f textarea{resize:vertical;min-height:64px}",
      ".vm-f input:focus,.vm-f textarea:focus,.vm-f select:focus{outline:none;border-color:var(--accent)}",
      ".vm-hint{font-size:12px;color:var(--text3)}",
      ".vm-err{color:var(--danger-ink);font-size:13px}",
      ".vm-fa{display:flex;align-items:center;gap:8px;flex-wrap:wrap}",
      ".vm-tools{margin-left:auto;display:flex;gap:4px}",
      ".vm-go{border:0;border-radius:10px;padding:8px 16px;background:var(--accent);color:var(--on-accent);font:inherit;font-size:14px;cursor:pointer}",
      ".vm-go:disabled{opacity:.6;cursor:default}",
      ".vm-ghost{border:0;background:transparent;color:var(--text2);border-radius:8px;padding:6px 10px;font:inherit;font-size:13px;cursor:pointer}",
      ".vm-ghost:hover{background:var(--wash);color:var(--text)}",
      ".vm-danger:hover{color:var(--danger-ink)}",
      ".vm-orow{display:flex;align-items:center;gap:6px;margin-bottom:6px}",
      ".vm-olab{flex:1;min-width:0}",
      ".vm-oreq{display:flex;align-items:center;gap:4px;font-size:12.5px;color:var(--text2);white-space:nowrap}",
      ".vm-xong{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0;padding:10px 12px;border:1px solid var(--line);",
      "border-radius:12px;background:var(--card);color:var(--text);font-size:14px}",
      ".vm-xi{display:inline-flex;color:var(--ok-ink)}",
      ".vm-xi svg{width:18px;height:18px}",
      ".vm-xt{flex:1;min-width:160px}",
      ".vm-menu{padding:8px 10px;min-width:260px;max-width:340px;max-height:60vh;overflow:auto}",
      ".vm-menu .vm-head{font-size:13px}",
    ].join("\n");
    document.head.appendChild(s);
  }

  function boot() {
    css();
    var area = document.getElementById("chatArea");
    if (!area || !document.getElementById("vmTray")) { setTimeout(boot, 500); return; }
    theoDoiBusy();
    dongBo();
    if (!dangKyMenu()) setTimeout(dangKyMenu, 800);
    // Đổi brain ở đầu trang không phát sự kiện riêng: bắt ở lần bấm kế tiếp rồi so tên brain.
    document.addEventListener("pointerdown", function () {
      clearTimeout(tm);
      tm = setTimeout(function () { if (daNapCho !== null && daNapCho !== brain()) { cache.data = null; dongBo(); } }, 350);
    }, true);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) dongBo(); });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

  window.JoyceVietMau = Object.assign({ mount: mount, refresh: dongBo }, pure);
})();
