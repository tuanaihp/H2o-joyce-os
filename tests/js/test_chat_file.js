/* Test chat-file.js (nut 📄 goi file brain + nut ★ ghi nho tin vao sources/). Chay:
       node tests/js/test_chat_file.js
   KHONG can trinh duyet: window/document/fetch gia. Ghi chu: KHONG dung ky tu em dash.

   Bat dung 3 loi tim thay khi ra soat d257b02:
   - `home` cache 1 lan cho moi brain -> doi brain roi bam ★ la ghi vao sources/ brain CU
   - ten file chi toi giay + /files/write ghi de im lang -> 2 tin cung giay mat 1
   - /files/list loi -> home rong -> ghi ra sources/ o TRAN (localhost = ca o dia) */
let brain = "brains/A";
const writes = [];
let listFail = false;
const HOMES = { "brains/A": "brains/A", "brains/B": "brains/B", "brain": "" };

global.window = { currentBrainPath: () => brain, t: (k) => k };
global.document = { addEventListener() {}, getElementById() { return null; } };
global.fetch = async (url, opts) => {
  if (String(url).startsWith("/files/list")) {
    if (listFail) return { json: async () => ({ error: "x" }) };
    const b = decodeURIComponent(String(url).match(/brain=([^&]*)/)[1]);
    return { json: async () => ({ home: HOMES[b], path: HOMES[b], items: [] }) };
  }
  if (String(url) === "/files/write") {
    writes.push({ brain: opts.body.get("brain"), path: opts.body.get("path"), content: opts.body.get("content") });
    return { json: async () => ({ ok: true }) };
  }
  throw new Error("fetch la: " + url);
};
require("../../dashboard/chat-file.js");
const F = window.JoyceChatFile;

const fails = [];
function check(name, cond) {
  console.log((cond ? "ok   " : "FAIL ") + name);
  if (!cond) fails.push(name);
}

(async () => {
  // ---- 1. Ghi dung sources/ cua brain dang choi, ke ca sau khi doi brain ----
  const p1 = await F.remember("tin o brain A", 1760000000000);
  check("brain A: ghi vao brains/A/sources/", p1.startsWith("brains/A/sources/ghi-nho-") && writes[0].brain === "brains/A");
  brain = "brains/B";
  const p2 = await F.remember("tin o brain B", 1760000000000);
  check("doi sang brain B: KHONG ghi vao brain A", p2.startsWith("brains/B/sources/") && writes[1].brain === "brains/B");

  // ---- 2. Hai tin cung mot thoi diem khong de len nhau ----
  const p3 = await F.remember("tin 1", 1760000000000);
  const p4 = await F.remember("tin 2", 1760000000000);
  check("cung mot ms: 2 ten file khac nhau", p3 !== p4);

  // ---- 3. Tran = goc brain (home rong) van hop le ----
  brain = "brain";
  const p5 = await F.remember("brain mac dinh", Date.now());
  check("home rong hop le: sources/ o goc", p5.startsWith("sources/ghi-nho-"));

  // ---- 4. Khong biet goc brain thi KHONG ghi ----
  brain = "brains/C";
  listFail = true;
  const n = writes.length;
  let threw = false;
  try { await F.remember("khong biet goc", Date.now()); } catch (e) { threw = true; }
  check("list loi: bao loi, khong ghi gi", threw && writes.length === n);
  listFail = false;

  // ---- 5. Tin trong ----
  let empty = false;
  try { await F.remember("   ", Date.now()); } catch (e) { empty = true; }
  check("tin trong: bao loi", empty);

  // ---- 6. Frontmatter: title an toan voi dau nhay ----
  brain = "brains/A";
  await F.remember('Anh noi "dung quen" nhe\ndong 2', Date.now());
  const c = writes[writes.length - 1].content;
  check("frontmatter co type/source_kind/status", /^---\ntype: source\nsource_kind: chat\nstatus: unprocessed\n/.test(c));
  check("title escape dau nhay", c.includes('title: "Anh noi \\"dung quen\\" nhe dong 2"'));
  check("noi dung giu nguyen van", c.includes('Anh noi "dung quen" nhe\ndong 2'));

  // ---- 7. linkifyMd ----
  const L = F.linkifyMd;
  check("`wiki/x.md` thanh link", L("xem `wiki/x.md` nhe").includes('data-vault-path="wiki/x.md"'));
  check("`../etc/passwd.md` khong link", !L("`../etc/passwd.md`").includes("jv-floc"));
  check("ky tu da escape (&quot;) khong link", !L("`a&quot;b.md`").includes("jv-floc"));
  check("chu khong co duoi file khong link", !L("`chao anh`").includes("jv-floc"));

  console.log(fails.length ? "\n" + fails.length + " test HỎNG" : "\nTất cả test đều đạt");
  process.exit(fails.length ? 1 : 0);
})();
