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
import os
import re
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
# Phòng ban: việc (kanban của brain phòng) + dữ liệu đã nạp (sources/wiki trong brain phòng)
# ---------------------------------------------------------------------------------------
def _departments(deps: OverviewDeps) -> dict:
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
            "un": tot["blocked"] + tot["review"] + tot["open"],
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
            "activity": activity[:8], "orchestration": view.get("orchestration") or "off",
            "partial": bool(down), "sections_down": sorted(set(down)),
        }

    @router.get("/api/joyce/v1/overview/departments")
    async def api_departments(request: Request):
        if _staff(deps, request):
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            d = _departments(deps)
        except Exception as e:  # noqa: BLE001
            _log("departments", e)
            return {"ok": False, "error": "không đọc được sổ phòng ban", "units": [], "phong": []}
        for u in d["units"]:
            u["top"] = [r["id"] for r in u["top"]]
        return {"ok": True, "generated_at": time.time(), **d}

    @router.get("/api/joyce/v1/overview/quy-trinh")
    async def api_quy_trinh(request: Request, brain: str = Query("")):
        """Quy trình THẬT trong wiki của một brain phòng, xếp theo Trước / Trong / Sau.

        Ba cột Trước-Trong-Sau của workspace trưởng phòng trước đây chỉ hiện mô tả vai trò
        lấy từ sổ phòng ban - chữ tĩnh, không nối vào tài liệu nào. Endpoint này trả đúng
        các file quy trình đang có để bấm thẳng vào mà sửa cùng Joyce."""
        if _staff(deps, request):
            return JSONResponse({"ok": False, "error": "staff_denied"}, status_code=403)
        try:
            return {"ok": True, **_quy_trinh(brain)}
        except Exception as e:  # noqa: BLE001
            _log("quy-trinh", e)
            return {"ok": False, "error": "không đọc được quy trình", "giai_doan": {}}

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
