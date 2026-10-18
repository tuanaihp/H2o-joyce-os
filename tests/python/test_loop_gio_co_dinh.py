"""Chu kỳ loop nhập theo giờ/ngày dễ đọc + ghim GIỜ CỐ ĐỊNH hằng ngày (run_at 'HH:MM').

Bối cảnh: form Việc định kỳ trước bắt nhập chu kỳ bằng SỐ PHÚT THÔ ("1445") - chủ phải tự
cộng giờ. Nay UI có preset + ô ngày/giờ/phút, và loop chu kỳ >= 1 ngày ghim được giờ chạy
cố định (vd "mỗi tối 21h") thay vì trôi theo last_run + interval.

Phạm vi test (backend self_improve.py):
  - _norm_run_at: nhận '21:00'/'7:5', loại '25:00'/'x:y'/rỗng
  - _next_run_at: loop mới ghim giờ -> đợi đúng giờ (KHÔNG chạy ngay); sau last_run -> mốc
    kế đúng giờ; chu kỳ 30 ngày -> mốc cách ~30 ngày đúng giờ; chu kỳ < 1 ngày -> không áp
  - _norm_loop: đọc run_at từ frontmatter
  - save_loop: ghi run_at vào file (và BỎ sót khi rỗng - file mặc định sạch)
  - _eligible_overdue + loop_view.next_run theo nhánh run_at
  - _fmt_chu_ky: 1445 -> 'mỗi ngày lúc 21:00' thay vì 'mỗi 1445 phút'

Chạy tay / CI:

    python tests/run.py loop_gio_co_dinh

KHÔNG cần Claude CLI/SDK/mạng - chỉ logic thuần.
"""
from _paths import ROOT, SERVER  # noqa: E402,F401
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("JOYCE_STATE_DIR", tempfile.mkdtemp(prefix="joyce-runat-"))

import self_improve  # noqa: E402
import localefmt  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


_BRAIN_ROOT = tempfile.mkdtemp(prefix="joyce-runat-brain-")


