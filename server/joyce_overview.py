# -*- coding: utf-8 -*-
"""
joyce_overview.py - nhóm "Tổng quan" (Command Center, spec V1.4 mục 53 + mẫu
tai-lieu-update-tu-openai/update-giao-dein-tong-quat/JOYCE_OVERVIEW_COMMAND_CENTER_V1.html).

LỚP ĐỌC THUẦN (Experience / Read Layer): chỉ tổng hợp từ các store đã có - kanban sqlite (qua
board_view), nhắc hẹn từng brain, hộp thư nền, sức khoẻ kết nối và bộ não, ping app H2O, sổ
phòng ban, chỉ mục mức dùng. KHÔNG tạo store nghiệp vụ, KHÔNG số mô phỏng. Bản mẫu HTML dùng
số giả (148 việc, SLA 93,8%...); Joyce không bịa số, nên khối nào chưa có nguồn thật thì trả
"chưa nối nguồn" chứ không vẽ con số.

Mỗi khối mang `source` + `as_of`. Một nguồn lỗi chỉ làm khối đó báo lỗi (`sections_down`),
không làm trắng cả trang (spec 53.3).

Staff (nhân viên H2O) bị chặn 403 ở cả ba endpoint: đây là mặt quản trị toàn hệ thống, nhân
viên dùng trang Hôm nay (bị giới hạn theo phòng ở chỗ khác).

Endpoint:
  GET /api/joyce/v1/overview              Bảng điều hành (brief, KPI, hàng đợi, lĩnh vực, ...)
  GET /api/joyce/v1/overview/departments  sức khoẻ từng phòng ban (việc + dữ liệu đã nạp)
  GET /api/joyce/v1/overview/calendar     lịch 7 ngày từ nhắc hẹn mọi brain
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

import joyce_today as jt

_DAY = 86400
_DOW = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
_OPEN = ("triage", "todo", "ready", "running", "review", "blocked")

# Nguồn nghiệp vụ spec 53.3 liệt kê mà Joyce CHƯA có dữ liệu. Trả về để UI nói thật "chưa nối"
# và chỉ đường sang trang Kết nối, thay vì một dòng KPI giả.
BUSINESS_SOURCES = [
    {"id": "crm", "name": "CRM & Sales", "desc": "Lead, cơ hội, lịch hẹn"},
    {"id": "wedding", "name": "Wedding Operations", "desc": "Hợp đồng, lịch chụp, bàn giao"},
    {"id": "academy", "name": "Academy Operations", "desc": "Tuyển sinh, lớp học, đánh giá"},
]


@dataclass
class OverviewDeps:
    """Tiêm từ main - đúng khuôn TodayDeps. `today` là chính bộ nguồn của trang Hôm nay."""

    today: Any                                          # joyce_today.TodayDeps
    phong_view: Callable[[], dict]                      # main._h2o_phong_view (sổ + số tài liệu)
    brain_paths: Callable[[], list]                     # đường dẫn TUYỆT ĐỐI mọi brain
    usage_today: Callable[[], dict] = lambda: {}        # usage_index.summary("today")["kpi"]
    vault_counts: Callable[[str], dict] = lambda b: {}  # {sources, wiki, facts} của một brain
    skills_count: Callable[[str], int] = lambda b: 0
    # Nhân viên H2O: phạm vi brain của họ (None = quản trị, không khoá) và cấp chức vụ
    staff_scope: Callable[[], Any] = lambda: None
    staff_cap: Callable[[Any], str] = lambda st: "nhan_vien"
    brain_root: Callable[[str], str] = lambda b: b  # "brain"/tên brain -> đường dẫn tuyệt đối


def _log(src: str, e: Exception) -> None:
    try:
        print(f"[joyce-overview] nguồn '{src}' lỗi: {e}")
    except Exception:
        pass


def _staff(deps: OverviewDeps, request: Request) -> bool:
    try:
        return bool(deps.today.staff_by_cookie(request.cookies.get("h2o_staff", "")))
    except Exception:
        return False


def _counts(view: dict) -> dict:
    c = view.get("counts") or {}
    out = {k: int(c.get(k, 0) or 0) for k in _OPEN}
    out["open"] = sum(out[k] for k in _OPEN)
    out["queue"] = out["triage"] + out["todo"] + out["ready"]
    out["done24"] = int(view.get("completed_24h") or 0)
    return out


def _status(c: dict) -> str:
    """Trạng thái một đơn vị theo việc thật: kẹt = rủi ro, chờ duyệt = cần chú ý."""
    if c.get("blocked"):
        return "risk"
    if c.get("review"):
        return "wait"
    return "good"


# ---------------------------------------------------------------------------------------
# Tài liệu chưng cất trong ngày: wiki nào được tạo/sửa hôm đó, gom theo khối và phòng.
# Không có bước duyệt trước: Joyce ghi thẳng vào wiki, trang này chỉ để người xem lại và
# đánh dấu "đã xem". Trạng thái đã xem gắn với THỜI ĐIỂM SỬA của file, nên khi Joyce chưng cất
# lại trang đó thì nó hiện lại thành chưa xem.
# ---------------------------------------------------------------------------------------
_CC_BO_QUA = {"index.md", "log.md"}


def _cc_file_xem() -> str:
    import config as _cfg
    return str(_cfg.STATE_DIR / "chung-cat-xem.json")


def _cc_doc_xem() -> dict:
    import json as _json
    try:
        with open(_cc_file_xem(), encoding="utf-8") as f:
            d = _json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


_CC_XEM_LOCK = threading.Lock()


def _cc_ghi_xem(d: dict) -> None:
    import json as _json
    p = _cc_file_xem()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        _json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def _cc_khoang_ngay(day: str) -> tuple:
    d = _dt.datetime.strptime(day, "%Y-%m-%d")
    bd = time.mktime(d.timetuple())
    return bd, bd + 86400


def _cc_quyen(request, deps) -> tuple:
    """(được xem, phạm vi). Quản trị: (True, None) - không khoá. Trưởng phòng (cấp quản lý):
    (True, các brain được phép). Nhân viên thường: (False, ()) - trang này chỉ dành cho người
    duyệt, không phải nơi nhân viên đọc tài liệu của phòng khác."""
    if not _staff(deps, request):
        return True, None
    st = getattr(request.state, "staff", None) or {}
    if deps.staff_cap(st) != "quan_ly":
        return False, ()
    return True, tuple(deps.staff_scope() or ())


def _cc_trong_pham_vi(bp: str, scope) -> bool:
    if scope is None:
        return True
    try:
        r = os.path.normcase(os.path.realpath(bp))
    except OSError:
        return False
    for s in scope:
        sc = os.path.normcase(os.path.realpath(str(s)))
        if r == sc or r.startswith(sc.rstrip(os.sep) + os.sep):
            return True
    return False


def _brain_trong_phep(bp: str, deps, scope) -> str:
    """Đường dẫn brain THẬT (đúng một trong danh sách brain của máy) mà người gọi được xem, hoặc
    chuỗi rỗng. So theo đường dẫn thật (realpath) để không ai lách bằng đường dẫn tương đối,
    biến thể hoa-thường hay liên kết."""
    if not bp:
        return ""
    k = os.path.normcase(os.path.realpath(str(bp)))
    for x in deps.brain_paths() or []:
        if os.path.normcase(os.path.realpath(str(x))) == k:
            return str(x) if _cc_trong_pham_vi(str(x), scope) else ""
    return ""


def _chung_cat(day: str, brain_paths: list, phong_theo_brain: dict) -> dict:
    bd, kt = _cc_khoang_ngay(day)
    xem = _cc_doc_xem()
    nhom = []
    tong = 0
    for bp in brain_paths:
        root = str(bp)
        items = []
        for sub in ("wiki", "07 - Wiki"):
            d = os.path.join(root, sub)
            if not os.path.isdir(d):
                continue
            for dp, dns, fns in os.walk(d):
                dns[:] = [x for x in dns if not x.startswith(".")]
                for f in fns:
                    if not f.lower().endswith(".md") or f.startswith("_") or f in _CC_BO_QUA:
                        continue
                    full = os.path.join(dp, f)
                    try:
                        mt = os.stat(full).st_mtime
                    except OSError:
                        continue
                    if not (bd <= mt < kt):
                        continue
                    rel = os.path.relpath(full, root).replace("\\", "/")
                    khoa = f"{root}|{rel}"
                    da = abs(float((xem.get(khoa) or {}).get("mtime") or 0) - mt) < 1
                    items.append({"ten": f[:-3], "rel": rel, "gio": _dt.datetime.fromtimestamp(mt).strftime("%H:%M"),
                                  "mtime": mt, "da_xem": da})
        if not items:
            continue
        items.sort(key=lambda x: x["mtime"], reverse=True)
        tong += len(items)
        ph = phong_theo_brain.get(os.path.normcase(root)) or {}
        nhom.append({
            "brain_path": root, "brain": os.path.basename(root),
            "phong": ph.get("ten") or os.path.basename(root),
            "khoi": ph.get("khoi") or "Chung", "brand": ph.get("brand") or "",
            "items": items, "chua_xem": sum(1 for x in items if not x["da_xem"]),
        })
    nhom.sort(key=lambda g: (g["khoi"], g["phong"]))
    return {"day": day, "tong": tong, "chua_xem": sum(g["chua_xem"] for g in nhom), "nhom": nhom}


# ---------------------------------------------------------------------------------------
# Hàng chờ DUYỆT chưng cất (3 nhóm trên trang Tài liệu chưng cất):
#   1. Draft mới hôm nay      - cần duyệt ngay
#   2. Draft còn lại          - hàng chờ tích luỹ
#   3. Đã chưng cất gần đây   - chủ xem lại chất lượng
#
# Draft = file .md nằm trong `wiki/_cho-duyet/` hoặc `wiki/_cho_duyet/` (hai biến thể dấu
# tồn tại song song - `_gop_cho_duyet` chuẩn hoá về `_cho-duyet`, tên khớp tag `cho-duyet`
# và plans/ke-hoach-ingest-o-D.md), HOẶC file wiki có frontmatter `status: draft` kèm
# `staging: cho-duyet` hay tag `cho-duyet`.
# ---------------------------------------------------------------------------------------
_CC_STAGING_RE = re.compile(r"^_cho[-_]duyet$", re.I)
_CC_STAGING_CHUAN = "_cho-duyet"
_CC_FM_RE = re.compile(r"^---[ \t]*\r?\n(.*?)\r?\n---", re.S)
_CC_GAN_DAY = 7 * _DAY          # "đã chưng cất gần đây" = sửa trong 7 ngày
_CC_RECENT_MAX = 60             # trần tổng số trang đã chưng cất trả về


def _cc_fm(text: str) -> dict:
    """Frontmatter (dict) của một file .md; {} khi thiếu hoặc YAML hỏng."""
    m = _CC_FM_RE.match(text or "")
    if not m:
        return {}
    try:
        import fastyaml
        d = fastyaml.safe_load(m.group(1)) or {}
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _cc_head(fp: str, n: int = 4000) -> str:
    try:
        with open(fp, encoding="utf-8", errors="replace") as f:
            return f.read(n)
    except Exception:
        return ""


def _cc_tags(meta: dict) -> list:
    t = (meta or {}).get("tags")
    if isinstance(t, list):
        return [str(x).strip() for x in t if str(x).strip()]
    if isinstance(t, str):
        return [x.strip() for x in t.split(",") if x.strip()]
    return []


def _cc_la_nhap(meta: dict, trong_staging: bool) -> bool:
    """True khi file là bản nháp chờ duyệt: nằm trong thư mục staging, hoặc frontmatter
    tự nói `status: draft` + dấu hiệu cho-duyet (staging field hoặc tag)."""
    if trong_staging:
        return True
    st = str((meta or {}).get("status") or "").strip().lower()
    if st != "draft":
        return False
    tags = {x.lower().replace("_", "-") for x in _cc_tags(meta)}
    staging = str(meta.get("staging") or "").strip().lower().replace("_", "-")
    return "cho-duyet" in tags or staging == "cho-duyet"


def _cc_ngay_tao(meta: dict, mt: float) -> str:
    """Ngày tạo YYYY-MM-DD: ưu tiên frontmatter `created`, rơi về mtime file."""
    c = str((meta or {}).get("created") or "").strip()[:10]
    try:
        _dt.datetime.strptime(c, "%Y-%m-%d")
        return c
    except ValueError:
        return _dt.datetime.fromtimestamp(mt).strftime("%Y-%m-%d")


def _duyet_scan_brain(root: str, xem: dict, hom_nay: str, now: float) -> dict:
    """Quét một brain -> {moi, cho, da_duyet, lech}. `lech` = số file còn nằm trong thư
    mục staging biến thể gạch dưới `_cho_duyet` (để giao diện đề nghị gộp về `_cho-duyet`)."""
    moi, cho, da_duyet = [], [], []
    lech = 0
    for sub in ("wiki", "07 - Wiki"):
        wdir = os.path.join(root, sub)
        if not os.path.isdir(wdir):
            continue
        for dp, dns, fns in os.walk(wdir):
            dns[:] = [x for x in dns if not x.startswith(".")]
            rel_dir = os.path.relpath(dp, wdir).replace("\\", "/")
            trong = rel_dir != "." and _CC_STAGING_RE.match(rel_dir.split("/")[0] or "") is not None
            for f in fns:
                if not f.lower().endswith(".md"):
                    continue
                full = os.path.join(dp, f)
                try:
                    mt = os.stat(full).st_mtime
                except OSError:
                    continue
                rel = os.path.relpath(full, root).replace("\\", "/")
                if trong:
                    meta = _cc_fm(_cc_head(full))
                    if rel_dir.split("/")[0].lower() != _CC_STAGING_CHUAN:
                        lech += 1
                    tao = _cc_ngay_tao(meta, mt)
                    item = {"ten": f[:-3], "rel": rel, "gio": _dt.datetime.fromtimestamp(mt).strftime("%H:%M"),
                            "mtime": mt, "tao": tao, "trang_thai": "draft",
                            "thu_muc": rel_dir.split("/")[0],
                            "cho_ngay": max(0, (_dt.datetime.now() - _dt.datetime.fromtimestamp(mt)).days)}
                    (moi if tao == hom_nay else cho).append(item)
                    continue
                # Ngoài staging: draft theo frontmatter -> hàng chờ; còn lại là wiki
                # chính thức, nếu mới sửa gần đây thì xếp vào nhóm "đã chưng cất".
                if f.startswith("_") or f in _CC_BO_QUA:
                    continue
                meta = _cc_fm(_cc_head(full))
                if _cc_la_nhap(meta, False):
                    tao = _cc_ngay_tao(meta, mt)
                    item = {"ten": f[:-3], "rel": rel, "gio": _dt.datetime.fromtimestamp(mt).strftime("%H:%M"),
                            "mtime": mt, "tao": tao, "trang_thai": "draft", "thu_muc": "wiki",
                            "cho_ngay": max(0, (_dt.datetime.now() - _dt.datetime.fromtimestamp(mt)).days)}
                    (moi if tao == hom_nay else cho).append(item)
                    continue
                st = str(meta.get("status") or "").strip().lower()
                if st == "draft" or now - mt > _CC_GAN_DAY:
                    continue
                khoa = f"{root}|{rel}"
                da = abs(float((xem.get(khoa) or {}).get("mtime") or 0) - mt) < 1
                da_duyet.append({"ten": f[:-3], "rel": rel,
                                 "gio": _dt.datetime.fromtimestamp(mt).strftime("%H:%M"),
                                 "ngay": _dt.datetime.fromtimestamp(mt).strftime("%Y-%m-%d"),
                                 "mtime": mt, "trang_thai": "active", "da_xem": da,
                                 "moi_duyet": bool(meta.get("approved"))})
    moi.sort(key=lambda x: -x["mtime"])
    cho.sort(key=lambda x: x["mtime"])          # chờ lâu nhất lên đầu
    da_duyet.sort(key=lambda x: -x["mtime"])    # mới chưng cất trước
    return {"moi": moi, "cho": cho, "da_duyet": da_duyet, "lech": lech}


def _hang_cho_duyet(brain_paths: list, phong_theo_brain: dict) -> dict:
    xem = _cc_doc_xem()
    hom_nay = _dt.datetime.now().strftime("%Y-%m-%d")
    now = time.time()
    moi, cho, da_duyet, lech = [], [], [], []
    for bp in brain_paths:
        root = str(bp)
        ph = phong_theo_brain.get(os.path.normcase(root)) or {}
        phong = ph.get("ten") or os.path.basename(root)
        khoi = ph.get("khoi") or "Chung"
        try:
            r = _duyet_scan_brain(root, xem, hom_nay, now)
        except Exception as e:  # noqa: BLE001 - một brain lỗi không làm trắng trang
            _log("duyet/" + os.path.basename(root), e)
            continue
        tag = {"brain": os.path.basename(root), "brain_path": root, "phong": phong, "khoi": khoi}
        moi += [{**x, **tag} for x in r["moi"]]
        cho += [{**x, **tag} for x in r["cho"]]
        da_duyet += [{**x, **tag} for x in r["da_duyet"]]
        if r["lech"]:
            lech.append({"brain_path": root, "brain": os.path.basename(root),
                         "phong": phong, "so_file": r["lech"]})
    moi.sort(key=lambda x: -x["mtime"])
    cho.sort(key=lambda x: x["mtime"])
    da_duyet.sort(key=lambda x: -x["mtime"])
    return {"moi": moi, "cho": cho, "da_duyet": da_duyet[:_CC_RECENT_MAX],
            "lech_thu_muc": lech, "tong_cho": len(moi) + len(cho)}


def _cc_dump_fm(meta: dict) -> str:
    """Serialise frontmatter dict về YAML block (giữ thứ tự khoá), tags dạng inline list
    cho khớp phong cách tay của các bản nháp hiện có."""
    import yaml
    return yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()


def _cc_cap_nhat_fm(text: str, hom_nay: str) -> str:
    """draft -> active: bỏ `staging`, bỏ tag cho-duyet/cho_duyet, cập nhật `updated`,
    đánh dấu `approved`. File không có frontmatter thì thêm khối tối thiểu."""
    m = _CC_FM_RE.match(text or "")
    if m:
        try:
            import fastyaml
            meta = fastyaml.safe_load(m.group(1)) or {}
        except Exception:
            meta = {}
        if not isinstance(meta, dict):
            meta = {}
        body = text[m.end():]
    else:
        meta, body = {}, text
    meta["type"] = "wiki"                 # trang wiki chuẩn sau khi chưng cất xong
    meta["status"] = "active"
    meta.pop("staging", None)
    tags = [x for x in _cc_tags(meta) if x.lower().replace("_", "-") != "cho-duyet"]
    if tags or meta.get("tags") is not None:
        meta["tags"] = tags
    meta["updated"] = hom_nay
    meta["approved"] = hom_nay
    return "---\n" + _cc_dump_fm(meta) + "\n---" + (body if body.startswith("\n") else "\n" + body)


def _cc_nguon_cua(meta: dict) -> str:
    """Frontmatter `source:` của bản nháp -> đường rel 'sources/<slug>.md' trong vault,
    hoặc "" khi không có/không hợp lệ. Chấp nhận wikilink [[sources/x]] (có hoặc không
    ngoặc kép) lẫn path trần. Chỉ công nhận đường nằm TRONG thư mục sources của brain -
    bản nháp viết 'source: D:/file.xlsx' hay '[[../x]]' thì coi như không có nguồn,
    tuyệt đối không trỏ ra ngoài vault."""
    s = (meta or {}).get("source")
    if isinstance(s, list):
        s = s[0] if s else ""
    s = str(s or "").strip().strip("\"'")
    m = re.match(r"^\[\[(.+?)\]\]$", s)
    if m:
        s = m.group(1).strip()
    s = s.replace("\\", "/").strip("/")
    if s.lower().endswith(".md"):
        s = s[:-3]
    phan = s.split("/")
    if len(phan) < 2 or phan[0].lower() not in ("sources", "01 - sources") or ".." in phan:
        return ""
    return s + ".md"


def _cc_danh_dau_nguon(root: str, nguon_rel: str, link: str, hom_nay: str) -> bool:
    """Chốt INGEST ở lúc duyệt: file nguồn trong sources/ chuyển `status: processed`,
    ghi `processed_at`, nối `wiki_links` tới trang wiki vừa lên. Trả False khi không có
    file hoặc không ghi được - lỗi nguồn không làm hỏng thao tác duyệt chính."""
    try:
        full = os.path.join(root, *nguon_rel.split("/"))
        if not os.path.isfile(full):
            return False
        text = open(full, encoding="utf-8", errors="replace").read()
        m = _CC_FM_RE.match(text)
        if m:
            try:
                import fastyaml
                meta = fastyaml.safe_load(m.group(1)) or {}
            except Exception:
                meta = {}
            if not isinstance(meta, dict):
                meta = {}
            body = text[m.end():]
        else:
            meta, body = {}, text
        meta["status"] = "processed"
        meta["processed_at"] = hom_nay
        wl = meta.get("wiki_links")
        wl = [x for x in wl] if isinstance(wl, list) else ([wl] if wl else [])
        moi = f"[[{link}]]"
        if moi not in [str(x) for x in wl]:
            wl.append(moi)
        meta["wiki_links"] = wl
        _atomic_ghi(full, "---\n" + _cc_dump_fm(meta) + "\n---" +
                    (body if body.startswith("\n") else "\n" + body))
        return True
    except Exception as e:  # noqa: BLE001
        _log("duyet/nguon", e)
        return False


def _cc_dich_duyet(root: str, wiki_dir: str, rel: str) -> str:
    """Đường đích trong wiki chính thức cho một bản nháp. Tên file ưu tiên đặt ngay gốc
    wiki (cấu trúc phẳng đang dùng); trùng tên thì giữ thư mục nhóm của staging; vẫn
    trùng thì đuôi -2, -3..."""
    ten = os.path.basename(rel)
    phan = rel.split("/")
    # phan = [wiki_dir, _cho-*, (nhóm...)/]ten — nhóm là phần giữa staging và tên file
    nhom = "/".join(phan[2:-1])
    cand = f"{wiki_dir}/{ten}"
    if not os.path.exists(os.path.join(root, cand.replace("/", os.sep))):
        return cand
    if nhom:
        cand2 = f"{wiki_dir}/{nhom}/{ten}"
        if not os.path.exists(os.path.join(root, cand2.replace("/", os.sep))):
            return cand2
    stem, ext = os.path.splitext(ten)
    for i in range(2, 50):
        cand = f"{wiki_dir}/{stem}-{i}{ext}"
        if not os.path.exists(os.path.join(root, cand.replace("/", os.sep))):
            return cand
    return f"{wiki_dir}/{ten}"


def _cc_mo_ta(body: str) -> str:
    """Một dòng mô tả cho index.md: dòng chữ đầu tiên sau tiêu đề, tối đa ~90 ký tự."""
    for ln in (body or "").splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith("---"):
            continue
        return s[:90]
    return ""


def _cc_ghi_index(root: str, wiki_dir: str, link: str, mo_ta: str) -> None:
    """Thêm dòng `- [[link]] — mô tả` vào cuối wiki/index.md (bảng catalog cho phép mục
    lục phẳng; chủ có thể xếp lại nhóm sau). Không có index.md thì tạo khung tối thiểu."""
    p = os.path.join(root, wiki_dir, "index.md")
    try:
        cur = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
    except Exception:
        cur = ""
    if f"[[{link}]]" in cur:
        return
    if not cur.strip():
        cur = "# Wiki Index\n\nCatalog nội dung wiki (cập nhật mỗi lần INGEST).\n"
    dong = f"- [[{link}]] — {mo_ta}" if mo_ta else f"- [[{link}]]"
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(cur.rstrip() + "\n" + dong + "\n")
    os.replace(tmp, p)


def _cc_ghi_log(root: str, wiki_dir: str, ten: str, link: str, rel_cu: str, hom_nay: str) -> None:
    p = os.path.join(root, wiki_dir, "log.md")
    try:
        cur = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
    except Exception:
        cur = ""
    if not cur.strip():
        cur = "# Wiki Log\n\nNhật ký thời gian (append-only).\n"
    entry = (f"\n\n## [{hom_nay}] duyet | {ten}\n\n"
             f"- Wiki: [[{link}]]\n- Từ bản nháp: {rel_cu}\n")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(cur.rstrip() + entry)
    os.replace(tmp, p)


def _atomic_ghi(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)


def _don_rong_staging(root: str, wiki_dir: str, staging_dir: str) -> None:
    """Xoá thư mục rỗng BÊN TRONG thư mục staging sau khi file đã chuyển đi (không đụng
    gì ngoài staging)."""
    base = os.path.join(root, wiki_dir, staging_dir)
    for dp, dns, fns in os.walk(base, topdown=False):
        if dns or fns:
            continue
        try:
            os.rmdir(dp)
        except OSError:
            pass
    try:
        if os.path.isdir(base) and not os.listdir(base):
            os.rmdir(base)
    except OSError:
        pass


def _duyet_mot_file(root: str, rel: str) -> dict:
    """Duyệt một bản nháp lên wiki chính thức. Trả {ok, rel_moi, ten, error}."""
    rel = str(rel or "").replace("\\", "/").strip("/")
    phan = rel.split("/")
    if len(phan) < 2 or ".." in phan or not rel.lower().endswith(".md"):
        return {"ok": False, "error": "đường dẫn không hợp lệ"}
    wiki_dir = phan[0]
    if wiki_dir.lower() not in ("wiki", "07 - wiki"):
        return {"ok": False, "error": "không nằm trong wiki"}
    full = os.path.join(root, *phan)
    if not os.path.isfile(full):
        return {"ok": False, "error": "không thấy tài liệu"}
    try:
        text = open(full, encoding="utf-8").read()
    except Exception as e:
        return {"ok": False, "error": f"không đọc được: {e}"}
    trong_staging = len(phan) >= 3 and _CC_STAGING_RE.match(phan[1]) is not None
    meta = _cc_fm(text)
    # Ngoài thư mục staging thì ít nhất phải là bản nháp (status: draft) - tránh nút
    # duyệt đụng nhầm trang wiki đang active.
    if not trong_staging and str(meta.get("status") or "").strip().lower() != "draft":
        return {"ok": False, "error": "tài liệu này không ở trạng thái chờ duyệt"}

    hom_nay = _dt.datetime.now().strftime("%Y-%m-%d")
    moi = _cc_cap_nhat_fm(text, hom_nay)
    if trong_staging:
        rel_moi = _cc_dich_duyet(root, wiki_dir, rel)
    else:
        rel_moi = rel                     # draft ngoài staging: đổi trạng thái tại chỗ
    dich = os.path.join(root, *rel_moi.split("/"))
    try:
        _atomic_ghi(dich, moi)
        if rel_moi != rel:
            os.remove(full)
            _don_rong_staging(root, wiki_dir, phan[1])
    except Exception as e:
        return {"ok": False, "error": f"không ghi được: {e}"}

    link = "/".join(rel_moi.split("/")[1:])[:-3]      # bỏ 'wiki/' và đuôi .md
    m2 = _CC_FM_RE.match(moi)
    mo_ta = _cc_mo_ta(moi[m2.end():] if m2 else moi)
    try:
        _cc_ghi_index(root, wiki_dir, link, mo_ta)
    except Exception as e:
        _log("duyet/index", e)
    try:
        _cc_ghi_log(root, wiki_dir, os.path.basename(rel_moi)[:-3], link, rel, hom_nay)
    except Exception as e:
        _log("duyet/log", e)
    # Chốt đầu kia của INGEST: nguồn trong sources/ (nếu bản nháp có `source:`) chuyển
    # sang processed + nối wiki_links tới trang vừa lên.
    nguon = _cc_nguon_cua(meta)
    nguon_xong = bool(nguon) and _cc_danh_dau_nguon(root, nguon, link, hom_nay)
    return {"ok": True, "rel_moi": rel_moi, "ten": os.path.basename(rel_moi)[:-3],
            "nguon": nguon if nguon_xong else ""}


def _xoa_nhap(root: str, rel: str) -> dict:
    """'Không duyệt' = loại bỏ hẳn tài liệu: xoá file nháp VÀ file nguồn của nó trong
    sources/ (khi frontmatter `source:` trỏ tới một file thật trong vault). Không copy,
    không lên wiki, không ghi lại nội dung. Chỉ được xoá file trong thư mục staging hoặc
    file draft ngoài staging - cùng ngưỡng với _duyet_mot_file để không đụng nhầm trang
    wiki đang active. File nguồn NGOÀI vault (đường D:/..., link wiki khác) không đụng."""
    rel = str(rel or "").replace("\\", "/").strip("/")
    phan = rel.split("/")
    if len(phan) < 2 or ".." in phan or not rel.lower().endswith(".md"):
        return {"ok": False, "error": "đường dẫn không hợp lệ"}
    if phan[0].lower() not in ("wiki", "07 - wiki"):
        return {"ok": False, "error": "không nằm trong wiki"}
    full = os.path.join(root, *phan)
    if not os.path.isfile(full):
        return {"ok": False, "error": "không thấy tài liệu"}
    meta = _cc_fm(_cc_head(full))
    trong_staging = len(phan) >= 3 and _CC_STAGING_RE.match(phan[1]) is not None
    if not trong_staging:
        if str(meta.get("status") or "").strip().lower() != "draft":
            return {"ok": False, "error": "tài liệu này không ở trạng thái chờ duyệt"}
    nguon = _cc_nguon_cua(meta)
    try:
        os.remove(full)
        if trong_staging:
            _don_rong_staging(root, phan[0], phan[1])
    except Exception as e:
        return {"ok": False, "error": f"không xoá được: {e}"}
    nguon_xoa = ""
    if nguon:
        fng = os.path.join(root, *nguon.split("/"))
        try:
            if os.path.isfile(fng):
                os.remove(fng)
                nguon_xoa = nguon
        except Exception as e:  # noqa: BLE001 - nháp đã xoá, chỉ báo thêm nguồn sót
            _log("xoa/nguon", e)
    return {"ok": True, "ten": phan[-1][:-3], "nguon_xoa": nguon_xoa}


def _gop_cho_duyet(root: str) -> dict:
    """Gộp `wiki/_cho_duyet` (gạch dưới) vào `_cho-duyet` (gạch ngang, tên chuẩn theo
    tag + kế hoạch ingest). Giữ cây thư mục con; trùng tên thì đuôi -2; xoá thư mục rỗng."""
    moved = 0
    for sub in ("wiki", "07 - Wiki"):
        cu = os.path.join(root, sub, "_cho_duyet")
        moi = os.path.join(root, sub, _CC_STAGING_CHUAN)
        if not os.path.isdir(cu):
            continue
        for dp, dns, fns in os.walk(cu):
            for f in fns:
                src = os.path.join(dp, f)
                rel_in = os.path.relpath(src, cu).replace("\\", "/")
                dst = os.path.join(moi, rel_in)
                if os.path.exists(dst):
                    stem, ext = os.path.splitext(rel_in)
                    for i in range(2, 50):
                        dst = os.path.join(moi, f"{stem}-{i}{ext}")
                        if not os.path.exists(dst):
                            break
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                os.replace(src, dst)
                moved += 1
        _don_rong_staging(root, sub, "_cho_duyet")
    return {"moved": moved}


# ---------------------------------------------------------------------------------------
# Quy trình của một phòng, xếp theo giai đoạn Trước / Trong / Sau dịch vụ
# ---------------------------------------------------------------------------------------
# Quy ước đặt tên có sẵn trong vault của chủ: hậu tố "- Trước/Trong/Sau dịch vụ.md" (108
# file). Nhưng còn tên tự do kiểu "Quy Trình Tư Vấn Trước Khi Chụp" - có "trước" mà không có
# "dịch vụ" - bản đầu soi đúng cụm ba từ nên file đó rơi xuống nhóm "khác". Nới thành từ
# khoá giai đoạn, khớp theo RANH GIỚI TỪ trên tên đã bỏ dấu. Thứ tự truoc -> trong -> sau:
# file chứa từ khoá của nhiều giai đoạn ("ngay chup den ban giao hau ky" có cả hai) về cột
# được khớp trước.
_GIAI_DOAN = (
    ("truoc", ("truoc", "chuan bi", "tiep nhan", "tu van", "len lich")),
    # "dich vu" KHÔNG là từ khoá riêng: "- Sau dịch vụ" cũng chứa nó, để "trong" tự lo.
    ("trong", ("trong", "ngay chup", "thi cong", "thuc hien")),
    ("sau", ("sau", "hau ky", "ban giao", "cham soc")),
)
_QT_MAX = 40          # trần mỗi giai đoạn, tránh phòng có vài trăm trang làm nặng drawer
# workflows/ xu-ly-y-tuong-moi.md là pipeline mẫu CÀI SẴN cho mọi brain, không phải quy trình
# riêng của phòng; wiki/y-tuong/ là KẾT QUẢ ý tưởng đã xử, cũng không phải quy trình.
_QT_BO_FILE = {"xu-ly-y-tuong-moi.md"}
_QT_BO_DIR = {"y-tuong"}


def _bo_dau(s: str) -> str:
    import unicodedata
    s = str(s or "").replace("Đ", "D").replace("đ", "d")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _tieu_de_qt(ten: str) -> str:
    """'3. Quy Trình Tư Vấn Báo Giá Offline - Trước dịch vụ.md' -> 'Quy Trình Tư Vấn Báo
    Giá Offline'. Bỏ đuôi .md, bỏ hậu tố giai đoạn, bỏ số thứ tự đầu tên."""
    import re as _re
    t = _re.sub(r"\.md$", "", str(ten or ""), flags=_re.I)
    t = _re.sub(r"\s*[-–]\s*(trước|trong|sau)\s+dịch\s+vụ\s*$", "", t, flags=_re.I)
    t = _re.sub(r"^\s*\d+[.)]\s*", "", t).strip() or t.strip()
    # Tên slug của workflows/ ("ngay-chup-den-ban-giao-hau-ky") hiện thô khó đọc - đổi
    # gạch ngang thành khoảng trắng và viết hoa chữ cái đầu.
    if " " not in t and "-" in t:
        t = t.replace("-", " ").strip()
        t = t[:1].upper() + t[1:]
    return t


