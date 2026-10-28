"""B03 (gói B): bản kê chứng nhận đường thực thi và ghi dữ liệu là trung thực và không trượt.

    python tests/run.py b03_chung_nhan_route      (không mạng)

Không chứng nhận route nào trong test này. Nó chỉ bảo đảm: bản kê đủ trường, test được viện dẫn có thật, không đường nào tự xưng chứng
nhận khi thiếu căn cứ, và KHÔNG có route HTTP ghi file trực tiếp mới nào mà chưa được phân loại.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import inspect
import os
import re
import sys
import tempfile

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-b03-state-")
import route_cert as RC  # noqa: E402

fails = []


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)
        if detail:
            print("       " + str(detail)[:300])


TRUONG = ("id", "mo_ta", "chu_the", "nguon_quyen", "noi_kiem", "test", "trang_thai", "khoang_ho")
check("mọi dòng đủ trường và trạng thái hợp lệ", all(set(r) == set(TRUONG) and r["trang_thai"] in RC.TRANG_THAI for r in RC.REGISTRY))
check("id không trùng", len({r["id"] for r in RC.REGISTRY}) == len(RC.REGISTRY))
check("mọi đường chưa đủ chứng nhận đều nói rõ khoảng hở", all(r["khoang_ho"].strip() for r in RC.REGISTRY if r["trang_thai"] != "chung_nhan"))
check("test được viện dẫn có thật trên đĩa (không viện dẫn test ma)",
      all((ROOT / t.split(" ")[0]).is_file() for t in (r["test"] for r in RC.REGISTRY) if t), [r["test"] for r in RC.REGISTRY if r["test"] and not (ROOT / r["test"].split(" ")[0]).is_file()])
check("đường không có test thì KHÔNG được ở trạng thái mot_phan hay chung_nhan", all(r["test"] for r in RC.REGISTRY if r["trang_thai"] != "chua_chung_nhan"))
check("đường không có nơi kiểm bắt buộc của Joyce thì phải ghi thẳng điều đó", all("không có chốt" in r["noi_kiem"] for r in RC.REGISTRY if r["id"] == "cli_native"))
check("hiện chưa có đường nào đạt chung_nhan (quyền theo thao tác là việc G2), không tự nâng", RC.tom_tat()["chung_nhan"] == 0, RC.tom_tat())
check("tóm tắt cộng đủ", sum(RC.tom_tat()[k] for k in RC.TRANG_THAI) == RC.tom_tat()["tong"] == len(RC.REGISTRY))

# dò route HTTP ghi file trực tiếp
import main  # noqa: E402
PAT = re.compile(r"\.write_text\(|\.write_bytes\(|open\([^)]*[\"'][wax]b?\+?[\"']|shutil\.(copy|move|rmtree)|os\.(replace|rename|remove|unlink)\(|\.unlink\(|\.rename\(")
thay = set()
for r in main.app.routes:
    if not (getattr(r, "methods", None) or set()) & {"POST", "PUT", "PATCH", "DELETE"}:
        continue
    try:
        src = inspect.getsource(r.endpoint)
    except (OSError, TypeError):
        continue
    if PAT.search(src):
        thay.add(r.path)
moi = sorted(thay - RC.ROUTE_GHI_TRUC_TIEP)
cu = sorted(RC.ROUTE_GHI_TRUC_TIEP - thay)
check("không có route HTTP ghi file trực tiếp nào CHƯA được phân loại (thêm route mới ghi file thì phải khai vào route_cert)", not moi, moi)
check("bản kê không giữ route đã biến mất hay đã hết ghi trực tiếp (xoá khỏi ROUTE_GHI_TRUC_TIEP)", not cu, cu)
check("không route ghi trực tiếp nào tự xưng đã qua file_policy (hiện đúng là chưa)",
      not any("file_policy" in inspect.getsource(r.endpoint) for r in main.app.routes if getattr(r, "path", "") in RC.ROUTE_GHI_TRUC_TIEP))

print()
if fails:
    print(f"FAIL {len(fails)} test: " + ", ".join(fails))
    sys.exit(1)
print("OK - test_b03_chung_nhan_route: tất cả pass")
