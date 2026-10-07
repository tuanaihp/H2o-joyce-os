/* Popup micro riêng của Joyce thay cho alert() của trình duyệt (dashboard/mic-dialog.js).

       node tests/js/test_mic_popup.js

   Chủ repo (2026-10-05, kèm ảnh): bật mic mà hiện hộp "ballet-sky...trycloudflare.com says"
   của trình duyệt. Muốn popup của chính app. Kiểm:
     - Lỗi mic (not-allowed / audio-capture / service / not-supported) đi qua JoyceMicDialog,
       alert() chỉ còn là đường lui khi file popup chưa nạp.
     - Nút mic hỏi gate() TRƯỚC khi bật cuộc gọi: quyền chưa hỏi -> popup giải thích trước,
       quyền đang chặn -> báo ngay, không mở cuộc gọi chắc chắn hỏng.
     - Popup nhận ra lúc người dùng cấp lại quyền (Permissions API onchange) và gọi lại.
     - Đủ chuỗi vi + en, không emoji, nạp trước app.js. */
const fs = require("fs");
const path = require("path");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const DLG = D("mic-dialog.js");
const APP = D("app.js");
const HTML = D("index.html");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));

let fails = [];
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) fails.push(name);
}

const iD = HTML.indexOf("/static/mic-dialog.js"), iA = HTML.indexOf("/static/app.js");
check("index.html nạp mic-dialog.js TRƯỚC app.js", iD > 0 && iD < iA);

const alertMic = APP.slice(APP.indexOf("function alertMic(err)"), APP.indexOf('voiceBtn.addEventListener("click"'));
const iPopup = alertMic.indexOf("window.JoyceMicDialog.explain(err)");
const iAlert = alertMic.indexOf("alert(window");
check("alertMic dùng popup của app trước", iPopup > 0 && iPopup < iAlert);
check("cả bốn lỗi mic cứng đều đi qua popup",
  ["not-allowed", "audio-capture", "service-not-allowed", "not-supported"].every((e) => alertMic.slice(0, iPopup).indexOf('"' + e + '"') > 0));

const click = APP.slice(APP.indexOf('voiceBtn.addEventListener("click"'), APP.indexOf("handsFree = !handsFree;", APP.indexOf('voiceBtn.addEventListener("click"')));
check("nút mic hỏi gate() trước khi bật cuộc gọi",
  /if \(!handsFree && window\.JoyceMicDialog && !window\.JoyceMicDialog\.gate\(\)\) return;/.test(click));
check("trình duyệt không hỗ trợ giọng -> popup, không alert trần", /JoyceMicDialog\.explain\("voice_unsupported"\)/.test(click));

