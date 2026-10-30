"""Kiem ke thu vien skill (buoc 1): CHI DOC.

Quet moi brain, gom cac ban chep ve tung slug, chi ra ban nao lech noi dung, ban nao moi nhat, goi y nhom viec cho tung skill va
liet ke phong ban chua xep duoc. Khong bao gio ghi vao brains/. Ket qua duy nhat duoc ghi la file bao cao
<STATE_DIR>/skill-library/audit/latest.json (ghi atomic).

Luat tat dinh, khong goi model: nhom viec suy ra tu tien to ten brain (xem DEPT_PREFIXES) va tu cac brain dang giu skill do. Skill
co mat o gan het brain la skill he thong (cong-cu). Khi phieu bau khong ro (khong qua 50%) thi danh dau `needs_review`, khong doan.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import config as cfgmod
import fastyaml

router = APIRouter()
_LOCK = threading.Lock()      # chi chan hai lan kiem ke chay chong nhau (khong tai nhap)

GROUPS = ("ban-hang", "cskh", "marketing", "nghien-cuu", "san-xuat", "ke-toan", "nhan-su", "dieu-hanh", "ca-nhan", "cong-cu")

# Tien to ten brain (da bo dau, chu thuong) -> nhom viec. Khop khi ten bang tien to hoac bat dau bang "<tien to> - ".
DEPT_PREFIXES = (
    ("ban hang", "ban-hang"), ("cskh", "cskh"), ("marketing", "marketing"), ("nghien cuu", "nghien-cuu"),
    ("san xuat", "san-xuat"), ("ke toan", "ke-toan"), ("nhan su", "nhan-su"), ("h2o studio", "dieu-hanh"),
    ("thuyh2o studio", "dieu-hanh"), ("thuyh2o", "dieu-hanh"), ("ca nhan", "ca-nhan"),
)
# Phong chua khop quy tac nao: CHI GOI Y de chu quyet, khong bao gio tu ap dung (10 nhom viec do chu chot, khong co Truyen thong/Van thu/Ve sinh).
UNMATCHED_SUGGESTION = (("truyen thong", "marketing"), ("van thu", "dieu-hanh"), ("ve sinh", "san-xuat"),
                        ("kien thuc kinh doanh", "nghien-cuu"), ("brain default", "cong-cu"))
TEMPLATE_MIN_COPIES = 5     # tu 5 ban tro len ma gan nhu ban nao cung khac nhau: day la MAU CO BIEN theo phong, khong phai ban chep lech
TEMPLATE_UNIQUE_SHARE = 0.8
# Tu khoa trong phan sau " - " cua ten brain -> the nganh.
TAG_WORDS = (("makeup", "makeup"), ("vay cuoi", "vay-cuoi"), ("hinh anh", "chup-anh"), ("phu kien", "phu-kien"),
             ("boi toc", "boi-toc"), ("in an", "in-an"), ("photoshop", "photoshop"))
# Goi y tu truong `group` cu trong frontmatter skill (chi dung khi phieu bau hoa).
OLD_GROUP_HINT = {"marketing": "marketing", "ai": "cong-cu", "cong cu": "cong-cu", "dieu phoi h2o": "dieu-hanh", "y tuong": "nghien-cuu"}
SYSTEM_SLUGS = frozenset({"joyce-builder", "ingest-source", "query-wiki", "lint-wiki", "notes", "html-to-webcake", "cham-diem-tuong-phan"})
SYSTEM_SHARE = 0.9          # co mat o tu 90% brain tro len = skill he thong
VOTE_MIN_SHARE = 0.5        # nhom thang phieu phai chiem QUA nua moi tu tin (hoa 50% la chua ro)
_SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv"}


def _fold(text: str) -> str:
    s = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(s.lower().split())


def dept_group(brain_name: str) -> str:
    """Nhom viec cua mot brain theo tien to ten, hoac '' neu khong khop (khong doan)."""
    n = _fold(brain_name)
    for prefix, grp in DEPT_PREFIXES:
        if n == prefix or n.startswith(prefix + " - "):
            return grp
    return ""


def suggest_group(brain_name: str) -> str:
    """Goi y nhom cho brain chua khop quy tac (rong neu khong co goi y). Chi de hien cho chu, khong dung de xep that."""
    n = _fold(brain_name)
    for prefix, grp in UNMATCHED_SUGGESTION:
        if n == prefix or n.startswith(prefix + " - ") or n.startswith(prefix + " "):
            return grp
    return ""


def brain_tags(brain_name: str) -> list[str]:
    n = _fold(brain_name)
    tail = n.split(" - ", 1)[1] if " - " in n else ""
    return [tag for word, tag in TAG_WORDS if word in tail]


def _is_text(data: bytes) -> bool:
    return b"\0" not in data[:4096]


def package_hash(folder: Path) -> tuple[str, int]:
    """Bam ca goi skill. File chu bi chuan hoa CRLF thanh LF de khac biet xuong dong khong bi tinh la lech noi dung."""
    h = hashlib.sha256()
    total = 0
    for p in sorted(folder.rglob("*")):
        try:
            rel = p.relative_to(folder)
            if p.is_symlink() or not p.is_file() or any(part in _SKIP_DIRS for part in rel.parts):
                continue
            data = p.read_bytes()
        except OSError:
            continue
        total += len(data)
        if _is_text(data):
            data = data.replace(b"\r\n", b"\n")
        h.update(rel.as_posix().encode("utf-8") + b"\0" + data + b"\0")
    return h.hexdigest(), total


def _newest_mtime(folder: Path) -> float:
    best = 0.0
    for p in folder.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink() and not any(part in _SKIP_DIRS for part in p.relative_to(folder).parts):
                best = max(best, p.stat().st_mtime)
        except OSError:
            continue
    return best


def _meta(skill_md: Path) -> dict:
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    parts = fastyaml.split_frontmatter(text)
    if not parts:
        return {}
    try:
        m = fastyaml.safe_load(parts[0]) or {}
    except Exception:  # noqa: BLE001 - frontmatter hong thi coi nhu khong co
        return {}
    return m if isinstance(m, dict) else {}


def _subdirs(p: Path):
    try:
        return sorted(x for x in p.iterdir() if x.is_dir() and not x.is_symlink())
    except OSError:
        return []


def _agent_skills(agents_dir: Path) -> list[list[str]]:
    out: list[list[str]] = []
    try:
        files = sorted(agents_dir.glob("*.md"))
    except OSError:
        return out
    for f in files:
        try:
            parts = fastyaml.split_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
            meta = (fastyaml.safe_load(parts[0]) or {}) if parts else {}
        except Exception:  # noqa: BLE001
            continue
        sk = meta.get("skills") if isinstance(meta, dict) else None
        out.append([str(x) for x in sk] if isinstance(sk, list) else [])
    return out


def audit(brains_dir: str | Path) -> dict:
    """Quet moi brain duoi `brains_dir`. Ham thuan doc: khong ghi, khong goi model."""
    root = Path(brains_dir)
    brains: list[dict] = []
    copies: dict[str, list[dict]] = defaultdict(list)       # slug -> cac ban chep
    agent_refs = dangling = agents_total = 0
    agents_using: Counter = Counter()
    for bdir in _subdirs(root):
        if bdir.name.startswith("."):
            continue
        name = bdir.name
        present: set[str] = set()
        sk_base = bdir / "skills"
        entries = [(d, True) for d in _subdirs(sk_base) if d.name != ".disabled" and (d / "SKILL.md").is_file()]
        entries += [(d, False) for d in _subdirs(sk_base / ".disabled") if (d / "SKILL.md").is_file()]
        for d, enabled in entries:
            sha, size = package_hash(d)
            meta = _meta(d / "SKILL.md")
            if enabled:
                present.add(d.name)
            copies[d.name].append({"brain": name, "enabled": enabled, "sha": sha, "bytes": size, "mtime": _newest_mtime(d),
                                   "name": str(meta.get("name") or d.name)[:120],
                                   "description": " ".join(str(meta.get("description") or "").split())[:300],
                                   "old_group": str(meta.get("group") or "")})
        agents = _agent_skills(bdir / "agents")
        agents_total += len(agents)
        for sk in agents:
            for slug in sk:
                agent_refs += 1
                agents_using[slug] += 1
                if slug not in present:
                    dangling += 1
        brains.append({"name": name, "group": dept_group(name), "tags": brain_tags(name),
                       "skills": len(entries), "agents": len(agents)})
    n_brains = len(brains)
    group_of = {b["name"]: b["group"] for b in brains}
    tags_of = {b["name"]: b["tags"] for b in brains}
    skills: list[dict] = []
    for slug, cps in sorted(copies.items()):
        live = [c for c in cps if c["enabled"]]
        basis = live or cps
        by_sha: dict[str, list[dict]] = defaultdict(list)
        for c in basis:
            by_sha[c["sha"]].append(c)
        variants = sorted(({"sha": s, "count": len(v), "brains": sorted(x["brain"] for x in v), "bytes": v[0]["bytes"],
                            "newest_mtime": max(x["mtime"] for x in v)} for s, v in by_sha.items()),
                          key=lambda x: (-x["count"], -x["newest_mtime"]))
        majority = variants[0]["sha"]
        newest = max(variants, key=lambda x: x["newest_mtime"])["sha"]
        newest_mtime = max(c["mtime"] for c in basis)
        newest_brains = sorted(c["brain"] for c in basis if c["mtime"] == newest_mtime)
        brain_names = sorted({c["brain"] for c in basis})
        system = slug in SYSTEM_SLUGS or (n_brains > 0 and len(brain_names) / n_brains >= SYSTEM_SHARE)
        votes = Counter(group_of[b] for b in brain_names if group_of.get(b))
        needs_review, share, reason = False, 0.0, ""
        uniq = len(variants) / max(1, len(basis))
        template = len(basis) >= TEMPLATE_MIN_COPIES and uniq >= TEMPLATE_UNIQUE_SHARE
        if system:
            grp, reason = "cong-cu", "skill he thong, co mat o gan het brain"
        elif template and n_brains and len(brain_names) / n_brains >= 0.5:
            grp, needs_review = "cong-cu", True
            reason = "mau dung chung o nhieu phong, moi phong mot ban rieng (khong phai ban chep lech)"
        elif votes:
            grp, top = votes.most_common(1)[0]
            share = top / sum(votes.values())
            reason = f"{top}/{sum(votes.values())} brain giu skill nay thuoc nhom {grp}"
            if share <= VOTE_MIN_SHARE:
                hint = OLD_GROUP_HINT.get(_fold(basis[0]["old_group"]), "")
                if hint:
                    grp, reason = hint, reason + "; lay goi y tu nhom cu " + repr(basis[0]["old_group"])
                else:
                    needs_review = True
        else:
            hint = OLD_GROUP_HINT.get(_fold(basis[0]["old_group"]), "")
            if hint:
                grp, reason = hint, "lay theo nhom cu " + repr(basis[0]["old_group"]) + " (khong brain nao xep duoc nhom)"
            else:
                grp, needs_review, reason = "", True, "khong brain nao giu skill nay xep duoc nhom"
        sg_votes = Counter(suggest_group(b) for b in brain_names if not group_of.get(b) and suggest_group(b))
        suggested = sg_votes.most_common(1)[0][0] if (not grp and sg_votes) else ""
        tag_count = Counter(t for b in brain_names for t in tags_of.get(b, []))
        tags = [] if system else sorted(t for t, k in tag_count.items() if k / len(brain_names) >= 0.6)
        first = basis[0]
        skills.append({
            "slug": slug, "name": first["name"], "description": first["description"], "old_group": first["old_group"],
            "copies": len(live), "disabled_copies": len(cps) - len(live), "brains": brain_names, "variants": variants,
            "majority_sha": majority, "newest_sha": newest, "diverged": len(variants) > 1,
            "newest_mtime": newest_mtime, "newest_brains": newest_brains,
            "diverged_brains": sorted(b for v in variants[1:] for b in v["brains"]),
            "proposed_group": grp, "group_share": round(share, 2), "group_reason": reason, "needs_review": needs_review,
            "tags": tags, "system": system, "template": template, "suggested_group": suggested,
            "agents_using": agents_using.get(slug, 0),
        })
    unmatched = [{"name": b["name"], "skills": b["skills"], "agents": b["agents"], "suggested_group": suggest_group(b["name"])}
                 for b in brains if not b["group"]]
    by_group = Counter(s["proposed_group"] or "(chua xep)" for s in skills)
    return {
        "version": 1, "generated_at": int(time.time()), "brains_dir": str(root),
        "summary": {
            "brains": n_brains, "brains_with_skills": sum(1 for b in brains if b["skills"]),
            "files": sum(len(v) for v in copies.values()), "distinct_slugs": len(skills),
            "templates": sum(s["template"] for s in skills),
            "slugs_diverged": sum(s["diverged"] and not s["template"] for s in skills),
            "copies_diverged": sum(len(s["diverged_brains"]) for s in skills if not s["template"]),
            "disabled_copies": sum(s["disabled_copies"] for s in skills),
            "unmatched_brains": len(unmatched), "needs_review": sum(s["needs_review"] for s in skills),
            "agents": agents_total, "agent_refs": agent_refs, "agent_refs_dangling": dangling,
        },
        "groups": [{"key": k, "skills": by_group.get(k, 0)} for k in GROUPS] + ([{"key": "", "skills": by_group["(chua xep)"]}] if by_group.get("(chua xep)") else []),
        "skills": skills, "brains": brains, "unmatched_brains": unmatched,
    }


def _report_path() -> Path:
    p = cfgmod.STATE_DIR / "skill-library" / "audit"
    p.mkdir(parents=True, exist_ok=True)
    return p / "latest.json"


def _save(report: dict) -> None:
    p = _report_path()
    fd, tmp = tempfile.mkstemp(prefix="latest.", suffix=".tmp", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, ensure_ascii=False)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def load_latest() -> dict | None:
    try:
        d = json.loads(_report_path().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def register(app, brains_dir: Callable[[], str]):
    @router.get("/skill-library/audit")
    async def get_audit():
        return {"ok": True, "report": load_latest()}

    @router.post("/skill-library/audit/run")
    async def run_audit():
        import asyncio
        if not _LOCK.acquire(blocking=False):
            return JSONResponse({"ok": False, "error": "Đang kiểm kê, chờ lượt này xong"}, status_code=409)
        try:
            report = await asyncio.to_thread(audit, brains_dir())
            _save(report)
        finally:
            _LOCK.release()
        return {"ok": True, "report": report}

    app.include_router(router)
    return router
