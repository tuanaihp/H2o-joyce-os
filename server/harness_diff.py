"""So sánh QUYỀN giữa hai bản của một file cấu hình (agent, workflow, loop, skill) theo CÂY YAML.

Sinh ra từ FIX-01 của gói G1 (Joyce Harness, JHA-01, docs/dev/Joyce-harness-phong-ban-ke-hoach.md mục 13).

Bản trước (1.3.39) lọc các dòng `key: value` rồi SẮP XẾP, nên hai lỗi cùng một gốc: khoá lồng nhau
(`harness.budgets.max_tokens`) không thấy, và tráo `tools` giữa hai bước workflow ra cùng tập dòng
đã sắp xếp. Bản này đọc YAML thật rồi so từng đường dẫn:

- Khoá nằm trong `KHOA_QUYEN` được so NGUYÊN giá trị (cả cây con), ở mọi độ sâu, kể cả bên trong
  `steps`. Phần tử danh sách là mapping thì định danh theo `id`, rồi `name`, không có thì theo vị trí,
  nên tráo giữa hai nút vẫn là một thay đổi.
- Alias và anchor được giải TRƯỚC khi so (thêm quyền bằng `tools: *t` vẫn bị thấy; viết lại bằng alias
  mà cùng giá trị thì không phải thay đổi).
- Kiểu dữ liệu được so: `2` khác `"2"`, `false` khác `"false"`.
- Danh sách thuần giá trị so như TẬP: đổi thứ tự `tools: [a, b]` không phải đổi quyền.
- Khoá ở cấp ngoài (và trong từng bước) KHÔNG thuộc nhóm quyền cũng KHÔNG thuộc nhóm nội dung đã biết
  (trừ khoá `x-...` chỉ để khai báo anchor) mà bị thêm, bỏ hay sửa thì tính là "khoá chưa biết" (`?tên`): một khoá quyền mới chưa kịp đăng ký
  ở đây không được trượt qua như một lần sửa nội dung thuần.

ĐIỀU KIỆN DỪNG: không đọc chắc được cấu hình (YAML lỗi, không phải mapping, quá lớn, thiếu PyYAML) thì
trả `[KHONG_DOC_DUOC]`, người gọi KHÔNG được tự áp. Không bao giờ suy ra "chỉ sửa nội dung".
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

KHONG_DOC_DUOC = "(frontmatter không đọc được)"
TRAN_FRONTMATTER = 64 * 1024     # byte; frontmatter lớn hơn thế không phải cấu hình, không đọc
TRAN_SAU = 24                    # độ sâu tối đa khi đi cây; sâu hơn coi như không đọc chắc được

# Khoá chạm QUYỀN, công cụ, model, phạm vi, lịch chạy hay cách kiểm. Đổi bất kỳ khoá nào ở đây KHÔNG bao giờ
# tự áp (1.3.39 B-12). 1.3.41 thêm các khoá của hệ loop/workflow mà bản cũ bỏ sót: workspace (phạm vi file),
# tools_profile, quiet_hours, max_runs_per_day, run_at, ambient_mcp, status (workflow bật/tắt), steps không ở đây
# vì là vật chứa: ta đi vào trong nó.
KHOA_QUYEN = frozenset({
    "agent", "tools", "allowed_tools", "verify_agent", "max_retries", "mode", "execution_mode",
    "muc_quyen", "enabled", "model", "model_provider", "skills", "harness", "min_mode", "risk",
    "capability", "scope", "system_shared", "delegates", "allowed_effects", "deny", "budget",
    "max_rounds", "max_minutes", "reasoning", "notify", "owner_chat", "interval_min",
    "workspace", "tools_profile", "quiet_hours", "max_runs_per_day", "run_at", "ambient_mcp", "status",
})

# Khoá chỉ là chữ hiện ra hoặc ghi chú, sửa tự do. `type` ở đây vì người gọi kiểm riêng rằng nó không đổi.
KHOA_NOI_DUNG = frozenset({
    "type", "name", "name_en", "description", "description_en", "role", "role_en", "group", "tags", "icon",
    "pinned", "avatar", "updated", "created", "goal",
})
# Trong một bước workflow: lời giao việc là nội dung; mọi khoá khác ngoài KHOA_QUYEN là chưa biết.
KHOA_BUOC_NOI_DUNG = frozenset({"task", "name", "id", "title", "note", "description"})
VAT_CHUA = frozenset({"steps"})


def _doc_frontmatter(text: str) -> Tuple[str, Optional[dict]]:
    """('co', dict) | ('khong', None) khi file không có frontmatter | ('loi', None) khi không đọc chắc được."""
    t = (text or "").replace("\r\n", "\n")
    if not t.startswith("---"):
        return "khong", None
    m = re.match(r"^---[ \t]*\n", t)
    if not m:
        return "khong", None
    end = re.search(r"^---[ \t]*$", t[m.end():], re.M)
    if not end:
        return "khong", None
    head = t[m.end():m.end() + end.start()]
    if len(head.encode("utf-8")) > TRAN_FRONTMATTER:
        return "loi", None
    try:
        import yaml
        try:
            from yaml import CSafeLoader as loader
        except ImportError:
            loader = yaml.SafeLoader
        d = yaml.load(head, Loader=loader)
    except Exception:      # noqa: BLE001 - mọi lỗi đọc đều là "không chắc", không bao giờ là "không đổi"
        return "loi", None
    if d is None:
        return "co", {}
    if not isinstance(d, dict):
        return "loi", None
    return "co", d


def _chuan(v: Any, sau: int = 0) -> Any:
    """Giá trị về dạng so được: danh sách thuần giá trị thành TẬP có thứ tự ổn định, giữ nguyên kiểu."""
    if sau > TRAN_SAU:
        raise ValueError("quá sâu")
    if isinstance(v, dict):
        return {str(k): _chuan(x, sau + 1) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        if all(not isinstance(x, (dict, list, tuple)) for x in v):
            return sorted((x for x in v), key=lambda x: (type(x).__name__, json.dumps(x, default=str, ensure_ascii=False)))
        return [_chuan(x, sau + 1) for x in v]
    return v


def _dinh_danh(item: Any, i: int) -> str:
    if isinstance(item, dict):
        for k in ("id", "name"):
            if item.get(k) not in (None, ""):
                return f"{k}={item[k]}"
    return f"#{i}"


def _thu_quyen(node: Any, duong: Tuple[str, ...], ra: Dict[Tuple[str, ...], Any], sau: int = 0) -> None:
    """Gom {đường dẫn: giá trị đã chuẩn} cho mọi khoá quyền và mọi khoá chưa biết. Đường dẫn chứa định danh."""
    if sau > TRAN_SAU:
        raise ValueError("quá sâu")
    if isinstance(node, dict):
        for k, v in node.items():
            ks = str(k)
            if ks in KHOA_QUYEN:
                ra[duong + (ks,)] = _chuan(v)
            elif ks in VAT_CHUA:
                _thu_quyen(v, duong + (ks,), ra, sau + 1)
            else:
                benh = KHOA_NOI_DUNG if not duong else KHOA_BUOC_NOI_DUNG
                # `x-...` là chỗ khai báo anchor YAML (quy ước mở rộng): tự nó không có tác dụng, quyền thật chỉ
                # hiện ở khoá thật SAU khi alias được giải, và ta so các khoá thật đó.
                if ks not in benh and not ks.startswith(("x-", "x_")):
                    ra[duong + ("?" + ks,)] = _chuan(v)
    elif isinstance(node, (list, tuple)):
        for i, it in enumerate(node):
            _thu_quyen(it, duong + (_dinh_danh(it, i),), ra, sau + 1)


def _ten(duong: Tuple[str, ...]) -> str:
    """Tên hiện cho người đọc: bỏ phần định danh của bước, giữ khoá cuối (`tools`, `?can_write`)."""
    cuoi = [p for p in duong if p == "steps" or not re.match(r"^(#\d+|id=|name=)", p)]
    k = cuoi[-1] if cuoi else ""
    if k.startswith("?"):
        return "?" + ("steps." if "steps" in cuoi[:-1] else "") + k[1:]
    return k


def _la(a: Any, b: Any, goc: str, ra: set) -> None:
    """Liệt kê CÁC LÁ khác nhau trong cây con quyền (cho `harness.budgets.max_tokens`)."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b or a[k] != b[k] or type(a.get(k)) is not type(b.get(k)):
                _la(a.get(k), b.get(k), f"{goc}.{k}", ra)
        return
    ra.add(goc)