def _atomic_write(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


deps = self_improve.LoopDeps(
    build_system_prompt=lambda brain: "SYS",
    brain_root=lambda brain: _BRAIN_ROOT,
    aux_model=lambda: None,
    atomic_write_text=_atomic_write,
    project_root=Path("."),
    state_dir=Path(os.environ["JOYCE_STATE_DIR"]),
    safe_tools=["Read", "Write", "Edit", "Glob", "Grep"],
    readonly_tools=["Read", "Glob", "Grep", "LS"],
)
feat = self_improve.LoopFeature(deps)


# ── 1. _norm_run_at ──
check("norm_run_at: '21:00' -> '21:00'", self_improve._norm_run_at("21:00") == "21:00")
check("norm_run_at: '7:5' -> '07:05'", self_improve._norm_run_at("7:5") == "07:05")
check("norm_run_at: rỗng -> ''", self_improve._norm_run_at("") == "")
check("norm_run_at: None -> ''", self_improve._norm_run_at(None) == "")
check("norm_run_at: '25:00' -> ''", self_improve._norm_run_at("25:00") == "")
check("norm_run_at: '12:60' -> ''", self_improve._norm_run_at("12:60") == "")
check("norm_run_at: 'x:y' -> ''", self_improve._norm_run_at("x:y") == "")


# ── 2. _next_run_at ──
now = time.time()
check("next_run_at: chu kỳ <1 ngày -> 0 (không áp)",
      self_improve._next_run_at("21:00", now - 3600, 120, now) == 0.0)
check("next_run_at: không ghim giờ -> 0",
      self_improve._next_run_at("", now - 3600, 1440, now) == 0.0)

# loop mới (last_run=0) vừa bật lúc `armed` -> đợi mốc 21:00 kế tiếp từ LÚC BẬT
armed = now - 3600  # bật 1 tiếng trước
nxt = self_improve._next_run_at("21:00", 0, 1440, now, armed)
nd = datetime.fromtimestamp(nxt, localefmt.tz())
check("next_run_at: loop mới -> mốc 21:00 sau lúc bật", nxt > armed and nd.hour == 21 and nd.minute == 0)
check("next_run_at: loop mới -> trong vòng 25h kể từ bật", nxt - armed < 90000)

# loop mới KHÔNG có armed_at (file viết tay / bật từ bản cũ) -> coi như vừa bật -> đợi mốc kế
nxt0 = self_improve._next_run_at("21:00", 0, 1440, now, 0)
nd0 = datetime.fromtimestamp(nxt0, localefmt.tz())
check("next_run_at: thiếu armed_at -> mốc 21:00 tương lai",
      nxt0 > now and nd0.hour == 21 and nd0.minute == 0)

# đã chạy xong -> mốc kế = lần 21:00 đầu tiên SAU last_run
last = now - 3600
nxt2 = self_improve._next_run_at("21:00", last, 1440, now)
nd2 = datetime.fromtimestamp(nxt2, localefmt.tz())
check("next_run_at: sau last_run -> đúng giờ 21:00", nd2.hour == 21 and nd2.minute == 0)
check("next_run_at: sau last_run -> mốc > last_run và < last_run + 2 ngày",
      last < nxt2 < last + 2 * 86400)

# chu kỳ 30 ngày + ghim giờ -> mốc cách ~30 ngày, đúng giờ
nxt3 = self_improve._next_run_at("08:00", last, 30 * 1440, now)
gap3 = (nxt3 - last) / 86400
nd3 = datetime.fromtimestamp(nxt3, localefmt.tz())
check("next_run_at: 30 ngày + run_at -> cách 29-31 ngày đúng giờ 08:00",
      29 <= gap3 <= 31 and nd3.hour == 8 and nd3.minute == 0)

# last_run vừa đúng giờ ghim -> mốc kế = NGÀY MAI cùng giờ (không lặp lại cùng mốc)
t0 = datetime.now(localefmt.tz()).replace(hour=21, minute=0, second=0, microsecond=0)
last_exact = t0.timestamp() - 86400  # hôm qua 21:00
nxt4 = self_improve._next_run_at("21:00", last_exact, 1440, now)
check("next_run_at: last_run tròn 21:00 -> mốc kế = 21:00 hôm nay/mai, > last_run",
      nxt4 > last_exact and datetime.fromtimestamp(nxt4, localefmt.tz()).hour == 21)


# ── 3. _norm_loop đọc run_at từ frontmatter ──
lp = feat._norm_loop({"name": "X", "enabled": True, "interval_min": 1440, "run_at": "21:00"},
                     "body", "x")
check("norm_loop: run_at '21:00' -> '21:00'", lp["run_at"] == "21:00")
lp_bad = feat._norm_loop({"name": "X", "interval_min": 1440, "run_at": "99:99"}, "body", "x")
check("norm_loop: run_at sai -> ''", lp_bad["run_at"] == "")
lp_none = feat._norm_loop({"name": "X", "interval_min": 1440}, "body", "x")
check("norm_loop: thiếu run_at -> ''", lp_none["run_at"] == "")


# ── 4. save_loop ghi run_at vào frontmatter ──
brain_dir = Path(_BRAIN_ROOT)
feat.save_loop("Ca Nhan - Tuan", {
    "slug": "ghim-gio", "name": "Ghim giờ", "enabled": False, "goal": "custom",
    "mode": "full", "interval_min": 1440, "run_at": "21:00", "workspace": "vault",
    "tools_profile": "vault-safe", "quiet_hours": "", "max_runs_per_day": 0,
    "owner_chat": "", "notify": True, "body": "viec gi do",
})
raw = (brain_dir / "Joyce" / "loops" / "ghim-gio.md").read_text(encoding="utf-8")
check("save_loop: frontmatter có run_at '21:00'", "run_at: '21:00'" in raw or 'run_at: "21:00"' in raw or "run_at: 21:00" in raw)
# đọc lại file -> run_at vẫn đúng (round-trip)
lp_rt = feat.get_loop("Ca Nhan - Tuan", "ghim-gio")
check("save_loop: đọc lại file -> run_at '21:00'", lp_rt is not None and lp_rt["run_at"] == "21:00")

# run_at rỗng -> KHÔNG ghi vào file (giữ file mặc định sạch)
feat.save_loop("Ca Nhan - Tuan", {
    "slug": "khong-ghim", "name": "Không ghim", "enabled": False, "goal": "custom",
    "mode": "full", "interval_min": 1440, "run_at": "", "workspace": "vault",
    "tools_profile": "vault-safe", "quiet_hours": "", "max_runs_per_day": 0,
    "owner_chat": "", "notify": True, "body": "viec",
})
raw2 = (brain_dir / "Joyce" / "loops" / "khong-ghim.md").read_text(encoding="utf-8")
check("save_loop: run_at rỗng -> file KHÔNG chứa dòng run_at", "run_at" not in raw2)


# ── 5. _eligible_overdue theo nhánh run_at ──
loop_ra = feat._norm_loop({"name": "R", "enabled": True, "interval_min": 1440, "run_at": "21:00"},
                          "body", "r")
moc_arm = self_improve._next_run_at("21:00", 0, 1440, now, armed)
# chưa tới giờ ghim (bật gần đây) -> chưa hết hạn (dù theo công thức interval cũ thì đã hết)
if now < moc_arm:
    check("eligible: loop mới ghim giờ CHƯA tới mốc -> chưa đủ điều kiện",
          feat._eligible_overdue(loop_ra, {"armed_at": armed}, now, 12) is None)
# đã QUA mốc ghim -> hết hạn (armed_at lâu rồi, mốc 21:00 gần nhất đã qua)
armed_xua = now - 3 * 86400
moc_qk = self_improve._next_run_at("21:00", 0, 1440, now, armed_xua)
check("eligible: mốc ghim đã qua -> hết hạn",
      feat._eligible_overdue(loop_ra, {"armed_at": armed_xua}, now, 12) is not None)
check("eligible: mốc ghim đã qua -> moc nằm trong quá khứ", moc_qk <= now)
# sau khi chạy xong (last_run mới) -> mốc kế trong tương lai -> chưa hết hạn
check("eligible: vừa chạy xong -> chưa hết hạn",
      feat._eligible_overdue(loop_ra, {"last_run": now}, now, 12) is None)
# loop KHÔNG ghim giờ giữ nguyên công thức cũ
loop_no = feat._norm_loop({"name": "R", "enabled": True, "interval_min": 60}, "body", "r")
check("eligible: không run_at -> công thức interval như cũ",
      feat._eligible_overdue(loop_no, {"last_run": now - 3600}, now, 12) is not None)


# ── 6. loop_view.next_run theo run_at + toggle ghi armed_at ──
view = feat.loop_view("Ca Nhan - Tuan", lp_rt)
# lp_rt đang enabled: False -> next_run = 0; bật giả lập
lp_rt["enabled"] = True
view2 = feat.loop_view("Ca Nhan - Tuan", lp_rt)
nd_view = datetime.fromtimestamp(view2["next_run"], localefmt.tz())
check("loop_view: next_run đúng giờ ghim 21:00",
      view2["next_run"] > now and nd_view.hour == 21 and nd_view.minute == 0)
# toggle bật loop run_at chưa chạy -> ghi armed_at vào state
lp_rt["enabled"] = False
feat.toggle("Ca Nhan - Tuan", "ghim-gio")
st_tg = feat.read_state("Ca Nhan - Tuan").get("ghim-gio", {})
check("toggle: bật loop run_at -> state có armed_at", st_tg.get("armed_at", 0) > 0)
lp_rt["enabled"] = False


# ── 7. _fmt_chu_ky ──
check("fmt: 1440 -> 'mỗi ngày'", self_improve._fmt_chu_ky(1440) == "mỗi ngày")
check("fmt: 1440+21:00 -> 'mỗi ngày lúc 21:00'",
      self_improve._fmt_chu_ky(1440, "21:00") == "mỗi ngày lúc 21:00")
check("fmt: 10080 -> 'mỗi tuần'", self_improve._fmt_chu_ky(10080) == "mỗi tuần")
check("fmt: 120 -> 'mỗi 2 giờ'", self_improve._fmt_chu_ky(120) == "mỗi 2 giờ")
check("fmt: 90 -> 'mỗi 1 giờ 30 phút'", self_improve._fmt_chu_ky(90) == "mỗi 1 giờ 30 phút")
check("fmt: 1445 -> 'mỗi 1 ngày lúc...' KHÔNG, 1445 không chia hết -> 'mỗi 24 giờ 5 phút'",
      self_improve._fmt_chu_ky(1445) == "mỗi 24 giờ 5 phút")
check("fmt: 30 -> 'mỗi 30 phút'", self_improve._fmt_chu_ky(30) == "mỗi 30 phút")


print()
if _fails:
    print(f"FAIL ({len(_fails)} failed)")
    raise SystemExit(1)
print("ALL PASS")
