"""h2o_projects - so dang ky cac app H2O (Vercel...) + kiem tra suc khoe.

Dung chung boi 3 noi:
  - plugin h2o-projects (tool chat: them/xoa/xem/ping/bao_cao)
  - endpoint /h2o-projects trong main.py (trang "Du an" tren dashboard)
  - script bao cao sang trong brains/<brain>/Joyce/scripts/h2o-bao-cao.py

Moi dự an: { id, ten, url, thu_muc, nhom, ghi_chu, api_check, keyword,
             vercel_project, them_luc }
  - api_check : URL tuy chon tra ve dữ lieu (vd endpoint API cua app) - bao cao
                coi day la "du lieu khach hang con chay" khi no tra HTTP 200.
  - keyword   : chuoi phai xuat hien trong HTML trang chu (chung toi trang render
                dung noi dung, khong phai trang loi trang).
  - vercel_project : ten project tren Vercel (neu khac `id`); can VERCEL_TOKEN
                trong env/settings de hoi trang thai deploy.

Registry: server/h2o_projects.json (cung cap voi settings.json).
"""

import json
import os
import socket
import ssl
import time
import urllib.request
import urllib.error
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent
REG_PATH = SERVER_DIR / "h2o_projects.json"
SETTINGS = SERVER_DIR / "settings.json"
TIMEOUT = 15


# ── registry ─────────────────────────────────────────────────────────

def load() -> list:
    try:
        d = json.loads(REG_PATH.read_text(encoding="utf-8"))
        return d if isinstance(d, list) else []
    except Exception:
        return []


def save(ds: list) -> None:
    REG_PATH.write_text(json.dumps(ds, ensure_ascii=False, indent=2), encoding="utf-8")


def _slug(ten: str) -> str:
    import re, unicodedata
    s = unicodedata.normalize("NFKD", ten).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "du-an"


def tim(ten: str):
    """Tim theo id hoac ten (khong phan biet hoa thuong)."""
    t = (ten or "").strip().lower()
    for p in load():
        if t in (p.get("id", "").lower(), (p.get("ten") or "").lower()):
            return p
    return None


def them(ten, url, thu_muc="", nhom="", ghi_chu="", api_check="", keyword="",
         vercel_project="", mcp_token="", auto_mcp=True):
    """Them/sua du an (match theo ten hoac id -> cap nhat). Tra (project, la_moi).

    auto_mcp=True: sau khi ghi, probe <url>/api/mcp — app H2O co chuan MCP thi
    tu dang ky vao mcp_store (xem auto_connect_mcp). Token rong van probe:
    endpoint cong khai van noi duoc, 401 thi danh dau needs_auth."""
    ten, url = (ten or "").strip(), (url or "").strip().rstrip("/")
    if not ten or not url:
        raise ValueError("thieu ten hoac url")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    ds = load()
    for p in ds:
        if (p.get("ten") or "").lower() == ten.lower() or p.get("id") == _slug(ten):
            p.update({"ten": ten, "url": url})
            for k, v in (("thu_muc", thu_muc), ("nhom", nhom), ("ghi_chu", ghi_chu),
                         ("api_check", api_check), ("keyword", keyword),
                         ("vercel_project", vercel_project)):
                if v:
                    p[k] = v
            save(ds)
            if auto_mcp:
                p["mcp"] = auto_connect_mcp(p, token=mcp_token)
            return p, False
    p = {"id": _slug(ten), "ten": ten, "url": url, "thu_muc": thu_muc,
         "nhom": nhom, "ghi_chu": ghi_chu, "api_check": api_check,
         "keyword": keyword, "vercel_project": vercel_project or _slug(ten),
         "them_luc": time.time()}
    ds.append(p)
    save(ds)
    if auto_mcp:
        p["mcp"] = auto_connect_mcp(p, token=mcp_token)
    return p, True


def xoa(ten: str) -> bool:
    p = tim(ten)
    if not p:
        return False
    save([x for x in load() if x.get("id") != p.get("id")])
    return True


