"""Joyce Harness Standard v1: schema máy đọc và bộ ví dụ tham chiếu phải khớp nhau.

    python tests/run.py joyce_harness_schema      (không mạng, không model)

Hợp đồng cần canh (docs/dev/Joyce-harness.md, docs/dev/joyce-harness/):
- Mọi mục `valid` trong reference.json qua contract.schema.json.
- Mọi mục `invalid` bị schema từ chối; mỗi mục ghi rõ vì sao (luật nào của đặc tả).
- reference.json đúng bằng thứ tao_reference.py sinh ra, để không ai sửa tay lệch khỏi script.
- Tài liệu đặc tả không trỏ tới file không tồn tại.
"""
from _paths import ROOT  # noqa: E402
import json
import re
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

import jsonschema

D = Path(ROOT) / "docs" / "dev" / "joyce-harness"
_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


schema = json.loads((D / "contract.schema.json").read_text(encoding="utf-8"))
jsonschema.Draft202012Validator.check_schema(schema)
check("schema là JSON Schema 2020-12 hợp lệ", True)
v = jsonschema.Draft202012Validator(schema)
ref = json.loads((D / "reference.json").read_text(encoding="utf-8"))

for group, items in ref["valid"].items():
    for k, doc in items.items():
        errs = list(v.iter_errors(doc))
        check(f"ví dụ đúng {group}/{k} qua schema" + (f" ({errs[0].message[:120]})" if errs else ""), not errs)

for b in ref["invalid"]:
    check(f"ví dụ sai '{b['name']}' bị từ chối và có lý do", bool(b.get("why")) and not v.is_valid(b["doc"]))

names = [b["name"] for b in ref["invalid"]]
for must in ("executor-giao-viec", "explorer-ghi-so", "giao-theo-lop", "completed-chua-pass", "completed-tac-dong-chua-ro"):
    check(f"bộ ví dụ sai có ca ranh giới '{must}'", must in names)

no_tools = ref["valid"]["manifests"]["soan-loi-nhan-khong-tool"]
check("có ví dụ agent không tool (grants rỗng) vẫn hợp lệ", no_tools["execution"]["grants"] == [] and v.is_valid(no_tools))

tmp = Path(tempfile.mkdtemp())
try:
    shutil.copy(D / "contract.schema.json", tmp / "contract.schema.json")
    r = subprocess.run([sys.executable, "-W", "ignore", str(D / "tao_reference.py"), str(tmp)], capture_output=True, text=True, encoding="utf-8")
    check("tao_reference.py chạy được: " + (r.stdout.strip() or r.stderr.strip())[:120], r.returncode == 0)
    if r.returncode == 0:
        check("reference.json đúng bằng bản script sinh ra", json.loads((tmp / "reference.json").read_text(encoding="utf-8")) == ref)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

for doc in ("Joyce-harness.md", "Joyce-harness-rollout.md", "Joyce-harness-final-audit.md", "joyce-harness/prompts.md", "joyce-harness/acceptance.md"):
    p = Path(ROOT) / "docs" / "dev" / doc
    check(f"tài liệu {doc} tồn tại", p.is_file())
    if p.is_file():
        text = p.read_text(encoding="utf-8")
        check(f"{doc} không có ký tự gạch dài", "—" not in text)
        for link in re.findall(r"\]\((\./[^)#]+)", text):
            check(f"{doc}: liên kết {link} tồn tại", (p.parent / link).resolve().exists())

if _fails:
    print("\nTHẤT BẠI %d: %s" % (len(_fails), _fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
