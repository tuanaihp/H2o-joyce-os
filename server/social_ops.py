"""Social Ops - endpoint chi doc cho trang Cam nang / tab con FanpageJoyce.

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

from fastapi import APIRouter, Query
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


@router.get("/social/facebook/pages")
async def fb_pages(brain: str = Query("brain")):
    """Danh sach Fanpage + quyen tren tung trang (fb_pages_list tra JSON array)."""
    out, err = await _call_tool("fb_pages_list", {}, brain)
    if err:
        return _err(err)
    if isinstance(out, list):
        return {"ok": True, "pages": out}
    return {"ok": True, **(out or {})}


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