# ── MCP gateway (chuẩn H2O: <url>/api/mcp, Bearer H2O_MCP_TOKEN) ───────
#
# Mo-i webapp H2O phơi 1 endpoint MCP-over-HTTP tai /api/mcp. Khi thêm dự
# án với mcp_token (hoặc app mở public), Joyce tự probe + đăng ký connection
# vào mcp_store — thêm dự án = tự có tool, không cần vào trang Kết nối.

def _rpc_post(url: str, method: str, params=None, token="", timeout=10, rid=1):
    """POST 1 JSON-RPC tới endpoint MCP. rid=None → notification (không id).
    Tra (status, body_dict|None, err)."""
    body = {"jsonrpc": "2.0", "method": method}
    if rid is not None:
        body["id"] = rid
    if params is not None:
        body["params"] = params
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream",
               "User-Agent": "Joyce-H2O/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read(2_000_000)
            ct = r.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        try:
            raw = e.read(200_000)
            j = json.loads(raw or b"{}")
            m = ((j.get("error") or {}).get("message")) or f"HTTP {e.code}"
        except Exception:
            m = f"HTTP {e.code}"
        return e.code, None, m
    except Exception as e:
        return 0, None, str(e)[:120]
    try:
        if "text/event-stream" in ct:
            # SSE: lấy dòng data: cuối cùng
            data_lines = [ln[5:].strip() for ln in raw.decode("utf-8", "replace").splitlines()
                          if ln.startswith("data:")]
            j = json.loads(data_lines[-1]) if data_lines else {}
        else:
            j = json.loads(raw or b"{}")
        return 200, j, ""
    except Exception as e:
        return 200, None, f"response không phải JSON-RPC: {str(e)[:80]}"


def probe_mcp(url: str, token: str = "") -> dict:
    """Probe <url>/api/mcp: initialize + tools/list.
    Tra {ok, mcp_url, tools[], tools_count, error, needs_auth}."""
    base = (url or "").strip().rstrip("/")
    if not base:
        return {"ok": False, "error": "thiếu url"}
    mcp_url = f"{base}/api/mcp"
    kq = {"ok": False, "mcp_url": mcp_url, "tools": [], "tools_count": 0,
          "needs_auth": False, "error": ""}
    st, j, err = _rpc_post(mcp_url, "initialize", {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "joyce-os", "version": "1.0"}}, token=token)
    if st == 401:
        kq["needs_auth"] = True
        kq["error"] = "endpoint yêu cầu H2O_MCP_TOKEN — nhập token rồi probe lại"
        return kq
    if st != 200 or not j:
        kq["error"] = err or f"HTTP {st}"
        return kq
    if "error" in j and not token:
        kq["error"] = str(j["error"].get("message", ""))[:120]
        return kq
    # initialize ok → notifications/initialized + tools/list
    _rpc_post(mcp_url, "notifications/initialized", token=token, rid=None)
    st2, j2, err2 = _rpc_post(mcp_url, "tools/list", token=token, rid=2)
    if st2 != 200 or not j2:
        kq["error"] = err2 or f"tools/list HTTP {st2}"
        return kq
    tools = ((j2.get("result") or {}).get("tools")) or []
    kq["tools"] = [t.get("name") for t in tools if isinstance(t, dict) and t.get("name")]
    kq["tools_count"] = len(kq["tools"])
    kq["ok"] = True
    return kq


