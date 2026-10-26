"""Plugin bundled apple-notes: đường push từ Shortcut -> ghi .md vào sources/apple-notes/.

    python tests/run.py apple_notes      (KHÔNG mạng)

Khoá đúng hợp đồng của plugin:
1. Đường công khai (push/folders/ping) TỰ xác thực bằng token của plugin - không token hay
   token sai thì 401, nhưng đường phải qua được hàng rào đăng nhập (public + no_cookie).
2. Note được ghi đúng chỗ <brain>/sources/apple-notes/<thư mục>/<tên>.md với frontmatter
   của một source (type/source_kind/status), và chỉ trong BRAINS_DIR.
3. Push lại note chưa đổi thì bỏ qua; note đổi tên thì ghi file mới và dọn file cũ.
4. Tên thư mục/tên note không được phép leo ra ngoài sources/apple-notes/ (traversal).
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import json
import tempfile
from pathlib import Path

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-apln-")
os.environ["JOYCE_REQUIRE_LOGIN"] = "1"
_BRAINS = tempfile.mkdtemp(prefix="joyce-apln-brains-")
os.environ["BRAINS_DIR"] = _BRAINS

from fastapi.testclient import TestClient   # noqa: E402
import config as cfg   # noqa: E402
import main            # noqa: E402
import plugins_host    # noqa: E402

_fails = []


def check(name, cond, them=""):
    print(("ok   " if cond else "FAIL ") + name + (f"  [{them}]" if them and not cond else ""))
    if not cond:
        _fails.append(name)


# Brain đích + session chủ
root = Path(_BRAINS) / "Brain Default"
(root / "sources").mkdir(parents=True, exist_ok=True)
(Path(_BRAINS) / "Marketing").mkdir(parents=True, exist_ok=True)

_s = cfg.read_settings()
_s["auth"] = {"username": "admin", **dict(zip(("password_hash", "salt"),
                                              cfg.hash_password("matkhau123")))}
cfg.write_settings(_s)

la = TestClient(main.app)
chu = TestClient(main.app)
r = chu.post("/auth/login", data={"username": "admin", "password": "matkhau123"})
check("chủ đăng nhập được", r.status_code == 200 and r.json().get("ok"))

# ---- trang cài đặt: người lạ bị chặn, chủ thấy token ----
check("người lạ mở trang cài đặt -> 401", la.get("/ext/apple-notes/").status_code == 401)
r = chu.get("/ext/apple-notes/")
check("chủ mở được trang cài đặt", r.status_code == 200 and "Apple Notes" in r.text, r.status_code)

tok_file = Path(os.environ["JOYCE_STATE_DIR"]) / "plugin-data" / "apple-notes" / "config.json"
tok = json.loads(tok_file.read_text(encoding="utf-8"))["token"]
check("token được sinh và nằm trong plugin-data", tok.startswith("japn_"))
check("token hiện trên trang cài đặt", tok in r.text)

# ---- ping / auth ----
check("ping không token -> 401", la.get("/ext/apple-notes/ping").status_code == 401)
check("ping token sai -> 401", la.get("/ext/apple-notes/ping?token=sai").status_code == 401)
r = la.get("/ext/apple-notes/ping", headers={"Authorization": f"Bearer {tok}"})
check("ping đúng token -> ok", r.status_code == 200 and r.json().get("brain") == "Brain Default")

# ---- push notes ----
payload = {
    "device": "iPhone cua anh",
    "folders": {
        "Work/Concept": [
            {"id": "n1", "title": "Ý tưởng chụp ảnh", "body": "Concept A: nền trắng",
             "modified": "2026-10-20T10:00:00+07:00", "created": "2026-10-19T09:00:00+07:00"},
            {"id": "n2", "title": "Checklist shoot", "body": "- đèn\n- nền",
             "modified": "2026-10-20T11:00:00+07:00"},
        ],
        "Cá nhân": [
            {"title": "Ghi chú không id", "body": "nội dung", "modified": "x"},
        ],
    },
}
r = la.post("/ext/apple-notes/push", json=payload)
check("push không token -> 401", r.status_code == 401)
r = la.post("/ext/apple-notes/push", content=json.dumps(payload),
            headers={"Authorization": f"Bearer {tok}", "Origin": "https://la.example"})
check("push đúng token (Origin lạ, no_cookie cho qua)", r.status_code == 200, r.text)
j = r.json()
check("ghi 3 note", j.get("written") == 3 and j.get("ok"), j)

f1 = root / "sources" / "apple-notes" / "Work" / "Concept" / "Ý tưởng chụp ảnh.md"
check("file .md vào đúng sources/apple-notes/<folder>/", f1.is_file())
txt = f1.read_text(encoding="utf-8") if f1.is_file() else ""
check("frontmatter đúng khuôn source", "type: source" in txt and "source_kind: own-note" in txt
      and "status: unprocessed" in txt)
check("giữ apple_id + apple_folder", 'apple_id: "n1"' in txt and 'apple_folder: "Work/Concept"' in txt)
check("thân note giữ nguyên", "Concept A: nền trắng" in txt)

# ---- push lại: không đổi -> skip ----
r = la.post("/ext/apple-notes/push", json=payload, headers={"Authorization": f"Bearer {tok}"})
check("push lại note chưa đổi -> skipped", r.json().get("skipped") == 3 and r.json().get("written") == 0, r.text)

# ---- đổi tên: file mới + file cũ được dọn ----
payload2 = {"folders": {"Work/Concept": [
    {"id": "n1", "title": "Ý tưởng chụp ảnh v2", "body": "đã sửa",
     "modified": "2026-10-21T10:00:00+07:00"}]}}
r = la.post("/ext/apple-notes/push", json=payload2, headers={"Authorization": f"Bearer {tok}"})
check("đổi tên note -> ghi file mới", r.json().get("written") == 1, r.text)
check("file tên mới tồn tại", (root / "sources/apple-notes/Work/Concept/Ý tưởng chụp ảnh v2.md").is_file())
check("file tên cũ bị dọn", not f1.exists())

# ---- traversal ----
r = la.post("/ext/apple-notes/push", json={"folders": {"../../evil": [
    {"id": "x9", "title": "hack", "body": "x", "modified": "1"}]}},
    headers={"Authorization": f"Bearer {tok}"})
check("folder traversal không nổ server", r.status_code == 200, r.text)
ngoai = list(Path(_BRAINS).glob("**/*.md"))
check("không ghi file nào ra ngoài sources/apple-notes",
      all("apple-notes" in str(p) for p in ngoai),
      ", ".join(str(p) for p in ngoai))
r = la.post("/ext/apple-notes/push", json={"folders": {"Work": [
    {"id": "t", "title": "..\\..\\esc", "body": "x", "modified": "1"}]}},
    headers={"Authorization": f"Bearer {tok}"})
check("tên note traversal cũng bị sạch", r.status_code == 200 and r.json().get("written") == 1, r.text)
check("không có file nào leo lên thư mục cha", not (root / "sources" / "esc.md").exists())

# ---- brain đích trong payload: tên lạ -> lỗi rõ, tên có -> ghi đúng brain đó ----
r = la.post("/ext/apple-notes/push", json={"brain": "KhongCo", "folder": "X",
            "notes": [{"title": "a", "body": "b", "modified": "1"}]},
            headers={"Authorization": f"Bearer {tok}"})
check("brain lạ -> báo lỗi, không fallback âm thầm", r.status_code == 400, r.text)
r = la.post("/ext/apple-notes/push", json={"brain": "Marketing", "folder": "Ads",
            "notes": [{"id": "m1", "title": "Note MKT", "body": "x", "modified": "1"}]},
            headers={"Authorization": f"Bearer {tok}"})
check("ghi được sang brain khác trong BRAINS_DIR", r.status_code == 200
      and (Path(_BRAINS) / "Marketing" / "sources" / "apple-notes" / "Ads" / "Note MKT.md").is_file(),
      r.text)

# ---- folders tree ----
r = la.post("/ext/apple-notes/folders", json={"device": "mac",
            "folders": ["Work", "Work/Concept", "Cá nhân"]},
            headers={"Authorization": f"Bearer {tok}"})
check("folders endpoint lưu cây thư mục", r.status_code == 200 and r.json().get("folders") == 3)
r = chu.get("/ext/apple-notes/")
check("trang cài đặt hiện cây thư mục đã gửi", "Work/Concept" in r.text)

# ---- tool apple_notes_status ----
lp = next((p for p in plugins_host._plugin_http() if p.slug == "apple-notes"), None)
check("plugin nạp được và có đường http", lp is not None)
if lp:
    h = {t["name"]: t for t in lp.tools}.get("apple_notes_status", {}).get("handler")
    check("tool apple_notes_status tồn tại", h is not None)
    if h:
        s = h({}, lp.ctx)
        check("tool báo đúng lần sync cuối + số note", "Brain Default" in s and "note" in s.lower(), s)

# ---- tải script Mac đã điền sẵn ----
check("người lạ tải script -> 401", la.get("/ext/apple-notes/script").status_code == 401)
r = chu.get("/ext/apple-notes/script")
check("chủ tải được script", r.status_code == 200 and "apple-notes-sync.command" in
      r.headers.get("content-disposition", ""), r.status_code)
check("script có token điền sẵn", f'TOKEN="{tok}"' in r.text)

# ---- đổi brain qua trang cài đặt ----
r = chu.post("/ext/apple-notes/cai-dat", data={"op": "brain", "brain": "Marketing"},
             headers={"Origin": "http://testserver"})
check("đổi brain đích qua trang cài đặt", r.status_code in (200, 303))
check("config lưu brain mới", json.loads(tok_file.read_text(encoding="utf-8"))["brain"] == "Marketing")
r = chu.post("/ext/apple-notes/cai-dat", data={"op": "brain", "brain": "KhongCo"},
             headers={"Origin": "http://testserver"})
check("đổi sang brain lạ -> báo lỗi", r.status_code == 200 and not r.json().get("ok", True), r.text)

print()
if _fails:
    print(f"ĐỎ {len(_fails)} ca")
    raise SystemExit(1)
print("xanh hết")
