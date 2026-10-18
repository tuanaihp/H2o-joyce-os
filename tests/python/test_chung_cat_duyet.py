"""Rà soát bảng DUYỆT tài liệu chưng cất (server/joyce_overview.py).

    python tests/python/test_chung_cat_duyet.py

Kiểm đầy đủ 3 nhóm và 4 endpoint:
  - GET chung-cat/duyet: draft trong `wiki/_cho-duyet` (và biến thể `_cho_duyet`) + draft
    theo frontmatter chia đúng nhóm "mới hôm nay" / "hàng chờ"; wiki active mới sửa xếp
    nhóm "đã chưng cất"; thư mục lệch tên được báo trong `lech_thu_muc`.
  - POST chung-cat/duyet: đổi status -> active, bỏ staging + tag cho-duyet, chuyển file
    ra wiki chính thức, cập nhật wiki/index.md + wiki/log.md, trả rel mới. Trùng tên thì
    né (giữ nhóm staging rồi mới đuôi -2). Duyệt lại / file active / path ngoài staging /
    brain ngoài danh sách / `..` đều bị chặn. Nhân viên thường 403.
  - POST chung-cat/xoa ('Không duyệt'): xoá file vĩnh viễn - không copy, không lên wiki,
    index.md/log.md nguyên vẹn; cùng rào bảo vệ với duyệt (staging/draft, phạm vi, `..`).
  - POST chung-cat/gop-thu-muc: gộp `_cho_duyet` -> `_cho-duyet`, giữ cây con, trùng tên
    đuôi -2, xoá thư mục rỗng.

Chỉ dùng thư mục tạm (không đụng brain thật). Đặt JOYCE_STATE_DIR trước khi nạp mô-đun nào.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import tempfile
import time
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="joyce-chung-cat-duyet-")
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


def _viet(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _doc(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


B_MAIN = os.path.join(TMP, "Brain Default")
B_SALE = os.path.join(TMP, "Sale - CRM")
B_NGOAI = os.path.join(TMP, "Ngoai Brain")          # có thật nhưng không phải brain của máy

HOM_NAY = time.strftime("%Y-%m-%d")
DRAFT = """---
type: wiki
status: draft
staging: cho-duyet
tags: [wiki, cho-duyet, {tag}]
created: {created}
---

# {ten}

Mo ta ngan cho {ten}.
"""

# Brain Default: 1 draft hôm nay trong _cho-duyet, 1 draft cũ trong _cho_duyet (lệch tên),
# 1 draft chỉ nhờ frontmatter (ngoài staging), 1 trang wiki active mới sửa.
_viet(os.path.join(B_MAIN, "wiki", "_cho-duyet", "Nhap Hom Nay.md"),
      DRAFT.format(tag="moi", created=HOM_NAY, ten="Nhap Hom Nay"))
cu = os.path.join(B_MAIN, "wiki", "_cho_duyet", "Goc Cu", "Nhap Ngay Cu.md")
_viet(cu, DRAFT.format(tag="cu", created="2020-01-01", ten="Nhap Ngay Cu"))
os.utime(cu, (time.time() - 5 * 86400, time.time() - 5 * 86400))
fm_draft = os.path.join(B_MAIN, "wiki", "Nhap Chi Frontmatter.md")
_viet(fm_draft, DRAFT.format(tag="fm", created="2020-02-02", ten="Nhap Chi Frontmatter"))
os.utime(fm_draft, (time.time() - 10 * 86400, time.time() - 10 * 86400))
_viet(os.path.join(B_MAIN, "wiki", "Trang Chinh Thuc.md"),
      "---\ntype: wiki\nstatus: active\ncreated: 2020-01-01\n---\n\n# Chính thức\n")
_viet(os.path.join(B_MAIN, "wiki", "index.md"), "# Wiki Index\n")
_viet(os.path.join(B_MAIN, "wiki", "log.md"), "# Wiki Log\n")

DRAFT_SRC = """---
type: wiki
status: draft
tags: [wiki, cho-duyet]
created: {created}
source: "[[sources/{src}]]"
---