def auto_connect_mcp(p: dict, token: str = "", force: bool = False) -> dict:
    """Probe MCP của dự án rồi đăng ký vào mcp_store nếu chưa có.
    Không ghi đè connection thủ công: nếu project đã có mcp_conn_id hoặc đã
    tồn tại connection custom trỏ cùng URL → chỉ cập nhật trạng thái.
    Token rỗng → rơi về env JOYCE_H2O_MCP_TOKEN (token H2O dùng chung)."""
    token = token or os.getenv("JOYCE_H2O_MCP_TOKEN", "")
    kq = probe_mcp(p.get("url") or "", token=token)
    out = {"mcp": kq, "connected": False, "conn_id": p.get("mcp_conn_id") or ""}
    if not kq["ok"]:
        p["mcp_status"] = "error"
        p["mcp_error"] = kq["error"]
        p["mcp_checked_at"] = time.time()
        save([x if x.get("id") != p.get("id") else p for x in load()])
        return out

    p["mcp_status"] = "ok"
    p["mcp_tools"] = kq["tools"]
    p["mcp_tools_count"] = kq["tools_count"]
    p["mcp_checked_at"] = time.time()
    p["mcp_error"] = ""

    # Đã có connection gắn sẵn hoặc tồn tại connection cùng URL → chỉ cập nhật
    try:
        import mcp_store
        existing = None
        for c in mcp_store.list_connections():
            if (c.get("url") or "").rstrip("/") == kq["mcp_url"].rstrip("/"):
                existing = c
                break
        if p.get("mcp_conn_id") and not force:
            out["connected"] = True
            out["conn_id"] = p["mcp_conn_id"]
        elif existing:
            out["connected"] = True
            out["conn_id"] = existing["id"]
            p["mcp_conn_id"] = existing["id"]
        else:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            cid, err = mcp_store.add_connection("custom", {
                "label": f"H2O {p.get('ten') or p.get('id')}",
                "url": kq["mcp_url"], "transport": "http",
                "headers": headers,
                "config": {"auto": "h2o-projects", "project_id": p.get("id")},
            })
            if cid:
                p["mcp_conn_id"] = cid
                out["connected"] = True
                out["conn_id"] = cid
            else:
                p["mcp_status"] = "error"
                p["mcp_error"] = err or "add_connection lỗi"
    except Exception as e:
        p["mcp_error"] = f"mcp_store: {str(e)[:100]}"
    save([x if x.get("id") != p.get("id") else p for x in load()])
    return out


def mcp_recheck(ten: str, token: str = "", force: bool = False):
    """Probe lai MCP cho du an co san (gateway deploy sau, hoac moi co token).
    Tra (project, ket_qua) hoac (None, err)."""
    p = tim(ten)
    if not p:
        return None, "không thấy dự án"
    return p, auto_connect_mcp(p, token=token, force=force)


# ── kiem tra suc khoe ────────────────────────────────────────────────

def _fetch(url: str, timeout=TIMEOUT, max_bytes=400_000):
    """GET url. Tra (status, ms, body_bytes|None, err)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Joyce-H2O/1.0"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, int((time.time() - t0) * 1000), r.read(max_bytes), ""
    except urllib.error.HTTPError as e:
        return e.code, int((time.time() - t0) * 1000), None, f"HTTP {e.code}"
    except Exception as e:
        return 0, int((time.time() - t0) * 1000), None, str(e)[:120]


def _ssl_days(host: str):
    """So ngay con han cua cert HTTPS; None neu khong do duoc."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as s:
                exp = s.getpeercert().get("notAfter", "")
        from datetime import datetime
        d = datetime.strptime(exp, "%b %d %H:%M:%S %Y %Z")
        return (d - datetime.utcnow()).days
    except Exception:
        return None


def _vercel_token() -> str:
    tok = os.getenv("VERCEL_TOKEN", "").strip()
    if tok:
        return tok
    try:
        v = json.loads(SETTINGS.read_text(encoding="utf-8")).get("vercel_token", "")
        if isinstance(v, str) and v.startswith("enc:"):
            import secrets_store
            return secrets_store.decrypt(v)
        return v or ""
    except Exception:
        return ""


