"""Kiem ke thu vien skill (buoc 1): chi doc, tat dinh, chay tren cay brain tam, khong cham brains/ va state that."""
from _paths import ROOT, SERVER  # noqa: E402,F401

import hashlib
import os
import tempfile
import time
from pathlib import Path

_STATE = tempfile.TemporaryDirectory(prefix="joyce-slib-state-", ignore_cleanup_errors=True)
os.environ["JOYCE_STATE_DIR"] = _STATE.name

import skill_library_audit as sla  # noqa: E402

fails = []


def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + (f" [{extra}]" if extra and not cond else ""))
    if not cond:
        fails.append(name)


def skill(brain, slug, body="Cach lam.\n", desc="Mo ta ngan", group="", extra=None, disabled=False, newline="\n"):
    base = brain / "skills" / (".disabled" if disabled else "") / slug
    base.mkdir(parents=True, exist_ok=True)
    fm = f"---\nname: {slug}\ndescription: {desc}\n" + (f"group: {group}\n" if group else "") + "---\n"
    (base / "SKILL.md").write_bytes((fm + body).replace("\n", newline).encode("utf-8"))
    for rel, data in (extra or {}).items():
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        (base / rel).write_bytes(data)
    return base


def snapshot(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode() + p.read_bytes() + str(p.stat().st_mtime_ns).encode())
    return h.hexdigest()


