/* JoyceDialog — hộp thoại/thông báo nội bộ thay alert() trình duyệt.
 *
 * VÌ SAO CÓ FILE NÀY: alert() native chặn tab, trông ngoài design, và không style được.
 * Trong app có ~80 chỗ gọi alert() rải rác — thay vì sửa từng chỗ, file này override
 * window.alert: mọi call-site cũ tự động thành popup Joyce mà không sửa một dòng nào.
 * alert không trả giá trị nên đổi sang hàm không-blocking là an toàn.
 *
 * API:
 *   JoyceDialog.alert(msg, kind?)          — kind: "err" | "ok" | "info" (tự đoán theo chữ)
 *   JoyceDialog.confirm(msg, opts?)        — Promise<boolean>, nút OK / Huỷ
 *   JoyceDialog.toast(msg, isErr?)         — thông báo tự tắt (window.toast cũng trỏ vào đây)
 *
 * Hàng đợi: alert gọi chồng nhau thì xếp hàng lần lượt (giữ đúng nghĩa serial của native).
 * Escape / click nền / Enter đóng. CSS dùng biến theme sẵn có nên tự đổi sáng/tối.
 */
(function () {
  "use strict";

  var hangDoi = [];      // [{msg, kind, resolve}] — alert/confirm chờ lượt hiện
  var dangMo = false;
  var elWrap = null;     // overlay gốc, tạo lười lần đầu

  function ti(k, duPhong) {
    try { var s = window.t && window.t(k); return (s && s !== k) ? s : duPhong; }
    catch (e) { return duPhong; }
  }

  function doanLoai(msg, kind) {
    if (kind) return kind;
    var m = String(msg || "").toLowerCase();
    if (/lỗi|không|fail|error|err_|chặn|từ chối|thiếu|sai|hỏng|chưa /.test(m)) return "err";
    if (/đã |thành công|xong|saved|deleted|created|copied/.test(m)) return "ok";
    return "info";
  }

  var ICON = {
    err: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="7" x2="12" y2="13"/><circle cx="12" cy="17" r="0.6" fill="currentColor"/></svg>',
    ok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><polyline points="8.5 12.5 11 15 15.5 9.5"/></svg>',
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="11" x2="12" y2="16"/><circle cx="12" cy="8" r="0.6" fill="currentColor"/></svg>',
  };

  function css() {
    if (document.getElementById("jd-css")) return;
    var s = document.createElement("style");
    s.id = "jd-css";
    s.textContent =
      ".jd-overlay{position:fixed;inset:0;background:var(--scrim,rgba(8,10,16,.55));backdrop-filter:blur(6px);" +
        "z-index:9990;display:flex;align-items:center;justify-content:center;padding:20px;" +
        "animation:jdIn .14s ease-out}" +
      "@keyframes jdIn{from{opacity:0}to{opacity:1}}" +
      ".jd-card{width:min(92vw,460px);background:var(--bg2,#1b1f2a);border:1px solid var(--border,rgba(255,255,255,.12));" +
        "border-radius:14px;box-shadow:var(--shadow-3,0 18px 50px rgba(0,0,0,.5));overflow:hidden;" +
        "animation:jdPop .16s ease-out}" +
      "@keyframes jdPop{from{opacity:0;transform:scale(.96) translateY(6px)}to{opacity:1;transform:none}}" +
      ".jd-head{display:flex;align-items:center;gap:10px;padding:15px 18px 0}" +
      ".jd-ico{flex:none;width:30px;height:30px;border-radius:9px;display:flex;align-items:center;justify-content:center}" +
      ".jd-ico svg{width:17px;height:17px}" +
      ".jd-ico.err{color:var(--red,#f87171);background:rgba(248,113,113,.14)}" +
      ".jd-ico.ok{color:var(--accent,#22d3ee);background:rgba(34,211,238,.13)}" +
      ".jd-ico.info{color:var(--accent,#22d3ee);background:rgba(34,211,238,.13)}" +
      ".jd-title{flex:1;font-size:16px;font-weight:700;color:var(--text,#e8eaf0);line-height:1.3}" +
      ".jd-x{flex:none;width:28px;height:28px;border-radius:7px;border:1px solid var(--border,rgba(255,255,255,.12));" +
        "background:var(--bg3,#232838);color:var(--text2,#9fb0cf);cursor:pointer;font-size:15px;line-height:1}" +
      ".jd-x:hover{color:var(--accent,#22d3ee);border-color:var(--accent,#22d3ee)}" +
      ".jd-body{padding:12px 18px 4px;font-size:14.5px;line-height:1.6;color:var(--text2,#9fb0cf);" +
        "white-space:pre-wrap;word-break:break-word;max-height:52vh;overflow-y:auto}" +
      ".jd-body::-webkit-scrollbar{width:5px}.jd-body::-webkit-scrollbar-thumb{background:var(--border,#39405180);border-radius:3px}" +
      ".jd-inp{display:block;width:100%;box-sizing:border-box;margin-top:10px;padding:9px 12px;border-radius:8px;font-family:inherit;font-size:15px;" +
        "color:var(--text,#e8eaf0);background:var(--bg,#141824);border:1px solid var(--border,rgba(255,255,255,.14));outline:none}" +
      ".jd-inp:focus{border-color:var(--accent,#22d3ee)}" +
      ".jd-foot{display:flex;justify-content:flex-end;gap:9px;padding:14px 18px 16px}" +
      ".jd-btn{padding:8px 20px;border-radius:8px;font-size:14.5px;font-weight:600;cursor:pointer;font-family:inherit;" +
        "border:1px solid var(--border,rgba(255,255,255,.14));background:var(--bg3,#232838);color:var(--text,#e8eaf0)}" +
      ".jd-btn:hover{opacity:.88}" +
      ".jd-btn.pri{background:var(--accent-solid,#22d3ee);border-color:var(--accent-solid,#22d3ee);color:var(--on-accent,#06232a)}" +
      ".jd-btn.pri.err{background:var(--red,#f87171);border-color:var(--red,#f87171);color:#fff}" +
      // Toast — trượt từ đỉnh, tự tắt
      ".jd-toast{position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:9999;display:flex;align-items:center;gap:10px;" +
        "max-width:min(92vw,560px);padding:11px 16px;border-radius:11px;font-size:14.5px;line-height:1.45;" +
        "background:var(--bg2,#1b1f2a);border:1px solid var(--border,rgba(255,255,255,.14));color:var(--text,#e8eaf0);" +
        "box-shadow:var(--shadow-3,0 14px 40px rgba(0,0,0,.45));animation:jdIn .15s ease-out}" +
      ".jd-toast.err{border-color:rgba(248,113,113,.45)}.jd-toast.err .jd-ico{color:var(--red,#f87171)}" +
      ".jd-toast .jd-ico{width:20px;height:20px;flex:none}.jd-toast .jd-ico svg{width:16px;height:16px}" +
      ".jd-toast.out{opacity:0;transform:translateX(-50%) translateY(-8px);transition:.25s}" +
      "@media(max-width:520px){.jd-card{width:94vw}.jd-body{font-size:14px}}";
    document.head.appendChild(s);
  }

  function dong() {
    if (elWrap) { elWrap.remove(); elWrap = null; }
    dangMo = false;
    if (hangDoi.length) setTimeout(chayTiep, 60);
  }

  function chayTiep() {
    if (dangMo || !hangDoi.length) return;
    var v = hangDoi.shift();
    dangMo = true;
    css();
    var loai = doanLoai(v.msg, v.kind);

    elWrap = document.createElement("div");
    elWrap.className = "jd-overlay";
    elWrap.setAttribute("role", "dialog");
    elWrap.setAttribute("aria-modal", "true");

    var card = document.createElement("div");
    card.className = "jd-card";

    var head = document.createElement("div");
    head.className = "jd-head";
    head.innerHTML =
      '<span class="jd-ico ' + loai + '">' + (ICON[loai] || ICON.info) + '</span>' +
      '<span class="jd-title"></span>' +
      '<button class="jd-x" aria-label="' + ti("common.close", "Đóng") + '">✕</button>';
    head.querySelector(".jd-title").textContent =
      v.title || (loai === "err" ? ti("jd.err", "Có lỗi") : loai === "ok" ? ti("jd.ok", "Xong") : ti("jd.info", "Thông báo"));

    var body = document.createElement("div");
    body.className = "jd-body";
    body.textContent = String(v.msg == null ? "" : v.msg);

    var input = null;
    if (v.isPrompt) {
      input = document.createElement("input");
      input.className = "jd-inp";
      input.type = "text";
      input.value = v.defVal == null ? "" : String(v.defVal);
      body.appendChild(input);
    }

    var foot = document.createElement("div");
    foot.className = "jd-foot";
    var btns = [];
    if (v.isConfirm || v.isPrompt) {
      var huy = document.createElement("button");
      huy.className = "jd-btn";
      huy.textContent = ti("common.cancel", "Huỷ");
      huy.onclick = function () { dong(); v.resolve(v.isPrompt ? null : false); };
      btns.push(huy);
    }
    var ok = document.createElement("button");
    ok.className = "jd-btn pri" + (loai === "err" ? " err" : "");
    ok.textContent = v.okText || ti("common.ok", "OK");
    ok.onclick = function () { dong(); v.resolve(v.isPrompt ? (input ? input.value : "") : true); };
    btns.push(ok);
    btns.forEach(function (b) { foot.appendChild(b); });

    card.appendChild(head); card.appendChild(body); card.appendChild(foot);
    elWrap.appendChild(card);
    document.body.appendChild(elWrap);
    setTimeout(function () { (input || ok).focus(); if (input) input.select(); }, 30);

    var thoat = function (val) { dong(); v.resolve(val); };
    var valNeuDong = v.isPrompt ? null : !v.isConfirm;
    elWrap.addEventListener("click", function (e) { if (e.target === elWrap) thoat(valNeuDong); });
    head.querySelector(".jd-x").onclick = function () { thoat(valNeuDong); };
    function phim(e) {
      if (!elWrap || !document.body.contains(elWrap)) { document.removeEventListener("keydown", phim); return; }
      if (e.key === "Escape") thoat(valNeuDong);
      else if (e.key === "Enter") { e.preventDefault(); ok.click(); }
    }
    document.addEventListener("keydown", phim);
  }

  var JoyceDialog = {
    alert: function (msg, kind) {
      return new Promise(function (res) { hangDoi.push({ msg: msg, kind: kind, isConfirm: false, resolve: res }); chayTiep(); });
    },
    confirm: function (msg, opts) {
      opts = opts || {};
      return new Promise(function (res) { hangDoi.push({ msg: msg, kind: opts.kind || "info", title: opts.title, okText: opts.okText, isConfirm: true, resolve: res }); chayTiep(); });
    },
    prompt: function (msg, defVal, opts) {
      opts = opts || {};
      return new Promise(function (res) { hangDoi.push({ msg: msg, kind: opts.kind || "info", title: opts.title, okText: opts.okText, defVal: defVal, isPrompt: true, resolve: res }); chayTiep(); });
    },
    toast: function (msg, isErr) {
      css();
      var el = document.createElement("div");
      el.className = "jd-toast" + (isErr ? " err" : "");
      el.setAttribute("role", "status");
      el.innerHTML = '<span class="jd-ico">' + (isErr ? ICON.err : ICON.ok) + '</span>';
      var tx = document.createElement("span");
      tx.textContent = String(msg == null ? "" : msg);
      el.appendChild(tx);
      document.body.appendChild(el);
      setTimeout(function () { el.classList.add("out"); setTimeout(function () { el.remove(); }, 280); }, 3200);
    },
  };

  window.JoyceDialog = JoyceDialog;
  // 80+ call-site alert() rải khắp app — override một lần, tất cả tự thành popup Joyce.
  // Giữ native dưới chân (JoyceDialog._nativeAlert) cho trường hợp DOM chưa sẵn (lỗi rất sớm).
  JoyceDialog._nativeAlert = window.alert.bind(window);
  window.alert = function (msg) {
    if (!document.body) return JoyceDialog._nativeAlert(msg);
    JoyceDialog.alert(msg);
  };
  // toast() đã được gọi ở vài chỗ (vd đổi ngôn ngữ) mà chưa có định nghĩa — gắn luôn.
  window.toast = JoyceDialog.toast;
})();