def _quy_trinh(brain_path: str) -> dict:
    """{giai_doan: {truoc|trong|sau|khac: [{ten, file, rel}]}, tong: n}."""
    out = {k: [] for k, _ in _GIAI_DOAN}
    out["khac"] = []
    root = str(brain_path or "")
    if not root or not os.path.isdir(root):
        return {"giai_doan": out, "tong": 0}
    tong = 0
    # workflows/ cũng là quy trình của phòng (file định nghĩa vận hành), không chỉ wiki/.
    for sub in ("wiki", "07 - Wiki", "workflows"):
        d = os.path.join(root, sub)
        if not os.path.isdir(d):
            continue
        for dp, dns, fns in os.walk(d):
            dns[:] = [x for x in dns if not x.startswith(".") and x not in _QT_BO_DIR]
            for f in sorted(fns):
                if not f.lower().endswith(".md") or f.startswith("_") or f in ("index.md", "log.md") \
                        or f.lower() in _QT_BO_FILE:
                    continue
                # Workflow đặt tên slug bằng gạch ngang ("ban-giao-khach") - đổi thành khoảng
                # trắng để từ khoá giai đoạn vẫn khớp như tên wiki viết thường.
                kho = _bo_dau(f).replace("-", " ").replace("_", " ")
                nhom = next((k for k, daus in _GIAI_DOAN
                             for w in daus
                             if re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", kho)), "khac")
                if len(out[nhom]) >= _QT_MAX:
                    continue
                rel = os.path.relpath(os.path.join(dp, f), root).replace("\\", "/")
                out[nhom].append({"ten": _tieu_de_qt(f), "file": f, "rel": rel})
                tong += 1
    return {"giai_doan": out, "tong": tong}


# ---------------------------------------------------------------------------------------
# Tri thức phòng: trưởng phòng cần trả lời "phòng tôi đang biết gì / còn thiếu gì" chứ
# không phải cây thư mục kỹ thuật. Gom một lần: sources = đã nạp (đánh dấu chưng cất hay
# chưa nhờ link 'source:' trong wiki), wiki = tri thức đang dùng gom theo chủ đề, inbox =
# file Telegram/Zalo nhận về, hot = file hay được mở (đếm từ /files/read).
# ---------------------------------------------------------------------------------------
_KNOW_BO_FILE = {"index.md", "log.md", "readme.md", "memory.md"}
_KNOW_SRC_RE = re.compile(r"^\s*source:\s*\[?\[?([^\]\n]+?)\]?\]?\s*$", re.M | re.I)
_KNOW_STATUS_RE = re.compile(r"^\s*status:\s*([^\s#]+)", re.M | re.I)
_KNOW_TEXT_EXT = (".md", ".markdown", ".txt")


def _thu_muc_that(root: str, ten: str) -> list:
    """Các thư mục thật của một loại (wiki, sources...), kể cả bản có số thứ tự như '07 - Wiki'
    của brain cũ. Cùng quy tắc với chung-cat và quy trình, để cả ba trang đếm cùng một thư mục."""
    pat = re.compile(r"^(\d+\s*[-_.]\s*)?" + re.escape(ten) + r"$", re.I)
    try:
        return sorted(n for n in os.listdir(root) if pat.match(n) and os.path.isdir(os.path.join(root, n)))
    except OSError:
        return []


def _know_scan(root: str, sub: str) -> list:
    out = []
    for thu_muc in _thu_muc_that(root, sub) or [sub]:
        base = os.path.join(root, thu_muc)
        if not os.path.isdir(base):
            continue
        for dp, dns, fns in os.walk(base):
            dns[:] = [x for x in dns if not x.startswith(".")]
            for fn in fns:
                if fn.startswith("."):
                    continue
                fp = os.path.join(dp, fn)
                try:
                    st = os.stat(fp)
                except OSError:
                    continue
                out.append({"ten": fn, "rel": os.path.relpath(fp, root).replace("\\", "/"),
                            "abs": fp, "mtime": st.st_mtime, "size": st.st_size})
    out.sort(key=lambda x: -x["mtime"])
    return out


def _know_head(fp: str) -> str:
    try:
        with open(fp, encoding="utf-8", errors="replace") as f:
            return f.read(4000)
    except Exception:
        return ""


def _knowledge(root: str) -> dict:
    out = {"sources": [], "wiki_groups": [], "inbox": [], "hot": [],
           "counts": {"sources": 0, "wiki": 0, "attachments": 0, "inbox": 0, "facts": 0},
           "stale": 0}
    if not root or not os.path.isdir(root):
        return out
    now = time.time()

    # --- wiki: đọc đầu mỗi trang để nhặt 'source:' link -> tập nguồn đã chưng cất,
    # đồng thời gom theo thư mục con (chủ đề) thay vì trả một list phẳng.
    ref_full, ref_stem, ref_base = set(), set(), set()
    wgrp: dict = {}
    wtong = 0
    for it in _know_scan(root, "wiki"):
        if not it["rel"].lower().endswith(_KNOW_TEXT_EXT):
            continue
        if os.path.basename(it["rel"]).lower() in _KNOW_BO_FILE:
            continue
        wtong += 1
        phan = it["rel"].split("/")
        chude = phan[1] if len(phan) > 2 else ""
        wgrp.setdefault(chude, []).append(
            {"ten": _tieu_de_qt(it["ten"]), "rel": it["rel"], "mtime": it["mtime"]})
        head = _know_head(it["abs"])
        for m in _KNOW_SRC_RE.finditer(head):
            r = m.group(1).strip().strip("[]").replace("\\", "/").lower()
            if not r:
                continue
            ref_full.add(r)
            ref_stem.add(os.path.splitext(r)[0])
            ref_base.add(os.path.splitext(os.path.basename(r))[0])
    out["wiki_groups"] = [{"chude": k, "items": v[:12]} for k, v in wgrp.items()]

    def _distilled(it) -> bool:
        # Bóc dần đuôi (x.docx.txt -> x.docx -> x): ref trỏ vào bản GỐC .docx nhưng trên
        # đĩa có thể chỉ còn bản trích xuất .txt, hoặc ngược lại - cả hai cùng là một
        # tài liệu. Lặp tối đa 3 lần là đủ cho đuôi kép.
        s = it["rel"].lower()
        for _ in range(3):
            if s in ref_full or s in ref_stem:
                return True
            if os.path.splitext(os.path.basename(s))[0] in ref_base:
                return True
            s2 = os.path.splitext(s)[0]
            if s2 == s:
                break
            s = s2
        if it["rel"].lower().endswith(_KNOW_TEXT_EXT):
            st = _KNOW_STATUS_RE.search(_know_head(it["abs"]))
            if st and st.group(1).strip().lower() not in ("unprocessed", "pending"):
                return True
        return False

    # --- sources: tài liệu đã nạp, mới trước. Gộp cặp "X.docx" + "X.docx.txt" (bản
    # trích xuất chữ của chính file gốc) thành MỘT dòng tên gốc, trường `doc` trỏ bản
    # .txt để bấm mở là đọc được chữ thay vì file nhị phân.
    src_all = _know_scan(root, "sources")
    byrel = {it["rel"].lower(): it for it in src_all}
    src = []
    for it in src_all:
        rel_l = it["rel"].lower()
        if rel_l.endswith(".txt") and rel_l[:-4] in byrel:
            continue  # sidecar trích xuất - nhập vào dòng bản gốc
        twin = byrel.get(rel_l + ".txt")
        if twin:
            it["doc"] = twin["rel"]
        it["distilled"] = _distilled(it)
        it.pop("abs", None)
        src.append(it)
    stale = 0
    for it in src:
        if not it["distilled"] and now - it["mtime"] > 7 * _DAY:
            stale += 1
            it["cu"] = True
    out["sources"] = src[:40]
    out["stale"] = stale

    # --- inbox: file nhận từ kênh ngoài (telegram/zalo/khach...), kenh = thư mục con.
    inbox = []
    inbox_all = _know_scan(root, "inbox")
    for it in inbox_all[:15]:
        phan = it["rel"].split("/")
        it["kenh"] = phan[1] if len(phan) > 2 else ""
        it.pop("abs", None)
        inbox.append(it)
    out["inbox"] = inbox

    # --- hot: file hay được mở nhất. Store đếm lượt mở ghi từ /files/read; mới chạy
    # lần đầu thì rỗng - trả rỗng thay vì bịa xếp hạng.
    hot = []
    try:
        import json as _json
        import config as _cfg
        d = _json.loads((_cfg.STATE_DIR / "file-views.json").read_text(encoding="utf-8"))
        if isinstance(d, dict):
            pfx = os.path.normcase(os.path.realpath(root)) + "|"
            for k, v in d.items():
                if not (isinstance(k, str) and k.startswith(pfx) and isinstance(v, dict)):
                    continue
                rel = k[len(pfx):]
                # File đã bị xoá hoặc đổi tên thì bỏ: bấm vào sẽ ra 404, và không có ngày để hiển thị.
                try:
                    mt = os.stat(os.path.join(root, rel)).st_mtime
                except OSError:
                    continue
                hot.append({"ten": v.get("ten") or os.path.basename(rel), "rel": rel,
                            "lan": int(v.get("n") or 0), "mtime": mt})
            hot.sort(key=lambda x: -x["lan"])
    except Exception:
        pass
    out["hot"] = hot[:6]

    # Ký ức = memory/facts/*.md (tôn trọng cả bố cục 'Memory' chữ hoa của brain cũ -
    # chỉ đọc, không tạo thư mục như _brain_memory_dir).
    facts = 0
    for memname in ("memory", "Memory"):
        fd = os.path.join(root, memname, "facts")
        try:
            if os.path.isdir(fd):
                facts = sum(1 for f in os.listdir(fd) if f.endswith(".md"))
                break
        except OSError:
            pass
    out["counts"] = {"sources": len(src), "wiki": wtong,
                     "attachments": len(_know_scan(root, "attachments")),
                     "inbox": len(inbox_all), "facts": facts}
    return out


# ---------------------------------------------------------------------------------------
# Phòng ban: việc (kanban của brain phòng) + dữ liệu đã nạp (sources/wiki trong brain phòng)
# ---------------------------------------------------------------------------------------
def _departments(deps: OverviewDeps, scope=None) -> dict:
    """Sổ phòng ban gộp theo đơn vị (brand) và khối. scope=None: quản trị xem tất cả; scope là
    danh sách brain trưởng phòng được cấp: chỉ phòng có brain nằm trong đó được đưa vào, còn
    đơn vị và khối được tính lại từ đúng những phòng đó (không lộ số của phòng khác)."""
    d = deps.phong_view() or {}
    khoi = {k.get("id"): k for k in (d.get("khoi") or [])}
    brands = {b.get("id"): b for b in (d.get("brands") or [])}
    rows = []
    for p in d.get("phong") or []:
        path = str(p.get("brain_path") or "")
        # _brain_root() gặp đường dẫn không tồn tại sẽ âm thầm quay về brain MẶC ĐỊNH, nên phòng
        # chưa có thư mục brain tuyệt đối không được đọc kanban - không thì việc của brain chính
        # bị tính nhầm cho phòng đó.
        has_brain = bool(p.get("brain_ok")) and bool(path) and os.path.isdir(path)
        if scope is not None and not (has_brain and _cc_trong_pham_vi(path, scope)):
            continue
        c = None
        if has_brain:
            try:
                c = _counts(deps.today.board_view(path) or {})
            except Exception as e:
                _log("kanban/" + str(p.get("brain")), e)
        k = khoi.get(p.get("khoi_id")) or {}
        b = brands.get(k.get("brand") or "h2o") or {}
        nguon, wiki = int(p.get("so_nguon") or 0), int(p.get("so_wiki") or 0)
        if not has_brain:
            st = "nobrain"
        elif c is None:
            st = "error"
        # Trang wiki KHÔNG tính là dữ liệu: dựng sơ đồ phòng ban là mỗi brain có sẵn vài trang wiki
        # khung, đếm vào thì phòng trống trơn cũng hiện "ổn định". Chỉ việc thật + tài liệu đã nạp.
        elif not (c["open"] or c["done24"] or nguon):
            st = "empty"
        else:
            st = _status(c)
        rows.append({
            "id": p.get("id"), "ten": p.get("ten") or p.get("id"), "agent": p.get("agent") or "",
            "agent_slug": p.get("agent_slug") or "",
            "khoi": k.get("ten") or "", "khoi_id": k.get("id") or "",
            "brand_id": b.get("id") or "h2o",
            "brand": b.get("ten") or "H2O Studio", "brain": p.get("brain") or "",
            "brain_path": path if has_brain else "", "has_brain": has_brain,
            "vai": p.get("vai") or "", "nhiem_vu": list(p.get("nhiem_vu") or []),
            "nhan_vien": int(p.get("so_nhan_vien") or 0), "nguon": nguon, "wiki": wiki,
            "tasks": c, "status": st,
        })
    units = []
    for bid, b in brands.items():
        rs = [r for r in rows if r["brand_id"] == bid]
        if not rs:
            continue
        tot = {"done24": 0, "open": 0, "review": 0, "blocked": 0, "running": 0}
        for r in rs:
            for key in tot:
                tot[key] += int((r["tasks"] or {}).get(key, 0))
        units.append({
            "id": bid, "ten": b.get("ten") or bid, "shared_brain": b.get("shared_brain") or "",
            "phong": len(rs),
            "co_du_lieu": sum(1 for r in rs if r["nguon"]),
            "co_brain": sum(1 for r in rs if r["has_brain"]),
            "tasks": tot, "status": _status(tot),
            # Phòng cần nhìn trước: kẹt > chờ duyệt > đang mở nhiều
            "top": sorted(rs, key=lambda r: (-(r["tasks"] or {}).get("blocked", 0),
                                             -(r["tasks"] or {}).get("review", 0),
                                             -(r["tasks"] or {}).get("open", 0),
                                             -(r["nguon"] + r["wiki"])))[:4],
        })
    # Thong tin khoi cho so do day noi tren trang Phong ban: boi_canh/dau_ra la khuon
    # bao cao ky vong cua ca khoi, de workspace truong phong hien "dau ra mong muon".
    #
    # thu_tu_luong/trai_dai den TU SO phong ban chu khong hardcode ben JS nua (xem
    # h2o_departments._LUONG_MAC_DINH). `tasks` la tong cua ca khoi, va `un` = so viec dang
    # dong lai (ket + cho duyet + dang mo) - do la con so gan len mui ten so do, de nhin ra
    # cho tac thay vi chi thay mot mui ten trang tri.
    khois = []
    for k in (d.get("khoi") or []):
        rs = [r for r in rows if r["khoi_id"] == k.get("id")]
        if scope is not None and not rs:
            continue  # khối không có phòng nào trong phạm vi thì không hiện với trưởng phòng
        tot = {"done24": 0, "open": 0, "review": 0, "blocked": 0, "running": 0}
        for r in rs:
            for key in tot:
                tot[key] += int((r["tasks"] or {}).get(key, 0))
        khois.append({
            "id": k.get("id"), "ten": k.get("ten") or k.get("id"),
            "prefix": k.get("prefix") or "", "boi_canh": k.get("boi_canh") or "",
            "dau_ra": k.get("dau_ra") or "", "brand_id": k.get("brand") or "h2o",
            "thu_tu_luong": int(k.get("thu_tu_luong") or 0),
            "trai_dai": bool(k.get("trai_dai")),
            "phong": len(rs), "tasks": tot, "status": _status(tot),
            # `open` đã gồm cả kẹt và chờ duyệt (xem _OPEN). Cộng thêm hai số đó là đếm đôi.
            "un": tot["open"],
        })
    return {"units": units, "phong": rows, "khois": khois}


# ---------------------------------------------------------------------------------------
# Lịch: nhắc hẹn pending của MỌI brain (đường dẫn tuyệt đối, bỏ trùng theo id)
# ---------------------------------------------------------------------------------------
def _reminders(deps: OverviewDeps, start: float, end: float) -> list:
    out, seen = [], set()
    for path in deps.brain_paths() or []:
        try:
            rems = (deps.today.reminders_load(path) or {}).get("reminders") or []
        except Exception as e:
            _log("reminders/" + os.path.basename(str(path)), e)
            continue
        for r in rems:
            rid = str(r.get("id") or "") or f"{path}:{r.get('due_at')}:{r.get('text')}"
            if rid in seen:
                continue
            due = float(r.get("due_at") or 0)
            if r.get("status") != "pending" or not (start <= due < end):
                continue
            seen.add(rid)
            out.append({
                "id": rid, "due_at": due, "time": time.strftime("%H:%M", time.localtime(due)),
                "day": time.strftime("%Y-%m-%d", time.localtime(due)),
                "title": r.get("text") or r.get("label") or "(nhắc hẹn)",
                "label": r.get("label") or "", "mode": r.get("mode") or "",
                "repeat": bool(r.get("cron") or r.get("repeat_min")),
                "brain": os.path.basename(str(path).rstrip("/\\")),
            })
    out.sort(key=lambda x: x["due_at"])
    return out


def _today_bounds() -> tuple:
    now = _dt.datetime.now()
    s = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    return s, s + _DAY


def _harness(deps: OverviewDeps, brain: str) -> dict:
    """Tầng tự cải tiến (Harness² -> Joyce): đề xuất chờ duyệt trong Joyce/proposals/,
    trạng thái vòng học trong Joyce/ppc-state.json, nhật ký bài học Joyce/learn-log/.
    Chỉ đọc file - lỗi/mục thiếu trả về số 0, không làm hỏng cả trang tổng quan."""
    out = {"pending": [], "pending_n": 0, "applied_n": 0,
           "lessons_total": 0, "learn_log_days": 0, "last_run": "", "last_items": []}
    try:
        root = str(deps.brain_root(brain) or "")
        if not root or not os.path.isdir(root):
            return out
        jdir = os.path.join(root, "Joyce")
        pdir = os.path.join(jdir, "proposals")
        if os.path.isdir(pdir):
            for fn in sorted(os.listdir(pdir)):
                if not fn.endswith(".md"):
                    continue
                try:
                    head = open(os.path.join(pdir, fn), encoding="utf-8", errors="ignore").read(1500)
                except OSError:
                    continue
                if not re.search(r"^type:\s*proposal\b", head, re.M):
                    continue  # README.md, file ghi chú - không phải đề xuất
                m = re.search(r"^status:\s*([a-z]+)", head, re.M)
                st = m.group(1) if m else "pending"
                if st == "applied":
                    out["applied_n"] += 1
                elif st == "pending":
                    t = re.search(r"^target:\s*(\S+)", head, re.M)
                    v = re.search(r"^verdict:\s*\"?([a-z]*)", head, re.M)
                    out["pending"].append({"file": fn,
                                           "target": t.group(1) if t else "",
                                           "verdict": (v.group(1) if v else "") or ""})
            out["pending_n"] = len(out["pending"])
            out["pending"] = out["pending"][:6]
        try:
            state = json.load(open(os.path.join(jdir, "ppc-state.json"), encoding="utf-8"))
            out["lessons_total"] = int(state.get("lessons_total") or 0)
            out["last_run"] = str(state.get("last_run") or "")
            out["last_items"] = [str(x)[:80] for x in (state.get("last_items") or [])][:5]
        except (OSError, ValueError, TypeError):
            pass
        ldir = os.path.join(jdir, "learn-log")
        if os.path.isdir(ldir):
            out["learn_log_days"] = sum(1 for f in os.listdir(ldir) if f.endswith(".md"))
    except Exception:  # noqa: BLE001
        pass
    return out


def register(app, deps: OverviewDeps):
    router = APIRouter()

    @router.get("/api/joyce/v1/overview")
    async def api_overview(request: Request, brain: str = Query("brain")):
        if _staff(deps, request):
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        T = deps.today
        now = time.time()
        down: list = []

        def run(name, fn, fallback):
            try:
                return fn()
            except Exception as e:  # noqa: BLE001 - mỗi khối tự chịu lỗi của nó
                _log(name, e)
                down.append(name)
                return fallback

        view = run("kanban", lambda: T.board_view(brain) or {}, {})
        c = _counts(view)
        cols = view.get("columns") or {}
        apps = await jt._ping_projects(T)
        pulse, pulse_down = jt._pulse(T, brain, apps)
        down += [x for x in pulse_down if x not in down]
        unread = run("inbox", lambda: int(T.inbox_unread() or 0), 0)
        snap = run("connectors", lambda: T.connect_snapshot() or {}, {})
        conns = run("connectors", lambda: (T.conns_list() if T.conns_list else []) or [], [])
        engines = run("engines", lambda: T.engines_health() or {}, {})
        usage = run("usage", lambda: deps.usage_today() or {}, {})
        stale = sum(1 for t in (cols.get("review") or [])
                    if now - float(t.get("updated_at") or t.get("created_at") or now) > jt._REVIEW_STALE_SEC)

        # ---- Brief + chip chú ý: cùng công thức trang Hôm nay để hai trang không nói khác nhau
        conn_down = sum(1 for r in snap.values() if r.get("ok") is False)
        brief = jt._brief({"blocked": c["blocked"], "review": c["review"],
                           "apps_down": sum(1 for a in apps if a.get("ok") is False),
                           "connectors_down": conn_down, "unread": unread})
        hi = sum(1 for p in pulse if p.get("severity") in ("critical", "high"))
        attention = [
            {"key": "review", "n": c["review"], "tone": "red"},
            {"key": "blocked", "n": c["blocked"], "tone": "amber"},
            {"key": "alerts", "n": hi, "tone": "teal"},
        ]

        kpis = [
            {"key": "done24", "value": c["done24"], "tone": "good", "source": "kanban"},
            {"key": "running", "value": c["running"], "tone": "", "source": "kanban"},
            {"key": "review", "value": c["review"], "meta_n": stale,
             "tone": "warn" if c["review"] else "", "source": "kanban"},
            {"key": "blocked", "value": c["blocked"], "tone": "bad" if c["blocked"] else "", "source": "kanban"},
            {"key": "queue", "value": c["queue"], "meta": view.get("orchestration") or "off",
             "tone": "warn" if c["queue"] and view.get("orchestration") in ("off", "", None) else "",
             "source": "kanban"},
            {"key": "turns", "value": int(usage.get("turns") or 0), "meta_n": int(usage.get("tokens") or 0),
             "tone": "", "source": "usage"},
        ]

        # ---- Hàng đợi ưu tiên: Pulse (đã xếp theo mức) + việc chờ duyệt/sẵn sàng chưa có trong Pulse
        seen_t = {p.get("task_id") for p in pulse if p.get("task_id")}
        prio = [{"severity": p.get("severity"), "title": p.get("title"), "meta": p.get("meta") or "",
                 "source": p.get("source"), "href": p.get("href") or "kanban",
                 "task_id": p.get("task_id"), "age": jt._age_sec(p.get("since") or now)}
                for p in pulse]
        for col, sev in (("review", "medium"), ("ready", "low"), ("running", "low")):
            for t in cols.get(col) or []:
                if t.get("id") in seen_t:
                    continue
                prio.append({"severity": sev, "title": t.get("title") or "(không tên)",
                             "meta": (t.get("route") or t.get("block_reason") or "")[:120],
                             "source": "kanban", "status": col, "href": "kanban", "task_id": t.get("id"),
                             "age": jt._age_sec(t.get("updated_at") or t.get("created_at") or now)})
        prio = prio[:8]

        # ---- Nhịp vận hành theo lĩnh vực: chỉ lĩnh vực có NGUỒN THẬT trong Joyce
        ok_conns = [x for x in conns if x.get("enabled")]
        conn_ok = sum(1 for x in ok_conns if (snap.get(str(x.get("id"))) or {}).get("ok") is not False)
        eng_ok = sum(1 for r in engines.values() if r.get("ok") is not False)
        rem_ok, rem_why = run("reminders", lambda: T.reminders_notify() or (True, ""), (True, ""))
        s0, s1 = _today_bounds()
        rems_today = run("reminders", lambda: _reminders(deps, s0, s1), [])
        rems_7d = run("reminders", lambda: _reminders(deps, now, now + 7 * _DAY), [])
        vc = run("vault", lambda: deps.vault_counts(brain) or {}, {})
        domains = [
            {"key": "work", "done": c["done24"], "open": c["open"], "risk": c["blocked"] + stale,
             "ratio": (c["done24"] / (c["done24"] + c["open"])) if (c["done24"] + c["open"]) else None,
             "ratio_key": "done", "href": "kanban", "source": "kanban",
             "meta": view.get("orchestration") or "off"},
            {"key": "connectors", "done": conn_ok, "open": len(ok_conns), "risk": conn_down,
             "ratio": (conn_ok / len(ok_conns)) if ok_conns else None, "ratio_key": "online",
             "href": "mcp", "source": "connect_health"},
            {"key": "apps", "done": sum(1 for a in apps if a.get("ok")), "open": len(apps),
             "risk": sum(1 for a in apps if a.get("ok") is False),
             "ratio": (sum(1 for a in apps if a.get("ok")) / len(apps)) if apps else None,
             "ratio_key": "online", "href": "projects", "source": "h2o_projects"},
            {"key": "engines", "done": eng_ok, "open": len(engines), "risk": len(engines) - eng_ok,
             "ratio": (eng_ok / len(engines)) if engines else None, "ratio_key": "online",
             "href": "models", "source": "engines"},
            {"key": "reminders", "done": len(rems_today), "open": len(rems_7d), "risk": 0 if rem_ok else 1,
             "ratio": None, "href": "selfimprove", "source": "reminders",
             "meta": "" if rem_ok else str(rem_why or "")[:120]},
            {"key": "knowledge", "done": int(vc.get("wiki") or 0), "open": int(vc.get("sources") or 0),
             "risk": 0, "ratio": None, "href": "files", "source": "vault",
             "meta_n": int(vc.get("facts") or 0)},
        ]

        dep = run("departments", lambda: _departments(deps), {"units": [], "phong": []})
        units = [{k: u[k] for k in ("id", "ten", "phong", "co_du_lieu", "co_brain", "tasks", "status")}
                 | {"top": [{k: r[k] for k in ("id", "ten", "khoi", "tasks", "status", "nguon", "wiki")}
                            for r in u["top"]]}
                 for u in dep["units"]]

        system = []
        for name, r in engines.items():
            system.append({"key": "engine", "name": name, "ok": r.get("ok") is not False,
                           "meta": (r.get("message") or "")[:100], "href": "models"})
        system.append({"key": "connectors", "ok": conn_down == 0, "n_ok": conn_ok, "n": len(ok_conns),
                       "href": "mcp"})
        system.append({"key": "apps", "ok": not any(a.get("ok") is False for a in apps),
                       "n_ok": sum(1 for a in apps if a.get("ok")), "n": len(apps), "href": "projects"})
        system.append({"key": "kanban", "ok": "kanban" not in down,
                       "meta": view.get("orchestration") or "off", "href": "kanban"})
        system.append({"key": "reminders", "ok": bool(rem_ok), "meta": "" if rem_ok else str(rem_why or "")[:100],
                       "href": "channels"})

        memory = {"facts": int(vc.get("facts") or 0), "sources": int(vc.get("sources") or 0),
                  "wiki": int(vc.get("wiki") or 0),
                  "skills": run("skills", lambda: int(deps.skills_count(brain) or 0), 0),
                  "phong": len(dep["phong"]), "brands": len(dep["units"])}

        activity = []
        for it in run("inbox", lambda: T.inbox_recent(8) or [], []):
            activity.append({"title": it.get("title") or "", "kind": it.get("kind") or "",
                             "label": it.get("label") or "", "read": bool(it.get("read")),
                             "age": jt._age_sec(it.get("ts") or now)})
        for t in sorted(cols.get("done") or [], key=lambda x: -float(x.get("updated_at") or 0))[:4]:
            activity.append({"title": t.get("title") or "", "kind": "task_done", "label": "",
                             "read": True, "age": jt._age_sec(t.get("updated_at") or now),
                             "_ts": float(t.get("updated_at") or 0)})

        d_now = _dt.datetime.now()
        return {
            "ok": True, "brain": brain, "generated_at": now,
            "date": d_now.strftime("%d/%m/%Y"), "weekday": _DOW[d_now.weekday()],
            "brief": brief, "attention": attention, "kpis": kpis, "priority": prio,
            "domains": domains, "business_sources": BUSINESS_SOURCES,
            "units": units, "schedule": rems_today[:8], "system": system, "memory": memory,
            "harness": run("harness", lambda: _harness(deps, brain), {}),
            "activity": activity[:8], "orchestration": view.get("orchestration") or "off",
            "partial": bool(down), "sections_down": sorted(set(down)),
        }

    @router.get("/api/joyce/v1/overview/departments")
    async def api_departments(request: Request):
        # Quản trị xem cả sổ. Trưởng phòng chỉ thấy phòng trong phạm vi được cấp; nhân viên thường
        # bị 403 (đúng như trước). Trước đây mọi nhân viên đều bị 403 nên trưởng phòng mất luôn tab.
        duoc, scope = _cc_quyen(request, deps)
        if not duoc:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            d = _departments(deps, scope)
        except Exception as e:  # noqa: BLE001
            _log("departments", e)
            return {"ok": False, "error": "không đọc được sổ phòng ban", "units": [], "phong": []}
        for u in d["units"]:
            u["top"] = [r["id"] for r in u["top"]]
        return {"ok": True, "generated_at": time.time(), **d}

    @router.get("/api/joyce/v1/overview/chung-cat")
    async def api_chung_cat(request: Request, day: str = Query("")):
        duoc, scope = _cc_quyen(request, deps)
        if not duoc:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            ngay = day or _dt.datetime.now().strftime("%Y-%m-%d")
            _dt.datetime.strptime(ngay, "%Y-%m-%d")
        except ValueError:
            return JSONResponse({"ok": False, "error": "day phải dạng YYYY-MM-DD"}, status_code=400)
        try:
            pv = deps.phong_view() or {}
            ten_khoi = {k.get("id"): k.get("ten") for k in (pv.get("khoi") or [])}
            phong = {}
            for p in pv.get("phong") or []:
                bp = str(p.get("brain_path") or "")
                if bp:
                    phong[os.path.normcase(bp)] = {"ten": p.get("ten"), "khoi": ten_khoi.get(p.get("khoi_id")) or "",
                                                   "brand": (p.get("brand") or {}).get("ten") or ""}
            ds = [str(x) for x in (deps.brain_paths() or []) if _cc_trong_pham_vi(str(x), scope)]
            d = _chung_cat(ngay, ds, phong)
            return {"ok": True, "generated_at": time.time(), **d}
        except Exception as e:  # noqa: BLE001
            _log("chung-cat", e)
            return {"ok": False, "error": "không đọc được tài liệu chưng cất", "nhom": []}

    @router.post("/api/joyce/v1/overview/chung-cat/xem")
    async def api_chung_cat_xem(request: Request):
        """Đánh dấu một tài liệu chưng cất là đã xem (hoặc bỏ đánh dấu). Chỉ nhận đường dẫn
        đã nằm trong danh sách brain thật, trong wiki của brain đó, và trong phạm vi người gọi."""
        duoc, scope = _cc_quyen(request, deps)
        if not duoc:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "thiếu dữ liệu"}, status_code=400)
        bp = str(body.get("brain_path") or "")
        rel = str(body.get("rel") or "").replace("\\", "/")
        da_xem = bool(body.get("da_xem", True))
        brains = {os.path.normcase(str(x)): str(x) for x in (deps.brain_paths() or [])}
        goc = brains.get(os.path.normcase(bp))
        if goc and not _cc_trong_pham_vi(goc, scope):
            goc = None
        if not goc or ".." in rel.split("/") or not (rel.startswith("wiki/") or rel.startswith("07 - Wiki/")):
            return JSONResponse({"ok": False, "error": "tài liệu không hợp lệ"}, status_code=400)
        full = os.path.join(goc, rel)
        if not os.path.isfile(full):
            return JSONResponse({"ok": False, "error": "không thấy tài liệu"}, status_code=404)
        khoa = f"{goc}|{rel}"
        # Đọc-sửa-ghi phải nằm trong cùng một khoá, không thì hai lần bấm gần nhau làm mất dấu của nhau.
        with _CC_XEM_LOCK:
            d = _cc_doc_xem()
            if da_xem:
                d[khoa] = {"mtime": os.stat(full).st_mtime, "luc": time.time()}
            else:
                d.pop(khoa, None)
            _cc_ghi_xem(d)
        return {"ok": True, "da_xem": da_xem}

    @router.get("/api/joyce/v1/overview/chung-cat/duyet")
    async def api_chung_cat_hang_cho(request: Request):
        """Bảng duyệt tài liệu chưng cất: draft mới hôm nay, hàng chờ tích luỹ, và các
        trang vừa chưng cất trong 7 ngày để chủ xem lại. Phạm vi giống chung-cat/xem."""
        duoc, scope = _cc_quyen(request, deps)
        if not duoc:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            pv = deps.phong_view() or {}
            ten_khoi = {k.get("id"): k.get("ten") for k in (pv.get("khoi") or [])}
            phong = {}
            for p in pv.get("phong") or []:
                bp = str(p.get("brain_path") or "")
                if bp:
                    phong[os.path.normcase(bp)] = {"ten": p.get("ten"), "khoi": ten_khoi.get(p.get("khoi_id")) or "",
                                                   "brand": (p.get("brand") or {}).get("ten") or ""}
            ds = [str(x) for x in (deps.brain_paths() or []) if _cc_trong_pham_vi(str(x), scope)]
            d = _hang_cho_duyet(ds, phong)
            return {"ok": True, "generated_at": time.time(), **d}
        except Exception as e:  # noqa: BLE001
            _log("chung-cat/duyet", e)
            return {"ok": False, "error": "không đọc được hàng chờ duyệt",
                    "moi": [], "cho": [], "da_duyet": [], "lech_thu_muc": []}

    @router.post("/api/joyce/v1/overview/chung-cat/duyet")
    async def api_chung_cat_duyet(request: Request):
        """Duyệt một bản nháp: frontmatter draft -> active (bỏ staging, bỏ tag cho-duyet,
        đánh `approved`), chuyển file ra wiki chính thức, cập nhật index.md + log.md."""
        duoc, scope = _cc_quyen(request, deps)
        if not duoc:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "thiếu dữ liệu"}, status_code=400)
        bp = str(body.get("brain_path") or "")
        rel = str(body.get("rel") or "").replace("\\", "/")
        brains = {os.path.normcase(str(x)): str(x) for x in (deps.brain_paths() or [])}
        goc = brains.get(os.path.normcase(bp))
        if goc and not _cc_trong_pham_vi(goc, scope):
            goc = None
        if not goc:
            return JSONResponse({"ok": False, "error": "tài liệu không hợp lệ"}, status_code=400)
        try:
            r = _duyet_mot_file(goc, rel)
        except Exception as e:  # noqa: BLE001
            _log("chung-cat/duyet POST", e)
            return JSONResponse({"ok": False, "error": "không duyệt được tài liệu"}, status_code=500)
        if not r.get("ok"):
            return JSONResponse(r, status_code=400)
        return r

    @router.post("/api/joyce/v1/overview/chung-cat/xoa")
    async def api_chung_cat_xoa(request: Request):
        """'Không duyệt' một bản nháp: xoá file VĨNH VIỄN khỏi vault - không copy, không
        lên wiki, không ghi log nội dung. Rào y hệt duyệt: brain trong danh sách + phạm
        vi, rel nằm trong wiki, chỉ file staging/draft mới được xoá."""
        duoc, scope = _cc_quyen(request, deps)
        if not duoc:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "thiếu dữ liệu"}, status_code=400)
        bp = str(body.get("brain_path") or "")
        rel = str(body.get("rel") or "").replace("\\", "/")
        brains = {os.path.normcase(str(x)): str(x) for x in (deps.brain_paths() or [])}
        goc = brains.get(os.path.normcase(bp))
        if goc and not _cc_trong_pham_vi(goc, scope):
            goc = None
        if not goc:
            return JSONResponse({"ok": False, "error": "tài liệu không hợp lệ"}, status_code=400)
        try:
            r = _xoa_nhap(goc, rel)
        except Exception as e:  # noqa: BLE001
            _log("chung-cat/xoa", e)
            return JSONResponse({"ok": False, "error": "không xoá được tài liệu"}, status_code=500)
        if not r.get("ok"):
            return JSONResponse(r, status_code=400)
        return r

    @router.post("/api/joyce/v1/overview/chung-cat/gop-thu-muc")
    async def api_chung_cat_gop(request: Request):
        """Chuẩn hoá tên thư mục staging: gộp `wiki/_cho_duyet` (gạch dưới) về
        `wiki/_cho-duyet` (gạch ngang - tên chuẩn khớp tag cho-duyet và kế hoạch ingest).
        `brain_path` rỗng = gộp mọi brain trong phạm vi."""
        duoc, scope = _cc_quyen(request, deps)
        if not duoc:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            body = await request.json()
        except Exception:
            body = {}
        bp = str(body.get("brain_path") or "")
        brains = {os.path.normcase(str(x)): str(x) for x in (deps.brain_paths() or [])}
        if bp:
            goc = brains.get(os.path.normcase(bp))
            ds = [goc] if goc and _cc_trong_pham_vi(goc, scope) else []
            if not ds:
                return JSONResponse({"ok": False, "error": "brain không hợp lệ"}, status_code=400)
        else:
            ds = [str(x) for x in brains.values() if _cc_trong_pham_vi(str(x), scope)]
        moved = 0
        try:
            for goc in ds:
                moved += int(_gop_cho_duyet(goc).get("moved") or 0)
        except Exception as e:  # noqa: BLE001
            _log("chung-cat/gop-thu-muc", e)
            return JSONResponse({"ok": False, "error": "gộp thư mục lỗi giữa chừng", "moved": moved},
                                status_code=500)
        return {"ok": True, "moved": moved, "brains": len(ds)}

    @router.get("/api/joyce/v1/overview/quy-trinh")
    async def api_quy_trinh(request: Request, brain: str = Query("")):
        """Quy trình THẬT trong wiki của một brain phòng, xếp theo Trước / Trong / Sau.

        Ba cột Trước-Trong-Sau của workspace trưởng phòng trước đây chỉ hiện mô tả vai trò
        lấy từ sổ phòng ban - chữ tĩnh, không nối vào tài liệu nào. Endpoint này trả đúng
        các file quy trình đang có để bấm thẳng vào mà sửa cùng Joyce."""
        duoc, scope = _cc_quyen(request, deps)
        if not duoc:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        # Chỉ đọc brain THẬT trong danh sách brain của máy, và trưởng phòng chỉ trong phạm vi
        # của mình. Đường dẫn tự do ở đây sẽ liệt kê wiki của bất kỳ thư mục nào trên ổ đĩa.
        if not (brain or "").strip():
            return {"ok": True, **_quy_trinh("")}
        bp = deps.brain_root("brain") if brain.strip() == "brain" else brain
        root = _brain_trong_phep(bp, deps, scope)
        if not root:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            return {"ok": True, **_quy_trinh(root)}
        except Exception as e:  # noqa: BLE001
            _log("quy-trinh", e)
            return {"ok": False, "error": "không đọc được quy trình", "giai_doan": {}}

    @router.get("/api/joyce/v1/overview/knowledge")
    async def api_knowledge(request: Request, brain: str = Query("")):
        """Panel 'tri thức phòng' trong workspace trưởng phòng: gom nguồn/wiki/inbox/
        file hay mở một lần thay vì frontend gọi N request /files/list. `brain` là đường
        dẫn brain (giống quy-trinh) hoặc 'brain' = Brain Default. Trưởng phòng chỉ đọc
        được brain trong phạm vi được cấp (_cc_trong_pham_vi)."""
        duoc, scope = _cc_quyen(request, deps)
        if not duoc:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        # "brain" = Brain Default: quy về đúng gốc mặc định qua deps (có áp phạm vi nhân viên).
        # Tên hay đường dẫn khác thì phải là brain thật của máy - KHÔNG đoán theo thư mục hiện
        # hành, nên một tên lạ không bao giờ rơi lặng lẽ vào brain mặc định.
        bp = deps.brain_root("brain") if (brain or "brain").strip() in ("", "brain") else brain
        root = _brain_trong_phep(bp, deps, scope)
        if not root:
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            return {"ok": True, **_knowledge(os.path.realpath(root))}
        except Exception as e:  # noqa: BLE001
            _log("knowledge", e)
            return {"ok": False, "error": "không đọc được tri thức phòng"}

    @router.get("/api/joyce/v1/overview/calendar")
    async def api_calendar(request: Request, start: str = Query(""), days: int = Query(7, ge=1, le=31)):
        if _staff(deps, request):
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            d0 = _dt.datetime.strptime(start, "%Y-%m-%d") if start else _dt.datetime.now()
        except ValueError:
            d0 = _dt.datetime.now()
        d0 = d0.replace(hour=0, minute=0, second=0, microsecond=0)
        s = d0.timestamp()
        try:
            items = _reminders(deps, s, s + days * _DAY)
            ok = True
        except Exception as e:  # noqa: BLE001
            _log("calendar", e)
            items, ok = [], False
        out_days = []
        for i in range(days):
            di = d0 + _dt.timedelta(days=i)
            key = di.strftime("%Y-%m-%d")
            out_days.append({"date": key, "dd": di.strftime("%d/%m"), "dow": di.weekday(),
                             "today": key == _dt.datetime.now().strftime("%Y-%m-%d"),
                             "items": [x for x in items if x["day"] == key]})
        return {"ok": ok, "start": d0.strftime("%Y-%m-%d"), "days": out_days,
                "total": len(items), "source": "reminders", "generated_at": time.time()}

    app.include_router(router)