with tempfile.TemporaryDirectory(prefix="joyce-slib-", ignore_cleanup_errors=True) as td:
    brains = Path(td) / "brains"
    names = ["Marketing - Makeup", "Marketing - Vay Cuoi", "Marketing", "Ban Hang - Sales Makeup", "Ke Toan - Thu", "Kien Thuc Ngoai", "Brain Default"]
    for n in names:
        (brains / n).mkdir(parents=True)
        skill(brains / n, "notes", group="AI")                                  # skill he thong o moi brain
    # skill marketing co mat o 3 brain marketing, 2 ban giong nhau (mot ban chi khac CRLF) va 1 ban lech noi dung
    skill(brains / "Marketing - Makeup", "viet-quang-cao", body="Buoc 1\nBuoc 2\n", group="Marketing")
    time.sleep(0.02)
    skill(brains / "Marketing - Vay Cuoi", "viet-quang-cao", body="Buoc 1\nBuoc 2\n", group="Marketing", newline="\r\n")
    time.sleep(0.02)
    skill(brains / "Marketing", "viet-quang-cao", body="Buoc 1\nBuoc 2\nBuoc 3 moi\n", group="Marketing")
    # skill gioi han o phong makeup
    skill(brains / "Marketing - Makeup", "tong-hop-makeup", extra={"references/a.md": b"ref"})
    skill(brains / "Ban Hang - Sales Makeup", "tong-hop-makeup", extra={"references/a.md": b"ref"})
    # skill chi nam o brain khong xep duoc nhom
    skill(brains / "Kien Thuc Ngoai", "rieng-le")
    # ban da tat
    skill(brains / "Ke Toan - Thu", "da-tat", disabled=True)
    # phieu bau hoa: hai nhom 1-1, khong goi y tu nhom cu thi can duyet
    skill(brains / "Ke Toan - Thu", "chung-chung")
    skill(brains / "Marketing", "chung-chung")
    # agent tham chieu: mot dung, mot gay
    (brains / "Marketing" / "agents").mkdir()
    (brains / "Marketing" / "agents" / "a.md").write_text("---\nname: A\nskills:\n- viet-quang-cao\n- khong-ton-tai\n---\nBody\n", encoding="utf-8")

    # mau co bien: 6 phong cung mot skill, moi phong mot ban rieng (ten phong nam trong noi dung) -> khong phai ban chep lech
    for n in names:
        skill(brains / n, "y-tuong-mau", body=f"# Xu ly y tuong - phong {n}\nGoc nhin rieng cua {n}\n")
    # phong chua xep duoc nhung co goi y; skill chi o phong do co nhom cu de dua vao
    (brains / "Van Thu").mkdir()
    skill(brains / "Van Thu", "quy-trinh-van-thu")
    skill(brains / "Van Thu", "cong-cu-rieng", group="Cong cu")

    before = snapshot(brains)
    rep = sla.audit(brains)
    check("audit never writes into the brains tree", snapshot(brains) == before)

    s = rep["summary"]
    check("counts brains, files and distinct slugs", s["brains"] == 8 and s["distinct_slugs"] == 9 and s["files"] == 16 + 7 + 2, s)
    by = {x["slug"]: x for x in rep["skills"]}
    va = by["viet-quang-cao"]
    check("CRLF-only difference is NOT counted as a content difference", len(va["variants"]) == 2 and va["variants"][0]["count"] == 2, va["variants"])
    check("the real divergence is reported with its brain", va["diverged"] and va["diverged_brains"] == ["Marketing"], va["diverged_brains"])
    check("newest variant is the last one written", va["newest_sha"] == va["variants"][1]["sha"] and va["majority_sha"] == va["variants"][0]["sha"])
    check("newest copy names the exact brain that changed last", va["newest_brains"] == ["Marketing"] and va["newest_mtime"] > 0, va["newest_brains"])
    check("identical copies are not flagged", not by["tong-hop-makeup"]["diverged"] and by["tong-hop-makeup"]["copies"] == 2)
    check("a skill present everywhere is a system skill in cong-cu", by["notes"]["system"] and by["notes"]["proposed_group"] == "cong-cu")
    check("group follows the departments that hold the skill", va["proposed_group"] == "marketing" and va["group_share"] == 1.0, va["group_reason"])
    check("industry tags come from the sub-department names", by["tong-hop-makeup"]["tags"] == ["makeup"] and "makeup" not in by["notes"]["tags"], by["tong-hop-makeup"]["tags"])
    check("a skill held only by an unplaceable brain is flagged for review, not guessed",
          by["rieng-le"]["proposed_group"] == "" and by["rieng-le"]["needs_review"] is True)
    check("a tie with no old-group hint is flagged for review", by["chung-chung"]["needs_review"] is True and by["chung-chung"]["group_share"] == 0.5, by["chung-chung"])
    check("disabled copies are counted apart from live ones", by["da-tat"]["copies"] == 0 and by["da-tat"]["disabled_copies"] == 1)
    check("brains that match no department rule are listed, not guessed",
          sorted(b["name"] for b in rep["unmatched_brains"]) == ["Brain Default", "Kien Thuc Ngoai", "Van Thu"], rep["unmatched_brains"])
    sg = {b["name"]: b["suggested_group"] for b in rep["unmatched_brains"]}
    check("unplaced brains get a suggestion for the owner but are not placed", sg["Van Thu"] == "dieu-hanh" and sg["Kien Thuc Ngoai"] == "" and sla.dept_group("Van Thu") == "", sg)
    tm = by["y-tuong-mau"]
    check("a per-department template is recognised and not counted as divergence", tm["template"] is True and tm["diverged"] is True
          and rep["summary"]["templates"] == 1 and rep["summary"]["slugs_diverged"] == 1, (tm["template"], rep["summary"]))
    check("a template spread over many departments is proposed as cong-cu but flagged for review", tm["proposed_group"] == "cong-cu" and tm["needs_review"] is True)
    check("a skill held only by an unplaced brain carries that brain's suggested group", by["quy-trinh-van-thu"]["proposed_group"] == "" and by["quy-trinh-van-thu"]["suggested_group"] == "dieu-hanh", by["quy-trinh-van-thu"])
    check("old group hint is used when no brain can be placed", by["cong-cu-rieng"]["proposed_group"] == "cong-cu" and not by["cong-cu-rieng"]["needs_review"], by["cong-cu-rieng"])
    check("agent references are counted and the broken one is found", s["agent_refs"] == 2 and s["agent_refs_dangling"] == 1 and va["agents_using"] == 1, s)
    check("department prefix rules", sla.dept_group("ThuyH2O Studio") == "dieu-hanh" and sla.dept_group("Nhan Su - Photoshop") == "nhan-su" and sla.dept_group("ThuyH2O - Hoc Vien") == "dieu-hanh"
          and sla.dept_group("H2O Studio") == "dieu-hanh" and sla.dept_group("Marketingxyz") == "" and sla.dept_group("Ban Hang - Sales Vay Cuoi") == "ban-hang")
    check("names with diacritics fold to the same rule", sla.dept_group("Kế Toán - Thu") == "ke-toan")

    # luu / doc bao cao: atomic, doc lai y het
    sla._save(rep)
    again = sla.load_latest()
    check("report round-trips through the state dir", again and again["summary"] == rep["summary"] and str(sla._report_path()).startswith(_STATE.name))
    check("brains tree still untouched after saving", snapshot(brains) == before)

if fails:
    raise SystemExit(f"{len(fails)} checks failed: {', '.join(fails)}")
print("ALL OK")