def diff_quyen(original: str, draft: str) -> List[str]:
    """Tên các khoá quyền (hoặc `?khoá chưa biết`) bị đổi giữa hai bản; rỗng = chỉ đổi nội dung.

    Trả `[KHONG_DOC_DUOC]` khi không đọc chắc được một trong hai bản: người gọi coi đó là CẦN CHỦ XEM."""
    t1, d1 = _doc_frontmatter(original)
    t2, d2 = _doc_frontmatter(draft)
    if "loi" in (t1, t2):
        return [KHONG_DOC_DUOC]
    if t1 == "khong" and t2 == "khong":
        return []
    try:
        a: Dict[Tuple[str, ...], Any] = {}
        b: Dict[Tuple[str, ...], Any] = {}
        _thu_quyen(d1 or {}, (), a)
        _thu_quyen(d2 or {}, (), b)
    except Exception:      # noqa: BLE001
        return [KHONG_DOC_DUOC]
    doi: set = set()
    for p in set(a) | set(b):
        va, vb = a.get(p), b.get(p)
        if p in a and p in b and va == vb and json.dumps(va, default=str, sort_keys=True) == json.dumps(vb, default=str, sort_keys=True):
            continue
        ten = _ten(p)
        if isinstance(va, dict) and isinstance(vb, dict):
            _la(va, vb, ten, doi)
        else:
            doi.add(ten)
    return sorted(doi)
