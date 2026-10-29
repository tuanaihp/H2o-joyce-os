"""Skill Learn Update qua HTTP that: them nguon -> quet -> AI (model gia) ghi chu -> duyet hang loat -> cai.

Chay trong thu muc tam voi brain tam, KHONG cham state hay brain that cua may."""
from _paths import ROOT, SERVER  # noqa: E402,F401

import json
import os
import tempfile
import time
from pathlib import Path

_STATE = tempfile.TemporaryDirectory(prefix="joyce-sl-api-state-", ignore_cleanup_errors=True)
os.environ["JOYCE_STATE_DIR"] = _STATE.name
os.environ.pop("JOYCE_REQUIRE_LOGIN", None)

import main  # noqa: E402
import skill_learn  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

fails = []


def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (f" [{extra}]" if extra and not cond else ""))
    if not cond:
        fails.append(name)


work = tempfile.TemporaryDirectory(prefix="joyce-sl-api-", ignore_cleanup_errors=True)
repo, brain = Path(work.name) / "repo", Path(work.name) / "brain"
brain.mkdir()
(repo / "skills" / "viet-email").mkdir(parents=True)
(repo / "skills" / "viet-email" / "SKILL.md").write_text("---\nname: Write email\ndescription: Draft emails in brand voice\n---\nSteps.\n", encoding="utf-8")
(repo / "plugins" / "gia-ca").mkdir(parents=True)
(repo / "plugins" / "gia-ca" / "plugin.yaml").write_text("name: Price tool\nslug: gia-ca\nenabled: true\nmin_mode: readonly\ntools:\n  - gia_ca\n", encoding="utf-8")
(repo / "plugins" / "gia-ca" / "plugin.py").write_text("def register(ctx):\n    pass\n", encoding="utf-8")

seen = {}


async def fake_ask(prompt, routing_model):
    seen["routing_model"] = routing_model
    import re
    ids = re.findall(r"### ITEM id=(\w+)", prompt)
    return json.dumps([{"id": i, "verdict": "take", "category": "ban-hang", "title": "Mục " + i[:4], "what": "Làm việc có ích.",
                        "gain": "Joyce có thêm khả năng.", "reason": "Chưa có.", "overlap": "", "caution": ""} for i in ids]), "fake:model"


skill_learn._DEPS = skill_learn.Deps(brain_root=lambda b: str(brain), ask=fake_ask)
c = TestClient(main.app, base_url="http://127.0.0.1:8080")

r = c.post("/skill-learn/sources", json={"location": str(repo)})
check("adds a local source", r.status_code == 200 and r.json().get("source_id"), r.text[:200])
sid = r.json()["source_id"]

r = c.post("/skill-learn/sync", json={"source_ids": [sid]})
j = r.json()
check("sync finds the skill and the plugin", r.status_code == 200 and j["state"]["stats"]["skills"] == 1 and j["state"]["stats"]["plugins"] == 1, j.get("state", {}).get("stats"))
check("sync starts the AI step by itself", (j.get("analysis") or {}).get("started") is True, j.get("analysis"))
for _ in range(100):
    st = c.get("/skill-learn").json()
    if not st["job"].get("running"):
        break
    time.sleep(0.1)
check("polling GET shows the job finishing", not st["job"].get("running") and st["stats"]["unanalyzed"] == 0, st["job"])
check("model routing value reaches the model call", seen.get("routing_model") == "glm-4.7-flash", seen)
check("cards carry Vietnamese notes", all((x.get("analysis") or {}).get("gain") for x in st["candidates"]))

r = c.post("/skill-learn/analyze", json={"candidate_ids": [st["candidates"][0]["id"]], "force": True})
check("analyze endpoint accepts a forced re-read", r.status_code == 200, r.text[:200])
for _ in range(100):
    if not c.get("/skill-learn").json()["job"].get("running"):
        break
    time.sleep(0.1)

ids = [x["id"] for x in st["candidates"]]

