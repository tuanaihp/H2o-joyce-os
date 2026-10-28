"""Trợ lý hệ thống DÙNG CHUNG: một bản gốc trong `system/agents/`, mọi brain đọc chung.

Vì sao có module này (1.3.39, chuẩn Joyce Harness mục 16 và audit `docs/dev/Joyce-hardness.md`):
trước đây 9 trợ lý giống nhau (5 giám định, kỹ sư cải tiến, hai trợ lý đại tu, trợ lý onboarding)
được CHÉP vào `agents/` của cả 61 brain, thành 549 file độc lập mà app không quản. Sửa một bản thì
60 bản kia không đổi theo; bản tốt hơn của Giám định Tương phản chỉ nằm ở Brain Default.

Luật đọc, giống skill hệ thống:
- Brain có file `agents/<slug>.md` của chính nó thì bản của brain THẮNG (phòng tự sửa riêng).
- Không có thì đọc bản gốc ở đây. Slug cũ đổi tên được giữ qua `aliases`.
- Module này CHỈ ĐỌC. Mọi đường ghi (lưu ở trang Cộng sự, đổi mức suy luận, tài liệu của trợ lý)
  vẫn ghi vào brain, tức là tạo bản riêng của phòng đó; bản gốc chỉ đổi qua bản phát hành.

`scope` trong frontmatter quyết định trợ lý hiện ở đâu trong danh sách:
- `department`: việc thật của mọi phòng (Trợ lý Onboarding), hiện ở MỌI brain, đọc dữ liệu của
  đúng brain đang dùng nó.
- `system`: bộ máy cải tiến và đại tu, chỉ hiện ở brain chung (Brain Default). Ở các phòng khác vẫn
  gọi được (workflow `tu-cai-tien-agent`, `review-da-mien`, `dai-tu-codebase`), chỉ không chiếm
  danh sách trợ lý nghiệp vụ.
"""
from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Dict, List, Optional

import fastyaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_AGENTS_DIR = PROJECT_ROOT / "system" / "agents"
# Joyce Core cũng sống trong thư mục này nhưng là trợ lý nền tảng riêng (joyce_core.py), không
# thuộc nhóm dùng chung.
_LOAI_TRU = {"joyce-core"}
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SCOPES = ("department", "system")

_lock = threading.Lock()
_cache: Dict[str, object] = {"sig": None, "by_slug": {}, "alias": {}}


def _sig() -> tuple:
    try:
        return tuple(sorted((p.name, p.stat().st_mtime_ns) for p in SYSTEM_AGENTS_DIR.glob("*.md")))
    except OSError:
        return ()


def _nap() -> None:
    sig = _sig()
    if _cache["sig"] == sig:
        return
    by_slug: Dict[str, dict] = {}
    alias: Dict[str, str] = {}
    for p in sorted(SYSTEM_AGENTS_DIR.glob("*.md")):
        slug = p.stem
        if slug in _LOAI_TRU or not _SLUG_RE.match(slug):
            continue
        try:
            parts = fastyaml.split_frontmatter(p.read_text(encoding="utf-8"))
            meta = fastyaml.safe_load(parts[0]) if parts else {}
        except Exception:  # noqa: BLE001 - một file hỏng không làm mất các trợ lý khác
            meta = {}
        if not isinstance(meta, dict) or not meta.get("system_shared"):
            continue
        scope = meta.get("scope") if meta.get("scope") in SCOPES else "system"
        by_slug[slug] = {"slug": slug, "path": p, "scope": scope, "name": str(meta.get("name") or slug)}
        for a in meta.get("aliases") or []:
            a = str(a or "").strip()
            if _SLUG_RE.match(a) and a not in by_slug:
                alias[a] = slug
    _cache.update(sig=sig, by_slug=by_slug, alias=alias)


def resolve(slug: str) -> Optional[str]:
    """Slug chuẩn của một trợ lý dùng chung (theo cả tên cũ), hoặc None."""
    with _lock:
        _nap()
        s = str(slug or "").strip()
        if s in _cache["by_slug"]:
            return s
        return _cache["alias"].get(s)


def path(slug: str) -> Optional[Path]:
    """File bản gốc, hoặc None nếu slug không phải trợ lý dùng chung."""
    s = resolve(slug)
    if not s:
        return None
    with _lock:
        return _cache["by_slug"][s]["path"]


def is_shared(slug: str) -> bool:
    return resolve(slug) is not None


def entries() -> List[dict]:
    """Mọi trợ lý dùng chung: [{slug, path, scope, name}], theo tên file."""
    with _lock:
        _nap()
        return [dict(v) for _, v in sorted(_cache["by_slug"].items())]


def aliases() -> Dict[str, str]:
    """Bản đồ tên cũ -> slug chuẩn (vd `ke-toan-vien-dai-tu` -> `lap-ke-hoach-dai-tu`)."""
    with _lock:
        _nap()
        return dict(_cache["alias"])


def visible_in(scope: str, is_shared_brain: bool) -> bool:
    """Trợ lý có `scope` này có hiện trong danh sách của brain không."""
    return scope == "department" or (scope == "system" and is_shared_brain)
