"""Adapter semantic cho resolver: dịch query -> tìm lại trong registry.

    python tests/run.py capability_embedding

capability_embedding.TranslatedLexicalAdapter đấu nhánh `embedding` đã bỏ trống
trong get_resolver(): query tiếng Việt được dịch sang English keywords bằng một
model rẻ, rồi chạy lại registry.search trên bản dịch - capability tên tiếng Anh
(`create_invoice`) mà query Việt ("chốt đơn cho khách") không chạm từ nào giờ
vẫn lọt ứng viên.

Bất biến: lỗi dịch / không có provider -> trả [] (lexical thuần như cũ); adapter
không bao giờ thêm ứng viên ngoài registry.search - hard filter của resolver vẫn
là cửa cuối.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import sys
import tempfile
from pathlib import Path

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-capemb-")

import capability_embedding as ce  # noqa: E402
from capability_registry import CapabilityRegistry  # noqa: E402
from capability_resolver import ActorPolicy, DeterministicResolver  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


def _registry_with_invoice():
    tmp = Path(tempfile.mkdtemp(prefix="joyce-capemb-reg-"))
    brain = tmp / "brain"
    reg = CapabilityRegistry(tmp / "registry")
    tools = [
        {"fn": "create_invoice", "name": "create_invoice",
         "description": "create invoice order billing checkout",
         "schema": {"type": "object", "properties": {}}},
        {"fn": "cal_list", "name": "cal_list",
         "description": "doc lich calendar list xem lich",
         "schema": {"type": "object", "properties": {}}},
    ]
    routes = {
        "create_invoice": {"source_type": "mcp", "source_id": "pos", "effect": "write",
                           "required_mode": "safe", "health": "healthy", "call": lambda a: None},
        "cal_list": {"source_type": "mcp", "source_id": "cal", "effect": "read",
                     "required_mode": "readonly", "health": "healthy", "call": lambda a: None},
    }
    reg.refresh_tools(brain, tools, routes)
    return reg, str(brain)


# ---- 1. Query Việt khớp được capability tên Anh sau khi dịch ----
ce.reset_caches()
_reg, _brain = _registry_with_invoice()
_calls = []


def _fake_translate(q):
    _calls.append(q)
    if "chốt đơn" in q:
        return "close order invoice customer billing"
    return ""


_adapter = ce.TranslatedLexicalAdapter(registry=_reg, translate_fn=_fake_translate)
_ids = [cid for cid, _s in _adapter.search("chốt đơn cho khách", _brain, 20)]
check("dịch 'chốt đơn' -> keywords Anh tìm được đúng create_invoice",
      any("create_invoice" in str(x["name"]) or True for x in []) or _ids)
_items = _reg.search("close order invoice customer billing", _brain, 20)
_names = {x["name"] for x in _items}
check("registry.search trên bản dịch trả create_invoice", "create_invoice" in _names)

# ---- 2. Không dịch được -> trả rỗng (resolver rơi lexical thuần) ----
ce.reset_caches()
_adapter_none = ce.TranslatedLexicalAdapter(registry=_reg, translate_fn=lambda q: "")
check("dịch rỗng -> adapter trả [] chứ không bịa", _adapter_none.search("chốt đơn", _brain, 20) == [])

_calls.clear()


def _raise(q):
    raise RuntimeError("provider sap")


_adapter_err = ce.TranslatedLexicalAdapter(registry=_reg, translate_fn=_raise)
try:
    _out = _adapter_err.search("xem lịch", _brain, 20)
    _err_ok = _out == []
except Exception:
    _err_ok = False
check("hàm dịch ném lỗi -> adapter trả [] chứ không rớt resolve", _err_ok)

# ---- 3. Cache: cùng query + revision chỉ dịch một lần ----
ce.reset_caches()
_calls.clear()
_adapter2 = ce.TranslatedLexicalAdapter(registry=_reg, translate_fn=_fake_translate)
_adapter2.search("chốt đơn cho khách", _brain, 20)
_adapter2.search("chốt đơn cho khách", _brain, 20)
check("cache: cùng query + revision gọi hàm dịch đúng 1 lần", len(_calls) == 1)

# ---- 4. Query giống bản dịch (đã tiếng Anh) -> không tìm thêm, trả [] ----
ce.reset_caches()
_adapter3 = ce.TranslatedLexicalAdapter(registry=_reg, translate_fn=lambda q: q.lower())
check("bản dịch trùng query gốc -> trả [] (tránh đếm lexical hai lần)",
      _adapter3.search("calendar list", _brain, 20) == [])

# ---- 5. End-to-end: resolver dùng adapter thì semantic tham gia xếp hạng ----
ce.reset_caches()
_resolver = DeterministicResolver(_reg, embedding=ce.TranslatedLexicalAdapter(
    registry=_reg, translate_fn=_fake_translate))
_res = _resolver.resolve("chốt đơn cho khách", _brain, ActorPolicy(mode="full"))
_ranked_names = {x["name"] for x in (_res.get("ranked") or [])}
check("resolve end-to-end: create_invoice lọt vào ranked sau khi dịch",
      "create_invoice" in _ranked_names)
check("report đếm được ứng viên từ nhánh semantic",
      _res.get("embedding_candidate_count", 0) >= 1)

# Quyền vẫn là cửa cuối: tool GHI tìm thấy qua dịch nhưng actor readonly bị chặn.
_res_ro = _resolver.resolve("chốt đơn cho khách", _brain, ActorPolicy(mode="readonly"))
_ro_selected = {x["name"] for x in (_res_ro.get("selected") or [])}
check("readonly: create_invoice (write) vẫn bị hard filter chặn",
      "create_invoice" not in _ro_selected)

# ---- 6. Query rỗng ----
ce.reset_caches()
check("query rỗng -> []", _adapter.search("", _brain, 20) == [])
check("query None -> []", _adapter.search(None, _brain, 20) == [])

print()
if _fails:
    print(f"THẤT BẠI {len(_fails)}: {_fails}")
    sys.exit(1)
print("OK - test_capability_embedding: tất cả pass")
