"""Trợ lý dùng chung: một bản gốc ở system/agents/ cho mọi brain (1.3.39, server/system_agents.py).

    python tests/run.py system_agents      (không mạng, không model)

Hợp đồng cần canh:
- Đủ 9 bản gốc, mỗi bản có `system_shared: true` và `scope` hợp lệ; Joyce Core không lẫn vào.
- Brain phòng thấy Trợ lý Onboarding (scope department), KHÔNG thấy 8 trợ lý hệ thống; brain chung
  (Brain Default) thấy đủ 9.
- Bản trong brain THẮNG bản gốc (phòng sửa riêng được); xoá bản riêng thì quay lại bản gốc.
- Tên cũ `ke-toan-vien-dai-tu` vẫn chạy (workflow `dai-tu-codebase` cũ còn trỏ tên này).
- Workflow và chat với trợ lý đọc được bản gốc khi brain không có file.
- Không xoá bản gốc từ một phòng; lưu ở một phòng tạo bản riêng, bản gốc không đổi.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import hashlib
import os
import pathlib
import tempfile
import sys

os.environ["JOYCE_STATE_DIR"] = tempfile.mkdtemp(prefix="joyce-sysag-")
BR = pathlib.Path(tempfile.mkdtemp(prefix="joyce-brains-sysag-"))
os.environ["BRAINS_DIR"] = str(BR)

import main  # noqa: E402
import system_agents  # noqa: E402

fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)


NINE = {"giam-dinh-bao-mat", "giam-dinh-du-lieu", "giam-dinh-noi-dung", "giam-dinh-ux", "giam-dinh-harness",
        "ky-su-harness", "giam-sat-dai-tu", "lap-ke-hoach-dai-tu", "tro-ly-onboarding"}
ent = {e["slug"]: e for e in system_agents.entries()}
check("đủ 9 bản gốc dùng chung", set(ent) == NINE)
check("Joyce Core không lẫn vào nhóm dùng chung", "joyce-core" not in ent)
check("Trợ lý Onboarding scope department, 8 cái kia scope system",
      ent["tro-ly-onboarding"]["scope"] == "department" and all(ent[s]["scope"] == "system" for s in NINE - {"tro-ly-onboarding"}))
check("tên cũ ke-toan-vien-dai-tu trỏ về lap-ke-hoach-dai-tu", system_agents.resolve("ke-toan-vien-dai-tu") == "lap-ke-hoach-dai-tu")
check("slug lạ không phải trợ lý dùng chung", system_agents.resolve("truong-phong-thu") is None and system_agents.path("../x") is None)
for s in NINE:
    t = ent[s]["path"].read_text(encoding="utf-8")
    check(f"bản gốc {s} không có ký tự gạch dài", "—" not in t)
check("bản gốc Giám định Tương phản là bản đã cải tiến (có bước tự phản bác)", "TỰ PHẢN BÁC" in ent["giam-dinh-harness"]["path"].read_text(encoding="utf-8"))

# ---- danh sách theo brain
chung = main._default_brain_dir()
phong = BR / "Ke Toan - Thu"
(phong / "agents").mkdir(parents=True)
(phong / "agents" / "truong-phong-thu.md").write_text("---\ntype: agent\nname: Trưởng Phòng Thu\nrole: Thu\n---\nBạn là trưởng phòng thu.", encoding="utf-8")
ds_phong = {a["slug"]: a for a in main.agents_index(str(phong), kem_prompt=False)}
ds_chung = {a["slug"]: a for a in main.agents_index(str(chung), kem_prompt=False)}
check("phòng thấy trưởng phòng của mình và Trợ lý Onboarding", {"truong-phong-thu", "tro-ly-onboarding"} <= set(ds_phong))
check("phòng KHÔNG thấy 8 trợ lý hệ thống", not (set(ds_phong) & (NINE - {"tro-ly-onboarding"})))
check("brain chung thấy đủ 9", NINE <= set(ds_chung))
check("trợ lý dùng chung có cờ system_shared", ds_phong["tro-ly-onboarding"].get("system_shared") is True
      and not ds_phong["truong-phong-thu"].get("system_shared"))

# ---- đọc: workflow, chat, model
p = main._agent_path(str(phong), "giam-dinh-harness")
check("phòng đọc được bản gốc trợ lý hệ thống (workflow tu-cai-tien-agent cần)", p == ent["giam-dinh-harness"]["path"])
check("tên cũ đọc được qua _agent_path", main._agent_path(str(phong), "ke-toan-vien-dai-tu") == ent["lap-ke-hoach-dai-tu"]["path"])
check("slug không tồn tại trả đường brain chưa có file", not main._agent_path(str(phong), "khong-co").exists())
_mk, sysprompt, _log, _learn = main._workflow_agent_helpers(str(phong), None)
name, sp, _m, _pv = sysprompt("giam-dinh-harness")
check("bước workflow dựng được prompt từ bản gốc", name == "Giám định Tương phản" and "TỰ PHẢN BÁC" in sp)
name2, sp2, _m2, _pv2 = sysprompt("ke-toan-vien-dai-tu")
check("bước workflow dùng tên cũ vẫn ra trợ lý lập kế hoạch", name2 == "Lập kế hoạch Đại-tu")
check("chat trực tiếp với trợ lý dùng chung dựng được prompt", "Onboarding" in main._agent_chat_prompt(str(phong), "tro-ly-onboarding"))

# ---- HTTP
from fastapi.testclient import TestClient  # noqa: E402
from urllib.parse import quote  # noqa: E402
c = TestClient(main.app, base_url="http://127.0.0.1:8080")
q = quote(str(phong), safe="")
g = c.get(f"/agents/get?slug=tro-ly-onboarding&brain={q}")
check("GET /agents/get mở được trợ lý dùng chung, có cờ", g.status_code == 200 and g.json().get("system_shared") is True and g.json().get("prompt"))
goc_hash = hashlib.sha256(ent["tro-ly-onboarding"]["path"].read_bytes()).hexdigest()
d = c.post("/agents/delete", data={"slug": "tro-ly-onboarding", "brain": str(phong)})
check("không xoá được bản gốc từ một phòng (403)", d.status_code == 403 and d.json().get("code") == "system_shared")
check("bản gốc còn nguyên sau lời xoá", hashlib.sha256(ent["tro-ly-onboarding"]["path"].read_bytes()).hexdigest() == goc_hash)

# ---- phòng sửa riêng: bản riêng thắng, bản gốc không đổi; xoá bản riêng thì về bản gốc
(phong / "agents" / "tro-ly-onboarding.md").write_text("---\ntype: agent\nname: Onboarding Phòng Thu\nrole: riêng\n---\nBản riêng của Phòng Thu.", encoding="utf-8")
ds2 = {a["slug"]: a for a in main.agents_index(str(phong), kem_prompt=False)}
check("bản riêng của phòng thắng bản gốc, không còn cờ dùng chung", ds2["tro-ly-onboarding"]["name"] == "Onboarding Phòng Thu"
      and not ds2["tro-ly-onboarding"].get("system_shared") and sum(1 for a in main.agents_index(str(phong)) if a["slug"] == "tro-ly-onboarding") == 1)
check("bản gốc không bị đổi khi phòng có bản riêng", hashlib.sha256(ent["tro-ly-onboarding"]["path"].read_bytes()).hexdigest() == goc_hash)
d2 = c.post("/agents/delete", data={"slug": "tro-ly-onboarding", "brain": str(phong)})
check("xoá bản riêng của phòng được", d2.status_code == 200)
check("xoá bản riêng xong thì quay lại bản gốc", main._agent_path(str(phong), "tro-ly-onboarding") == ent["tro-ly-onboarding"]["path"])

if fails:
    print("\nTHẤT BẠI %d: %s" % (len(fails), fails))
    sys.exit(1)
print("\nTẤT CẢ OK")
