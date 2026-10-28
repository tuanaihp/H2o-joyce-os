/* A06 (gói A): bảng "Triển khai tự cải tiến" trên trang Sơ đồ (dashboard/sodo.js).

       node tests/js/test_a06_trien_khai.js

   Chạy THẬT dpSection() và dpAct() trong vm với fetch giả. Kiểm: trạng thái chưa đủ dữ liệu KHÔNG hiện xanh; nút nhân bị khoá và
   nêu điều kiện thiếu; chỉ đích có receipt mới có nút Khôi phục; mọi thao tác ghi gửi đủ expected_revision, action_id mới mỗi lần,
   lý do; thao tác huỷ thì không gọi server; lỗi và stale được nói rõ; chữ lạ được thoát HTML; i18n đủ vi và en. */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const D = (f) => fs.readFileSync(path.join(__dirname, "..", "..", "dashboard", f), "utf8");
const SODO = D("sodo.js");
const VI = JSON.parse(D("i18n/vi.json"));
const EN = JSON.parse(D("i18n/en.json"));
const fails = [];
const check = (n, c, d) => { console.log((c ? "ok   " : "FAIL ") + n); if (!c) { fails.push(n); if (d) console.log("       " + String(d).slice(0, 300)); } };

function ctxFor(opts) {
  opts = opts || {};
  const goi = [];
  const out = { hidden: true, textContent: "", className: "" };
  const win = {
    t: (k, v) => { let s = VI[k]; if (s == null) return "THIEU_I18N:" + k; if (v) for (const kk in v) s = s.replaceAll("{" + kk + "}", v[kk]); return s; },
    ic: () => "<i/>", currentBrainPath: () => "b", JoyceNav: { go() {} },
    confirm: () => opts.xacNhan !== false, prompt: () => (opts.lyDo === undefined ? "lý do thử" : opts.lyDo),
  };
  const doc = { createElement: () => ({ set textContent(v) {} }), head: { appendChild() {} }, getElementById: (id) => (id === "sdDpOut" ? out : null) };
  const ctx = { window: win, document: doc, console, setTimeout: () => 0, setInterval: () => 0, clearInterval() {}, URLSearchParams,
    fetch: async (u, o) => {
      const body = o && o.body ? Object.fromEntries(new URLSearchParams(o.body.toString())) : null;
      goi.push({ u, method: (o && o.method) || "GET", body });
      const r = typeof opts.tra === "function" ? opts.tra(u, body) : { ok: true, json: {} };
      return { ok: r.ok !== false, status: r.ok === false ? (r.status || 409) : 200, json: async () => r.json || {} };
    } };
  vm.createContext(ctx);
  vm.runInContext(SODO, ctx);
  return { J: ctx.window.JoyceSoDo, goi, out, win };
}

const C = (o) => Object.assign({ id: "c1", brain: "Brain <b>Thu</b>", file: "agents/tro-ly-a.md", state: "canary", nguon_chay: "ban_moi", ung_vien: "abcdef1234",
  revision: "r".repeat(64), evidence: { tasks: 0 }, min_tasks: 20, acknowledged: false, legacy: false, ly_do: "", nguon_co_the_khoi_phuc: true, thieu: [], dich: [] }, o || {});
const FC = (cs, extra) => ({ deployments: Object.assign({ ok: true, telemetry_ready: false, tam_dung: false, canaries: cs }, extra || {}) });

