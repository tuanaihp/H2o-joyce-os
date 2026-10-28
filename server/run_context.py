"""Ngữ cảnh lượt chạy do HOST dựng và một quyết định quyền chung (G2, Joyce Harness; nền của B01 "host sinh execution context").

Vì sao có: tool ở tầng dưới (ví dụ ghi file qua MCP Hub) cho tới nay không biết nó đang chạy cho AGENT nào, nên không thể kiểm `allowed_effects`
agent đã khai. Host đặt ngữ cảnh này ở ba cửa đã ghi sổ lượt chạy (bot khách, việc giao cho trợ lý, bước workflow); tool đọc nó, không phải
đọc lời agent. `contextvars` đi theo task asyncio và thread do `asyncio.to_thread`, nên cùng một lượt thấy cùng một ngữ cảnh.

Quyết định (`cho_phep`) cố ý THẬN TRỌNG VỀ TƯƠNG THÍCH và nói thật về phạm vi:
- Không có ngữ cảnh (route chưa nối): cho phép, lý do `khong_ngu_canh`. Route đó chưa được chứng nhận (xem route_cert).
- Agent KHÔNG khai `allowed_effects`: cho phép, lý do `chua_khai_bao`. Phần lớn agent hiện ở trường hợp này; đó là khoảng hở, không phải xanh.
- Agent có khai `allowed_effects`: effect của thao tác phải nằm trong danh sách, ngược lại CHẶN. Danh sách rỗng nghĩa là chỉ tính toán.
- Effect lạ hoặc không rõ: CHẶN khi agent đã khai (không biết thì không cho), cho phép khi agent chưa khai.
Tập effect theo contract.schema.json: read, internal_write, business_write, external_write, financial_write, policy_write, destructive.
"""
from __future__ import annotations

import contextvars
import re
from dataclasses import dataclass
from typing import Optional, Tuple

EFFECTS = ("read", "internal_write", "business_write", "external_write", "financial_write", "policy_write", "destructive")

_CTX: contextvars.ContextVar = contextvars.ContextVar("joyce_run_context", default=None)


@dataclass(frozen=True)
class RunContext:
    run_id: str
    agent_id: str
    brain_id: str
    entrypoint: str
    # None = agent không khai (tương thích); tuple (kể cả rỗng) = đã khai
    allowed_effects: Optional[Tuple[str, ...]] = None


def hien_tai() -> Optional[RunContext]:
    return _CTX.get()


def dat(ctx: Optional[RunContext]):
    """Đặt ngữ cảnh cho lượt hiện tại. Trả token để `go` về giá trị trước."""
    return _CTX.set(ctx)


def go(token) -> None:
    try:
        _CTX.reset(token)
    except (ValueError, LookupError):
        pass       # token từ context khác: không làm hỏng lượt vì dọn dẹp


def doc_allowed_effects(agent_text: str) -> Optional[Tuple[str, ...]]:
    """Đọc `allowed_effects` từ đầu file agent. None nếu không khai hoặc đọc không chắc (khi đó không áp quyền, và đó là khoảng hở đã nêu)."""
    try:
        m = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", agent_text or "", re.S)
        if not m:
            return None
        import fastyaml
        d = fastyaml.safe_load(m.group(1))
        if not isinstance(d, dict) or "allowed_effects" not in d:
            return None
        v = d["allowed_effects"]
        if v is None:
            return ()
        if isinstance(v, str):
            v = [v]
        if not isinstance(v, (list, tuple)):
            return None
        return tuple(str(x) for x in v)
    except Exception:  # noqa: BLE001
        return None


def cho_phep(effect: str, ctx: Optional[RunContext] = None) -> Tuple[bool, str]:
    """(được phép, lý do). `effect` là một giá trị của EFFECTS. Xem docstring module về phạm vi."""
    c = ctx if ctx is not None else hien_tai()
    if c is None:
        return True, "khong_ngu_canh"
    if c.allowed_effects is None:
        return True, "chua_khai_bao"
    if effect not in EFFECTS:
        return False, f"effect_la:{str(effect)[:30]}"
    if effect in c.allowed_effects:
        return True, "trong_grant"
    return False, "ngoai_grant"
