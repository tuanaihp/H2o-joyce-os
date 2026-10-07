"""Cổng OpenAI-compatible cho app ngoài (H2O Legacy) — gọi qua Joyce thay vì gọi
Ollama trực tiếp.

VÌ SAO cần lớp này (thay vì app gọi thẳng Ollama :11434):
  - Private Network Access: trang HTTPS (vercel.app) gọi http://127.0.0.1 bị
    Chrome bắt preflight PNA; Ollama KHÔNG trả `Access-Control-Allow-Private-Network`,
    Joyce thì trả được — nên đi qua Joyce là đường duy nhất cho bản production HTTPS.
  - Một chỗ quản model: endpoint/model đổi ở UI Joyce (Models tab) là app theo,
    không phải sửa cấu hình trên từng máy.
  - Ollama endpoint lấy từ settings Joyce (`model.ollama_local_endpoint`) — kể
    cả khi Ollama nằm máy khác trong LAN (Joyce trong Docker, Ollama máy nhà).

BẢO MẬT — dùng đúng rào có sẵn của Joyce, không khoan thêm lỗ:
  - Auth: Bearer API token tạo ở dashboard (/auth/tokens, scope 'full').
    `_auth_guard` tự áp cho /h2o/* như mọi route khác; token scope 'chat' KHÔNG
    đủ (TOKEN_SCOPE_CHAT không chứa /h2o) — dùng 'full'. Gate tắt (chưa đặt mật
    khẩu) thì máy local chạy không cần token.
  - CSRF: origin app phải nằm trong allowlist có sẵn — env JOYCE_ALLOWED_HOSTS
    (vd "h2-o-legacy.vercel.app") hoặc settings.domain.custom. Không có thì
    _csrf_guard chặn 403 trước khi tới đây — đúng ý đồ, không bypass.
  - CORS: middleware gốc của app chỉ mở localhost nên /h2o tự xử ACAO + PNA —
    nhưng CHỈ echo origin khi host của nó đã có trong allowed_web_hosts()
    (cùng một allowlist với CSRF — một chỗ khai, hai rào dùng chung).
    Origin lạ → không trả ACAO → browser tự chặn, không cần code thêm.

Namespace /h2o (không đụng route sẵn có của Joyce):
  GET  /h2o/health              → {ok, endpoint, models}
  GET  /h2o/api/tags            → proxy Ollama /api/tags (list model đã cài)
  GET  /h2o/v1/models           → proxy Ollama /v1/models (OpenAI format)
  POST /h2o/v1/chat/completions → proxy Ollama /v1/chat/completions (stream + non-stream)
  POST /h2o/image/generate      → image_gen.generate_chatgpt (gói ChatGPT OAuth,
                                   KHÔNG cần API key) → {images:[dataUrl], errors}

Client (H2O Legacy): provider 'local' trỏ base = http://127.0.0.1:7777/h2o,
kèm header `Authorization: Bearer jvs_...` (token tạo trong Joyce dashboard).
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

import config as cfgmod
import ollama_local
import web_security

router = APIRouter(prefix="/h2o")

# Chat có thể chạy phút trời trên model lớn — chỉ chặn connect, để read vô hạn
# (Ollama tự hủy khi client ngắt; trần read cứng chỉ cắt nhầm generation dài).
_TIMEOUT = httpx.Timeout(None, connect=10.0)


def _ollama() -> tuple[str, str]:
    """(endpoint, key) Ollama như Joyce đang cấu hình — không suy diễn lại."""
    m = cfgmod.read_settings().get("model", {}) or {}
    ep = (m.get("ollama_local_endpoint") or "").strip() or ollama_local.GOI_Y_ENDPOINT
    return ep.rstrip("/"), (m.get("ollama_local_key") or "").strip()


def _auth_headers(key: str) -> dict:
    """Ollama Cloud/remote có key thì gắn Bearer; Ollama local thường không cần."""
    return {"Authorization": f"Bearer {key}"} if key else {}


async def _proxy_get(request: Request, path: str):
    ep, key = _ollama()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as c:
            r = await c.get(f"{ep}{path}", headers=_auth_headers(key))
    except Exception as e:  # noqa: BLE001 — proxy phải trả lỗi thật, không crash
        return JSONResponse({"error": f"không kết nối Ollama {ep}: {e}"}, status_code=502)
    return JSONResponse(r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text},
                        status_code=r.status_code)


@router.get("/health")
async def health():
    """Tình trạng gateway + Ollama phía sau — đủ để app phân biệt 'Joyce sống'
    và 'Ollama sống' (Joyce có thể chạy mà Ollama chưa bật)."""
    ep, key = _ollama()
    try:
        p = await ollama_local.probe(ep, key)
        return {"ok": True, "ollama": True, "endpoint": ep,
                "models": len(p.get("models") or [])}
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "ollama": False, "endpoint": ep,
                             "error": str(e)[:200]}, status_code=502)


@router.get("/api/tags")
async def api_tags(request: Request):
    return await _proxy_get(request, "/api/tags")


@router.get("/v1/models")
async def v1_models(request: Request):
    return await _proxy_get(request, "/v1/models")


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Proxy thẳng OpenAI chat completions → Ollama (hỗ trợ /v1 native).
    stream:true cũng qua được — đọc raw byte stream chuyển tiếp, không parse."""
    ep, key = _ollama()
    body = await request.body()
    headers = {"Content-Type": "application/json", **_auth_headers(key)}
    try:
        client = httpx.AsyncClient(timeout=_TIMEOUT)
        upstream = client.build_request("POST", f"{ep}/v1/chat/completions",
                                        content=body, headers=headers)
        resp = await client.send(upstream, stream=True)
    except Exception as e:  # noqa: BLE001
        await client.aclose()
        return JSONResponse({"error": f"không kết nối Ollama {ep}: {e}"}, status_code=502)

    async def gen():
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(gen(), status_code=resp.status_code,
                             media_type=resp.headers.get("content-type", "application/json"))


