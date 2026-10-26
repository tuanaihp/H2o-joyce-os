"""Web Pilot - lái Chrome thật qua CDP, pattern Jev Ultrafast (chọn thay vì generate).

Cơ chế: snapshot.js chạy trong trang → bảng phần tử đánh số [1] button "…", [2] textbox "…" →
engine CHỈ CẦN CHỌN số + hành động, không tự viết selector (chống hallucinate). Trước khi
mutate (bấm/gõ/chọn) luôn kiểm guard: element + ngữ cảnh còn y hệt không - trang đã đổi thì
báo stale, KHÔNG retry hành động cũ (chống double-submit/double-click).

Trình duyệt (theo thứ tự ưu tiên):
  1. WEB_PILOT_CDP / attach: nối vào Chrome đang mở với --remote-debugging-port (mặc định 9222)
     → dùng profile thật của người dùng, có sẵn đăng nhập.
  2. Tự launch Chrome/Edge tìm được với --user-data-dir=<state>/profile riêng → đăng nhập 1 lần
     trong cửa sổ đó, phiên sau vẫn còn (profile riêng, không đụng Chrome đang dùng hằng ngày).
  3. Chromium Joyce tải trong STATE_DIR/browsers (máy chủ headless).

Không thêm dependency: dùng httpx + websockets đã có trong requirements.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import websockets

_SNAPSHOT_JS = (Path(__file__).parent / "snapshot.js").read_text(encoding="utf-8")
_OPS = {"click": "CLICK", "fill": "TYPE_TEXT", "select": "SELECT"}
_TEXT_LIMIT = 4000


# ---------------------------------------------------------------------------
# Luồng asyncio nền: giữ 1 event loop sống cả phiên server, mọi tool sync đẩy
# coroutine vào đây. Websocket CDP mở một lần, dùng lại giữa các lượt tool.
# ---------------------------------------------------------------------------
_LOOP = None
_READY = threading.Event()



def _no_window() -> int:
    """Cờ CREATE_NO_WINDOW trên Windows (winproc), 0 nơi khác hoặc khi không nạp được."""
    try:
        import winproc
        return winproc.no_window()
    except Exception:
        return 0


def _loop_thread():
    global _LOOP
    _LOOP = asyncio.new_event_loop()
    asyncio.set_event_loop(_LOOP)
    _READY.set()
    _LOOP.run_forever()


def _run(coro):
    if _LOOP is None:
        t = threading.Thread(target=_loop_thread, daemon=True)
        t.start()
        _READY.wait(5)
    return asyncio.run_coroutine_threadsafe(coro, _LOOP).result(timeout=90)


# ---------------------------------------------------------------------------
# CDP client tối giản qua websocket (theo mô hình browser-harness, không cần gói)
# ---------------------------------------------------------------------------
class _CDP:
    def __init__(self):
        self.ws = None
        self.pending = {}
        self.mid = 0
        self.loop = None

    async def connect(self, ws_url):
        self.loop = asyncio.get_event_loop()
        self.ws = await websockets.connect(ws_url, max_size=50 * 1024 * 1024)
        asyncio.create_task(self._read())

    async def _read(self):
        try:
            async for raw in self.ws:
                m = json.loads(raw)
                f = self.pending.pop(m.get("id"), None)
                if f and not f.done():
                    f.set_result(m)
        except Exception:
            for f in self.pending.values():
                if not f.done():
                    f.set_exception(ConnectionError("Mất kết nối tới trang web"))

    async def call(self, method, **params):
        self.mid += 1
        mid = self.mid
        fut = self.loop.create_future()
        self.pending[mid] = fut
        await self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        r = await asyncio.wait_for(fut, timeout=40)
        if "error" in r:
            raise RuntimeError(f"{method}: {r['error'].get('message')}")
        return r.get("result", {})


_PILOT = {"cdp": None, "page": None, "endpoint": "", "target": "", "proc": None,
          "mode": "", "lock": threading.Lock()}


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _alive(endpoint):
    try:
        return bool(httpx.get(endpoint.rstrip("/") + "/json/version", timeout=2).json().get("Browser"))
    except Exception:
        return False


def _find_running(ctx):
    """Chrome đang mở với remote-debugging - attach được cả profile thật lẫn tab sẵn có."""
    attach = os.environ.get("WEB_PILOT_ATTACH", "")
    urls = []
    if attach.strip():
        urls.append("http://127.0.0.1:9222")
    if os.environ.get("WEB_PILOT_CDP"):
        urls.append(os.environ["WEB_PILOT_CDP"].rstrip("/"))
    for u in urls:
        if _alive(u):
            return u
    return ""


def _chrome_candidates(ctx):
    out = [os.environ.get("WEB_PILOT_CHROME", "")]
    if sys.platform == "win32":
        out += [
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
    else:
        out += ["google-chrome", "chromium", "chromium-browser", "microsoft-edge", "google-chrome-stable"]
        try:
            import optional_tools  # thư mục Chromium Joyce tải (STATE_DIR/browsers)
            bdir = getattr(optional_tools, "BROWSERS_DIR", None)
            if bdir:
                for pat in ("*/chrome-linux*/chrome", "*/chrome-linux*/headless_shell",
                            "*/*/chromium*/chrome", "*/chrome-mac*/**/*.app/Contents/MacOS/*"):
                    out += [str(p) for p in Path(bdir).glob(pat)]
        except Exception:
            pass
    return [c for c in out if c]


def _headless_default():
    # VPS không có DISPLAY → headless; máy cá nhân mặc định HIỆN cửa sổ để người dùng nhìn Joyce làm.
    if os.environ.get("WEB_PILOT_HEADLESS") is not None:
        return os.environ["WEB_PILOT_HEADLESS"] == "1"
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        return True
    return False


def _state_file(ctx):
    return Path(ctx.data_dir) / "pilot-state.json"


def _pilot_endpoint_from_state(ctx):
    """Chrome plugin đã mở ở phiên trước còn sống? Tái dùng - profile khoá một lần,
    không tái dùng thì mở Chrome thứ hai trên cùng profile sẽ exit ngay."""
    try:
        st = json.loads(_state_file(ctx).read_text(encoding="utf-8"))
        ep = str(st.get("endpoint") or "").rstrip("/")
        if ep and _alive(ep):
            return ep
    except Exception:
        pass
    return ""


def _profile_dir(ctx):
    return Path(ctx.data_dir) / "chrome-profile"


def _profile_endpoint(ctx):
    """Chrome plugin mồ côi từ lần chạy trước (mất state file)? Tìm cổng CDP theo
    file .pilot-port ta tự ghi, rồi quét command line chrome.exe cùng user-data-dir -
    Chrome bản mới không ghi DevToolsActivePort nên không trông chờ vào file đó."""
    profile = str(_profile_dir(ctx))
    try:
        port = int((_profile_dir(ctx) / ".pilot-port").read_text(encoding="utf-8").strip())
        ep = f"http://127.0.0.1:{port}"
        if _alive(ep):
            return ep
    except Exception:
        pass
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Select-Object -ExpandProperty CommandLine"],
                capture_output=True, text=True, timeout=15, creationflags=_no_window()).stdout
        else:
            out = subprocess.run(["pgrep", "-af", "chrome"], capture_output=True, text=True, timeout=10,
                                 creationflags=_no_window()).stdout
        for line in out.splitlines():
            if profile.lower() not in line.lower():
                continue
            m = re.search(r"--remote-debugging-port=(\d+)", line)
            if m:
                ep = f"http://127.0.0.1:{m.group(1)}"
                if _alive(ep):
                    return ep
    except Exception:
        pass
    return ""


def _launch(ctx, headless=None):
    exe = None
    for c in _chrome_candidates(ctx):
        if shutil.which(c) or os.path.exists(c):
            exe = c
            break
    if not exe:
        raise RuntimeError(
            "Không tìm thấy Chrome/Edge/Chromium. Cách dùng nhanh nhất: mở Chrome của bạn bằng lệnh "
            '"chrome.exe --remote-debugging-port=9222" rồi đặt WEB_PILOT_ATTACH=1, hoặc đặt '
            "WEB_PILOT_CHROME=<đường dẫn chrome.exe>.")
    port = _free_port()
    profile = _profile_dir(ctx)
    profile.mkdir(parents=True, exist_ok=True)
    args = [
        exe, f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
        "--remote-allow-origins=*", "--no-first-run", "--no-default-browser-check",
        "--disable-session-crashed-bubble", "--window-size=1180,860", "about:blank",
    ]
    if headless if headless is not None else _headless_default():
        args.append("--headless=new")
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=_no_window())
    _PILOT["proc"] = proc
    endpoint = f"http://127.0.0.1:{port}"
    for _ in range(80):
        if _alive(endpoint):
            try:
                _state_file(ctx).write_text(json.dumps({"endpoint": endpoint, "pid": proc.pid}), encoding="utf-8")
                (profile / ".pilot-port").write_text(str(port), encoding="utf-8")
            except Exception:
                pass
            return endpoint
        if proc.poll() is not None:
            # Chrome mới exit ngay = đã bàn giao cho instance cũ cùng profile
            # (chrome mồ côi từ phiên trước). Bám theo cổng nó ghi trong profile.
            ep = _profile_endpoint(ctx)
            if ep:
                return ep
            break
        time.sleep(0.25)
    raise RuntimeError(f"Chrome khởi động không xong (exit={proc.poll()}). Thử chạy tay: {exe}")


async def _page_ws(endpoint):
    targets = httpx.get(endpoint + "/json/list", timeout=5).json()
    page = next((t for t in targets if t.get("type") == "page"), None)
    if not page:
        try:
            page = httpx.put(endpoint + "/json/new?about:blank", timeout=5).json()
        except Exception:
            page = httpx.get(endpoint + "/json/new?about:blank", timeout=5).json()
    return page


async def _ensure(ctx, attach=None, headless=None):
    """Bảo đảm có phiên CDP sống tới 1 tab Chrome. Trả về mô tả chế độ đang chạy."""
    if _PILOT["cdp"]:
        return
    endpoint = _find_running(ctx)
    mode = "attach-chrome-dang-chay"
    if not endpoint:
        endpoint = _pilot_endpoint_from_state(ctx) or _profile_endpoint(ctx)
        mode = "chrome-plugin-tai-dung" if endpoint else ""
    if not endpoint:
        endpoint = _launch(ctx, headless=headless)
        mode = "chrome-plugin" + ("-headless" if (headless if headless is not None else _headless_default()) else "")
    page = await _page_ws(endpoint)
    cdp = _CDP()
    await cdp.connect(page["webSocketDebuggerUrl"])
    await cdp.call("Page.enable")
    await cdp.call("Runtime.enable")
    _PILOT.update(cdp=cdp, endpoint=endpoint, target=page.get("id", ""),
                  mode=mode, page=None)


async def _reconnect():
    """Websocket hỏng (tab đóng/crash): nối lại tới endpoint còn sống, Chrome không bị giết."""
    try:
        await _PILOT["cdp"].ws.close()
    except Exception:
        pass
    _PILOT["cdp"] = None
    ep = _PILOT.get("endpoint")
    if not ep or not _alive(ep):
        return
    page = await _page_ws(ep)
    cdp = _CDP()
    await cdp.connect(page["webSocketDebuggerUrl"])
    await cdp.call("Page.enable")
    await cdp.call("Runtime.enable")
    _PILOT.update(cdp=cdp, target=page.get("id", ""), page=None)


def _reset(ctx=None):
    try:
        if _PILOT["proc"]:
            _PILOT["proc"].terminate()
        elif str(_PILOT.get("mode") or "").startswith("chrome-plugin") and _PILOT.get("endpoint"):
            # Chrome mồ côi được tái dùng qua DevToolsActivePort - không có handle
            # process, đóng cả trình duyệt bằng lệnh CDP Browser.close.
            ver = httpx.get(_PILOT["endpoint"] + "/json/version", timeout=2).json()
            async def _bye():
                try:
                    ws = await websockets.connect(ver["webSocketDebuggerUrl"])
                    await ws.send(json.dumps({"id": 1, "method": "Browser.close"}))
                    await ws.close()
                except Exception:
                    pass
            _run(_bye())
    except Exception:
        pass
    if ctx is not None:
        try:
            _state_file(ctx).unlink(missing_ok=True)
        except Exception:
            pass
    _PILOT.update(cdp=None, page=None, endpoint="", target="", proc=None, mode="")


async def _eval(expr):
    r = await _PILOT["cdp"].call(
        "Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
    if r.get("exceptionDetails"):
        raise RuntimeError("JS trong trang lỗi: " +
                           str(r["exceptionDetails"].get("text", ""))[:200])
    return r.get("result", {}).get("value")


# ---------------------------------------------------------------------------
# Bảng hành động đánh số - port action_space() của Jev: element index + op
# ---------------------------------------------------------------------------
def _action_space(actions):
    elements, indices, targets, controls = [], {}, {}, {}
    for a in actions:
        kind = a["kind"]
        if kind not in _OPS:
            controls[a["id"]] = a
            continue
        node = a["node"]
        if node not in indices:
            index = str(len(elements) + 1)
            indices[node] = index
            el = {k: a[k] for k in ("role", "checked", "selected", "expanded") if k in a}
            el.update(index=index, label=a["label"].split(" → ")[0], ops=[],
                      value=a.get("value") or a.get("current_value", ""), node=node)
            elements.append(el)
        index = indices[node]
        op = _OPS[kind]
        group = targets.setdefault(op, {})
        el = elements[int(index) - 1]
        if op not in el["ops"]:
            el["ops"].append(op)
        target = index
        if kind == "select":
            el.setdefault("options", [])
            target = f"{index}:{len(el['options']) + 1}"
            el["options"].append({"index": target, "label": a["label"], "value": a["value"]})
        group[target] = a
    return elements, targets, controls


async def _observe():
    v = await _eval(_SNAPSHOT_JS)
    if not v:
        raise RuntimeError("Trang chưa sẵn sàng - thử lại sau 1 giây.")
    elements, targets, controls = _action_space(v.get("actions", []))
    v["elements"], v["targets"], v["controls"] = elements, targets, controls
    _PILOT["page"] = v
    return v


def _render(page, note=""):
    out = {"url": page["url"], "title": page["title"],
           "text": (page.get("text") or "")[:_TEXT_LIMIT], "elements": []}
    lines = []
    for el in page["elements"]:
        val = f' · đang="{str(el.get("value") or "")[:50]}"' if el.get("value") else ""
        chk = f' · checked={el["checked"]}' if "checked" in el else ""
        lines.append(f'[{el["index"]}] {el.get("role") or "?"} "{el["label"][:90]}" · ops: {",".join(el["ops"])}{val}{chk}')
        for o in el.get("options", []):
            lines.append(f'    option [{o["index"]}] {o["label"][:90]}')
    out["element_table"] = "\n".join(lines)
    out["controls"] = [c for c in ("scroll_down", "scroll_up", "wait") if c in page["controls"]]
    if page.get("omitted_actions"):
        out["omitted"] = page["omitted_actions"]
    if note:
        out["note"] = note
    return out


# ---------------------------------------------------------------------------
# Guard trước mutation - Jev fresh(): so sánh page_key + guard của đúng node
# ---------------------------------------------------------------------------
async def _fresh(page, action):
    node = action["node"]
    cur = await _eval(
        f'(() => {{ const c=window.__h2oPilot, n=c&&c.nodes.get({json.dumps(node)});'
        f' return c?[c.pageKey(), c.guard(n)]:null; }})()')
    if cur is None:
        return False
    stored = [page.get("page_key"), (page.get("guards") or {}).get(str(node))]
    return cur == stored


async def _act_impl(ctx, args):
    page = _PILOT["page"]
    if not page:
        return {"ok": False, "error": "Chưa có trang nào - gọi web_pilot_open hoặc web_pilot_snapshot trước."}
    op = str(args.get("op") or "").upper()
    element = str(args.get("element") or "").strip()
    text = args.get("text")
    option = str(args.get("option") or "").strip()
    press_enter = bool(args.get("press_enter"))
    seconds = float(args.get("seconds") or 1.2)

    # Điều khiển không gắn element
    if op in ("SCROLL_DOWN", "SCROLL_UP", "WAIT") or (not op and element in ("scroll_down", "scroll_up", "wait")):
        cid = element if element in ("scroll_down", "scroll_up", "wait") else op.lower()
        if cid == "wait":
            await asyncio.sleep(max(0.3, min(seconds, 15)))
        else:
            delta = 560 if cid == "scroll_down" else -560
            await _eval(f"window.scrollBy(0,{delta})")
            await asyncio.sleep(0.4)
        old_marker = page.get("marker")
        new_page = await _observe()
        return {"ok": True, "op": cid.upper(), "page_changed": json.dumps(old_marker) != json.dumps(new_page.get("marker")),
                "snapshot": _render(new_page)}

    if op not in _OPS.values():
        return {"ok": False, "error": f'op phải là CLICK | TYPE_TEXT | SELECT | SCROLL_DOWN | SCROLL_UP | WAIT (nhận "{op}").'}
    if not element:
        return {"ok": False, "error": "Thiếu 'element' = số thứ tự trong bảng ELEMENTS."}

    group = page["targets"].get(op, {})
    action = None
    if op == "SELECT" and option:
        action = group.get(option)
        if action is None:
            return {"ok": False, "error": f"Không có option '{option}'. Dùng đúng mã option như '{element}:1' trong bảng."}
    else:
        action = group.get(element)
    if action is None:
        return {"ok": False, "error": f"Element {element} không hỗ trợ {op} (xem cột ops). Chụp lại snapshot nếu trang vừa đổi."}

    node = action["node"]
    if not await _fresh(page, action):
        new_page = await _observe()
        return {"ok": False, "stale": True,
                "error": "Trang/element đã đổi từ lúc chụp - KHÔNG tự làm lại. Chọn lại từ bảng mới.",
                "snapshot": _render(new_page)}

    if op == "CLICK":
        rect = await _eval(
            f'(() => {{ const n=window.__h2oPilot.nodes.get({json.dumps(node)}); if(!n) return null;'
            f' n.scrollIntoView({{block:"nearest"}}); const r=n.getBoundingClientRect();'
            f' return {{x:r.x+r.width/2, y:r.y+r.height/2}}; }})()')
        if not rect:
            return {"ok": False, "error": "Element biến mất khỏi trang - chụp snapshot lại."}
        cdp = _PILOT["cdp"]
        for t in ("mousePressed", "mouseReleased"):
            await cdp.call("Input.dispatchMouseEvent", type=t,
                           x=rect["x"], y=rect["y"], button="left", clickCount=1)
    elif op == "TYPE_TEXT":
        if text is None:
            return {"ok": False, "error": "TYPE_TEXT cần tham số 'text' - engine tự viết nội dung cần gõ."}
        await _eval(
            f'(() => {{ const n=window.__h2oPilot.nodes.get({json.dumps(node)}); if(!n) return null;'
            f' n.focus();'
            f' if ("select" in n && typeof n.select === "function") n.select();'
            f' else if (n.isContentEditable) document.execCommand("selectAll");'
            f' return true; }})()')
        await _PILOT["cdp"].call("Input.insertText", text=str(text))
        if press_enter:
            # Chuỗi Enter đầy đủ theo kiểu Playwright: keydown -> char("\r") -> keyup,
            # thiếu "char" thì nhiều form không nhận phím submit.
            for t, kw in (("rawKeyDown", {}), ("char", {"text": "\r"}), ("keyUp", {})):
                await _PILOT["cdp"].call(
                    "Input.dispatchKeyEvent", type=t, windowsVirtualKeyCode=13,
                    key="Enter", code="Enter", **kw)
    elif op == "SELECT":
        await _eval(
            f'(() => {{ const n=window.__h2oPilot.nodes.get({json.dumps(node)}); if(!n) return null;'
            f' n.value={json.dumps(action["value"])};'
            f' n.dispatchEvent(new Event("input",{{bubbles:true}}));'
            f' n.dispatchEvent(new Event("change",{{bubbles:true}})); return true; }})()')

    await asyncio.sleep(0.35)
    old_marker = page.get("marker")
    # Trang có thể đang navigate - Runtime.evaluate tạm thời lỗi. Thử lại vài nhịp
    # trước khi kết luận; websocket chết thì nối lại tới endpoint (Chrome vẫn sống).
    new_page, last_err = None, ""
    for _ in range(8):
        try:
            new_page = await _observe()
            break
        except Exception as e:
            last_err = str(e)
            await asyncio.sleep(0.5)
            ws = _PILOT["cdp"] and _PILOT["cdp"].ws
            if not ws or getattr(ws, "closed", False) or getattr(ws, "close_code", None) is not None:
                await _reconnect()
    if new_page is None:
        return {"ok": True, "op": op, "element": element, "page_changed": None,
                "note": f"Hành động đã ghi nhận nhưng đọc lại trang lỗi ({last_err[:120]}) - có thể tab đã đóng/mở tab mới. Gọi web_pilot_snapshot để quan sát lại."}
    return {"ok": True, "op": op, "element": element, "label": action["label"][:80],
            "page_changed": json.dumps(old_marker) != json.dumps(new_page.get("marker")),
            "snapshot": _render(new_page)}


# ---------------------------------------------------------------------------
# Tool handlers (sync -> bg loop)
# ---------------------------------------------------------------------------
def _t_open(args, ctx):
    args = args or {}
    url = str(args.get("url") or "").strip()
    attach = bool(args.get("attach")) or os.environ.get("WEB_PILOT_ATTACH") == "1"
    headless = args.get("headless")
    with _PILOT["lock"]:
        try:
            _run(_ensure(ctx, attach=attach, headless=headless))
        except Exception as e:
            _reset()
            return "ERROR: " + str(e)
        if url:
            try:
                _run(_PILOT["cdp"].call("Page.navigate", url=url))
            except Exception as e:
                _reset()
                return "ERROR: " + str(e)
            # đợi trang nạp tối đa ~12s
            for _ in range(60):
                try:
                    st = _run(_eval("document.readyState"))
                    if st in ("interactive", "complete"):
                        time.sleep(0.4)
                        break
                except Exception:
                    pass
                time.sleep(0.2)
        try:
            page = _run(_observe())
        except Exception as e:
            return "ERROR: Không đọc được trang: " + str(e)
    mode = _PILOT["mode"]
    return json.dumps({**_render(page), "ok": True,
                       "pilot": {"mode": mode},
                       "note": ("Đang dùng Chrome đang mở của bạn (đăng nhập sẵn). " if mode.startswith("attach")
                                else "Đang dùng Chrome profile riêng của plugin - đăng nhập 1 lần trong cửa sổ này thì các phiên sau vẫn còn. ") +
                               "Chọn element + op rồi gọi web_pilot_act."}, ensure_ascii=False)


def _t_snapshot(args, ctx):
    args = args or {}
    with _PILOT["lock"]:
        try:
            _run(_ensure(ctx))
            page = _run(_observe())
        except Exception as e:
            _reset()
            return "ERROR: " + str(e) + " - gọi web_pilot_open trước."
    out = _render(page)
    if args.get("full_text"):
        try:
            out["text"] = str(_run(_eval(
                "(() => document.body ? document.body.innerText.slice(0, 20000) : '')()") or ""))
        except Exception:
            pass
    out["ok"] = True
    return json.dumps(out, ensure_ascii=False)


def _t_act(args, ctx):
    args = args or {}
    with _PILOT["lock"]:
        try:
            _run(_ensure(ctx))
            return json.dumps(_run(_act_impl(ctx, args)), ensure_ascii=False)
        except Exception as e:
            _reset()
            return "ERROR: " + str(e) + " - phiên trình duyệt đã đóng, gọi web_pilot_open để mở lại."


def _t_close(args, ctx):
    with _PILOT["lock"]:
        _reset(ctx)
    return json.dumps({"ok": True, "note": "Đã đóng phiên Web Pilot (Chrome riêng của plugin cũng tắt nếu do nó mở)."})


def _t_status(args, ctx):
    running = _find_running(ctx)
    exe = ""
    for c in _chrome_candidates(ctx):
        if shutil.which(c) or os.path.exists(c):
            exe = c
            break
    return json.dumps({
        "ok": True, "session": bool(_PILOT["cdp"]), "mode": _PILOT["mode"] or "",
        "chrome_found": exe or "(không thấy)",
        "attach_9222": bool(running),
        "headless": _headless_default(),
        "hint": ("Mở Chrome bằng: chrome.exe --remote-debugging-port=9222 để Joyce dùng luôn profile đang đăng nhập."
                 if not running else "Phát hiện Chrome debug tại 127.0.0.1:9222 - gọi web_pilot_open attach=true để lái nó."),
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
def register(ctx):
    ctx.register_tool(
        name="web_pilot_status",
        description=("Trạng thái Web Pilot: có Chrome không, đang attach hay chrome riêng, headless hay không. "
                     "Gọi đầu tiên khi user hỏi lái web hoặc khi các tool pilot khác báo lỗi."),
        handler=_t_status, min_mode="readonly",
        schema={"type": "object", "properties": {}},
    )
    ctx.register_tool(
        name="web_pilot_open",
        description=("Mở trang web trong Chrome: trả về URL + TITLE + TEXT trang + bảng ELEMENTS đánh số "
                     "([n] role \"nhãn\" · ops: CLICK,TYPE_TEXT,SELECT). Tham số: url (để trống = lấy tab hiện tại), "
                     "attach=true nối vào Chrome đang mở với --remote-debugging-port=9222 (dùng sẵn đăng nhập), "
                     "headless=true chạy ẩn. Sau khi có bảng, chọn element → gọi web_pilot_act."),
        handler=_t_open, min_mode="safe",
        schema={"type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL cần mở, bỏ trống = tab đang mở"},
                    "attach": {"type": "boolean", "description": "true = lái Chrome đang mở của user (port 9222)"},
                    "headless": {"type": "boolean", "description": "true = chạy ẩn không cửa sổ"}},
                "required": []},
    )
    ctx.register_tool(
        name="web_pilot_snapshot",
        description=("Chụp lại trang hiện tại: bảng ELEMENTS đánh số mới nhất + text trang. "
                     "Gọi khi trang vừa đổi, trước khi act lần đầu, hoặc khi act báo stale. "
                     "full_text=true để đọc nội dung dài (tối đa 20k ký tự) cho việc đọc số liệu/danh sách."),
        handler=_t_snapshot, min_mode="readonly",
        schema={"type": "object",
                "properties": {"full_text": {"type": "boolean", "description": "Đọc toàn văn bản trang (tối đa 20k)"}},
                "required": []},
    )
    ctx.register_tool(
        name="web_pilot_act",
        description=("Thực hiện 1 hành động trên element đã đánh số: op=CLICK | TYPE_TEXT | SELECT | SCROLL_DOWN | "
                     "SCROLL_UP | WAIT; element=số trong bảng; text=nội dung gõ (TYPE_TEXT, bạn tự viết); "
                     "option='3:2' cho SELECT; press_enter=true gõ xong bấm Enter (search/submit); "
                     "seconds cho WAIT. Trang có guard - nếu báo 'stale' phải snapshot lại rồi chọn lại, không được "
                     "lặp hành động cũ. DONE của bạn không phải bằng chứng: sau khi xong phải tự kiểm kết quả thật "
                     "(URL, text trang, dữ liệu xuất hiện)."),
        handler=_t_act, min_mode="full",
        schema={"type": "object",
                "properties": {
                    "element": {"type": "string", "description": "Số element trong bảng, hoặc scroll_down/scroll_up/wait"},
                    "op": {"type": "string", "description": "CLICK | TYPE_TEXT | SELECT | SCROLL_DOWN | SCROLL_UP | WAIT"},
                    "text": {"type": "string", "description": "Nội dung gõ khi op=TYPE_TEXT"},
                    "option": {"type": "string", "description": "Mã option 'n:m' khi op=SELECT"},
                    "press_enter": {"type": "boolean", "description": "Bấm Enter sau khi gõ (form/search)"},
                    "seconds": {"type": "number", "description": "Số giây chờ khi WAIT (mặc định 1.2)"}},
                "required": []},
    )
    ctx.register_tool(
        name="web_pilot_close",
        description="Đóng phiên Web Pilot + tắt Chrome riêng nếu plugin đã mở. Gọi khi xong việc.",
        handler=_t_close, min_mode="safe",
        schema={"type": "object", "properties": {}},
    )
