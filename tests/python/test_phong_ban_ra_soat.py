"""Rà soát tab Phòng ban (server/joyce_overview.py), bản 1.3.5.

    python tests/python/test_phong_ban_ra_soat.py

Kiểm các chỗ đã sửa, mỗi chỗ một nhóm:
  - Số việc của khối: `un` đếm ĐÚNG một lần (open đã gồm kẹt và chờ duyệt).
  - Trưởng phòng (quan_ly) chỉ thấy phòng/khối trong phạm vi được cấp, ở cả sổ phòng ban lẫn quy trình;
    phạm vi rỗng thì không thấy gì. Nhân viên thường vẫn bị 403.
  - Quy trình và tri thức chỉ đọc brain THẬT của máy: đường dẫn tự do bị 403, tên lạ không rơi lặng lẽ
    vào brain mặc định.
  - Hot: file đã xoá không còn hiện, file còn lại có ngày (mtime) thật.
  - Lượt "đã xem" ghi đồng thời không mất dấu nhau.

Chỉ dùng thư mục tạm (không đụng brain thật). Đặt JOYCE_STATE_DIR trước khi nạp mô-đun nào.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import json
import os
import tempfile
import threading
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="joyce-phong-ban-ra-soat-")
os.environ["JOYCE_STATE_DIR"] = str(Path(TMP) / "state")
os.environ["BRAINS_DIR"] = str(Path(TMP) / "brains")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import joyce_overview as ov  # noqa: E402

_fails = []


def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (("  " + str(extra)) if extra else ""))
    if not cond:
        _fails.append(name)


def _mkbrain(name):
    p = os.path.join(TMP, name)
    os.makedirs(p, exist_ok=True)
    return p


B_MAIN = _mkbrain("Brain Default")
B_SALE = _mkbrain("Sale - CRM")
B_THU = _mkbrain("Ke Toan - Thu")
B_GONE = os.path.join(TMP, "Chua Tao")          # phòng có trong sổ nhưng chưa có thư mục
B_NGOAI = _mkbrain("Ngoai Brain")               # thư mục có thật nhưng KHÔNG phải brain của máy
B_CU = _mkbrain("Brain Cu")                     # brain cũ: thư mục có số thứ tự '07 - Wiki', '01 - Sources'


def _viet(path, text="# Nội dung\n"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


_viet(os.path.join(B_SALE, "wiki", "1. Quy Trinh Tu Van - Trước dịch vụ.md"))
_viet(os.path.join(B_SALE, "wiki", "Quy trinh thi cong - Trong dich vu.md"))
_viet(os.path.join(B_SALE, "sources", "bao-cao.md"))
_viet(os.path.join(B_THU, "wiki", "Quy trinh ke toan - Sau dich vu.md"))
_viet(os.path.join(B_NGOAI, "wiki", "Quy trinh la - Truoc dich vu.md"))
_viet(os.path.join(B_CU, "07 - Wiki", "Quy trinh cu.md"))
_viet(os.path.join(B_CU, "07 - Wiki", "topic", "Chu de cu.md"))
_viet(os.path.join(B_CU, "01 - Sources", "tai-lieu-cu.md"))

# Bảng việc giả: sale có kẹt 1, chờ duyệt 1, đang chạy 2 -> open = 4
BOARDS = {
    B_MAIN: {"counts": {}, "columns": {}, "completed_24h": 0},
    B_SALE: {"counts": {"blocked": 1, "review": 1, "running": 2}, "columns": {}, "completed_24h": 0},
    B_THU: {"counts": {"ready": 1}, "columns": {}, "completed_24h": 0},
}

ROLE_CAP = {"truong_phong": "quan_ly", "truong_rong": "quan_ly", "nhan_vien": "nhan_vien", "hoc_viec": "hoc_viec"}
SCOPE = {"truong_phong": [B_SALE, B_THU], "truong_rong": []}
MAY = {"scope": None}   # phạm vi của request đang xử lý (đặt bởi middleware)


def board_view(path):
    return BOARDS.get(path) or {"counts": {}, "columns": {}, "completed_24h": 0}


PHONG_VIEW = {
    "brands": [{"id": "h2o", "ten": "H2O Studio", "shared_brain": "H2O Studio"},
               {"id": "thuy", "ten": "ThuyH2O", "shared_brain": "ThuyH2O Studio"}],
    "khoi": [{"id": "k1", "ten": "Kinh Doanh", "brand": "h2o", "thu_tu_luong": 1},
             {"id": "k2", "ten": "Kế Toán", "brand": "thuy", "thu_tu_luong": 0}],
    "phong": [
        {"id": "sale", "ten": "Sale & CRM", "khoi_id": "k1", "brain": "Sale - CRM", "brain_path": B_SALE,
         "brain_ok": True, "so_nguon": 1, "so_wiki": 2, "so_nhan_vien": 3},
        {"id": "gone", "ten": "Phòng Mới", "khoi_id": "k1", "brain": "Chua Tao", "brain_path": B_GONE,
         "brain_ok": False, "so_nguon": 0, "so_wiki": 0, "so_nhan_vien": 1},
        {"id": "thu", "ten": "Phòng Thu", "khoi_id": "k2", "brain": "Ke Toan - Thu", "brain_path": B_THU,
         "brain_ok": True, "so_nguon": 0, "so_wiki": 1, "so_nhan_vien": 0},
    ],
}


class _Today:
    def board_view(self, path):
        return board_view(path)

    def staff_by_cookie(self, tok):
        return {"role": tok} if tok in ROLE_CAP else None


def make():
    app = FastAPI()

    @app.middleware("http")
    async def _nhan_dien(request: Request, call_next):
        tok = request.cookies.get("h2o_staff", "")
        if tok in ROLE_CAP:
            request.state.staff = {"role": tok}
            MAY["scope"] = SCOPE.get(tok, [])
        else:
            request.state.staff = None
            MAY["scope"] = None
        return await call_next(request)

    ov.register(app, ov.OverviewDeps(
        today=_Today(),
        phong_view=lambda: PHONG_VIEW,
        brain_paths=lambda: [B_MAIN, B_SALE, B_THU, B_CU],
        staff_scope=lambda: MAY["scope"],
        staff_cap=lambda st: ROLE_CAP.get((st or {}).get("role"), "nhan_vien"),
        brain_root=lambda b: B_MAIN if b in ("", "brain") else b,
    ))
    return TestClient(app, base_url="http://127.0.0.1:7777")


def _khach(role=None):
    cl = make()
    if role:
        cl.cookies.set("h2o_staff", role)
    return cl


# ---- 1. Sổ phòng ban: đếm số việc và phạm vi ----
admin = _khach()
d = admin.get("/api/joyce/v1/overview/departments").json()
khoi = {k["id"]: k for k in d["khois"]}
check("quản trị thấy đủ 3 phòng", {p["id"] for p in d["phong"]} == {"sale", "gone", "thu"})
check("khối Kinh Doanh: số việc đang mở = 4 (kẹt 1 + chờ duyệt 1 + đang chạy 2)", khoi["k1"]["un"] == 4,
      khoi["k1"]["un"])
check("số việc của khối bằng tổng open, không cộng đôi kẹt và chờ duyệt",
      khoi["k1"]["un"] == khoi["k1"]["tasks"]["open"])

mg = _khach("truong_phong")
dm = mg.get("/api/joyce/v1/overview/departments").json()
check("trưởng phòng: 200", dm.get("ok") is True)
check("trưởng phòng chỉ thấy phòng trong phạm vi (sale, thu) - không thấy 'gone' (chưa có brain)",
      {p["id"] for p in dm["phong"]} == {"sale", "thu"}, [p["id"] for p in dm["phong"]])
check("trưởng phòng: khối không có phòng trong phạm vi bị ẩn",
      {k["id"] for k in dm["khois"]} == {"k1", "k2"}, [k["id"] for k in dm["khois"]])
check("trưởng phòng: đơn vị được tính lại từ phòng của mình",
      {u["id"] for u in dm["units"]} == {"h2o", "thuy"})
check("trưởng phòng: số khối vẫn đúng với phòng được xem", {k["id"]: k for k in dm["khois"]}["k1"]["un"] == 4)

rong = _khach("truong_rong")
dr = rong.get("/api/joyce/v1/overview/departments").json()
check("phạm vi rỗng: không thấy phòng nào (không rơi về xem tất cả)",
      dr.get("ok") is True and dr["phong"] == [] and dr["khois"] == [] and dr["units"] == [])

nv = _khach("nhan_vien")
check("nhân viên thường: 403 với sổ phòng ban", nv.get("/api/joyce/v1/overview/departments").status_code == 403)

# ---- 2. Quy trình: chỉ brain thật, trưởng phòng trong phạm vi ----
r = admin.get("/api/joyce/v1/overview/quy-trinh", params={"brain": B_SALE})
g = (r.json().get("giai_doan") or {})
check("quy trình: quản trị đọc được brain phòng", r.status_code == 200 and len(g.get("truoc", [])) >= 1,
      r.status_code)
check("quy trình: brain ngoài máy (đường dẫn tự do) bị 403",
      admin.get("/api/joyce/v1/overview/quy-trinh", params={"brain": B_NGOAI}).status_code == 403)
check("quy trình: đường dẫn lạ không tồn tại bị 403",
      admin.get("/api/joyce/v1/overview/quy-trinh", params={"brain": os.path.join(TMP, "khong-co")}).status_code == 403)
check("quy trình: không truyền brain thì trả rỗng, không lỗi",
      admin.get("/api/joyce/v1/overview/quy-trinh").json().get("tong") == 0)
check("quy trình: trưởng phòng xem được phòng của mình",
      mg.get("/api/joyce/v1/overview/quy-trinh", params={"brain": B_SALE}).status_code == 200)
check("quy trình: trưởng phòng bị 403 với brain ngoài phạm vi",
      mg.get("/api/joyce/v1/overview/quy-trinh", params={"brain": B_NGOAI}).status_code == 403)
check("quy trình: phạm vi rỗng bị 403 với mọi brain",
      rong.get("/api/joyce/v1/overview/quy-trinh", params={"brain": B_SALE}).status_code == 403)
check("quy trình: nhân viên thường bị 403",
      nv.get("/api/joyce/v1/overview/quy-trinh", params={"brain": B_SALE}).status_code == 403)

# ---- 3. Tri thức phòng: tên lạ không rơi vào brain mặc định ----
rk = admin.get("/api/joyce/v1/overview/knowledge", params={"brain": "brain"})
check("tri thức: 'brain' = Brain Default đọc được", rk.status_code == 200 and rk.json().get("ok") is True)
check("tri thức: tên brain (không phải đường dẫn) bị 403, không đoán sang brain mặc định",
      admin.get("/api/joyce/v1/overview/knowledge", params={"brain": "Sale - CRM"}).status_code == 403)
ks = admin.get("/api/joyce/v1/overview/knowledge", params={"brain": B_SALE}).json()
check("tri thức: đường dẫn brain thật đọc được và đếm nguồn", ks.get("ok") is True and ks["counts"]["sources"] == 1,
      ks.get("counts"))
check("tri thức: trưởng phòng ngoài phạm vi bị 403",
      mg.get("/api/joyce/v1/overview/knowledge", params={"brain": B_NGOAI}).status_code == 403)
check("tri thức: trưởng phòng trong phạm vi đọc được",
      mg.get("/api/joyce/v1/overview/knowledge", params={"brain": B_SALE}).status_code == 200)

kc = admin.get("/api/joyce/v1/overview/knowledge", params={"brain": B_CU}).json()
check("brain cũ: đếm wiki trong '07 - Wiki' (kể cả thư mục con)", kc.get("ok") is True and kc["counts"]["wiki"] == 2,
      kc.get("counts"))
check("brain cũ: đếm nguồn trong '01 - Sources'", kc["counts"]["sources"] == 1, kc.get("counts"))

# ---- 4. Hot: file đã xoá không hiện, file còn lại có ngày thật ----
state = Path(os.environ["JOYCE_STATE_DIR"])
state.mkdir(parents=True, exist_ok=True)
prefix = os.path.normcase(os.path.realpath(B_SALE)) + "|"
(state / "file-views.json").write_text(json.dumps({
    prefix + "sources/bao-cao.md": {"n": 3, "ten": "bao-cao.md"},
    prefix + "sources/da-xoa.md": {"n": 9, "ten": "da-xoa.md"},
}), encoding="utf-8")
hot = admin.get("/api/joyce/v1/overview/knowledge", params={"brain": B_SALE}).json().get("hot", [])
check("hot: file đã xoá bị bỏ", [h["rel"] for h in hot] == ["sources/bao-cao.md"], hot)
check("hot: file còn lại có mtime thật để hiện ngày", bool(hot) and hot[0].get("mtime", 0) > 0)

# ---- 5. "Đã xem" ghi đồng thời: không mất dấu nhau ----
for i in range(12):
    _viet(os.path.join(B_THU, "wiki", f"Trang dong thoi {i}.md"))
clients = [_khach() for _ in range(12)]
loi = []


def _danh_dau(cl, i):
    try:
        res = cl.post("/api/joyce/v1/overview/chung-cat/xem",
                      json={"brain_path": B_THU, "rel": f"wiki/Trang dong thoi {i}.md", "da_xem": True})
        if res.status_code != 200:
            loi.append((i, res.status_code))
    except Exception as e:  # noqa: BLE001
        loi.append((i, repr(e)))


luong = [threading.Thread(target=_danh_dau, args=(clients[i], i)) for i in range(12)]
for t in luong:
    t.start()
for t in luong:
    t.join()
luu = json.loads((state / "chung-cat-xem.json").read_text(encoding="utf-8"))
dem = sum(1 for k in luu if "Trang dong thoi" in k)
check("đã xem: 12 lượt ghi đồng thời đều được lưu", not loi and dem == 12, f"lưu {dem}/12 lỗi {loi}")

if _fails:
    print(f"\nTHẤT BẠI {len(_fails)}: {_fails}")
    raise SystemExit(1)
print("\nTất cả xanh.")
