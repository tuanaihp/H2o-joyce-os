"""Chính sách GHI FILE của brain: một nơi duy nhất, dùng chung cho hook báo sớm và chốt bắt buộc ở tool ghi.

Sinh ra từ FIX-03 của gói G1 (Joyce Harness, JHA-03, docs/dev/Joyce-harness-phong-ban-ke-hoach.md mục 13).

Hai lỗi của bản trước:
1. Hook `joyce-guard` tự cắt chuỗi đường dẫn, còn `joyce_write_file` giải bằng `Path.resolve()`. Hai bộ giải khác
   nhau nên `sources/x.md` bị chặn mà `wiki/../sources/x.md` (cùng file) lọt.
2. Chốt chỉ nằm ở hook, TRƯỚC khi ghi. Hook lỗi thì tool vẫn chạy (fail-open có chủ ý của plugins_host), và file đổi
   giữa lúc kiểm và lúc ghi thì kiểm vô nghĩa.

Cách sửa: mọi nơi hỏi `deny_reason(vault_root, target)` với `target` là đường dẫn ĐÃ GIẢI (realpath: dot segments,
symlink, junction, chữ hoa/thường thật của hệ tệp). `mcp_hub._write` gọi nó ngay trước khi ghi và ghi `sources/` bằng
tạo-độc-quyền, nên không ai ghi đè được dù file xuất hiện sau lúc kiểm.

Luật:
- `sources/` là tài liệu gốc bất biến: KHÔNG ghi đè file đã có. Tạo file mới vẫn được (skill notes cần).
- `Memory/` viết hoa là thư mục khác với `memory/` trên Linux: ghi vào đó là mất trí nhớ trong im lặng.
- Không xác định được đích thì TỪ CHỐI. Đích nằm ngoài brain không phải việc của chính sách này (hub tự quyết).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

MSG_SOURCES = ("`sources/` là tài liệu gốc bất biến: không ghi đè file đã có. Muốn lưu bản mới thì ghi file tên "
               "khác (thêm ngày hoặc số), muốn sửa kiến thức thì sửa trang trong `wiki/`.")
MSG_MEMORY = ("Thư mục trí nhớ là `memory/` viết thường. `Memory/` là thư mục khác trên Linux, ghi vào đó là mất. "
              "Ghi lại với đường dẫn bắt đầu bằng `memory/`.")
MSG_KHONG_XAC_DINH = "Không xác định được đích ghi một cách an toàn nên từ chối. Dùng đường dẫn tương đối trong brain."


def thuc(p) -> Path:
    """Đường dẫn đã giải hết: dot segments, symlink, junction, chữ hoa/thường thật. Ném khi không giải được."""
    return Path(os.path.realpath(os.fspath(p)))


def _khong_phan_biet_hoa_thuong(thu_muc: Path) -> bool:
    """Hệ tệp tại thư mục này có coi `A` và `a` là một không (Windows, macOS mặc định)."""
    s = str(thu_muc)
    sw = s.swapcase()
    if sw == s:
        return False
    try:
        return os.path.exists(sw) and os.path.samefile(sw, s)
    except OSError:
        return False


def _nam_trong(con: Path, cha: Path, bo_hoa_thuong: bool) -> bool:
    a, b = str(con), str(cha)
    if bo_hoa_thuong:
        a, b = a.casefold(), b.casefold()
    return a == b or a.startswith(b.rstrip("\\/") + os.sep)


def trong_sources(vault_root, target) -> bool:
    """Đích có nằm trong `sources/` của brain không (so trên đường dẫn đã giải, kể cả khác hoa/thường)."""
    try:
        s = thuc(Path(os.fspath(vault_root)) / "sources")
        t = thuc(target)
    except (OSError, ValueError, TypeError):
        return False
    return _nam_trong(t, s, _khong_phan_biet_hoa_thuong(s.parent))


def deny_reason(vault_root, target) -> Optional[str]:
    """Lý do TỪ CHỐI ghi vào `target`, hoặc None nếu được. Không ném: không giải được đích thì từ chối."""
    try:
        v = thuc(vault_root)
        t = thuc(target)
    except (OSError, ValueError, TypeError):
        return MSG_KHONG_XAC_DINH
    try:
        rel = t.relative_to(v)
    except ValueError:
        # Windows/macOS: relative_to đã so không phân biệt hoa thường trên Windows; macOS thì so lại bằng casefold.
        if _khong_phan_biet_hoa_thuong(v.parent) and _nam_trong(t, v, True):
            rel = Path(str(t)[len(str(v)):].lstrip("\\/"))
        else:
            return None            # ngoài brain: hub tự quyết (thư mục làm việc của phiên Coding)
    if not rel.parts:
        return None
    if rel.parts[0] == "Memory":
        return MSG_MEMORY
    if trong_sources(vault_root, t):
        try:
            if t.is_file():
                return MSG_SOURCES
        except OSError:
            return MSG_KHONG_XAC_DINH
    return None