@router.post("/image/generate")
async def image_generate(request: Request):
    """Sinh ảnh cho H2O Legacy bảng test — ChatGPT OAuth image_generation
    (gpt-image-2, dùng gói ChatGPT đã đăng nhập ở trang Model — không cần API key).
    Body {prompt, count, aspect_ratio?, quality?} → {images:[dataUrl], errors, provider, model}.
    Mỗi ảnh một lượt image_generation (quality medium, tối đa 5) — lỗi từng cái gom vào errors,
    không fail cả batch."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "body không phải JSON"}, status_code=400)
    prompt = str(body.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"error": "Thiếu prompt"}, status_code=422)
    count = max(1, min(5, int(body.get("count") or 1)))
    import image_gen  # noqa: PLC0415 — import lười, tránh nặng lúc boot

    images: list[str] = []
    errors: list[str] = []
    for _ in range(count):
        try:
            r = await image_gen.generate_chatgpt(
                prompt,
                aspect_ratio=str(body.get("aspect_ratio") or "portrait"),
                quality=str(body.get("quality") or "medium"),
            )
        except Exception as e:  # noqa: BLE001 — lỗi một ảnh không hủy batch
            errors.append(str(e)[:200])
            continue
        if not r.get("ok") or not r.get("abs_path"):
            errors.append(str(r.get("error") or "image_gen không trả ảnh")[:200])
            continue
        try:
            import base64  # noqa: PLC0415
            with open(r["abs_path"], "rb") as f:
                images.append("data:image/png;base64," + base64.b64encode(f.read()).decode())
        except Exception as e:  # noqa: BLE001
            errors.append(f"đọc ảnh sinh ra lỗi: {e}"[:200])
    return JSONResponse({"images": images, "errors": errors,
                         "provider": "joyce-chatgpt", "model": image_gen.IMAGE_MODEL})


# ---------- CORS + Private Network Access riêng cho /h2o ----------

def _origin_cho_phep(origin: str) -> bool:
    """Origin có trong allowlist (localhost luôn có + JOYCE_ALLOWED_HOSTS/custom domain)."""
    if not origin:
        return False
    return web_security.host_only(origin) in web_security.allowed_web_hosts()


def _cors_headers(origin: str) -> dict:
    return {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
        # Chrome Private Network Access: bắt buộc cho trang HTTPS → http://127.0.0.1.
        "Access-Control-Allow-Private-Network": "true",
    }


async def cors_mw(request: Request, call_next):
    """Middleware ngoài cùng CHỈ cho /h2o/* — đăng ký sau cùng để chạy TRƯỚC
    CORSMiddleware (vốn chỉ mở localhost) và trước cả _auth/_csrf guard
    (OPTIONS preflight không mang token/cookie → phải trả lời sớm)."""
    if not (request.scope.get("path") or "").startswith("/h2o"):
        return await call_next(request)
    origin = request.headers.get("origin") or ""
    ok = _origin_cho_phep(origin)
    if request.method == "OPTIONS":
        if not ok:
            return Response(status_code=403)
        return Response(status_code=204, headers={
            **_cors_headers(origin),
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400",
        })
    resp = await call_next(request)
    if ok:
        for k, v in _cors_headers(origin).items():
            resp.headers[k] = v
    return resp


def setup(app):
    """Gắn gateway vào app Joyce — gọi SAU khi các middleware core đã đăng ký
    (middleware thêm cuối chạy ngoài cùng → OPTIONS /h2o được xử lý trước
    CORSMiddleware/csrf/auth; request thường vẫn đi qua đủ các rào)."""
    app.middleware("http")(cors_mw)
    app.include_router(router)