# {ten}

Mo ta ngan cho {ten}.
"""
NGUON = """---
type: source
source_kind: own-note
status: unprocessed
created: 2020-01-01
---

# Nguồn {src}
"""

# Brain Sale: draft trùng tên trang wiki đã có -> kiểm né trùng.
_viet(os.path.join(B_SALE, "wiki", "Bai Viet.md"), "---\ntype: wiki\nstatus: active\n---\n\n# Cũ\n")
_viet(os.path.join(B_SALE, "wiki", "_cho-duyet", "Nhom", "Bai Viet.md"),
      DRAFT.format(tag="trung", created=HOM_NAY, ten="Bai Viet"))
_viet(os.path.join(B_SALE, "wiki", "index.md"), "# Wiki Index\n")
_viet(os.path.join(B_SALE, "wiki", "log.md"), "# Wiki Log\n")

_viet(os.path.join(B_NGOAI, "wiki", "_cho-duyet", "Nhap Ngoai.md"),
      DRAFT.format(tag="ngoai", created=HOM_NAY, ten="Nhap Ngoai"))

ROLE_CAP = {"truong_phong": "quan_ly", "nhan_vien": "nhan_vien"}
SCOPE = {"truong_phong": [B_SALE]}
MAY = {"scope": None}


class _Today:
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
        phong_view=lambda: {},
        brain_paths=lambda: [B_MAIN, B_SALE],
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


admin = _khach()
mg = _khach("truong_phong")
nv = _khach("nhan_vien")

# ---- 1. GET hàng chờ: 3 nhóm + báo thư mục lệch ----
r = admin.get("/api/joyce/v1/overview/chung-cat/duyet")
d = r.json()
check("GET hàng chờ: 200 và ok", r.status_code == 200 and d.get("ok") is True, r.status_code)
moi_rel = {x["rel"] for x in d.get("moi", [])}
cho_rel = {x["rel"] for x in d.get("cho", [])}
check("nhóm hôm nay: draft _cho-duyet hôm nay + draft trùng tên của Sale",
      "wiki/_cho-duyet/Nhap Hom Nay.md" in moi_rel and "wiki/_cho-duyet/Nhom/Bai Viet.md" in moi_rel,
      moi_rel)
check("hàng chờ: draft _cho_duyet ngày cũ + draft ngoài staging theo frontmatter",
      "wiki/_cho_duyet/Goc Cu/Nhap Ngay Cu.md" in cho_rel and "wiki/Nhap Chi Frontmatter.md" in cho_rel,
      cho_rel)
check("hàng chờ không tính trang active", not any("Trang Chinh Thuc" in x for x in moi_rel | cho_rel))
check("tổng chờ = 4 (gồm 2 brain)", d.get("tong_cho") == 4, d.get("tong_cho"))
da_rel = {x["rel"] for x in d.get("da_duyet", [])}
check("nhóm đã chưng cất: trang active mới sửa có mặt, draft thì không",
      "wiki/Trang Chinh Thuc.md" in da_rel and not any("_cho" in x for x in da_rel), da_rel)
lech = d.get("lech_thu_muc") or []
check("báo 1 brain còn _cho_duyet (lệch tên)",
      len(lech) == 1 and lech[0]["so_file"] == 1, lech)
check("item draft có đủ trường hiển thị",
      all(k in d["moi"][0] for k in ("ten", "rel", "tao", "gio", "cho_ngay", "brain_path", "phong")),
      sorted(d["moi"][0].keys()) if d.get("moi") else "rỗng")
check("nhân viên thường bị 403 hàng chờ",
      nv.get("/api/joyce/v1/overview/chung-cat/duyet").status_code == 403)
dm = mg.get("/api/joyce/v1/overview/chung-cat/duyet").json()
check("trưởng phòng chỉ thấy draft trong phạm vi (Sale), không thấy Brain Default",
      dm.get("tong_cho") == 1 and dm["cho"] == [], dm.get("tong_cho"))

# ---- 2. POST duyệt: frontmatter + move + index + log ----
r = admin.post("/api/joyce/v1/overview/chung-cat/duyet",
               json={"brain_path": B_MAIN, "rel": "wiki/_cho-duyet/Nhap Hom Nay.md"})
j = r.json()
check("duyệt draft: 200, trả rel mới trong wiki chính thức",
      r.status_code == 200 and j.get("ok") is True and j.get("rel_moi") == "wiki/Nhap Hom Nay.md", j)
moi = _doc(os.path.join(B_MAIN, "wiki", "Nhap Hom Nay.md"))
check("frontmatter: status -> active", "status: active" in moi)
check("frontmatter: bỏ staging + tag cho-duyet, giữ tag khác",
      "staging:" not in moi and "cho-duyet" not in moi and "- moi" in moi or "moi" in moi)
check("frontmatter: đánh dấu approved + updated hôm nay",
      f"approved: '{HOM_NAY}'" in moi or f"approved: {HOM_NAY}" in moi)
check("file draft cũ đã chuyển đi",
      not os.path.exists(os.path.join(B_MAIN, "wiki", "_cho-duyet", "Nhap Hom Nay.md")))
idx = _doc(os.path.join(B_MAIN, "wiki", "index.md"))
check("index.md có dòng catalog mới", "[[Nhap Hom Nay]]" in idx, idx.strip().splitlines()[-1])
log = _doc(os.path.join(B_MAIN, "wiki", "log.md"))
check("log.md có entry duyet | tên", f"## [{HOM_NAY}] duyet | Nhap Hom Nay" in log)

# Duyệt draft ngoài staging: chỉ đổi trạng thái tại chỗ.
r = admin.post("/api/joyce/v1/overview/chung-cat/duyet",
               json={"brain_path": B_MAIN, "rel": "wiki/Nhap Chi Frontmatter.md"})
j = r.json()
check("draft ngoài staging: duyệt tại chỗ (rel giữ nguyên)",
      r.status_code == 200 and j.get("rel_moi") == "wiki/Nhap Chi Frontmatter.md", j)
check("draft ngoài staging: status -> active",
      "status: active" in _doc(fm_draft))

# Trùng tên: Sale có sẵn wiki/Bai Viet.md -> phải né sang nhóm staging (wiki/Nhom/Bai Viet.md).
r = admin.post("/api/joyce/v1/overview/chung-cat/duyet",
               json={"brain_path": B_SALE, "rel": "wiki/_cho-duyet/Nhom/Bai Viet.md"})
j = r.json()
check("trùng tên: né vào wiki/Nhom/Bai Viet.md",
      r.status_code == 200 and j.get("rel_moi") == "wiki/Nhom/Bai Viet.md", j)
check("trùng tên: trang wiki cũ không bị ghi đè",
      "# Cũ" in _doc(os.path.join(B_SALE, "wiki", "Bai Viet.md")))

# Duyệt = chốt INGEST thật: nguồn trong sources/ chuyển processed + wiki_links.
_viet(os.path.join(B_MAIN, "sources", "D-nguon-thu.md"), NGUON.format(src="D-nguon-thu"))
_viet(os.path.join(B_MAIN, "wiki", "_cho-duyet", "Draft Co Nguon.md"),
      DRAFT_SRC.format(src="D-nguon-thu", created=HOM_NAY, ten="Draft Co Nguon"))
r = admin.post("/api/joyce/v1/overview/chung-cat/duyet",
               json={"brain_path": B_MAIN, "rel": "wiki/_cho-duyet/Draft Co Nguon.md"})
j = r.json()
check("duyệt draft có nguồn: trả nguồn đã xử lý",
      r.status_code == 200 and j.get("nguon") == "sources/D-nguon-thu.md", j)
nguon = _doc(os.path.join(B_MAIN, "sources", "D-nguon-thu.md"))
check("nguồn sau duyệt: status processed + processed_at hôm nay",
      "status: processed" in nguon and HOM_NAY in nguon, nguon[:200])
check("nguồn sau duyệt: wiki_links trỏ trang vừa lên",
      "[[Draft Co Nguon]]" in nguon)
check("trang vừa duyệt giữ lại source trong frontmatter",
      "source:" in _doc(os.path.join(B_MAIN, "wiki", "Draft Co Nguon.md")))

# ---- 3. Chặn các trường hợp không hợp lệ ----
check("duyệt lại file đã đi -> 400",
      admin.post("/api/joyce/v1/overview/chung-cat/duyet",
                 json={"brain_path": B_MAIN, "rel": "wiki/_cho-duyet/Nhap Hom Nay.md"}).status_code == 400)
check("duyệt trang active -> 400",
      admin.post("/api/joyce/v1/overview/chung-cat/duyet",
                 json={"brain_path": B_MAIN, "rel": "wiki/Trang Chinh Thuc.md"}).status_code == 400)
check("path .. -> 400",
      admin.post("/api/joyce/v1/overview/chung-cat/duyet",
                 json={"brain_path": B_MAIN, "rel": "wiki/../CLAUDE.md"}).status_code == 400)
check("ngoài wiki -> 400",
      admin.post("/api/joyce/v1/overview/chung-cat/duyet",
                 json={"brain_path": B_MAIN, "rel": "sources/x.md"}).status_code == 400)
check("không phải .md -> 400",
      admin.post("/api/joyce/v1/overview/chung-cat/duyet",
                 json={"brain_path": B_MAIN, "rel": "wiki/x.txt"}).status_code == 400)
check("brain ngoài danh sách -> 400 (không đụng brain lạ)",
      admin.post("/api/joyce/v1/overview/chung-cat/duyet",
                 json={"brain_path": B_NGOAI, "rel": "wiki/_cho-duyet/Nhap Ngoai.md"}).status_code == 400)
check("nhân viên thường bị 403 duyệt",
      nv.post("/api/joyce/v1/overview/chung-cat/duyet",
              json={"brain_path": B_SALE, "rel": "wiki/_cho-duyet/x.md"}).status_code == 403)
check("trưởng phòng ngoài phạm vi -> 400",
      mg.post("/api/joyce/v1/overview/chung-cat/duyet",
              json={"brain_path": B_MAIN, "rel": "wiki/x.md"}).status_code == 400)

# ---- 4. Gộp thư mục _cho_duyet -> _cho-duyet ----
r = admin.post("/api/joyce/v1/overview/chung-cat/gop-thu-muc", json={})
j = r.json()
check("gộp thư mục: 200, chuyển 1 file", r.status_code == 200 and j.get("moved") == 1, j)
check("file nằm lại trong _cho-duyet/Goc Cu, giữ cây con",
      os.path.isfile(os.path.join(B_MAIN, "wiki", "_cho-duyet", "Goc Cu", "Nhap Ngay Cu.md")))
check("thư mục _cho_duyet rỗng đã bị xoá",
      not os.path.exists(os.path.join(B_MAIN, "wiki", "_cho_duyet")))
check("gộp lần 2: không còn gì để chuyển",
      admin.post("/api/joyce/v1/overview/chung-cat/gop-thu-muc", json={}).json().get("moved") == 0)

# Gộp theo brain chỉ định + trùng tên trong staging đích.
_viet(os.path.join(B_SALE, "wiki", "_cho_duyet", "Bai Viet.md"),
      DRAFT.format(tag="gop", created=HOM_NAY, ten="Bai Viet"))
_viet(os.path.join(B_SALE, "wiki", "_cho-duyet", "Bai Viet.md"),
      DRAFT.format(tag="gop2", created=HOM_NAY, ten="Bai Viet"))
r = admin.post("/api/joyce/v1/overview/chung-cat/gop-thu-muc", json={"brain_path": B_SALE})
j = r.json()
check("gộp một brain: 1 file, trùng tên né bằng đuôi -2",
      j.get("moved") == 1 and
      os.path.isfile(os.path.join(B_SALE, "wiki", "_cho-duyet", "Bai Viet-2.md")), j)
check("gộp brain ngoài danh sách -> 400",
      admin.post("/api/joyce/v1/overview/chung-cat/gop-thu-muc",
                 json={"brain_path": B_NGOAI}).status_code == 400)
check("nhân viên thường bị 403 gộp",
      nv.post("/api/joyce/v1/overview/chung-cat/gop-thu-muc", json={}).status_code == 403)

# ---- 5. POST xoá ('Không duyệt'): xoá vĩnh viễn, không copy/log ----
# Trước khi xoá: chụp index.md + log.md của B_MAIN để chắc không bị đụng thêm.
idx_truoc = _doc(os.path.join(B_MAIN, "wiki", "index.md"))
log_truoc = _doc(os.path.join(B_MAIN, "wiki", "log.md"))
_viet(os.path.join(B_MAIN, "wiki", "_cho-duyet", "Xoa Nhe", "Draft Khong Lien Quan.md"),
      DRAFT.format(tag="xoa", created=HOM_NAY, ten="Draft Khong Lien Quan"))
r = admin.post("/api/joyce/v1/overview/chung-cat/xoa",
               json={"brain_path": B_MAIN, "rel": "wiki/_cho-duyet/Xoa Nhe/Draft Khong Lien Quan.md"})
j = r.json()
check("xoá draft: 200 ok", r.status_code == 200 and j.get("ok") is True, j)
check("xoá draft: file biến mất hẳn",
      not os.path.exists(os.path.join(B_MAIN, "wiki", "_cho-duyet", "Xoa Nhe", "Draft Khong Lien Quan.md")))
check("xoá draft: thư mục con rỗng trong staging cũng được dọn",
      not os.path.exists(os.path.join(B_MAIN, "wiki", "_cho-duyet", "Xoa Nhe")))
check("xoá draft: index.md và log.md không đổi (không giữ nội dung)",
      _doc(os.path.join(B_MAIN, "wiki", "index.md")) == idx_truoc and
      _doc(os.path.join(B_MAIN, "wiki", "log.md")) == log_truoc)
check("xoá trang active -> 400",
      admin.post("/api/joyce/v1/overview/chung-cat/xoa",
                 json={"brain_path": B_MAIN, "rel": "wiki/Trang Chinh Thuc.md"}).status_code == 400)
check("xoá path .. -> 400",
      admin.post("/api/joyce/v1/overview/chung-cat/xoa",
                 json={"brain_path": B_MAIN, "rel": "wiki/../CLAUDE.md"}).status_code == 400)
check("xoá file ngoài wiki -> 400",
      admin.post("/api/joyce/v1/overview/chung-cat/xoa",
                 json={"brain_path": B_MAIN, "rel": "sources/x.md"}).status_code == 400)
check("xoá brain ngoài danh sách -> 400",
      admin.post("/api/joyce/v1/overview/chung-cat/xoa",
                 json={"brain_path": B_NGOAI, "rel": "wiki/_cho-duyet/Nhap Ngoai.md"}).status_code == 400)
check("nhân viên thường bị 403 xoá",
      nv.post("/api/joyce/v1/overview/chung-cat/xoa",
              json={"brain_path": B_MAIN, "rel": "wiki/_cho-duyet/x.md"}).status_code == 403)
check("trưởng phòng xoá ngoài phạm vi -> 400",
      mg.post("/api/joyce/v1/overview/chung-cat/xoa",
              json={"brain_path": B_MAIN, "rel": "wiki/_cho-duyet/x.md"}).status_code == 400)
# Trưởng phòng xoá được draft trong phạm vi của mình.
_viet(os.path.join(B_SALE, "wiki", "_cho-duyet", "Draft Sale Xoa.md"),
      DRAFT.format(tag="sale", created=HOM_NAY, ten="Draft Sale Xoa"))
r = mg.post("/api/joyce/v1/overview/chung-cat/xoa",
            json={"brain_path": B_SALE, "rel": "wiki/_cho-duyet/Draft Sale Xoa.md"})
check("trưởng phòng xoá được draft trong phạm vi", r.status_code == 200 and r.json().get("ok") is True)
check("draft Sale đã xoá thật",
      not os.path.exists(os.path.join(B_SALE, "wiki", "_cho-duyet", "Draft Sale Xoa.md")))

# Xoá draft có nguồn: mất CẢ HAI (nháp + file sources/), báo rõ đường nguồn đã xoá.
_viet(os.path.join(B_MAIN, "sources", "D-nguon-xoa.md"), NGUON.format(src="D-nguon-xoa"))
_viet(os.path.join(B_MAIN, "wiki", "_cho-duyet", "Draft Xoa Co Nguon.md"),
      DRAFT_SRC.format(src="D-nguon-xoa", created=HOM_NAY, ten="Draft Xoa Co Nguon"))
r = admin.post("/api/joyce/v1/overview/chung-cat/xoa",
               json={"brain_path": B_MAIN, "rel": "wiki/_cho-duyet/Draft Xoa Co Nguon.md"})
j = r.json()
check("xoá draft có nguồn: 200 + báo nguồn_xoa",
      r.status_code == 200 and j.get("nguon_xoa") == "sources/D-nguon-xoa.md", j)
check("xoá draft có nguồn: nháp lẫn file nguồn đều biến mất",
      not os.path.exists(os.path.join(B_MAIN, "wiki", "_cho-duyet", "Draft Xoa Co Nguon.md")) and
      not os.path.exists(os.path.join(B_MAIN, "sources", "D-nguon-xoa.md")))

# Nguồn trỏ ra ngoài vault (../ hoặc đường tuyệt đối) KHÔNG bị đụng.
_viet(os.path.join(B_MAIN, "wiki", "index-keo.md"), "# Không phải nguồn\n")
_viet(os.path.join(B_MAIN, "wiki", "_cho-duyet", "Draft Nguon Xau.md"),
      DRAFT_SRC.format(src="../wiki/index-keo", created=HOM_NAY, ten="Draft Nguon Xau"))
r = admin.post("/api/joyce/v1/overview/chung-cat/xoa",
               json={"brain_path": B_MAIN, "rel": "wiki/_cho-duyet/Draft Nguon Xau.md"})
j = r.json()
check("source trỏ '..' ra ngoài sources/: vẫn xoá nháp nhưng KHÔNG đụng file ngoài",
      r.status_code == 200 and j.get("nguon_xoa") == "" and
      os.path.isfile(os.path.join(B_MAIN, "wiki", "index-keo.md")), j)

# ---- 6. Sau thao tác, hàng chờ phản ánh đúng ----
d2 = admin.get("/api/joyce/v1/overview/chung-cat/duyet").json()
rels = {x["rel"] for x in d2.get("moi", []) + d2.get("cho", [])}
check("sau duyệt + gộp: staging sạch lệch tên, draft đã duyệt biến mất",
      not d2.get("lech_thu_muc") and
      "wiki/_cho-duyet/Nhap Hom Nay.md" not in rels and "wiki/Nhap Chi Frontmatter.md" not in rels)
da2 = {x["rel"] for x in d2.get("da_duyet", [])}
check("trang vừa duyệt hiện trong nhóm đã chưng cất (approved)",
      "wiki/Nhap Hom Nay.md" in da2 and
      next(x for x in d2["da_duyet"] if x["rel"] == "wiki/Nhap Hom Nay.md").get("moi_duyet") is True,
      da2)

if _fails:
    print(f"\nTHẤT BẠI {len(_fails)}: {_fails}")
    raise SystemExit(1)
print("\nTất cả xanh.")
