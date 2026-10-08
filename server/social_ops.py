"""Social Ops - endpoint cho trang Cam nang / tab con FanpageJoyce.

Tat ca deu CHI DOC Facebook. Ngoai le duy nhat /social/facebook/pages/visibility ghi danh
sach Trang da go vao config ket noi cua Joyce (khong goi Facebook) - xem ham do.

Khong di vong: dashboard can so lieu THUC cua Facebook de ve the, ma tool fb_* chi
ton tai ben trong plugin host. Module nay goi DUNG plugin handler qua
plugins_host.plugin_tools(mode="readonly") - nghia la:

- Chi tool min_mode=readonly chay duoc; tool ghi (dang bai, tra loi, xoa) tra ve
  chuoi ERROR tu chinh gate cua plugins_host - khong the lo tay goi nham.
- Token/trang page van do plugin tu resolve (ctx connections) - endpoint nay
  khong cham vao token, khong doc file token.
- mode="readonly" co y nghia: ke ca khi ai do sua camnang.js goi tool ghi qua
  endpoint nay cung bi chan.

Router duoc main.py mount qua register(app, _brain_root); brain lay tu query param
nhu cac route khac.
"""
from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter()

_brain_root_fn = None  # main.py inject khi register (server/_brain_root nam trong main)


def register(app, brain_root_fn):
    """Mount router + inject ham resolve brain - theo convention xxx.register(app, deps)."""
    global _brain_root_fn
    _brain_root_fn = brain_root_fn
    app.include_router(router)


def _root(brain: str) -> str:
    return str(_brain_root_fn(brain)) if _brain_root_fn else brain


async def _call_tool(fn: str, args: dict, brain: str):
    """Goi plugin tool o mode readonly. Tra (payload, error_msg).

    Handler plugin tra CHUOI: "ERROR: ..." khi loi, json.dumps(payload) khi thanh cong.
    """
    import json as _json

    import plugins_host

    tools, route = plugins_host.plugin_tools("readonly", _root(brain))
    ent = route.get(fn)
    if not ent:
        return None, f"tool '{fn}' chua duoc dang ky (plugin meta-pages-graph dang tat?)"
    try:
        out = await ent["call"](args or {})
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    if isinstance(out, dict):
        if out.get("error"):
            return None, str(out["error"].get("message") or out["error"])
        return out, None
    if isinstance(out, str):
        s = out.strip()
        if s.startswith("ERROR:"):
            return None, s[6:].strip()
        try:
            return _json.loads(s), None
        except ValueError:
            return {"raw": s}, None     # payload khong phai JSON - tra nguyen van
    return None, "tool tra kieu du lieu khong mong doi"


def _page_args(page_id: str, page: str) -> dict:
    """fb_* nhan page_id (uu tien) hoac page (ten Trang) - khong phai page_name."""
    if page_id:
        return {"page_id": page_id}
    if page:
        return {"page": page}
    return {}


def _err(msg: str, status: int = 400):
    return JSONResponse({"ok": False, "error": msg}, status_code=status)


def _fb_conn_id():
    """id ket noi facebook-pages DA dang nhap (None neu chua) - cung luat voi plugin."""
    import mcp_store
    import oauth_mcp
    for c in mcp_store.list_connections():
        if c.get("connector_id") == "facebook-pages" and oauth_mcp.status(c["id"]).get("connected"):
            return c["id"]
    return None


@router.get("/social/facebook/pages")
async def fb_pages(brain: str = Query("brain")):
    """Danh sach Fanpage + quyen tren tung trang (fb_pages_list tra JSON array).

    `pages` = Trang Joyce dang quan ly; `hidden` = Trang co trong tai khoan Facebook nhung
    nguoi dung da GO khoi Joyce (Cam nang -> Fanpage), de giao dien cho them lai.
    `conn_id` de nut "Them Trang tu Facebook" mo lai dang nhap cua dung ket noi nay."""
    out, err = await _call_tool("fb_pages_list", {"include_hidden": True}, brain)
    if err:
        return _err(err)
    ds = out if isinstance(out, list) else (out or {}).get("pages") or []
    return {"ok": True, "conn_id": _fb_conn_id(),
            "pages": [p for p in ds if not p.get("hidden")],
            "hidden": [p for p in ds if p.get("hidden")]}


@router.post("/social/facebook/pages/visibility")
async def fb_pages_visibility(request: Request):
    """Go mot Trang khoi Joyce (hidden=true) hoac them lai (hidden=false).

    Chi ghi danh sach `hidden_pages` trong config cua ket noi facebook-pages; khong goi
    Facebook. Facebook khong cho app tu bo mot Trang khoi token, nen day la cach duy nhat de
    "thoi quan ly" mot Trang ma khong phai thu hoi ca ket noi. Plugin meta-pages-graph doc
    danh sach nay nen AI cung khong dung toi Trang da go."""
    import mcp_store
    try:
        data = await request.json()
    except Exception:
        data = {}
    pid = str((data or {}).get("page_id") or "").strip()
    if not pid or not pid.isdigit():
        return _err("can page_id (so)")
    cid = _fb_conn_id()
    if not cid:
        return _err("chua ket noi Facebook Trang", 409)
    cfg = mcp_store.connection_config(cid)
    an = [str(x) for x in (cfg.get("hidden_pages") or [])]
    if (data or {}).get("hidden", True):
        if pid not in an:
            an.append(pid)
    else:
        an = [x for x in an if x != pid]
    cfg["hidden_pages"] = an
    mcp_store.update_connection(cid, {"config": cfg})
    try:
        import mcp_hub
        mcp_hub.invalidate_cache()
    except Exception:
        pass
    return {"ok": True, "hidden_pages": an}


@router.get("/social/facebook/posts")
async def fb_posts(page_id: str = Query(""), page: str = Query(""),
                   limit: int = Query(10), brain: str = Query("brain")):
    """Bai gan nhat cua 1 Trang kem reactions/comments/shares (fb_page_posts)."""
    args = {"limit": min(max(int(limit), 1), 25)}
    args.update(_page_args(page_id, page))
    if not args.get("page_id") and not args.get("page"):
        return _err("can page_id hoac page")
    out, err = await _call_tool("fb_page_posts", args, brain)
    if err:
        return _err(err)
    return {"ok": True, **(out or {})}


@router.get("/social/facebook/insights")
async def fb_insights(page_id: str = Query(""), page: str = Query(""),
                      period: str = Query("week"), brain: str = Query("brain")):
    """So lieu tong hop Trang: reach/views/follower (fb_page_insights)."""
    args = {"period": period if period in ("day", "week", "days_28") else "week"}
    args.update(_page_args(page_id, page))
    if not args.get("page_id") and not args.get("page"):
        return _err("can page_id hoac page")
    out, err = await _call_tool("fb_page_insights", args, brain)
    if err:
        return _err(err)
    return {"ok": True, **(out or {})}


@router.get("/social/facebook/comments")
async def fb_comments(post_id: str = Query(""), page_id: str = Query(""),
                      page: str = Query(""), limit: int = Query(25),
                      brain: str = Query("brain")):
    """Binh luan cua 1 bai (fb_page_comments - bat buoc post_id)."""
    if not post_id:
        return _err("can post_id")
    args = {"post_id": post_id, "limit": min(max(int(limit), 1), 50)}
    args.update(_page_args(page_id, page))
    out, err = await _call_tool("fb_page_comments", args, brain)
    if err:
        return _err(err)
    return {"ok": True, **(out or {})}
