"""CRM vận hành: khách hàng, cơ hội, việc chăm sóc, đề xuất hồ sơ cho các phòng ban.

Thiết kế (docs/dev/2026-10-crm-quan-tri-khach-hang.md):
  - Dùng chung kho SQLite với hộp thư khách (conversations.py), bảng riêng `crm_*`, KHÔNG sửa
    bảng cũ. Một liên hệ có thể gắn với một khách trong hộp thư (`customer_id`) hoặc nhập tay.
  - Một khách thuộc NHIỀU phòng (`depts`). Cơ hội, việc, giai đoạn thì thuộc TỪNG phòng: phòng
    nào chỉ thấy phần của phòng đó (phòng B không đọc được cơ hội của phòng A).
  - Nhân viên chỉ vào được khi admin cấp quyền `crm` (h2o_staff.quyen). Admin thấy tất cả.
  - Đếm, lọc, nhắc hạn, phân khúc do CODE làm. Model chỉ dùng để đọc đoạn chat và trích hồ sơ,
    và kết quả đi qua hàng chờ "đề xuất" cho người duyệt (trừ khi admin bật chế độ tự áp).
"""
from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse

import conversations

router = APIRouter()

# Điểm cắm do main.py nạp (test nạp bản giả).
_deps: Dict[str, Callable] = {
    "phong": lambda: [],            # -> [{"brain": "Ban Hang - ...", "ten": "..."}]
    "scope": lambda: (),            # -> các gốc brain nhân viên được dùng (rỗng = admin)
    "tasks": lambda: None,          # -> TasksFeature
    "brain_root": lambda b: "",     # tên brain -> thư mục
    "model": lambda prompt, text: "",   # gọi model rẻ, trả chuỗi ("" = không có)
}

MAX_CHU = 4000
NGUONG_TRICH_MAC_DINH = 8
CHE_DO = ("off", "duyet", "auto")
GD_MAC_DINH = [
    {"key": "moi", "label": "Mới", "kind": "open"},
    {"key": "tu_van", "label": "Đang tư vấn", "kind": "open"},
    {"key": "cho_chot", "label": "Chờ chốt", "kind": "open"},
    {"key": "da_chot", "label": "Đã chốt", "kind": "won"},
    {"key": "mat", "label": "Mất", "kind": "lost"},
]
TRUONG_HO_SO = ("nhu_cau", "ngan_sach", "han", "phan_doi", "buoc_tiep", "tom_tat")
TRUONG_CHINH = ("name", "phone", "email", "company")
_RE_SDT = re.compile(r"(?<![\d])(?:\+?84|0)(?:[\s.\-]?\d){8,10}(?![\d])")
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS crm_contacts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    name TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    depts_json TEXT NOT NULL DEFAULT '[]',
    meta_json TEXT NOT NULL DEFAULT '{}',
    deleted INTEGER NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_crm_c_cust ON crm_contacts(customer_id);