# ---- Kho cho: luu de sau voi uu tien + ghi chu, song sot qua lan quet, noi dung repo doi thi gan nhan ----
skill_id = next(x["id"] for x in st["candidates"] if x["type"] == "skill")
r = c.post("/skill-learn/review", json={"candidate_id": skill_id, "action": "save", "priority": "high", "note": "Dùng cho phòng Marketing — tháng sau"})
sv = next(x for x in r.json()["state"]["candidates"] if x["id"] == skill_id)
check("save puts the item in the waiting store with priority and note",
      r.status_code == 200 and sv["status"] == "saved" and sv["priority"] == "high" and sv["saved_at"] > 0 and "Marketing" in sv["note"], sv.get("status"))
check("em dash in a note is stripped", "—" not in sv["note"])
check("saved items leave the review queue but are counted", r.json()["state"]["stats"]["saved"] == 1 and r.json()["state"]["stats"]["pending"] == 1)
saved_at = sv["saved_at"]
r = c.post("/skill-learn/review", json={"candidate_id": skill_id, "action": "save", "priority": "ref"})
sv = next(x for x in r.json()["state"]["candidates"] if x["id"] == skill_id)
check("re-saving changes priority, keeps the note and the original save date", sv["priority"] == "ref" and "Marketing" in sv["note"] and sv["saved_at"] == saved_at)
r = c.post("/skill-learn/review", json={"candidate_id": skill_id, "action": "save", "priority": "urgent!!"})
check("an invalid priority is refused", r.status_code == 400)
r = c.post("/skill-learn/sync", json={"source_ids": [sid], "analyze": False})
sv = next(x for x in r.json()["state"]["candidates"] if x["id"] == skill_id)
check("a rescan keeps the saved item untouched", sv["status"] == "saved" and sv["priority"] == "ref" and not sv["upstream_changed"])
(repo / "skills" / "viet-email" / "SKILL.md").write_text("---\nname: Write email\ndescription: Draft emails in brand voice\n---\nSteps, now improved.\n", encoding="utf-8")
r = c.post("/skill-learn/sync", json={"source_ids": [sid], "analyze": False})
rows = [x for x in r.json()["state"]["candidates"] if x["type"] == "skill"]
sv = rows[0]
check("repo changed the content: still saved, flagged 'new version upstream', one card only",
      len(rows) == 1 and sv["status"] == "saved" and sv["upstream_changed"] is True and sv["priority"] == "ref" and sv["analysis"] is None, (len(rows), sv.get("status")))
ids = [x["id"] for x in r.json()["state"]["candidates"]]
r = c.post("/skill-learn/review", json={"candidate_id": sv["id"], "action": "save", "priority": "mid"})
check("saving again after reading the new version clears the flag", not next(x for x in r.json()["state"]["candidates"] if x["id"] == sv["id"])["upstream_changed"])

r = c.post("/skill-learn/review-batch", json={"candidate_ids": ids + ["khong-co"], "action": "install"})
res = {x["id"]: x for x in r.json()["results"]}
check("batch install reports each item, bad ids do not stop the rest",
      r.status_code == 200 and sum(x["ok"] for x in res.values()) == 2 and res["khong-co"]["ok"] is False, r.text[:300])
check("skill landed in the brain", (brain / "skills" / "viet-email" / "SKILL.md").is_file())
plug = skill_learn.plugins_host.global_plugins_dir() / "gia-ca" / "plugin.yaml"
check("plugin landed switched off", plug.is_file() and "enabled: false" in plug.read_text(encoding="utf-8") and "enabled: true" not in plug.read_text(encoding="utf-8"))
after = c.get("/skill-learn").json()
check("installed items move out of the pending queue", after["stats"]["pending"] == 0, after["stats"])

# ---- bang chung cai that ----
cands = {x["type"]: x for x in after["candidates"]}
sk_inst, pl_inst = cands["skill"]["install"], cands["plugin"]["install"]
check("installed skill carries real evidence: files, content, Joyce lists it",
      sk_inst and sk_inst["ok"] and {c["key"] for c in sk_inst["checks"]} >= {"files", "match", "listed"} and sk_inst["where"] == "skills/viet-email" and sk_inst["page"] == "skills", sk_inst)