check("gate: quyền chưa hỏi -> popup giải thích", /if \(perm === "prompt"\) \{\s*open\("ask"/.test(DLG));
check("gate: quyền đang chặn -> popup hướng dẫn, không gọi", /if \(perm === "denied"\) \{/.test(DLG));
check("theo dõi quyền qua Permissions API", /navigator\.permissions\.query\(\{ name: "microphone" \}\)/.test(DLG) && /st\.onchange/.test(DLG));
check("cấp lại quyền lúc popup mở -> nút Gọi Joyce ngay", /onPermChange = function \(s\) \{ if \(s === "granted"\) showGranted\(\); \}/.test(DLG));
check("Thử lại xin quyền thật rồi tắt luồng ngay", /getUserMedia\(\{ audio: true \}\)/.test(DLG) && /tr\.stop\(\)/.test(DLG));
check("bấm Chặn ở hộp của trình duyệt -> chuyển sang popup hướng dẫn", /open\("denied", cb\)/.test(DLG));
check("không có ngữ cảnh bảo mật -> nói đúng nguyên nhân (insecure)", /!window\.isSecureContext\) kind = "insecure"/.test(DLG));
check("popup là alertdialog có aria-modal", /role="alertdialog" aria-modal="true"/.test(DLG));
check("Esc đóng popup", /e\.key === "Escape"/.test(DLG));
check("không còn alert() trong mic-dialog.js", !/\balert\(/.test(DLG.replace(/\/\/[^\n]*/g, "")));

const keys = (DLG.match(/"micdlg\.[a-z_]+"/g) || []).map((k) => k.slice(1, -1));
check("có chuỗi micdlg.* trong code", keys.length >= 15);
const miss = keys.filter((k) => !VI[k] || !EN[k]);
check("mọi chuỗi micdlg.* có đủ vi + en" + (miss.length ? " (thiếu: " + miss.join(", ") + ")" : ""), miss.length === 0);
check("không em dash trong file mới", DLG.indexOf("—") === -1);
check("không emoji trong file mới", !/[☀-➿⌀-⏿⬀-⯿]|[\uD83C-\uD83E][\uDC00-\uDFFF]/.test(DLG));

// ---- Điện thoại: chạy thật trong vm với UA + địa chỉ https giả lập ----
const vm = require("vm");
function load(ua, href, extra) {
  const loc = new URL(href);
  const ctx = {
    window: Object.assign({ isSecureContext: true, t: null, matchMedia: () => ({ matches: false }) }, extra || {}),
    navigator: { userAgent: ua, maxTouchPoints: 5 },
    location: { href: loc.href, host: loc.host, pathname: loc.pathname, search: loc.search, hash: loc.hash, protocol: loc.protocol },
    document: {}, setTimeout, console,
  };
  ctx.window.navigator = ctx.navigator;
  vm.createContext(ctx);
  vm.runInContext(DLG, ctx);
  return ctx.window.JoyceMicDialog;
}
const URL_ = "https://ballet-sky-interval-html.trycloudflare.com/";
const UA_ZALO = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Zalo iOS";
const UA_SAFARI = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1";
const UA_WKWEB = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148";
const UA_ANDROID_FB = "Mozilla/5.0 (Linux; Android 14; SM-S918B; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/480.0;]";
const UA_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36 coc_coc_browser/150.0";

let M = load(UA_ZALO, URL_);
check("Zalo trên iPhone = trình duyệt nhúng", M.env().inApp === true && M.env().os === "ios");
let p = M.plan("inapp");
const sf = (p.actions || []).find((a) => a.href);
check("popup trình duyệt nhúng có nút Mở bằng Safari (x-safari-https)", sf && sf.href === "x-safari-" + URL_);
check("có Chép link + Vẫn thử ở đây", p.actions.some((a) => a.act === "copy") && p.actions.some((a) => a.act === "bypass"));
check("WKWebView trần (không chữ Safari/) cũng là trình duyệt nhúng", load(UA_WKWEB, URL_).env().inApp === true);
M = load(UA_SAFARI, URL_);
check("Safari thật trên iPhone KHÔNG bị coi là trình duyệt nhúng", M.env().inApp === false);
p = M.plan("denied");
check("Safari iPhone: bước aA / Cài đặt trang web, không phải ổ khoá máy tính", p.steps[0] === "micdlg.step_ios_aa");
check("Safari iPhone: gợi ý Cài đặt iPhone, không phải Windows", p.hint === "micdlg.denied_ios");
check("Safari iPhone: vẫn có lối Mở bằng Safari (SFSafariViewController giả UA Safari)", p.actions.some((a) => a.href && a.href.indexOf("x-safari-https://") === 0));
M = load(UA_ANDROID_FB, URL_);
check("Facebook trên Android = trình duyệt nhúng", M.env().inApp === true && M.env().os === "android");
const ch = M.plan("inapp").actions.find((a) => a.href);
check("Android: nút Mở bằng Chrome bằng intent://", ch && /^intent:\/\/ballet-sky-interval-html\.trycloudflare\.com\/#Intent;scheme=https;package=com\.android\.chrome;end$/.test(ch.href));
M = load(UA_WIN, URL_);
p = M.plan("denied");
check("máy tính Cốc Cốc: bước ổ khoá Cốc Cốc + gợi ý Windows, không có nút Safari",
  p.steps[0] === "micdlg.step_lock_coccoc" && p.hint === "micdlg.denied_os" && !p.actions.some((a) => a.href));
check("gate: trình duyệt nhúng chưa có quyền -> chặn lại hiện popup", /if \(env\(\)\.inApp && !inAppBypass && perm !== "granted"\)/.test(DLG));
check("đã chọn Vẫn thử ở đây thì không lặp lại popup trình duyệt nhúng", /\(env\(\)\.inApp && !inAppBypass\) \? "inapp" : "denied"/.test(DLG));

if (fails.length) { console.log("\n" + fails.length + " FAIL"); process.exit(1); }
console.log("\nTất cả xanh.");
