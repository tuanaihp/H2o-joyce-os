"""FIX-03 (Joyce Harness G1, JHA-03): chốt chặn file dùng CHUNG một bộ giải đường dẫn với đường ghi.

    python tests/run.py fix03_file_guard      (không mạng, không model; chỉ ghi trong vault tạm)

Trước 1.3.41 hook `joyce-guard` tự cắt chuỗi đường dẫn, còn `joyce_write_file` giải đường dẫn bằng
`Path.resolve()`. Hai bộ giải khác nhau nên `sources/x.md` bị chặn mà `wiki/../sources/x.md` (cùng file) lọt.
Và kiểm ở hook là kiểm TRƯỚC, còn ghi thì sau: file đổi giữa hai lúc đó thì chốt vô dụng.

Điều kiện dừng của ticket: không xác định được đích an toàn thì TỪ CHỐI, không đi đường khác.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import asyncio
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-fix03-")

import mcp_hub  # noqa: E402
import plugins_host  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


def bo_nho_moi():
    v = pathlib.Path(tempfile.mkdtemp(prefix="joyce-fix03-vault-"))
    for d in ("sources", "wiki", "memory", "attachments"):
        (v / d).mkdir()
    (v / "sources" / "original.md").write_text("BẢN GỐC", encoding="utf-8")
    (v / "wiki" / "trang.md").write_text("wiki", encoding="utf-8")
    return v


def goi_hub(v, path, content="GHI ĐÈ"):
    """Gọi ĐÚNG tool ghi file của hub (đường ghi thật), không đi qua hook."""
    tools, route = mcp_hub._builtin_tools("full", str(v))
    return asyncio.run(route["joyce_write_file"]["call"]({"path": path, "content": content}))


def goi_qua_hook(v, path, content="GHI ĐÈ"):
    """Đi qua hook thật của plugins_host rồi mới tới hub, như một lời gọi engine."""
    tools, route = mcp_hub._builtin_tools("full", str(v))
    ham = plugins_host.wrap_with_hooks("joyce_write_file", route["joyce_write_file"]["call"], "full", str(v))
    return asyncio.run(ham({"path": path, "content": content}))


def con_nguyen(v):
    return (v / "sources" / "original.md").read_text(encoding="utf-8") == "BẢN GỐC"


# ============================================================
# 1. Mọi biểu diễn cùng một file phải cho cùng kết quả (hub là chốt bắt buộc, hook chỉ là lời báo sớm)
# ============================================================
v = bo_nho_moi()
BIEU_DIEN = {
    "thẳng": "sources/original.md",
    "dot segments": "wiki/../sources/original.md",
    "nhiều dot": "wiki/./../sources/./original.md",
    "dấu ./ đầu": "./sources/original.md",
    "gạch chéo kép": "sources//original.md",
    "gạch ngược": "sources\\original.md",
}
for ten, p in BIEU_DIEN.items():
    kq = goi_hub(v, p)
    check(f"hub chặn ghi đè sources/original.md qua cách viết: {ten}", str(kq).startswith("ERROR") and con_nguyen(v), kq)
kq = goi_hub(v, str(v / "sources" / "original.md"))
check("hub chặn đường dẫn TUYỆT ĐỐI tới file trong sources/", str(kq).startswith("ERROR") and con_nguyen(v), kq)
kq = goi_hub(v, str(v / "wiki" / ".." / "sources" / "original.md"))
check("hub chặn đường dẫn tuyệt đối có dot segments", str(kq).startswith("ERROR") and con_nguyen(v), kq)
kq = goi_hub(v, "wiki/../Memory/facts/a.md")
check("hub chặn Memory/ viết hoa dù đi qua dot segments (trên hệ phân biệt hoa thường)",
      str(kq).startswith("ERROR") or (v / "memory" / "facts" / "a.md").exists(), kq)

# Qua hook thật cũng cho cùng kết quả (lời báo sớm phải khớp chốt thật)
for ten, p in BIEU_DIEN.items():
    kq = goi_qua_hook(v, p)
    check(f"qua hook thật: chặn ({ten})", ("joyce-guard" in str(kq) or str(kq).startswith("ERROR")) and con_nguyen(v), kq)

# ============================================================
# 2. Không chặn oan
# ============================================================
v = bo_nho_moi()
check("ghi file MỚI vào sources/ vẫn được (skill notes cần)", str(goi_hub(v, "sources/2026-10-28-ghi-chu.md", "mới")).startswith("Đã ghi")
      and (v / "sources" / "2026-10-28-ghi-chu.md").read_text(encoding="utf-8") == "mới")
check("ghi file mới vào sources/ qua dot segments vẫn được", str(goi_hub(v, "wiki/../sources/khac.md", "x")).startswith("Đã ghi"))
check("ghi wiki bình thường vẫn được", str(goi_hub(v, "wiki/trang.md", "wiki mới")).startswith("Đã ghi")
      and (v / "wiki" / "trang.md").read_text(encoding="utf-8") == "wiki mới")
check("ghi memory/ viết thường vẫn được", str(goi_hub(v, "memory/facts/a.md", "nhớ")).startswith("Đã ghi"))
check("thư mục tên giống sources nhưng không phải (sources-cu/) không bị chặn", str(goi_hub(v, "sources-cu/a.md", "x")).startswith("Đã ghi"))
check("file tên bắt đầu bằng sources ở gốc (sources.md) không bị chặn", str(goi_hub(v, "sources.md", "x")).startswith("Đã ghi"))

# ============================================================
# 3. Windows/macOS: không phân biệt hoa thường
# ============================================================
if os.name == "nt" or sys.platform == "darwin":
    v = bo_nho_moi()
    kq = goi_hub(v, "Sources/ORIGINAL.md")
    check("hệ không phân biệt hoa thường: Sources/ORIGINAL.md cũng là file gốc, bị chặn", str(kq).startswith("ERROR") and con_nguyen(v), kq)
    kq = goi_hub(v, "WIKI/../SOURCES/original.md")
    check("không phân biệt hoa thường kèm dot segments: bị chặn", str(kq).startswith("ERROR") and con_nguyen(v), kq)
else:
    print("skip hệ phân biệt hoa thường (Linux): ca Windows/macOS không áp")

# ============================================================
# 4. Symlink / junction: đi vòng qua một đường dẫn trỏ vào sources/
# ============================================================
v = bo_nho_moi()
lien_ket_ok = False
try:
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(v / "wiki" / "loi-tat"), str(v / "sources")], capture_output=True, text=True)
        lien_ket_ok = r.returncode == 0
    else:
        os.symlink(v / "sources", v / "wiki" / "loi-tat", target_is_directory=True)
        lien_ket_ok = True
except (OSError, NotImplementedError):
    lien_ket_ok = False
if lien_ket_ok:
    kq = goi_hub(v, "wiki/loi-tat/original.md")
    check("thư mục liên kết (junction/symlink) trỏ vào sources/: ghi đè file gốc bị chặn", str(kq).startswith("ERROR") and con_nguyen(v), kq)
    kq = goi_qua_hook(v, "wiki/loi-tat/original.md")
    check("qua hook thật cũng chặn", con_nguyen(v), kq)
else:
    print("skip junction/symlink: máy này không tạo được liên kết (cần quyền)")
v2 = bo_nho_moi()
fl = None
try:
    os.symlink(v2 / "sources" / "original.md", v2 / "wiki" / "tat.md")
    fl = True
except (OSError, NotImplementedError):
    fl = False
if fl:
    kq = goi_hub(v2, "wiki/tat.md")
    check("file symlink trỏ vào sources/original.md: bị chặn", str(kq).startswith("ERROR") and con_nguyen(v2), kq)
else:
    print("skip file symlink: máy này không tạo được symlink file")

# ============================================================
# 5. File thay đổi GIỮA lúc kiểm và lúc ghi (chốt phải sát thời điểm ghi)
# ============================================================
import file_policy  # noqa: E402

v = bo_nho_moi()
goc = file_policy.deny_reason


def kiem_roi_tao_file(vault_root, target):
    kq = goc(vault_root, target)           # lúc kiểm: file chưa có nên được phép
    tp = pathlib.Path(target)
    if kq is None and tp.name == "dua.md" and not tp.exists():
        tp.write_text("NGƯỜI KHÁC VỪA TẠO", encoding="utf-8")      # ... rồi ai đó tạo nó trước khi ghi
    return kq


file_policy.deny_reason = kiem_roi_tao_file
try:
    kq = goi_hub(v, "sources/dua.md", "GHI ĐÈ LÊN FILE VỪA XUẤT HIỆN")
finally:
    file_policy.deny_reason = goc
check("file xuất hiện trong sources/ SAU lúc kiểm: ghi bằng tạo-độc-quyền nên KHÔNG ghi đè được",
      str(kq).startswith("ERROR") and (v / "sources" / "dua.md").read_text(encoding="utf-8") == "NGƯỜI KHÁC VỪA TẠO", kq)

if fl:
    v = bo_nho_moi()
    (v / "wiki" / "den.md").write_text("bình thường", encoding="utf-8")

    def kiem_roi_doi_thanh_symlink(vault_root, target):
        kq = goc(vault_root, target)       # lúc kiểm: wiki/den.md là file thường
        tp = pathlib.Path(target)
        if kq is None and tp.name == "den.md" and tp.exists() and not tp.is_symlink():
            tp.unlink()
            os.symlink(v / "sources" / "original.md", tp)       # ... rồi bị tráo bằng symlink vào sources/
        return kq

    file_policy.deny_reason = kiem_roi_doi_thanh_symlink
    try:
        kq = goi_hub(v, "wiki/den.md", "GHI ĐÈ QUA SYMLINK MỚI TRÁO")
    finally:
        file_policy.deny_reason = goc
    check("file bị tráo bằng symlink vào sources/ SAU lúc kiểm: bị chặn lúc ghi", str(kq).startswith("ERROR") and con_nguyen(v), kq)

if lien_ket_ok:
    # Cùng cơ chế nhưng bằng thư mục liên kết (chạy được cả khi không có quyền tạo symlink file): lúc kiểm `wiki/d/` là
    # thư mục thường, rồi nó bị thay bằng junction/symlink trỏ vào sources/ ngay trước lúc ghi.
    v = bo_nho_moi()
    (v / "wiki" / "d").mkdir()

    def tao_lien_ket(link, dich):
        if os.name == "nt":
            return subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(dich)], capture_output=True, text=True).returncode == 0
        os.symlink(dich, link, target_is_directory=True)
        return True

    def kiem_roi_doi_thu_muc(vault_root, target):
        kq = goc(vault_root, target)
        tp = pathlib.Path(target)
        if kq is None and tp.parent.name == "d" and tp.parent.is_dir() and not tp.parent.is_symlink() and not tp.exists():
            try:
                tp.parent.rmdir()
                tao_lien_ket(tp.parent, v / "sources")
            except OSError:
                pass
        return kq

    file_policy.deny_reason = kiem_roi_doi_thu_muc
    try:
        kq = goi_hub(v, "wiki/d/original.md", "GHI ĐÈ QUA THƯ MỤC VỪA BỊ TRÁO")
    finally:
        file_policy.deny_reason = goc
    check("thư mục cha bị tráo bằng liên kết vào sources/ SAU lúc kiểm: bị chặn lúc ghi, file gốc nguyên vẹn",
          str(kq).startswith("ERROR") and con_nguyen(v), kq)

# ============================================================
# 6. Điều kiện dừng: không xác định được đích an toàn thì TỪ CHỐI
# ============================================================
v = bo_nho_moi()
kq = goi_hub(v, "../ngoai-vault.md")
check("đường dẫn thoát ra ngoài vault: từ chối (đã có từ trước, giữ nguyên)", str(kq).startswith("ERROR") and not (v.parent / "ngoai-vault.md").exists(), kq)
check("deny_reason không xác định được đích (đối tượng hỏng) thì TỪ CHỐI, không cho qua",
      file_policy.deny_reason(str(v), object()) is not None)
kq = goi_hub(v, "")
check("đường dẫn rỗng hay chỉ tới thư mục: hub trả lỗi nói được, không văng exception", str(kq).startswith("ERROR") and "thư mục" in str(kq), kq)
kq = goi_hub(v, "wiki")
check("đường dẫn là thư mục wiki: cũng trả lỗi nói được", str(kq).startswith("ERROR") and "thư mục" in str(kq), kq)

# ============================================================
# 7. Memory/ viết hoa: cùng một quy tắc, đi qua cùng một hàm
# ============================================================
v = bo_nho_moi()
check("file_policy: Memory/ viết hoa bị từ chối trên hệ phân biệt hoa thường",
      (file_policy.deny_reason(str(v), v / "Memory" / "a.md") is not None) or os.name == "nt" or sys.platform == "darwin")

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