CREATE TABLE IF NOT EXISTS crm_deals(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    brain TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    value REAL NOT NULL DEFAULT 0,
    stage TEXT NOT NULL DEFAULT 'moi',
    owner TEXT NOT NULL DEFAULT '',
    closed_at REAL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_crm_d_brain ON crm_deals(brain, stage);
CREATE TABLE IF NOT EXISTS crm_todos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    brain TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    due TEXT NOT NULL DEFAULT '',
    owner TEXT NOT NULL DEFAULT '',
    done INTEGER NOT NULL DEFAULT 0,
    done_at REAL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_crm_t_brain ON crm_todos(brain, done);
CREATE TABLE IF NOT EXISTS crm_events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    brain TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT 'note',
    text TEXT NOT NULL DEFAULT '',
    by TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_crm_e_c ON crm_events(contact_id, id);
CREATE TABLE IF NOT EXISTS crm_proposals(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_id INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'chat',
    fields_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    decided_by TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    decided_at REAL
);
CREATE INDEX IF NOT EXISTS ix_crm_p_st ON crm_proposals(status, contact_id);
CREATE TABLE IF NOT EXISTS crm_settings(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
"""

def model_re(prompt: str, text: str) -> str:
    """Một lượt chat/completions qua model rẻ đã cấu hình (cùng cách chọn nhà với bộ gợi ý năng
    lực). "" khi không có nhà nào dùng được hoặc gọi lỗi - khi đó chỉ còn luật cố định."""
    import urllib.request
    try:
        import capability_embedding as ce
        url, key, model = ce._resolve_target(None)
        if not url:
            return ""
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        if "openrouter.ai" in url:
            headers.update({"HTTP-Referer": "http://localhost:7777", "X-Title": "Joyce OS"})
        payload = {"model": model, "temperature": 0, "stream": False, "max_tokens": 400,
                   "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}]}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    except Exception:
        return ""


_deps["model"] = model_re
_ready_for: Optional[str] = None
_dang_trich: set = set()
_lock_trich = threading.Lock()


# ------------------------------------------------------------------ kho
def _db():
    """Kết nối chung với hộp thư; dựng bảng crm_* một lần cho mỗi đường dẫn kho."""
    global _ready_for
    db = conversations._conn()
    key = str(getattr(conversations, "_db_path", ""))
    if _ready_for != key:
        with conversations._lock:
            db.executescript(_SCHEMA)
            db.commit()
        _ready_for = key
    return db


def _dung(fn):
    with conversations._lock:
        return fn(_db())


def _now() -> float:
    return time.time()


def _s(v: Any, n: int = MAX_CHU) -> str:
    return " ".join(str(v or "").split())[:n] if n <= 300 else str(v or "").strip()[:n]


def _loads(s: Any, mac_dinh):
    try:
        v = json.loads(s or "")
        return v if isinstance(v, type(mac_dinh)) else mac_dinh
    except Exception:
        return mac_dinh


def _row(r) -> dict:
    return {k: r[k] for k in r.keys()}


def _ascii(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s or "").replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _ascii(s).lower()).strip("-")[:60] or "khach"


def chuan_sdt(s: str) -> str:
    """0901 234 567 / +84901234567 / 84.901.234.567 về một dạng: 0901234567."""
    d = re.sub(r"[^\d+]", "", str(s or ""))
    if d.startswith("+84"):
        d = "0" + d[3:]
    elif d.startswith("84") and len(d) >= 11:
        d = "0" + d[2:]
    return d if 9 <= len(d) <= 11 and d.isdigit() else ""


def bat_sdt(text: str) -> List[str]:
    out: List[str] = []
    for m in _RE_SDT.findall(str(text or "")):
        n = chuan_sdt(m)
        if n and n not in out:
            out.append(n)
    return out


def bat_email(text: str) -> List[str]:
    out: List[str] = []
    for m in _RE_EMAIL.findall(str(text or "")):
        m = m.lower()
        if m not in out:
            out.append(m)
    return out


# ------------------------------------------------------------------ cài đặt
def _get_set(db, key: str, mac_dinh: str = "") -> str:
    r = db.execute("SELECT value FROM crm_settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else mac_dinh


def _put_set(db, key: str, value: str) -> None:
    db.execute("INSERT INTO crm_settings(key,value) VALUES(?,?)"
               " ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def phong_bat() -> Optional[set]:
    """Các phòng ĐƯỢC MỞ CRM. None = chưa ai cấu hình, mọi phòng đều mở (giữ hành vi cũ).
    Đã cấu hình thì phòng nào không có trong danh sách thì nhân viên phòng đó không xem được."""
    raw = _dung(lambda db: _get_set(db, "phong_bat", ""))
    if not raw:
        return None
    try:
        ds = json.loads(raw)
    except Exception:
        return None
    return {str(x) for x in ds} if isinstance(ds, list) else None


def dat_phong_bat(brain: str, bat: bool, tat_ca: List[str]) -> List[str]:
    cur = phong_bat()
    ds = set(tat_ca) if cur is None else set(cur)
    if bat:
        ds.add(brain)
    else:
        ds.discard(brain)
    ra = sorted(ds)

    def f(db):
        _put_set(db, "phong_bat", json.dumps(ra, ensure_ascii=False))
        db.commit()
    _dung(f)
    return ra


def che_do_trich() -> str:
    v = _dung(lambda db: _get_set(db, "auto_mode", "duyet"))
    return v if v in CHE_DO else "duyet"


def nguong_trich() -> int:
    try:
        return max(2, min(100, int(_dung(lambda db: _get_set(db, "auto_n", str(NGUONG_TRICH_MAC_DINH))))))
    except Exception:
        return NGUONG_TRICH_MAC_DINH


def giai_doan(brain: str) -> List[dict]:
    raw = _dung(lambda db: _get_set(db, "stages:" + brain, ""))
    ds = _loads(raw, [])
    ok = [g for g in ds if isinstance(g, dict) and g.get("key") and g.get("label")
          and g.get("kind") in ("open", "won", "lost")]
    if not any(g["kind"] == "won" for g in ok) or not any(g["kind"] == "lost" for g in ok) or not ok:
        return [dict(g) for g in GD_MAC_DINH]
    return ok


def _luu_giai_doan(brain: str, ds: List[dict]) -> None:
    _dung(lambda db: (_put_set(db, "stages:" + brain, json.dumps(ds, ensure_ascii=False)), db.commit()))


def them_giai_doan(brain: str, label: str) -> dict:
    label = _s(label, 40)
    if not label:
        raise ValueError("Thiếu tên giai đoạn")
    ds = giai_doan(brain)
    if any(_ascii(g["label"]).lower() == _ascii(label).lower() for g in ds):
        raise ValueError("Đã có giai đoạn tên này")
    key = _slug(label).replace("-", "_") or "gd"
    base, n = key, 2
    while any(g["key"] == key for g in ds):
        key = f"{base}_{n}"; n += 1
    moi = {"key": key, "label": label, "kind": "open"}
    # Chèn TRƯỚC giai đoạn "thắng" đầu tiên: Đã chốt và Mất luôn nằm cuối.
    i = next((j for j, g in enumerate(ds) if g["kind"] != "open"), len(ds))
    ds.insert(i, moi)
    _luu_giai_doan(brain, ds)
    return moi


def xoa_giai_doan(brain: str, key: str) -> dict:
    ds = giai_doan(brain)
    g = next((x for x in ds if x["key"] == key), None)
    if not g:
        raise ValueError("Không có giai đoạn này")
    if g["kind"] != "open":
        raise ValueError("Không xoá được giai đoạn Đã chốt hoặc Mất")
    con = [x for x in ds if x["key"] != key]
    if not any(x["kind"] == "open" for x in con):
        raise ValueError("Phải còn ít nhất một giai đoạn đang theo")
    dich = next(x for x in con if x["kind"] == "open")["key"]

    def f(db):
        cur = db.execute("UPDATE crm_deals SET stage=?, updated_at=? WHERE brain=? AND stage=?",
                         (dich, _now(), brain, key))
        db.commit()
        return cur.rowcount
    chuyen = _dung(f)
    _luu_giai_doan(brain, con)
    return {"chuyen": chuyen, "sang": dich}


def doi_ten_giai_doan(brain: str, key: str, label: str) -> None:
    label = _s(label, 40)
    if not label:
        raise ValueError("Thiếu tên giai đoạn")
    ds = giai_doan(brain)
    g = next((x for x in ds if x["key"] == key), None)
    if not g:
        raise ValueError("Không có giai đoạn này")
    g["label"] = label
    _luu_giai_doan(brain, ds)


# ------------------------------------------------------------------ liên hệ
def _lien_he_public(r: dict) -> dict:
    d = dict(r)
    d["tags"] = _loads(d.pop("tags_json", "[]"), [])
    d["depts"] = _loads(d.pop("depts_json", "[]"), [])
    meta = _loads(d.pop("meta_json", "{}"), {})
    d["profile"] = meta.get("profile") or {}
    d["locked"] = meta.get("khoa") or []
    d["deleted"] = bool(d.get("deleted"))
    return d


def _thay_hien_thi(c: dict, allowed: Optional[set]) -> bool:
    return allowed is None or bool(set(c.get("depts") or []) & allowed)


def lay_lien_he(cid: int) -> Optional[dict]:
    r = _dung(lambda db: db.execute("SELECT * FROM crm_contacts WHERE id=?", (int(cid),)).fetchone())
    return _lien_he_public(_row(r)) if r else None


def danh_sach_lien_he(allowed: Optional[set], brain: str = "", q: str = "", tag: str = "",
                      limit: int = 200, offset: int = 0, da_xoa: bool = False) -> List[dict]:
    where, args = ["deleted=?"], [1 if da_xoa else 0]
    if q:
        like = f"%{_s(q, 80)}%"
        where.append("(name LIKE ? OR phone LIKE ? OR email LIKE ? OR company LIKE ? OR note LIKE ?)")
        args += [like] * 5
    if tag:
        where.append("tags_json LIKE ?"); args.append('%"' + str(tag).replace('"', "") + '"%')
    sql = ("SELECT * FROM crm_contacts WHERE " + " AND ".join(where)
           + " ORDER BY updated_at DESC, id DESC")
    rows = _dung(lambda db: db.execute(sql, args).fetchall())
    out = []
    for r in rows:
        c = _lien_he_public(_row(r))
        if not _thay_hien_thi(c, allowed):
            continue
        if brain and brain not in c["depts"]:
            continue
        out.append(c)
    o = max(0, int(offset or 0))
    return out[o:o + max(1, min(int(limit or 200), 1000))]


def tong_da_chot(ids: list, allowed: Optional[set]) -> dict:
    """{contact_id: tổng giá trị cơ hội đã chốt} cho cột bên phải danh bạ. Chỉ cộng phòng người xem được thấy."""
    ids = [int(i) for i in ids]
    if not ids:
        return {}
    rows = _dung(lambda db: db.execute(
        "SELECT contact_id, brain, stage, value FROM crm_deals WHERE contact_id IN (%s)" % ",".join("?" * len(ids)), ids).fetchall())
    thang = {}
    out = {}
    for r in rows:
        b = r["brain"]
        if allowed is not None and b not in allowed:
            continue
        if b not in thang:
            thang[b] = {g["key"] for g in giai_doan(b) if g["kind"] == "won"}
        if r["stage"] in thang[b]:
            out[r["contact_id"]] = out.get(r["contact_id"], 0) + (r["value"] or 0)
    return out


def _su_kien(db, cid: int, kind: str, text: str, by: str, brain: str = "") -> None:
    db.execute("INSERT INTO crm_events(contact_id, brain, kind, text, by, created_at) VALUES(?,?,?,?,?,?)",
               (int(cid), brain, kind, _s(text, 600), _s(by, 60), _now()))


def ghi_su_kien_crm(cid: int, kind: str, text: str, by: str = "", brain: str = "") -> None:
    def f(db):
        _su_kien(db, cid, kind, text, by, brain)
        db.commit()
    _dung(f)


def luu_lien_he(data: dict, allowed: Optional[set], by: str, mac_dinh_phong: str = "") -> dict:
    """Tạo hoặc sửa. Nhân viên chỉ gán được phòng trong phạm vi của mình; phòng ngoài bị bỏ."""
    cid = int(data.get("id") or 0)
    name = _s(data.get("name"), 120)
    phone = chuan_sdt(data.get("phone")) if data.get("phone") else ""
    email = (bat_email(data.get("email") or "") or [""])[0]
    if not (name or phone or email):
        raise ValueError("Cần ít nhất tên, số điện thoại hoặc email")
    depts_in = [d for d in (data.get("depts") or []) if str(d or "").strip()]
    if allowed is not None:
        depts_in = [d for d in depts_in if d in allowed]
        if not depts_in and mac_dinh_phong:
            depts_in = [mac_dinh_phong]
    tags = conversations.chuan_hoa_tag(data.get("tags") or [])
    now = _now()

    def f(db):
        if cid:
            r = db.execute("SELECT * FROM crm_contacts WHERE id=?", (cid,)).fetchone()
            if not r:
                raise ValueError("Không tìm thấy khách")
            cu = _lien_he_public(_row(r))
            if not _thay_hien_thi(cu, allowed):
                raise PermissionError("Khách thuộc phòng khác")
            meta = _loads(r["meta_json"], {})
            khoa = set(meta.get("khoa") or [])
            for k in TRUONG_CHINH:
                if k in data and str(data.get(k) or "").strip() != str(cu.get(k) or ""):
                    khoa.add(k)
            meta["khoa"] = sorted(khoa)
            depts = depts_in if depts_in else cu["depts"]
            if allowed is not None:       # phòng ngoài phạm vi của người sửa được giữ nguyên
                depts = sorted(set(depts) | (set(cu["depts"]) - allowed))
            db.execute("UPDATE crm_contacts SET name=?, phone=?, email=?, company=?, source=?, note=?,"
                       " tags_json=?, depts_json=?, meta_json=?, updated_at=? WHERE id=?",
                       (name, phone, email, _s(data.get("company"), 120), _s(data.get("source"), 60),
                        str(data.get("note") or "").strip()[:MAX_CHU],
                        json.dumps(tags, ensure_ascii=False), json.dumps(depts, ensure_ascii=False),
                        json.dumps(meta, ensure_ascii=False), now, cid))
            _su_kien(db, cid, "sua", "Sửa thông tin khách", by)
        else:
            if allowed is not None and not depts_in:
                raise PermissionError("Chưa có phòng nào để gán khách")
            meta = {"profile": {}, "khoa": []}
            cur = db.execute(
                "INSERT INTO crm_contacts(customer_id, name, phone, email, company, source, note, tags_json,"
                " depts_json, meta_json, created_by, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (data.get("customer_id") or None, name, phone, email, _s(data.get("company"), 120),
                 _s(data.get("source"), 60), str(data.get("note") or "").strip()[:MAX_CHU],
                 json.dumps(tags, ensure_ascii=False), json.dumps(depts_in, ensure_ascii=False),
                 json.dumps(meta, ensure_ascii=False), _s(by, 60), now, now))
            cid_moi = int(cur.lastrowid)
            _su_kien(db, cid_moi, "tao", "Tạo khách", by, (depts_in or [""])[0])
            db.commit()
            return cid_moi
        db.commit()
        return cid
    new_id = _dung(f)
    return lay_lien_he(new_id)


def gan_phong(cid: int, brain: str, bat: bool, allowed: Optional[set], by: str) -> List[str]:
    """Nút + / - phòng của một khách. Bỏ hết phòng thì khách mất khỏi mọi danh sách phòng, nên
    không cho gỡ phòng cuối cùng."""
    c = lay_lien_he(cid)
    if not c or not _thay_hien_thi(c, allowed):
        raise PermissionError("Không thấy khách này")
    if allowed is not None and brain not in allowed:
        raise PermissionError("Phòng ngoài phạm vi của bạn")
    ds = list(c["depts"])
    if bat and brain not in ds:
        ds.append(brain)
    if not bat:
        if brain in ds and len(ds) <= 1:
            raise ValueError("Khách phải thuộc ít nhất một phòng")
        ds = [d for d in ds if d != brain]

    def f(db):
        db.execute("UPDATE crm_contacts SET depts_json=?, updated_at=? WHERE id=?",
                   (json.dumps(ds, ensure_ascii=False), _now(), int(cid)))
        _su_kien(db, cid, "phong", ("Thêm phòng " if bat else "Gỡ phòng ") + brain, by, brain)
        db.commit()
    _dung(f)
    return ds


def xoa_lien_he(cid: int, allowed: Optional[set], by: str, khoi_phuc: bool = False) -> bool:
    c = lay_lien_he(cid)
    if not c or not _thay_hien_thi(c, allowed):
        raise PermissionError("Không thấy khách này")

    def f(db):
        db.execute("UPDATE crm_contacts SET deleted=?, updated_at=? WHERE id=?",
                   (0 if khoi_phuc else 1, _now(), int(cid)))
        _su_kien(db, cid, "khoi_phuc" if khoi_phuc else "xoa",
                 "Khôi phục khách" if khoi_phuc else "Xoá khách (có thể khôi phục)", by)
        db.commit()
    _dung(f)
    return True


# ------------------------------------------------------------------ dữ liệu mẫu
NGUON_MAU = "Dữ liệu mẫu"
# (tên, điện thoại, công ty, nhãn, [(cơ hội, giá trị, giai đoạn)], [(việc, số ngày tới hạn so với hôm nay)])
_MAU = [
    ("Chị Lan Anh", "0901234567", "Quán cà phê Lan Anh", ["vip", "b2b"],
     [("Tiệc sinh nhật công ty", 12000000, "tu_van")], [("Gọi lại chị Lan Anh", 0)]),
    ("Anh Minh Tuấn", "0912888321", "Công ty Tuấn Minh", [],
     [("Đơn bánh hội nghị", 25000000, "moi")], [("Gửi báo giá cho anh Minh Tuấn", 2)]),
    ("Chị Hồng Nhung", "0987456123", "", ["thân thiết"],
     [("Bánh sinh nhật", 4000000, "cho_chot")], []),
    ("Anh Quốc Bảo", "0933000111", "", [],
     [("Đơn bánh tháng 10", 390000, "da_chot")], []),
]


def nap_mau(brain: str, allowed: Optional[set], by: str) -> int:
    """Nạp bốn khách mẫu (kèm cơ hội, việc) vào một phòng để xem giao diện có dữ liệu. Gắn nguồn "Dữ liệu mẫu"
    để xoá sạch được; phòng đã có khách mẫu thì không nạp thêm (trả 0)."""
    if not brain or (allowed is not None and brain not in allowed):
        raise PermissionError("Phòng ngoài phạm vi của bạn")
    if any(c.get("source") == NGUON_MAU for c in danh_sach_lien_he(allowed, brain=brain, limit=1000)):
        return 0
    from datetime import timedelta
    hom_nay = date.today()
    for ten, sdt, cty, nhan, deals, viec in _MAU:
        c = luu_lien_he({"name": ten, "phone": sdt, "company": cty, "tags": nhan, "source": NGUON_MAU,
                         "depts": [brain]}, allowed, by, brain)
        for tieu_de, gia_tri, gd in deals:
            luu_deal({"contact_id": c["id"], "brain": brain, "title": tieu_de, "value": str(gia_tri), "stage": gd}, allowed, by)
        for tieu_de, ngay in viec:
            them_viec({"contact_id": c["id"], "brain": brain, "title": tieu_de,
                       "due": (hom_nay + timedelta(days=ngay)).isoformat()}, allowed, by)
    return len(_MAU)


def xoa_mau(brain: str, allowed: Optional[set]) -> int:
    """Xoá HẲN các khách mẫu (và cơ hội, việc, sự kiện, đề xuất của họ) trong một phòng. Khách thật không bị đụng."""
    if not brain or (allowed is not None and brain not in allowed):
        raise PermissionError("Phòng ngoài phạm vi của bạn")
    ids = [c["id"] for c in danh_sach_lien_he(allowed, brain=brain, limit=1000) if c.get("source") == NGUON_MAU]
    ids += [c["id"] for c in danh_sach_lien_he(allowed, brain=brain, limit=1000, da_xoa=True) if c.get("source") == NGUON_MAU]
    if not ids:
        return 0

    def f(db):
        q = ",".join("?" * len(ids))
        for bang in ("crm_deals", "crm_todos", "crm_events", "crm_proposals"):
            db.execute("DELETE FROM %s WHERE contact_id IN (%s)" % (bang, q), ids)
        db.execute("DELETE FROM crm_contacts WHERE id IN (%s)" % q, ids)
        db.commit()
    _dung(f)
    return len(ids)


# ------------------------------------------------------------------ cơ hội
def _deal_public(r: dict) -> dict:
    return dict(r)


def luu_deal(data: dict, allowed: Optional[set], by: str) -> dict:
    cid = int(data.get("contact_id") or 0)
    brain = _s(data.get("brain"), 120)
    c = lay_lien_he(cid)
    if not c or not _thay_hien_thi(c, allowed):
        raise PermissionError("Không thấy khách này")
    if not brain or (allowed is not None and brain not in allowed):
        raise PermissionError("Phòng ngoài phạm vi của bạn")
    title = _s(data.get("title"), 160)
    if not title:
        raise ValueError("Thiếu tên cơ hội")
    chu_so = re.sub(r"[^\d]", "", str(data.get("value") or ""))
    value = float(chu_so) if chu_so else 0.0
    ds = giai_doan(brain)
    stage = str(data.get("stage") or ds[0]["key"])
    if stage not in {g["key"] for g in ds}:
        stage = ds[0]["key"]
    now = _now()
    did = int(data.get("id") or 0)

    def f(db):
        if did:
            r = db.execute("SELECT * FROM crm_deals WHERE id=?", (did,)).fetchone()
            if not r or (allowed is not None and r["brain"] not in allowed):
                raise PermissionError("Không thấy cơ hội này")
            db.execute("UPDATE crm_deals SET title=?, value=?, updated_at=? WHERE id=?",
                       (title, value, now, did))
            return did
        cur = db.execute("INSERT INTO crm_deals(contact_id, brain, title, value, stage, owner, created_at, updated_at)"
                         " VALUES(?,?,?,?,?,?,?,?)", (cid, brain, title, value, stage, _s(by, 60), now, now))
        # Một cơ hội cho phòng X thì khách phải hiện trong phòng X.
        ds_c = c["depts"]
        if brain not in ds_c:
            db.execute("UPDATE crm_contacts SET depts_json=?, updated_at=? WHERE id=?",
                       (json.dumps(ds_c + [brain], ensure_ascii=False), now, cid))
        _su_kien(db, cid, "deal", f"Tạo cơ hội: {title}", by, brain)
        db.commit()
        return int(cur.lastrowid)
    did = _dung(f)
    return lay_deal(did)


def lay_deal(did: int) -> Optional[dict]:
    r = _dung(lambda db: db.execute("SELECT * FROM crm_deals WHERE id=?", (int(did),)).fetchone())
    return _deal_public(_row(r)) if r else None


def chuyen_buoc(did: int, stage: str, allowed: Optional[set], by: str) -> dict:
    d = lay_deal(did)
    if not d or (allowed is not None and d["brain"] not in allowed):
        raise PermissionError("Không thấy cơ hội này")
    ds = {g["key"]: g for g in giai_doan(d["brain"])}
    if stage not in ds:
        raise ValueError("Giai đoạn không có trong phòng này")
    kind = ds[stage]["kind"]

    def f(db):
        db.execute("UPDATE crm_deals SET stage=?, closed_at=?, updated_at=? WHERE id=?",
                   (stage, _now() if kind != "open" else None, _now(), int(did)))
        _su_kien(db, d["contact_id"], "deal", f"{d['title']}: chuyển sang {ds[stage]['label']}", by, d["brain"])
        db.commit()
    _dung(f)
    return lay_deal(did)


def xoa_deal(did: int, allowed: Optional[set], by: str) -> bool:
    d = lay_deal(did)
    if not d or (allowed is not None and d["brain"] not in allowed):
        raise PermissionError("Không thấy cơ hội này")

    def f(db):
        db.execute("DELETE FROM crm_deals WHERE id=?", (int(did),))
        _su_kien(db, d["contact_id"], "deal", f"Xoá cơ hội: {d['title']}", by, d["brain"])
        db.commit()
    _dung(f)
    return True


def pipeline(brain: str, allowed: Optional[set]) -> dict:
    if allowed is not None and brain not in allowed:
        raise PermissionError("Phòng ngoài phạm vi của bạn")
    ds = giai_doan(brain)
    rows = _dung(lambda db: db.execute(
        "SELECT d.*, c.name AS contact_name, c.deleted AS contact_deleted FROM crm_deals d"
        " JOIN crm_contacts c ON c.id=d.contact_id WHERE d.brain=? ORDER BY d.updated_at DESC", (brain,)).fetchall())
    cot = {g["key"]: [] for g in ds}
    for r in rows:
        d = _row(r)
        if d.pop("contact_deleted"):
            continue
        cot.setdefault(d["stage"], cot[ds[0]["key"]]).append(d)
    out = []
    for g in ds:
        items = cot.get(g["key"], [])
        out.append({**g, "deals": items, "count": len(items), "total": sum(i["value"] for i in items)})
    thang = [x for g in out if g["kind"] == "won" for x in g["deals"]]
    mat = [x for g in out if g["kind"] == "lost" for x in g["deals"]]
    dong = len(thang) + len(mat)
    return {"brain": brain, "stages": out,
            "dang_theo": sum(g["total"] for g in out if g["kind"] == "open"),
            "da_chot": sum(x["value"] for x in thang),
            "ti_le_thang": round(len(thang) / dong, 3) if dong else None}


# ------------------------------------------------------------------ việc chăm sóc
def _han_ok(s: str) -> str:
    s = str(s or "").strip()[:10]
    if not s:
        return ""
    try:
        return date.fromisoformat(s).isoformat()
    except Exception:
        raise ValueError("Hạn phải dạng năm-tháng-ngày, ví dụ 2026-10-30")


def them_viec(data: dict, allowed: Optional[set], by: str) -> dict:
    cid = int(data.get("contact_id") or 0)
    brain = _s(data.get("brain"), 120)
    c = lay_lien_he(cid)
    if not c or not _thay_hien_thi(c, allowed):
        raise PermissionError("Không thấy khách này")
    if not brain or (allowed is not None and brain not in allowed):
        raise PermissionError("Phòng ngoài phạm vi của bạn")
    title = _s(data.get("title"), 200)
    if not title:
        raise ValueError("Thiếu nội dung việc")
    han = _han_ok(data.get("due"))
    now = _now()

    def f(db):
        cur = db.execute("INSERT INTO crm_todos(contact_id, brain, title, due, owner, created_at) VALUES(?,?,?,?,?,?)",
                         (cid, brain, title, han, _s(by, 60), now))
        if brain not in c["depts"]:
            db.execute("UPDATE crm_contacts SET depts_json=?, updated_at=? WHERE id=?",
                       (json.dumps(c["depts"] + [brain], ensure_ascii=False), now, cid))
        _su_kien(db, cid, "viec", f"Việc mới: {title}" + (f" (hạn {han})" if han else ""), by, brain)
        db.commit()
        return int(cur.lastrowid)
    tid = _dung(f)
    return lay_viec(tid)


def lay_viec(tid: int) -> Optional[dict]:
    r = _dung(lambda db: db.execute("SELECT * FROM crm_todos WHERE id=?", (int(tid),)).fetchone())
    return _row(r) if r else None


def danh_sach_viec(allowed: Optional[set], brain: str = "", contact_id: int = 0,
                   xong: Optional[bool] = False) -> List[dict]:
    where, args = [], []
    if brain:
        where.append("t.brain=?"); args.append(brain)
    if contact_id:
        where.append("t.contact_id=?"); args.append(int(contact_id))
    if xong is not None:
        where.append("t.done=?"); args.append(1 if xong else 0)
    sql = ("SELECT t.*, c.name AS contact_name FROM crm_todos t JOIN crm_contacts c ON c.id=t.contact_id"
           " WHERE c.deleted=0" + (" AND " + " AND ".join(where) if where else "")
           + " ORDER BY t.done, CASE WHEN t.due='' THEN '9999' ELSE t.due END, t.id")
    hom_nay = date.today().isoformat()
    out = []
    for r in _dung(lambda db: db.execute(sql, args).fetchall()):
        d = _row(r)
        if allowed is not None and d["brain"] not in allowed:
            continue
        d["tre_han"] = bool(d["due"]) and not d["done"] and d["due"] < hom_nay
        d["hom_nay"] = d["due"] == hom_nay and not d["done"]
        out.append(d)
    return out


def xong_viec(tid: int, allowed: Optional[set], by: str, xong: bool = True) -> dict:
    t = lay_viec(tid)
    if not t or (allowed is not None and t["brain"] not in allowed):
        raise PermissionError("Không thấy việc này")

    def f(db):
        db.execute("UPDATE crm_todos SET done=?, done_at=? WHERE id=?",
                   (1 if xong else 0, _now() if xong else None, int(tid)))
        if xong:
            _su_kien(db, t["contact_id"], "viec", f"Đã xong: {t['title']}", by, t["brain"])
        db.commit()
    _dung(f)
    kq = lay_viec(tid)
    if xong:
        _ghi_kanban_xong(kq, by)
    return kq


def _ghi_kanban_xong(t: dict, by: str) -> None:
    """Việc xong đáp xuống cột Xong của Kanban phòng (giống việc mẫu). Hỏng thì bỏ qua:
    đã đánh dấu xong trong CRM là đủ, không để lỗi Kanban chặn nhân viên."""
    try:
        tasks = _deps["tasks"]()
        if tasks is None:
            return
        c = lay_lien_he(t["contact_id"]) or {}
        tieu_de = f"[CRM] {t['title']} ({c.get('name') or 'khách'})"
        tasks.ghi_viec_xong(t["brain"], tieu_de, tieu_de, "", f"crm:todo:{t['id']}", by or "crm",
                            {"crm_contact": t["contact_id"], "crm_todo": t["id"]})
    except Exception as e:
        print(f"[crm] ghi Kanban lỗi: {type(e).__name__}: {e}")


# ------------------------------------------------------------------ trích hồ sơ
_PROMPT_TRICH = (
    "Bạn đọc đoạn chat giữa nhân viên và khách hàng rồi trích hồ sơ khách. Chỉ trả về MỘT đối tượng JSON, "
    "không giải thích, với các khoá (bỏ khoá nào không có thông tin chắc chắn trong đoạn chat): "
    "name, phone, email, company, nhu_cau, ngan_sach, han, phan_doi, buoc_tiep, tom_tat. "
    "Tuyệt đối không bịa. Mỗi giá trị là chuỗi ngắn tiếng Việt. tom_tat tối đa 2 câu.")


def _json_tu_chu(txt: str) -> dict:
    m = re.search(r"\{.*\}", str(txt or ""), re.S)
    if not m:
        return {}
    try:
        d = json.loads(m.group(0))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def trich_tu_chu(text: str, dung_model: bool = True) -> dict:
    """Luật cố định trước (SĐT, email), model sau nếu có. Trả các trường tìm được."""
    out: Dict[str, str] = {}
    sdt, em = bat_sdt(text), bat_email(text)
    if sdt:
        out["phone"] = sdt[0]
    if em:
        out["email"] = em[0]
    if dung_model and str(text or "").strip():
        try:
            raw = _deps["model"](_PROMPT_TRICH, str(text)[-6000:])
        except Exception:
            raw = ""
        for k, v in _json_tu_chu(raw).items():
            v = str(v or "").strip()[:300]
            if not v or k not in TRUONG_CHINH + TRUONG_HO_SO:
                continue
            if k == "phone":
                v = chuan_sdt(v)
            elif k == "email":
                v = (bat_email(v) or [""])[0]
            if v and k not in out:     # luật cố định thắng model
                out[k] = v
    return out


def _tin_gan_day(customer_id: int, sau_id: int = 0, limit: int = 60) -> List[dict]:
    def f(db):
        return db.execute(
            "SELECT m.id, m.sender_type, m.text, m.created_at FROM messages m JOIN conversations c"
            " ON c.id=m.conversation_id WHERE c.customer_id=? AND m.id>? AND m.text!=''"
            " ORDER BY m.id DESC LIMIT ?", (int(customer_id), int(sau_id), int(limit))).fetchall()
    return [_row(r) for r in reversed(_dung(f))]


def _loc_thay_doi(c: dict, found: dict) -> dict:
    """Bỏ trường trùng giá trị hiện có và trường nhân viên đã sửa tay (khoá)."""
    khoa = set(c.get("locked") or [])
    out = {}
    for k, v in found.items():
        if k in TRUONG_CHINH:
            if k in khoa or str(c.get(k) or "") == v:
                continue
            if k == "name" and c.get("name"):
                continue       # không đổi tên đã có
        else:
            if str((c.get("profile") or {}).get(k) or "") == v:
                continue
        out[k] = v
    return out


def tao_de_xuat(cid: int, found: dict, source: str = "chat") -> Optional[int]:
    c = lay_lien_he(cid)
    if not c or not found:
        return None
    ch = _loc_thay_doi(c, found)
    if not ch:
        return None

    def f(db):
        # Đã có đề xuất chờ cho khách này thì gộp vào đó, không chất đống.
        r = db.execute("SELECT id, fields_json FROM crm_proposals WHERE contact_id=? AND status='pending'"
                       " ORDER BY id DESC LIMIT 1", (int(cid),)).fetchone()
        if r:
            cu = _loads(r["fields_json"], {})
            cu.update(ch)
            db.execute("UPDATE crm_proposals SET fields_json=?, source=? WHERE id=?",
                       (json.dumps(cu, ensure_ascii=False), source, r["id"]))
            db.commit()
            return int(r["id"])
        cur = db.execute("INSERT INTO crm_proposals(contact_id, source, fields_json, created_at) VALUES(?,?,?,?)",
                         (int(cid), source, json.dumps(ch, ensure_ascii=False), _now()))
        db.commit()
        return int(cur.lastrowid)
    return _dung(f)


def ap_dung(cid: int, fields: dict, by: str, kind: str = "trich") -> dict:
    """Ghi các trường vào hồ sơ. Trường chính vào cột, còn lại vào profile."""
    c = lay_lien_he(cid)
    if not c:
        raise ValueError("Không tìm thấy khách")
    chinh = {k: v for k, v in fields.items() if k in TRUONG_CHINH}
    ho_so = {k: v for k, v in fields.items() if k in TRUONG_HO_SO}

    def f(db):
        r = db.execute("SELECT meta_json FROM crm_contacts WHERE id=?", (int(cid),)).fetchone()
        meta = _loads(r["meta_json"], {})
        pf = dict(meta.get("profile") or {})
        pf.update(ho_so)
        meta["profile"] = pf
        sets, args = ["meta_json=?", "updated_at=?"], [json.dumps(meta, ensure_ascii=False), _now()]
        for k, v in chinh.items():
            sets.insert(0, f"{k}=?"); args.insert(0, v)
        db.execute(f"UPDATE crm_contacts SET {', '.join(sets)} WHERE id=?", args + [int(cid)])
        # Số điện thoại, email là dữ liệu liên lạc: dòng thời gian chỉ ghi TÊN trường đã đổi.
        tt = ", ".join((k if k in ("phone", "email") else f"{k}: {v}") for k, v in list(fields.items())[:6])
        _su_kien(db, cid, kind, "Cập nhật hồ sơ (" + tt + ")", by)
        db.commit()
    _dung(f)
    return lay_lien_he(cid)


def _danh_dau_da_trich(cid: int, msg_id: int) -> None:
    def f(db):
        r = db.execute("SELECT meta_json FROM crm_contacts WHERE id=?", (int(cid),)).fetchone()
        if not r:
            return
        meta = _loads(r["meta_json"], {})
        meta["trich_msg"] = int(msg_id)
        db.execute("UPDATE crm_contacts SET meta_json=? WHERE id=?",
                   (json.dumps(meta, ensure_ascii=False), int(cid)))
        db.commit()
    _dung(f)


def trich_lien_he(cid: int, tu_dong: bool = False) -> dict:
    """Đọc tin MỚI của khách (kể từ lần trích trước), trích hồ sơ, rồi theo chế độ: tạo đề xuất
    chờ duyệt, hoặc (chế độ auto, chỉ khi Joyce tự chạy) áp thẳng. Bấm tay luôn ra đề xuất."""
    c = lay_lien_he(cid)
    if not c:
        return {"ok": False, "error": "Không tìm thấy khách"}
    if not c.get("customer_id"):
        return {"ok": False, "error": "Khách này nhập tay, không có hội thoại để đọc"}
    meta_msg = int(_loads(_dung(lambda db: db.execute(
        "SELECT meta_json FROM crm_contacts WHERE id=?", (int(cid),)).fetchone()["meta_json"]), {}).get("trich_msg") or 0)
    tin = _tin_gan_day(c["customer_id"], meta_msg)
    if not tin:
        return {"ok": True, "co_gi_moi": False}
    text = "\n".join(("Khách: " if m["sender_type"] == "customer" else "Nhân viên: ") + m["text"] for m in tin)
    found = trich_tu_chu(text)
    _danh_dau_da_trich(cid, tin[-1]["id"])
    ch = _loc_thay_doi(c, found)
    if not ch:
        return {"ok": True, "co_gi_moi": False, "da_doc": len(tin)}
    if tu_dong and che_do_trich() == "auto":
        ap_dung(cid, ch, "Joyce (tự động)")
        return {"ok": True, "co_gi_moi": True, "da_ap": True, "fields": ch}
    pid = tao_de_xuat(cid, ch, "tu_dong" if tu_dong else "tay")
    return {"ok": True, "co_gi_moi": True, "da_ap": False, "de_xuat": pid, "fields": ch}


def khi_khach_nhan(customer_id: int) -> None:
    """Móc từ conversations.ghi_su_kien sau mỗi tin KHÁCH. Rẻ: chỉ đếm khi khách đã có trong CRM,
    và chỉ mở luồng trích khi đủ ngưỡng. Mọi lỗi nuốt vào đây, không bao giờ làm hỏng lượt chat."""
    try:
        if che_do_trich() == "off" or not customer_id:
            return
        r = _dung(lambda db: db.execute(
            "SELECT id, meta_json FROM crm_contacts WHERE customer_id=? AND deleted=0 LIMIT 1",
            (int(customer_id),)).fetchone())
        if not r:
            return
        cid = int(r["id"])
        meta = _loads(r["meta_json"], {})
        n = _dung(lambda db: db.execute(
            "SELECT COUNT(*) AS n FROM messages m JOIN conversations c ON c.id=m.conversation_id"
            " WHERE c.customer_id=? AND m.id>? AND m.sender_type='customer'",
            (int(customer_id), int(meta.get("trich_msg") or 0))).fetchone()["n"])
        if n < nguong_trich():
            return
        with _lock_trich:
            if cid in _dang_trich:
                return
            _dang_trich.add(cid)

        def chay():
            try:
                trich_lien_he(cid, tu_dong=True)
            except Exception as e:
                print(f"[crm] trích lỗi: {type(e).__name__}: {e}")
            finally:
                with _lock_trich:
                    _dang_trich.discard(cid)
        threading.Thread(target=chay, daemon=True).start()
    except Exception as e:
        print(f"[crm] móc tin khách lỗi: {type(e).__name__}: {e}")


def danh_sach_de_xuat(allowed: Optional[set], brain: str = "") -> List[dict]:
    rows = _dung(lambda db: db.execute(
        "SELECT p.*, c.name AS contact_name, c.depts_json AS depts_json FROM crm_proposals p"
        " JOIN crm_contacts c ON c.id=p.contact_id WHERE p.status='pending' AND c.deleted=0"
        " ORDER BY p.id DESC").fetchall())
    out = []
    for r in rows:
        d = _row(r)
        depts = _loads(d.pop("depts_json"), [])
        if allowed is not None and not (set(depts) & allowed):
            continue
        if brain and brain not in depts:
            continue
        d["fields"] = _loads(d.pop("fields_json"), {})
        d["depts"] = depts
        out.append(d)
    return out


def duyet_de_xuat(pid: int, allowed: Optional[set], by: str, chon: Optional[List[str]] = None,
                  tu_choi: bool = False) -> dict:
    r = _dung(lambda db: db.execute("SELECT * FROM crm_proposals WHERE id=?", (int(pid),)).fetchone())
    if not r or r["status"] != "pending":
        raise ValueError("Đề xuất không còn chờ duyệt")
    c = lay_lien_he(r["contact_id"])
    if not c or not _thay_hien_thi(c, allowed):
        raise PermissionError("Không thấy khách này")
    fields = _loads(r["fields_json"], {})
    if chon is not None:
        fields = {k: v for k, v in fields.items() if k in set(chon)}
    if not tu_choi and fields:
        ap_dung(c["id"], fields, by, "duyet")

    def f(db):
        db.execute("UPDATE crm_proposals SET status=?, decided_by=?, decided_at=? WHERE id=?",
                   ("rejected" if tu_choi or not fields else "approved", _s(by, 60), _now(), int(pid)))
        db.commit()
    _dung(f)
    return {"ok": True, "da_ap": (not tu_choi) and bool(fields)}


# ------------------------------------------------------------------ nhập từ hộp thư, wiki, phân khúc
def khach_hop_thu_chua_nhap(q: str = "", limit: int = 100) -> List[dict]:
    ds = conversations.danh_sach_khach(q=q, limit=limit)
    da = {r["customer_id"] for r in _dung(lambda db: db.execute(
        "SELECT customer_id FROM crm_contacts WHERE customer_id IS NOT NULL").fetchall())}
    return [k for k in ds if k["id"] not in da]


def nhap_tu_hop_thu(customer_id: int, brain: str, by: str) -> dict:
    k = conversations.khach(customer_id)
    if not k:
        raise ValueError("Không tìm thấy khách trong hộp thư")
    ex = _dung(lambda db: db.execute("SELECT id FROM crm_contacts WHERE customer_id=?", (int(customer_id),)).fetchone())
    if ex:
        c = lay_lien_he(ex["id"])
        if brain not in c["depts"]:
            gan_phong(c["id"], brain, True, None, by)
        return lay_lien_he(ex["id"])
    return luu_lien_he({"customer_id": int(customer_id), "name": k.get("name") or "Khách " + str(customer_id),
                        "source": k.get("channel_label") or k.get("channel") or "hộp thư",
                        "note": k.get("note") or "", "tags": k.get("tags") or [], "depts": [brain]},
                       None, by)


def _bo_lien_lac(text: str) -> str:
    """Xoá số điện thoại và email khỏi một dòng chữ trước khi đưa lên wiki."""
    t = _RE_EMAIL.sub("[email]", str(text or ""))
    return _RE_SDT.sub("[sđt]", t)


def ghi_nho_wiki(cid: int, brain: str, allowed: Optional[set], by: str) -> dict:
    """Chưng cất một khách thành trang wiki của PHÒNG, bằng luật cố định (không tốn model).
    Cố ý KHÔNG ghi số điện thoại, email, ghi chú nguyên văn: wiki là tri thức dùng lại, không
    phải sổ liên lạc. Chỉ giữ nhu cầu, phản đối, giai đoạn, kết quả."""
    c = lay_lien_he(cid)
    if not c or not _thay_hien_thi(c, allowed):
        raise PermissionError("Không thấy khách này")
    if allowed is not None and brain not in allowed:
        raise PermissionError("Phòng ngoài phạm vi của bạn")
    root = _deps["brain_root"](brain)
    if not root or not Path(root).is_dir():
        raise ValueError("Không tìm thấy brain của phòng")
    pf = c["profile"]
    deals = [d for d in _dung(lambda db: [_row(r) for r in db.execute(
        "SELECT * FROM crm_deals WHERE contact_id=? AND brain=?", (int(cid), brain)).fetchall()])]
    gd = {g["key"]: g["label"] for g in giai_doan(brain)}
    ev = _dung(lambda db: [_row(r) for r in db.execute(
        "SELECT * FROM crm_events WHERE contact_id=? AND (brain='' OR brain=?) ORDER BY id DESC LIMIT 15",
        (int(cid), brain)).fetchall()])
    ten = c["name"] or "Khách"
    lines = ["---", "type: wiki", f"title: Khách {ten}", "nguon: crm", f"cap_nhat: {date.today().isoformat()}", "---", "",
             f"# Khách {ten}", ""]
    for k, nhan in (("nhu_cau", "Nhu cầu"), ("ngan_sach", "Ngân sách"), ("han", "Thời hạn"),
                    ("phan_doi", "Điều khách lo ngại"), ("buoc_tiep", "Bước tiếp theo"), ("tom_tat", "Tóm tắt")):
        if pf.get(k):
            lines.append(f"- **{nhan}:** {pf[k]}")
    if c.get("company"):
        lines.append(f"- **Đơn vị:** {c['company']}")
    if deals:
        lines += ["", "## Cơ hội"]
        for d in deals:
            lines.append(f"- {d['title']}: {gd.get(d['stage'], d['stage'])}"
                         + (f", {int(d['value']):,} đ".replace(",", ".") if d["value"] else ""))
    if ev:
        lines += ["", "## Diễn biến gần đây"]
        for e in reversed(ev):
            lines.append(f"- {datetime.fromtimestamp(e['created_at']).strftime('%d/%m/%Y')}: {_bo_lien_lac(e['text'])}")
    lines += ["", "_Trang này do CRM chưng cất; số điện thoại và email không ghi ở đây._", ""]
    thu_muc = Path(root) / "wiki" / "khach-hang"
    thu_muc.mkdir(parents=True, exist_ok=True)
    f = thu_muc / (_slug(ten) + f"-{cid}.md")
    f.write_text("\n".join(lines), encoding="utf-8")
    ghi_su_kien_crm(cid, "wiki", "Ghi nhớ cách xử lý vào wiki phòng", by, brain)
    return {"ok": True, "path": f"wiki/khach-hang/{f.name}"}


def phan_khuc(brain: str, allowed: Optional[set]) -> List[dict]:
    """Phân khúc tính bằng luật cố định. Mỗi nhóm kèm danh sách khách để mở ngay."""
    if allowed is not None and brain not in allowed:
        raise PermissionError("Phòng ngoài phạm vi của bạn")
    lh = danh_sach_lien_he(allowed, brain=brain, limit=1000)
    ids = {c["id"] for c in lh}
    deals = [d for d in _dung(lambda db: [_row(r) for r in db.execute(
        "SELECT * FROM crm_deals WHERE brain=?", (brain,)).fetchall()]) if d["contact_id"] in ids]
    kind = {g["key"]: g["kind"] for g in giai_doan(brain)}
    viec = [t for t in danh_sach_viec(allowed, brain=brain) if t["contact_id"] in ids]
    hom_nay = date.today().isoformat()
    ten = {c["id"]: c for c in lh}

    def mini(cids):
        return [{"id": i, "name": ten[i]["name"] or ten[i]["phone"] or ("#" + str(i))} for i in cids if i in ten]
    thang = {}
    for d in deals:
        if kind.get(d["stage"]) == "won":
            thang[d["contact_id"]] = thang.get(d["contact_id"], 0) + 1
    dang_theo = {d["contact_id"] for d in deals if kind.get(d["stage"]) == "open"}
    co_deal = {d["contact_id"] for d in deals}
    cham = {t["contact_id"] for t in viec if t["due"] and t["due"] <= hom_nay}
    ba_muoi = _now() - 30 * 86400
    im = [c["id"] for c in lh if c["updated_at"] < ba_muoi and c["id"] in dang_theo]
    nhom = [
        ("can_cham_hom_nay", "Cần chăm hôm nay", sorted(cham)),
        ("dang_theo", "Đang có cơ hội mở", sorted(dang_theo)),
        ("chua_co_co_hoi", "Chưa có cơ hội nào", sorted(ids - co_deal)),
        ("than_thiet", "Thân thiết (từ 3 cơ hội đã chốt)", sorted(i for i, n in thang.items() if n >= 3)),
        ("nguoi_lau_khong_cham", "Cơ hội mở nhưng lâu chưa chăm (30 ngày)", sorted(im)),
    ]
    return [{"key": k, "label": lb, "count": len(v), "contacts": mini(v)} for k, lb, v in nhom]


def tong_quan(brain: str, allowed: Optional[set]) -> dict:
    lh = danh_sach_lien_he(allowed, brain=brain, limit=1000)
    # Chọn một phòng thì tính phòng đó; "Tất cả phòng" cộng dồn các phòng đang có cơ hội mà người xem được thấy.
    if brain:
        brains = [brain]
    else:
        co = _dung(lambda db: [r[0] for r in db.execute("SELECT DISTINCT brain FROM crm_deals").fetchall()])
        brains = sorted(b for b in co if allowed is None or b in allowed)
    dang_theo = da_chot = so_mo = thang = dong = 0
    mua = set()
    for b in brains:
        pl = pipeline(b, allowed)
        dang_theo += pl["dang_theo"]
        da_chot += pl["da_chot"]
        for g in pl["stages"]:
            if g["kind"] == "open":
                so_mo += g["count"]
            elif g["kind"] == "won":
                thang += g["count"]
                dong += g["count"]
                mua.update(d["contact_id"] for d in g["deals"])
            else:
                dong += g["count"]
    viec = danh_sach_viec(allowed, brain=brain)
    return {"lien_he": len(lh), "viec_mo": len(viec), "viec_tre": sum(1 for t in viec if t["tre_han"]),
            "viec_hom_nay": sum(1 for t in viec if t["hom_nay"]),
            "de_xuat": len(danh_sach_de_xuat(allowed, brain)),
            "dang_theo": dang_theo, "da_chot": da_chot, "so_co_hoi": so_mo, "da_mua": len(mua),
            "ti_le_thang": round(thang / dong, 3) if dong else None}


# ------------------------------------------------------------------ HTTP
QUAN_LY = ("ceo", "giam_doc", "truong_phong", "lead")


def _nguoi(request: Request) -> tuple:
    """(ten, allowed|None, la_quan_ly).

    Nhân viên cần quyền `crm` (dùng đầy đủ) hoặc `crm_xem` (chỉ xem; mọi method ghi trả 403), và chỉ
    thấy các phòng vừa thuộc phạm vi của mình vừa đã được admin MỞ CRM (`phong_bat`)."""
    st = getattr(request.state, "staff", None) or {}
    if not st:
        return "Chủ", None, True
    q = st.get("quyen") or []
    if "crm" not in q and "crm_xem" not in q:
        raise HTTPException(403, "Tài khoản chưa được cấp quyền dùng CRM")
    if "crm" not in q and request.method != "GET":
        raise HTTPException(403, "Tài khoản chỉ được xem CRM, không sửa được")
    scope = _deps["scope"]() or ()
    allowed = {Path(r).name for r in scope}
    bat = phong_bat()
    if bat is not None:
        allowed &= bat
    quan_ly = str(st.get("role") or "") in QUAN_LY
    return str(st.get("ten") or "Nhân viên"), allowed, quan_ly


def _phong_chinh(allowed: Optional[set], request: Request) -> str:
    if allowed is None:
        return ""
    scope = _deps["scope"]() or ()
    return Path(scope[0]).name if scope else ""


def _loi(fn):
    """Đổi PermissionError thành 403 và ValueError thành 400, cho cả hàm thường lẫn async."""
    import functools
    import inspect

    def doi(e):
        if isinstance(e, PermissionError):
            return HTTPException(403, str(e) or "Không có quyền")
        return HTTPException(400, str(e))

    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def wrap(*a, **k):
            try:
                return await fn(*a, **k)
            except (PermissionError, ValueError) as e:
                raise doi(e)
    else:
        @functools.wraps(fn)
        def wrap(*a, **k):
            try:
                return fn(*a, **k)
            except (PermissionError, ValueError) as e:
                raise doi(e)
    return wrap


def _brain_hop_le(brain: str, allowed: Optional[set], request: Request) -> str:
    b = str(brain or "").strip()
    if allowed is None:
        return b
    return b if b in allowed else _phong_chinh(allowed, request)


@router.get("/crm/me")
async def crm_me(request: Request):
    ten, allowed, ql = _nguoi(request)
    ph = _deps["phong"]()
    if allowed is not None:
        ph = [p for p in ph if p.get("brain") in allowed] or [{"brain": b, "ten": b} for b in sorted(allowed)]
    else:
        bat = phong_bat()
        ph = [dict(p, bat=(bat is None or p.get("brain") in bat)) for p in ph]
    st = getattr(request.state, "staff", None) or {}
    chi_xem = bool(st) and "crm" not in (st.get("quyen") or [])
    return {"ok": True, "ten": ten, "admin": allowed is None, "quan_ly": ql, "phong": ph, "chi_xem": chi_xem,
            "mac_dinh": (_phong_chinh(allowed, request) if allowed is not None
                         else (ph[0]["brain"] if ph else "")),
            "che_do": che_do_trich(), "nguong": nguong_trich()}


@router.get("/crm/lien-he")
async def crm_list(request: Request, brain: str = Query(""), q: str = Query(""), tag: str = Query(""),
                   limit: int = Query(200), offset: int = Query(0), da_xoa: int = Query(0)):
    _, allowed, _ql = _nguoi(request)
    b = _brain_hop_le(brain, allowed, request) if brain else ""
    items = danh_sach_lien_he(allowed, brain=b, q=q, tag=tag, limit=limit, offset=offset, da_xoa=bool(da_xoa))
    chot = tong_da_chot([c["id"] for c in items], allowed)
    for c in items:
        c["da_chot"] = chot.get(c["id"], 0)
        c["mau"] = c.get("source") == NGUON_MAU
    return {"ok": True, "items": items}


@router.get("/crm/lien-he/{cid}")
@_loi
def crm_detail(request: Request, cid: int, brain: str = Query("")):
    _, allowed, _ql = _nguoi(request)
    c = lay_lien_he(cid)
    if not c or not _thay_hien_thi(c, allowed):
        raise HTTPException(404, "Không thấy khách")
    deals = [d for d in _dung(lambda db: [_row(r) for r in db.execute(
        "SELECT * FROM crm_deals WHERE contact_id=? ORDER BY updated_at DESC", (cid,)).fetchall()])
        if allowed is None or d["brain"] in allowed]
    ev = [e for e in _dung(lambda db: [_row(r) for r in db.execute(
        "SELECT * FROM crm_events WHERE contact_id=? ORDER BY id DESC LIMIT 60", (cid,)).fetchall()])
        if allowed is None or e["brain"] == "" or e["brain"] in allowed]
    convs = []
    if c.get("customer_id"):
        try:
            convs = [{"id": x.get("id"), "title": x.get("title") or x.get("customer_name"),
                      "channel": x.get("channel"), "last_message": x.get("last_message"),
                      "last_message_at": x.get("last_message_at")}
                     for x in conversations.hoi_thoai_cua_khach(c["customer_id"])[:5]]
        except Exception:
            convs = []
    stages = {}
    for d in deals:
        if d["brain"] not in stages:
            stages[d["brain"]] = {g["key"]: g["label"] for g in giai_doan(d["brain"])}
    return {"ok": True, "contact": c, "deals": deals, "events": ev, "conversations": convs,
            "stage_labels": stages,
            "todos": danh_sach_viec(allowed, contact_id=cid, xong=None),
            "proposals": [p for p in danh_sach_de_xuat(allowed) if p["contact_id"] == cid]}


@router.post("/crm/lien-he")
@_loi
async def crm_save(request: Request, id: int = Form(0), name: str = Form(""), phone: str = Form(""),
                   email: str = Form(""), company: str = Form(""), source: str = Form(""),
                   note: str = Form(""), tags: str = Form(""), depts: str = Form("")):
    ten, allowed, _ql = _nguoi(request)
    ds = [x.strip() for x in re.split(r"[,\n]", depts or "") if x.strip()]
    c = luu_lien_he({"id": id, "name": name, "phone": phone, "email": email, "company": company,
                     "source": source, "note": note,
                     "tags": [x.strip() for x in re.split(r"[,\n]", tags or "") if x.strip()], "depts": ds},
                    allowed, ten, _phong_chinh(allowed, request))
    return {"ok": True, "contact": c}


@router.post("/crm/mau")
@_loi
async def crm_mau_nap(request: Request, brain: str = Form(...)):
    ten, allowed, ql = _nguoi(request)
    if allowed is not None and not ql:
        raise HTTPException(403, "Chỉ chủ hoặc quản lý nạp được dữ liệu mẫu")
    return {"ok": True, "da_nap": nap_mau(brain.strip(), allowed, ten)}


@router.post("/crm/mau/xoa")
@_loi
async def crm_mau_xoa(request: Request, brain: str = Form(...)):
    _, allowed, ql = _nguoi(request)
    if allowed is not None and not ql:
        raise HTTPException(403, "Chỉ chủ hoặc quản lý xoá được dữ liệu mẫu")
    return {"ok": True, "da_xoa": xoa_mau(brain.strip(), allowed)}


@router.post("/crm/lien-he/phong")
@_loi
async def crm_phong(request: Request, id: int = Form(...), brain: str = Form(...), bat: int = Form(1)):
    ten, allowed, _ql = _nguoi(request)
    return {"ok": True, "depts": gan_phong(id, brain.strip(), bool(bat), allowed, ten)}


@router.post("/crm/lien-he/xoa")
@_loi
async def crm_xoa(request: Request, id: int = Form(...), khoi_phuc: int = Form(0)):
    ten, allowed, ql = _nguoi(request)
    if allowed is not None and not ql:
        raise HTTPException(403, "Chỉ chủ, CEO, giám đốc hoặc trưởng phòng được xoá hoặc khôi phục khách")
    return {"ok": xoa_lien_he(id, allowed, ten, bool(khoi_phuc))}


@router.get("/crm/cau-hinh")
@_loi
def crm_config(request: Request, brain: str = Query("")):
    _, allowed, _ql = _nguoi(request)
    b = _brain_hop_le(brain, allowed, request)
    return {"ok": True, "brain": b, "stages": giai_doan(b) if b else [],
            "che_do": che_do_trich(), "nguong": nguong_trich()}


@router.post("/crm/cau-hinh/trich")
@_loi
async def crm_set_trich(request: Request, che_do: str = Form(""), nguong: int = Form(0)):
    _, allowed, ql = _nguoi(request)
    if allowed is not None and not ql:
        raise HTTPException(403, "Chỉ quản lý hoặc chủ đổi được chế độ tự trích")
    if che_do and che_do not in CHE_DO:
        raise HTTPException(400, "Chế độ không hợp lệ")

    def f(db):
        if che_do:
            _put_set(db, "auto_mode", che_do)
        if nguong:
            _put_set(db, "auto_n", str(max(2, min(100, int(nguong)))))
        db.commit()
    _dung(f)
    return {"ok": True, "che_do": che_do_trich(), "nguong": nguong_trich()}


@router.post("/crm/cau-hinh/phong")
@_loi
async def crm_set_phong(request: Request, brain: str = Form(...), bat: int = Form(1)):
    """Admin mở/đóng CRM cho từng phòng. Phòng đóng thì nhân viên phòng đó không xem được gì."""
    _, allowed, _ql = _nguoi(request)
    if allowed is not None:
        raise HTTPException(403, "Chỉ chủ mới mở hoặc đóng CRM theo phòng")
    tat_ca = [p.get("brain") for p in _deps["phong"]() if p.get("brain")]
    if brain.strip() not in tat_ca:
        raise HTTPException(400, "Không có phòng này")
    return {"ok": True, "phong_bat": dat_phong_bat(brain.strip(), bool(bat), tat_ca)}


@router.post("/crm/giai-doan")
@_loi
async def crm_stage_add(request: Request, brain: str = Form(...), label: str = Form(...)):
    _, allowed, _ql = _nguoi(request)
    b = _brain_hop_le(brain, allowed, request)
    them_giai_doan(b, label)
    return {"ok": True, "stages": giai_doan(b)}


@router.post("/crm/giai-doan/xoa")
@_loi
async def crm_stage_del(request: Request, brain: str = Form(...), key: str = Form(...)):
    _, allowed, _ql = _nguoi(request)
    b = _brain_hop_le(brain, allowed, request)
    kq = xoa_giai_doan(b, key)
    return {"ok": True, "stages": giai_doan(b), **kq}


@router.post("/crm/giai-doan/ten")
@_loi
async def crm_stage_rename(request: Request, brain: str = Form(...), key: str = Form(...), label: str = Form(...)):
    _, allowed, _ql = _nguoi(request)
    b = _brain_hop_le(brain, allowed, request)
    doi_ten_giai_doan(b, key, label)
    return {"ok": True, "stages": giai_doan(b)}


@router.get("/crm/pipeline")
@_loi
def crm_pipeline(request: Request, brain: str = Query("")):
    _, allowed, _ql = _nguoi(request)
    return {"ok": True, **pipeline(_brain_hop_le(brain, allowed, request), allowed)}


@router.post("/crm/deal")
@_loi
async def crm_deal_save(request: Request, id: int = Form(0), contact_id: int = Form(...), brain: str = Form(...),
                        title: str = Form(""), value: str = Form("0"), stage: str = Form("")):
    ten, allowed, _ql = _nguoi(request)
    return {"ok": True, "deal": luu_deal({"id": id, "contact_id": contact_id, "brain": brain.strip(),
                                          "title": title, "value": value, "stage": stage}, allowed, ten)}


@router.post("/crm/deal/buoc")
@_loi
async def crm_deal_stage(request: Request, id: int = Form(...), stage: str = Form(...)):
    ten, allowed, _ql = _nguoi(request)
    return {"ok": True, "deal": chuyen_buoc(id, stage, allowed, ten)}


@router.post("/crm/deal/xoa")
@_loi
async def crm_deal_del(request: Request, id: int = Form(...)):
    ten, allowed, _ql = _nguoi(request)
    return {"ok": xoa_deal(id, allowed, ten)}


@router.get("/crm/viec")
@_loi
def crm_todo_list(request: Request, brain: str = Query(""), contact_id: int = Query(0), xong: int = Query(0)):
    _, allowed, _ql = _nguoi(request)
    b = _brain_hop_le(brain, allowed, request) if brain else ""
    return {"ok": True, "items": danh_sach_viec(allowed, brain=b, contact_id=contact_id, xong=bool(xong))}


@router.post("/crm/viec")
@_loi
async def crm_todo_add(request: Request, contact_id: int = Form(...), brain: str = Form(...),
                       title: str = Form(...), due: str = Form("")):
    ten, allowed, _ql = _nguoi(request)
    return {"ok": True, "todo": them_viec({"contact_id": contact_id, "brain": brain.strip(),
                                           "title": title, "due": due}, allowed, ten)}


@router.post("/crm/viec/xong")
@_loi
async def crm_todo_done(request: Request, id: int = Form(...), xong: int = Form(1)):
    ten, allowed, _ql = _nguoi(request)
    return {"ok": True, "todo": xong_viec(id, allowed, ten, bool(xong))}


@router.post("/crm/viec/xoa")
@_loi
async def crm_todo_del(request: Request, id: int = Form(...)):
    ten, allowed, _ql = _nguoi(request)
    t = lay_viec(id)
    if not t or (allowed is not None and t["brain"] not in allowed):
        raise HTTPException(403, "Không thấy việc này")
    _dung(lambda db: (db.execute("DELETE FROM crm_todos WHERE id=?", (int(id),)), db.commit()))
    return {"ok": True}


@router.get("/crm/de-xuat")
@_loi
def crm_proposals(request: Request, brain: str = Query("")):
    _, allowed, _ql = _nguoi(request)
    return {"ok": True, "items": danh_sach_de_xuat(allowed, _brain_hop_le(brain, allowed, request) if brain else "")}


@router.post("/crm/de-xuat/duyet")
@_loi
async def crm_proposal_ok(request: Request, id: int = Form(...), chon: str = Form("")):
    ten, allowed, _ql = _nguoi(request)
    ds = [x for x in re.split(r"[,\s]+", chon or "") if x] if chon.strip() else None
    return duyet_de_xuat(id, allowed, ten, ds)


@router.post("/crm/de-xuat/bo")
@_loi
async def crm_proposal_no(request: Request, id: int = Form(...)):
    ten, allowed, _ql = _nguoi(request)
    return duyet_de_xuat(id, allowed, ten, None, tu_choi=True)


@router.post("/crm/trich")
@_loi
async def crm_extract(request: Request, id: int = Form(...)):
    _, allowed, _ql = _nguoi(request)
    c = lay_lien_he(id)
    if not c or not _thay_hien_thi(c, allowed):
        raise HTTPException(404, "Không thấy khách")
    import asyncio
    return await asyncio.to_thread(trich_lien_he, id, False)


@router.post("/crm/nhap-nhanh")
@_loi
async def crm_quick(request: Request, text: str = Form(...), model: int = Form(1)):
    """Dán đoạn chat/email/danh thiếp -> bản NHÁP các trường. Không lưu gì: người dùng xem và bấm lưu."""
    _nguoi(request)
    import asyncio
    found = await asyncio.to_thread(trich_tu_chu, text, bool(model))
    return {"ok": True, "fields": found}


@router.get("/crm/hop-thu")
@_loi
def crm_inbox_customers(request: Request, q: str = Query("")):
    _, allowed, ql = _nguoi(request)
    if allowed is not None and not ql:
        raise HTTPException(403, "Chỉ quản lý hoặc chủ nhập khách từ hộp thư")
    return {"ok": True, "items": [{"id": k["id"], "name": k.get("name"), "channel": k.get("channel_label"),
                                   "tags": k.get("tags")} for k in khach_hop_thu_chua_nhap(q)]}


@router.post("/crm/hop-thu/nhap")
@_loi
async def crm_inbox_import(request: Request, customer_id: int = Form(...), brain: str = Form(...)):
    ten, allowed, ql = _nguoi(request)
    if allowed is not None and (not ql or brain not in allowed):
        raise HTTPException(403, "Không có quyền nhập khách vào phòng này")
    return {"ok": True, "contact": nhap_tu_hop_thu(customer_id, brain.strip(), ten)}


@router.post("/crm/ghi-nho")
@_loi
async def crm_remember(request: Request, id: int = Form(...), brain: str = Form(...)):
    ten, allowed, _ql = _nguoi(request)
    return ghi_nho_wiki(id, brain.strip(), allowed, ten)


@router.get("/crm/phan-khuc")
@_loi
def crm_segments(request: Request, brain: str = Query("")):
    _, allowed, _ql = _nguoi(request)
    return {"ok": True, "items": phan_khuc(_brain_hop_le(brain, allowed, request), allowed)}


@router.get("/crm/tong-quan")
@_loi
def crm_overview(request: Request, brain: str = Query("")):
    _, allowed, _ql = _nguoi(request)
    return {"ok": True, **tong_quan(_brain_hop_le(brain, allowed, request), allowed)}


def register(app, phong_fn, scope_fn, tasks_fn, brain_root_fn, model_fn=None) -> None:
    _deps.update(phong=phong_fn, scope=scope_fn, tasks=tasks_fn, brain_root=brain_root_fn)
    if model_fn:
        _deps["model"] = model_fn
    app.include_router(router)
