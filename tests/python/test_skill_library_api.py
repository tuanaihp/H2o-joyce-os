"""Kiem ke thu vien skill qua HTTP: chay tren brains tam + state tam, khong cham du lieu that."""
from _paths import ROOT, SERVER  # noqa: E402,F401

import os
import tempfile
from pathlib import Path

_STATE = tempfile.TemporaryDirectory(prefix="joyce-slib-api-state-", ignore_cleanup_errors=True)
os.environ["JOYCE_STATE_DIR"] = _STATE.name
os.environ.pop("JOYCE_REQUIRE_LOGIN", None)

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

fails = []


def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (f" [{extra}]" if extra and not cond else ""))
    if not cond:
        fails.append(name)


work = tempfile.TemporaryDirectory(prefix="joyce-slib-api-", ignore_cleanup_errors=True)
brains = Path(work.name) / "brains"
for n in ("Marketing - Makeup", "Ban Hang"):
    d = brains / n / "skills" / "chao-khach"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: Chao khach\ndescription: Chao khach moi\n---\nBuoc 1\n", encoding="utf-8")
main.BRAINS_DIR = str(brains)          # route doc BRAINS_DIR luc goi, nen tro sang cay tam

c = TestClient(main.app, base_url="http://127.0.0.1:8080")
r = c.get("/skill-library/audit")
check("no report yet gives a clean empty answer", r.status_code == 200 and r.json() == {"ok": True, "report": None}, r.text[:120])
r = c.post("/skill-library/audit/run")
j = r.json()
check("run returns the report", r.status_code == 200 and j["report"]["summary"]["brains"] == 2 and j["report"]["summary"]["distinct_slugs"] == 1, r.text[:200])
check("two identical copies are one skill, not diverged", j["report"]["skills"][0]["copies"] == 2 and not j["report"]["skills"][0]["diverged"])
r = c.get("/skill-library/audit")
check("the report is stored and served back", r.json()["report"]["summary"]["files"] == 2 and (Path(_STATE.name) / "skill-library" / "audit" / "latest.json").is_file())
check("running the audit left the brains untouched", sorted(p.name for p in (brains / "Ban Hang" / "skills" / "chao-khach").iterdir()) == ["SKILL.md"])
check("staff are blocked from the library admin routes", "/skill-library" in main._STAFF_DENY)

if fails:
    raise SystemExit(f"{len(fails)} checks failed: {', '.join(fails)}")
print("ALL OK")