check("installed plugin carries evidence: off by default, syntax valid, listed in the Tools page",
      pl_inst and pl_inst["ok"] and all(c["ok"] for c in pl_inst["checks"] if c["key"] in ("files", "off", "syntax", "register", "listed")) and pl_inst["page"] == "plugins", pl_inst)
r = c.post("/skill-learn/sync", json={"source_ids": [sid], "analyze": False})
again = {x["type"]: x for x in r.json()["state"]["candidates"]}
check("a rescan keeps installed items as installed, with their evidence",
      again["skill"]["status"] == "installed" and again["skill"]["install"] and again["plugin"]["status"] == "installed", [x["status"] for x in again.values()])
(brain / "skills" / "viet-email" / "SKILL.md").write_text("tampered", encoding="utf-8")
r = c.post("/skill-learn/verify", json={"candidate_id": again["skill"]["id"]})
vv = next(x for x in r.json()["state"]["candidates"] if x["id"] == again["skill"]["id"])["install"]
check("re-verify catches a file changed behind Joyce's back", vv["ok"] is False and any(ch["key"] == "match" and not ch["ok"] for ch in vv["checks"]), vv["checks"])
r = c.post("/skill-learn/verify", json={"candidate_id": "khong-co"})
check("verify of an unknown id is a clean 404", r.status_code == 404)

r = c.post("/skill-learn/trial", json={"candidate_id": again["skill"]["id"], "request": "Viết email chào khách mới"})
tr = next((x for x in r.json().get("state", {}).get("candidates", []) if x["id"] == again["skill"]["id"]), {}).get("trial") or {}
check("trial runs the skill and stores the real answer on the card", r.status_code == 200 and tr.get("answer") and tr.get("request") == "Viết email chào khách mới" and tr.get("model") == "fake:model", r.text[:200])
r = c.post("/skill-learn/trial", json={"candidate_id": again["plugin"]["id"]})
check("a plugin is never 'trialled' in a sandbox", r.status_code == 400 and "Công cụ" in r.json()["error"])

(repo / "plugins" / "hong").mkdir()
(repo / "plugins" / "hong" / "plugin.yaml").write_text("name: Hong\nslug: hong\nenabled: true\ntools: [x]\n", encoding="utf-8")
(repo / "plugins" / "hong" / "plugin.py").write_text("def register(ctx:\n    pass\n", encoding="utf-8")
r = c.post("/skill-learn/sync", json={"source_ids": [sid], "analyze": False})
bad = next(x for x in r.json()["state"]["candidates"] if x["slug"] == "hong")
r = c.post("/skill-learn/review", json={"candidate_id": bad["id"], "action": "install"})
check("a plugin that fails verification is NOT marked installed and its files are removed",
      r.status_code == 400 and "syntax" in r.json()["error"] and not (skill_learn.plugins_host.global_plugins_dir() / "hong").exists(), r.text[:200])
r = c.post("/skill-learn/review", json={"candidate_id": bad["id"], "action": "reject"})
check("rejecting works", next(x for x in r.json()["state"]["candidates"] if x["id"] == bad["id"])["status"] == "rejected")
r = c.post("/skill-learn/review", json={"candidate_id": bad["id"], "action": "restore"})
check("a skipped item can be restored to the review queue", next(x for x in r.json()["state"]["candidates"] if x["id"] == bad["id"])["status"] == "pending")
r = c.post("/skill-learn/review", json={"candidate_id": again["skill"]["id"], "action": "restore"})
check("restoring an installed item is refused", r.status_code == 400)

r = c.post("/skill-learn/review", json={"candidate_id": ids[0], "action": "delete-everything"})
check("unknown review action is rejected", r.status_code == 400)
r = c.post("/skill-learn/analyze", json={})
check("analysing with nothing to do still answers cleanly", r.status_code in (200, 409))
r = c.delete(f"/skill-learn/sources/{sid}")
check("removing the source drops its candidates", r.status_code == 200 and r.json()["state"]["stats"]["pending"] == 0)

if fails:
    raise SystemExit(f"{len(fails)} checks failed: {', '.join(fails)}")
print("ALL OK")
