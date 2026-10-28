"""Phân loại thay đổi giữa hai bản của một file cấu hình (agent, workflow, loop, skill) theo CÂY YAML.

FIX-01 (1.3.41, JHA-01) đọc YAML thật thay cho dấu vân dòng. A03 (1.3.42) bổ sung PHÂN LOẠI: không chỉ "có đổi quyền
không" mà "thay đổi này thuộc loại nào", để cổng tự áp biết phải chờ chủ hay không.

Năm loại, theo mức nghiêm trọng tăng dần (docs/dev/2026-10-28-joyce-harness-g1-g2-sonnet-plan.md mục A03):

    display_only       chỉ đổi chữ hay metadata mà runtime KHÔNG đưa vào prompt hay dùng để quyết hành vi
    behavior_change    đổi thứ model đọc để hành xử: thân bài, `name`, `role`, `description`, `goal`, lời giao việc của
                       bước workflow, thứ tự hay cấu trúc các bước
    permission_change  đổi khoá quyền, công cụ, model, phạm vi, lịch chạy, cách kiểm (KHOA_QUYEN), kể cả khoá lồng
    unknown            khoá chưa đăng ký ở đâu hết: không biết nó làm gì thì không tự áp
    invalid            không đọc chắc được: YAML lỗi, thiếu dấu đóng, khoá trùng, `id` bước trùng, không phải mapping, quá
                       sâu hoặc quá lớn

Allowlist "chỉ hiển thị" CỐ Ý hẹp và dựa trên nơi runtime dùng trường: `name`/`role` đi vào prompt agent
(`main._agent_sysprompt`), `description` đi vào bộ định tuyến skill (`skill_router`), nên không trường nào trong số đó là
trung tính. Bản FIX-01 coi `name`/`role`/`description`/`goal` là nội dung tự do là SAI so với plan; đã sửa.

Thân bài luôn là hành vi (D3 của plan): không dùng ngưỡng độ dài hay tìm chữ "được phép" để cho qua.

Giữ nguyên các nguyên tắc FIX-01: alias và anchor được giải trước khi so; kiểu dữ liệu được so (`2` khác `"2"`); danh sách
thuần giá trị so như TẬP; phần tử mapping định danh theo `id` rồi `name`, không có thì theo vị trí.

ĐIỀU KIỆN DỪNG: không đọc chắc thì `invalid`, người gọi KHÔNG tự áp. Không bao giờ suy ra "chỉ sửa nội dung".
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

KHONG_DOC_DUOC = "(frontmatter không đọc được)"
TRAN_FRONTMATTER = 64 * 1024     # byte; frontmatter lớn hơn thế không phải cấu hình, không đọc
TRAN_SAU = 24                    # độ sâu tối đa khi đi cây; sâu hơn coi như không đọc chắc được

CLASSES = ("display_only", "behavior_change", "permission_change", "unknown", "invalid")
_MUC = {c: i for i, c in enumerate(CLASSES)}

# Khoá chạm QUYỀN, công cụ, model, phạm vi, lịch chạy hay cách kiểm. Đổi bất kỳ khoá nào ở đây KHÔNG bao giờ tự áp
# (1.3.39 B-12; 1.3.41 thêm các khoá của hệ loop/workflow). `steps` không ở đây vì là vật chứa: ta đi vào trong nó.
KHOA_QUYEN = frozenset({
    "agent", "tools", "allowed_tools", "verify_agent", "max_retries", "mode", "execution_mode",
    "muc_quyen", "enabled", "model", "model_provider", "skills", "harness", "min_mode", "risk",
    "capability", "scope", "system_shared", "delegates", "allowed_effects", "deny", "budget",
    "max_rounds", "max_minutes", "reasoning", "notify", "owner_chat", "interval_min",
    "workspace", "tools_profile", "quiet_hours", "max_runs_per_day", "run_at", "ambient_mcp", "status",
})
# Đổi thứ model ĐỌC để hành xử. Mỗi khoá có lý do runtime dùng nó (xem docstring đầu file).
KHOA_HANH_VI = frozenset({"name", "name_en", "role", "role_en", "description", "description_en", "group", "goal"})
# Chỉ hiển thị hoặc ghi chép: runtime không đưa vào prompt. Giữ HẸP, thêm khi có bằng chứng.
KHOA_HIEN_THI = frozenset({"updated", "created", "icon", "avatar", "pinned", "tags"})
# Tương thích tên cũ (FIX-01 dùng một tập chung "nội dung").
KHOA_NOI_DUNG = KHOA_HANH_VI | KHOA_HIEN_THI | {"type"}
# Trong một bước workflow: lời giao việc và nhãn là hành vi; định danh bước (`id`, `name`) cũng vậy vì quyết nút nào là nút nào.
KHOA_BUOC_HANH_VI = frozenset({"task", "name", "id", "title", "note", "description"})
VAT_CHUA = frozenset({"steps"})


def _tao_loader():
    """Bộ nạp YAML an toàn mà TỪ CHỐI khoá trùng. PyYAML mặc định giữ khoá cuối âm thầm, nên một bản nháp có hai `tools:`
    sẽ có "quyền" khác với thứ người duyệt nhìn thấy ở dòng đầu."""
    import yaml

    class Loader(yaml.SafeLoader):
        pass

    def mapping(loader, node, deep=False):
        thay = set()
        for k, _ in node.value:
            if k.tag == "tag:yaml.org,2002:merge":
                continue
            key = loader.construct_object(k, deep=True)
            if key in thay:
                raise yaml.constructor.ConstructorError(None, None, f"khoá trùng: {key!r}", k.start_mark)
            thay.add(key)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    return Loader


_LOADER = None


def _doc(text: str) -> Tuple[str, Optional[dict], str, str, str]:
    """(trạng thái, frontmatter, thân bài, lỗi, phần đầu thô). Trạng thái: 'co' | 'khong' | 'loi'.

    'khong' chỉ khi file KHÔNG mở bằng `---`. File mở bằng `---` mà thiếu dấu đóng là 'loi' (bản FIX-01 coi nó là 'khong'
    và trả "không đổi", một lỗ thật)."""
    global _LOADER
    t = (text or "").replace("\r\n", "\n")
    if not t.startswith("---"):
        return "khong", None, t, "", ""
    m = re.match(r"^---[ \t]*\n", t)
    if not m:
        return "khong", None, t, "", ""
    end = re.search(r"^---[ \t]*$", t[m.end():], re.M)
    if not end:
        return "loi", None, "", "thiếu dấu đóng frontmatter", ""
    head = t[m.end():m.end() + end.start()]
    body = t[m.end() + end.end():]
    if len(head.encode("utf-8")) > TRAN_FRONTMATTER:
        return "loi", None, "", "frontmatter quá lớn", ""
    try:
        import yaml
        if _LOADER is None:
            _LOADER = _tao_loader()
        d = yaml.load(head, Loader=_LOADER)
    except Exception as e:      # noqa: BLE001 - mọi lỗi đọc đều là "không chắc", không bao giờ là "không đổi"
        return "loi", None, "", f"YAML không đọc được: {type(e).__name__}", ""
    if d is None:
        return "co", {}, body, "", head
    if not isinstance(d, dict):
        return "loi", None, "", "frontmatter không phải mapping", ""
    return "co", d, body, "", head


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


def _neo_dung(head: str) -> set:
    """Khoá `x-...`/`x_...` chỉ để khai báo anchor VÀ anchor đó có được dùng (alias) ở nơi khác trong đầu file."""
    ra = set()
    for m in re.finditer(r"^(x[-_][\w-]*)\s*:\s*&([\w-]+)", head, re.M):
        if re.search(r"\*" + re.escape(m.group(2)) + r"(?![\w-])", head):
            ra.add(m.group(1))
    return ra


def _thu(node: Any, duong: Tuple[str, ...], quyen: dict, hanh_vi: dict, la: dict, hien_thi: dict,
         neo: set, sau: int = 0) -> None:
    """Gom giá trị theo 4 nhóm. `duong` chứa định danh của bước nên tráo hai bước vẫn là thay đổi."""
    if sau > TRAN_SAU:
        raise ValueError("quá sâu")
    if isinstance(node, dict):
        trong_buoc = len(duong) >= 1 and duong[0] == "steps"
        for k, v in node.items():
            ks = str(k)
            p = duong + (ks,)
            if ks in KHOA_QUYEN:
                quyen[p] = _chuan(v)
            elif ks in VAT_CHUA and not duong:
                _thu(v, p, quyen, hanh_vi, la, hien_thi, neo, sau + 1)
            elif trong_buoc:
                (hanh_vi if ks in KHOA_BUOC_HANH_VI else la)[p] = _chuan(v)
            elif not duong and ks in KHOA_HANH_VI:
                hanh_vi[p] = _chuan(v)
            elif not duong and ks in KHOA_HIEN_THI:
                hien_thi[p] = _chuan(v)
            elif not duong and ks == "type":
                la[p] = _chuan(v)
            elif not duong and ks in neo:
                hien_thi[p] = _chuan(v)
            else:
                la[p] = _chuan(v)
    elif isinstance(node, (list, tuple)):
        for i, it in enumerate(node):
            _thu(it, duong + (_dinh_danh(it, i),), quyen, hanh_vi, la, hien_thi, neo, sau + 1)


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


def _khac(a: dict, b: dict, ten_ra: set, ten=None) -> None:
    for p in set(a) | set(b):
        va, vb = a.get(p), b.get(p)
        if p in a and p in b and json.dumps(va, default=str, sort_keys=True) == json.dumps(vb, default=str, sort_keys=True):
            continue
        ten_p = (ten or _ten)(p)
        if isinstance(va, dict) and isinstance(vb, dict):
            _la(va, vb, ten_p, ten_ra)
        else:
            ten_ra.add(ten_p)


def _chuan_than(body: str) -> str:
    """Thân bài về dạng so được: bỏ khoảng trắng cuối dòng và dòng trống đầu/cuối. Không đụng nội dung chữ."""
    return "\n".join(ln.rstrip() for ln in (body or "").split("\n")).strip("\n")


def _buoc_hop_le(d: dict) -> Optional[str]:
    """Lỗi cấu trúc của `steps` (id trùng, không phải danh sách) hoặc None."""
    st = d.get("steps")
    if st is None:
        return None
    if not isinstance(st, list):
        return "`steps` không phải danh sách"
    thay = set()
    for it in st:
        if isinstance(it, dict) and it.get("id") not in (None, ""):
            k = str(it["id"])
            if k in thay:
                return f"id bước trùng: {k}"
            thay.add(k)
    return None


def _khung_buoc(d: dict) -> list:
    """Khung thứ tự các bước: dãy định danh. Đổi dãy này (chèn, bỏ, đổi chỗ) là đổi cấu trúc."""
    st = d.get("steps")
    return [_dinh_danh(it, i) if isinstance(it, dict) and (it.get("id") or it.get("name")) else
            ("agent=" + str(it.get("agent")) if isinstance(it, dict) and it.get("agent") else f"#{i}")
            for i, it in enumerate(st if isinstance(st, list) else [])]


def classify(original: str, draft: str) -> dict:
    """Phân loại thay đổi giữa hai bản.

    Trả {"class": loại nặng nhất, "paths": {loại: [tên khoá/đường dẫn]}, "errors": [lý do invalid]}. `class` là
    `display_only` khi và chỉ khi không có gì khác ngoài `KHOA_HIEN_THI` (và neo anchor đã dùng) đổi, thân bài giống hệt
    và cấu trúc bước giữ nguyên. Hai bản giống hệt là `display_only` với danh sách rỗng."""
    kq = {"class": "display_only", "paths": {c: [] for c in CLASSES}, "errors": []}

    def nang(loai: str, *ten: str) -> None:
        for t in ten:
            if t and t not in kq["paths"][loai]:
                kq["paths"][loai].append(t)
        if _MUC[loai] > _MUC[kq["class"]]:
            kq["class"] = loai

    s1, d1, b1, e1, h1 = _doc(original)
    s2, d2, b2, e2, h2 = _doc(draft)
    for e in (e1, e2):
        if e:
            kq["errors"].append(e)
    if "loi" in (s1, s2):
        nang("invalid", KHONG_DOC_DUOC)
        return kq
    for d in (d1, d2):
        sai = _buoc_hop_le(d or {})
        if sai:
            kq["errors"].append(sai)
    if kq["errors"]:
        nang("invalid", KHONG_DOC_DUOC)
        return kq
    try:
        neo = _neo_dung(h2) | _neo_dung(h1)
        q1, q2, h1d, h2d, l1, l2, v1, v2 = {}, {}, {}, {}, {}, {}, {}, {}
        _thu(d1 or {}, (), q1, h1d, l1, v1, neo)
        _thu(d2 or {}, (), q2, h2d, l2, v2, neo)
        khung_1, khung_2 = _khung_buoc(d1 or {}), _khung_buoc(d2 or {})
    except Exception:      # noqa: BLE001
        nang("invalid", KHONG_DOC_DUOC)
        kq["errors"].append("cấu trúc quá sâu hoặc có vòng alias")
        return kq
    ten_q, ten_h, ten_l, ten_v = set(), set(), set(), set()
    _khac(q1, q2, ten_q)
    _khac(h1d, h2d, ten_h)
    _khac(l1, l2, ten_l, lambda p: "?" + (("steps." if "steps" in p[:-1] else "") + p[-1]))
    _khac(v1, v2, ten_v)
    if ten_q:
        nang("permission_change", *sorted(ten_q))
    if ten_l:
        nang("unknown", *sorted(ten_l))
    if ten_h:
        nang("behavior_change", *sorted(ten_h))
    if khung_1 != khung_2:
        nang("behavior_change", "steps.cau_truc")
    if ten_v:
        nang("display_only", *sorted(ten_v))
    if _chuan_than(b1) != _chuan_than(b2):
        nang("behavior_change", "than_bai")
    return kq


def diff_quyen(original: str, draft: str) -> List[str]:
    """Tên các khoá quyền (hoặc `?khoá chưa biết`) bị đổi; rỗng = không đổi quyền. Bộ chuyển tương thích cho chỗ gọi cũ.

    Trả `[KHONG_DOC_DUOC]` khi không đọc chắc được một trong hai bản. KHÔNG báo thay đổi thân bài hay `role`/`goal`: đó là
    `behavior_change`, dùng `classify` để biết."""
    kq = classify(original, draft)
    if kq["class"] == "invalid":
        return [KHONG_DOC_DUOC]
    return sorted(set(kq["paths"]["permission_change"]) | set(kq["paths"]["unknown"]))