async function main() {
  const { J, goi, out } = ctxFor();
  // ---- hiển thị
  const h0 = J._dpSection(FC([]));
  check("không có triển khai: nói rõ bảng có thể trống vì mọi thay đổi chờ chủ", h0.includes(VI["sodo.dp.none"]));
  check("chưa có telemetry: banner nói thẳng chưa đủ dữ liệu, không phải không có lỗi", h0.includes(VI["sodo.dp.no_telemetry"]));
  check("telemetry sẵn sàng thì không hiện banner đó", !J._dpSection(FC([], { telemetry_ready: true })).includes(VI["sodo.dp.no_telemetry"]));
  check("đang tạm dừng: banner nói rõ không tự áp, bản đã duyệt vẫn chạy và nút đổi thành Bật lại",
        J._dpSection(FC([], { tam_dung: true })).includes(VI["sodo.dp.paused"]) && J._dpSection(FC([], { tam_dung: true })).includes(VI["sodo.dp.btn.resume"]));
  check("chưa dừng: nút Tạm dừng, gửi on=1", /data-dp="pause" data-on="1"/.test(h0));

  const hs = {};
  for (const st of ["canary", "legacy_review", "promoted", "reverted", "superseded", "het_han", "partial", "conflict"]) hs[st] = J._dpSection(FC([C({ state: st })]));
  for (const st of ["legacy_review", "het_han", "partial", "conflict", "reverted"]) check(`trạng thái ${st}: vàng, KHÔNG xanh`, /sd-dp-r sd-st-warn/.test(hs[st]) && !/sd-dp-r sd-st-ok/.test(hs[st]));
  check("canary đã nhân xong: xanh", /sd-dp-r sd-st-ok/.test(hs.promoted));
  check("mỗi trạng thái có nhãn chữ, không rò key", Object.values(hs).every(x => !x.includes("THIEU_I18N")));
  check("tên brain chứa HTML được thoát", !hs.canary.includes("<b>Thu</b>") && hs.canary.includes("&lt;b&gt;Thu&lt;/b&gt;"));
  check("nêu nguồn đang chạy bản nào", hs.canary.includes(VI["sodo.dp.src.ban_moi"]) && J._dpSection(FC([C({ nguon_chay: "da_khoi_phuc" })])).includes(VI["sodo.dp.src.da_khoi_phuc"]));
  check("hiện số bằng chứng so với ngưỡng", J._dpSection(FC([C({ evidence: { tasks: 7 } })])).includes("7/20"));

  const dichOk = { target_id: "t1", brain: "Phòng Thu", state: "promoted", co_the_khoi_phuc: true };
  const dichKhong = { target_id: "t2", brain: "Phòng Chi", state: "already", co_the_khoi_phuc: false };
  const dichOv = { target_id: "t3", brain: "Phòng Sales", state: "override", co_the_khoi_phuc: false };
  const hd = J._dpSection(FC([C({ state: "partial", dich: [dichOk, dichKhong, dichOv] })]));
  check("chỉ đích có receipt mới có nút Khôi phục và Xem diff", (hd.match(/data-dp="restore" data-c="c1" data-t="t1"/g) || []).length === 1 && !/data-t="t2"/.test(hd) && !/data-t="t3"/.test(hd));
  check("đích override hiện nhãn giữ bản riêng, không xanh", hd.includes(VI["sodo.dp.t.override"]) && /sd-dp-t sd-st-warn[^]*?Phòng Sales/.test(hd));
  check("đích already (không có receipt) không xanh quá mức nhưng cũng không có nút ghi", hd.includes(VI["sodo.dp.t.already"]));

  const hn = J._dpSection(FC([C({ thieu: ["chưa có telemetry", "mới có 0/20 việc"] })]));
  check("nút Yêu cầu nhân bị khoá (aria-disabled) và title liệt kê điều kiện thiếu", /data-dp="promote"[^>]*aria-disabled="true"[^>]*title="chưa có telemetry · mới có 0\/20 việc"/.test(hn));
  check("điều kiện thiếu cũng hiện ra chữ cho người dùng không rê chuột", hn.includes(VI["sodo.dp.missing"]) && hn.includes("chưa có telemetry"));
  check("canary đã kết thúc (promoted) không có nút nhân và không có nút Đã đọc", !/data-dp="promote"/.test(hs.promoted) && !/data-dp="ack"/.test(hs.promoted));
  check("canary cũ cần xem có nút Đã đọc; đã đọc rồi thì không", /data-dp="ack"/.test(hs.legacy_review) && !/data-dp="ack"/.test(J._dpSection(FC([C({ state: "legacy_review", acknowledged: true })]))));
  check("nguồn đã khôi phục thì không còn nút Khôi phục nguồn", !J._dpSection(FC([C({ nguon_chay: "da_khoi_phuc" })])).includes(VI["sodo.dp.btn.restore_src"]));
  check("không có đường dẫn tuyệt đối của máy trong HTML", !/[A-Za-z]:\\|\/Users\//.test(hd));
  check("không dùng em dash", !hd.includes("—"));
  check("fc không có deployments (server cũ): không vẽ khối rỗng", J._dpSection({}) === "");

  // ---- thao tác
  let r = await J._dpAct({ dp: "restore", c: "c1", t: "t1", rev: "REV" });
  const ghi = goi.filter(x => x.method === "POST");
  check("Khôi phục gọi /work/factory/action với đủ trường: action, canary, đích, expected_revision, action_id, lý do",
        ghi.length === 1 && ghi[0].u === "/work/factory/action" && ghi[0].body.action === "restore" && ghi[0].body.canary_id === "c1" && ghi[0].body.target_id === "t1"
        && ghi[0].body.expected_revision === "REV" && ghi[0].body.action_id.length >= 8 && ghi[0].body.reason === "lý do thử", ghi[0]);
  check("KHÔNG gửi đường dẫn tệp nào từ client", !JSON.stringify(ghi[0].body).match(/[A-Za-z]:\\|\.\.\/|\/Users\//));
  await J._dpAct({ dp: "restore", c: "c1", t: "t1", rev: "REV" });
  const ghi2 = goi.filter(x => x.method === "POST");
  check("mỗi lần bấm sinh action_id MỚI (hai lần bấm là hai ý định; chống lặp do server giữ theo id)", ghi2.length === 2 && ghi2[0].body.action_id !== ghi2[1].body.action_id);

  const huy = ctxFor({ xacNhan: false });
  await huy.J._dpAct({ dp: "restore", c: "c1", t: "t1", rev: "REV" });
  check("từ chối xác nhận: KHÔNG gọi server", huy.goi.length === 0);
  const khongLyDo = ctxFor({ lyDo: "" });
  await khongLyDo.J._dpAct({ dp: "ack", c: "c1", rev: "REV" });
  check("không nhập lý do: KHÔNG gọi server", khongLyDo.goi.length === 0);
  const huyPrompt = ctxFor({ lyDo: null });
  await huyPrompt.J._dpAct({ dp: "ack", c: "c1", rev: "REV" });
  check("bấm Huỷ ở ô nhập lý do: KHÔNG gọi server", huyPrompt.goi.length === 0);

  const pa = ctxFor();
  await pa.J._dpAct({ dp: "pause", on: "1" });
  check("Tạm dừng: gửi action=pause, on=1, không cần hỏi lý do", pa.goi.length === 1 && pa.goi[0].body.action === "pause" && pa.goi[0].body.on === "1");

  const nh = ctxFor({ tra: () => ({ ok: false, status: 409, json: { dieu_kien_thieu: ["chưa có telemetry", "mới có 0/20 việc"], error: "x" } }) });
  const msg = await nh.J._dpAct({ dp: "promote", c: "c1", rev: "REV" });
  check("Yêu cầu nhân bị từ chối: hiện NGUYÊN danh sách điều kiện còn thiếu", msg.includes(VI["sodo.dp.not_ready"]) && msg.includes("chưa có telemetry") && msg.includes("mới có 0/20 việc"), msg);
  check("kết quả hiện ở ô đầu ra dạng lỗi", nh.out.hidden === false && /bad/.test(nh.out.className));

  const st = ctxFor({ tra: () => ({ ok: false, json: { stale: true, error: "x" } }) });
  check("canary đã đổi (stale): nói đúng điều đó", (await st.J._dpAct({ dp: "restore", c: "c1", t: "t1", rev: "CU" })) === VI["sodo.dp.stale"]);
  const lo = ctxFor({ tra: () => ({ ok: false, json: { error: "file đã bị sửa sau lần triển khai" } }) });
  check("lỗi của server được hiện nguyên văn", (await lo.J._dpAct({ dp: "restore", c: "c1", t: "t1", rev: "R" })).includes("file đã bị sửa"));

  const df = ctxFor({ tra: () => ({ json: { diff: "-dòng cũ\n+dòng mới" } }) });
  await df.J._dpAct({ dp: "diff", c: "c 1", t: "t/1" });
  check("Xem diff: GET có mã hoá tham số, hiện nội dung diff bằng textContent", df.goi[0].method === "GET" && df.goi[0].u === "/work/factory/diff?canary_id=c%201&target_id=t%2F1" && df.out.textContent.includes("+dòng mới"));

  // ---- i18n
  const keys = [...new Set((SODO.match(/t\("(sodo\.dp\.[a-z_.]+)"/g) || []).map((m) => m.slice(3, -1))
    .concat(Object.values({ a: "sodo.dp.s.canary" })))];
  const dong = Object.keys(VI).filter(k => k.startsWith("sodo.dp."));
  check("mọi khoá sodo.dp.* dùng trong sodo.js có trong vi.json và en.json", keys.length > 15 && keys.every((k) => k in VI && k in EN), keys.filter((k) => !(k in VI && k in EN)).join(","));
  check("mọi khoá sodo.dp.* khai trong bảng hằng số cũng có đủ vi và en", dong.every((k) => k in EN) && dong.length >= 40);
  check("giá trị không có em dash, không có thẻ HTML", dong.every((k) => !/—|<[a-z\/]/i.test(VI[k]) && !/—|<[a-z\/]/i.test(EN[k] || "")));
  const tho = (SODO.match(/DP_(?:STATE_KEY|TG_KEY|SRC_KEY)[^;]*;/g) || []).join(" ");
  const kb = [...tho.matchAll(/"(sodo\.dp\.[a-z_.]+)"/g)].map((m) => m[1]);
  check("các khoá nhãn trạng thái trong bảng tra đều có đủ vi và en", kb.length >= 15 && kb.every((k) => k in VI && k in EN), kb.filter((k) => !(k in VI && k in EN)).join(","));

  if (fails.length) { console.log("\nĐỎ " + fails.length + " mục"); process.exit(1); }
  console.log("\nTất cả xanh.");
}
main().catch((e) => { console.log("FAIL chạy test:", e); process.exit(1); });