def _vercel_deploy(p: dict):
    """Trang thai deploy moi nhat cua project tren Vercel; can token. Tra dict|None."""
    tok = _vercel_token()
    if not tok:
        return None
    proj = p.get("vercel_project") or p.get("id") or ""
    try:
        url = f"https://api.vercel.com/v6/deployments?projectIdOrName={urllib.request.quote(proj)}&limit=1"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            ds = json.loads(r.read() or b"{}").get("deployments") or []
        if not ds:
            return {"trang_thai": "khong-co-deploy"}
        d = ds[0]
        return {"trang_thai": d.get("state") or d.get("readyState") or "?",
                "url": d.get("url") or "",
                "luc": d.get("createdAt") or d.get("created") or 0}
    except Exception as e:
        return {"trang_thai": f"loi-api: {str(e)[:80]}"}


def ping_project(p: dict) -> dict:
    """Kiem tra 1 du an: HTTP + do tre + keyword + api_check + SSL + Vercel deploy."""
    url = p.get("url") or ""
    st, ms, body, err = _fetch(url)
    host = url.split("://")[-1].split("/")[0]
    kq = {"id": p.get("id"), "ten": p.get("ten"), "url": url,
          "ok": 200 <= st < 400, "status": st, "ms": ms, "err": err,
          "ssl_days": _ssl_days(host) if host else None,
          "keyword_ok": None, "api_ok": None, "vercel": None}
    if p.get("keyword") and body is not None:
        kq["keyword_ok"] = p["keyword"].lower() in body.decode("utf-8", "replace").lower()
        if kq["keyword_ok"] is False:
            kq["ok"] = False
            kq["err"] = kq["err"] or "trang len nhung thieu keyword"
    if p.get("api_check"):
        st2, ms2, _, err2 = _fetch(p["api_check"])
        kq["api_ok"] = 200 <= st2 < 400
        kq["api_ms"] = ms2
        if not kq["api_ok"]:
            kq["err"] = (kq["err"] + "; " if kq["err"] else "") + f"api_check HTTP {st2} {err2}"
    kq["vercel"] = _vercel_deploy(p)
    return kq


def ping_all() -> list:
    """Song song nhe bang thread - 15 app cho nhau thi mat 15 x timeout."""
    import concurrent.futures as cf
    ds = load()
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(ping_project, ds))


# ── bao cao (dung chung cho script 7h + tool chat) ───────────────────

def bao_cao() -> str:
    ds = load()
    if not ds:
        return "Chua co du an nao trong so H2O. Them bang: 'them du an <ten> <url>'."
    from datetime import datetime
    kqs = ping_all()
    chet = [k for k in kqs if not k["ok"]]
    canh = []
    for k in kqs:
        if k.get("ssl_days") is not None and k["ssl_days"] < 30:
            canh.append(f"SSL {k['ten']} con {k['ssl_days']} ngay")
        v = k.get("vercel")
        if v and v.get("trang_thai") not in (None, "READY", "khong-co-deploy"):
            canh.append(f"Vercel {k['ten']}: {v['trang_thai']}")
        if k.get("api_ok") is False:
            canh.append(f"{k['ten']}: du lieu khach hang (api_check) khong phan hoi")
        if k.get("keyword_ok") is False:
            canh.append(f"{k['ten']}: trang thieu noi dung mong doi")

    dong = [f"BAO CAO H2O - {datetime.now().strftime('%d/%m %H:%M')}",
            f"{len(kqs)-len(chet)}/{len(kqs)} du an online", ""]
    for k in kqs:
        cham = " (cham)" if k["ms"] > 4000 else ""
        if k["ok"]:
            dong.append(f"[OK] {k['ten']} - {k['status']} - {k['ms']}ms{cham}")
        else:
            dong.append(f"[LOI] {k['ten']} - {k['err'] or k['status']} - {k['url']}")
        v = k.get("vercel")
        if v and v.get("trang_thai") not in (None, "khong-co-deploy"):
            dong.append(f"      deploy: {v['trang_thai']}")
    if canh:
        dong += ["", "CANH BAO:"] + ["- " + c for c in canh]
    if chet:
        dong += ["", "CAN XU LY NGAY:"] + [f"- {k['ten']}: {k['url']}" for k in chet]
    return "\n".join(dong)
