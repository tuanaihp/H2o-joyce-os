"""Sổ nhân viên H2O Studio: đăng nhập bằng SĐT + PIN, mỗi người một workspace
và một danh sách model được admin cấp (tránh hai người cùng nạp model nặng).

File state: STATE_DIR/h2o_staff.json — nằm cùng nơi settings.json, được
.gitignore che cùng nhóm state runtime (có hash PIN, không commit).

Session nhân viên (cookie `h2o_staff`) tách khỏi `joyce_session` của admin:
token -> staff_id, TTL 30 ngày giống session admin. Nhân viên hợp lệ được coi
là "đã đăng nhập" cho middleware, nhưng request ghi vào các prefix admin
(_STAFF_DENY bên main.py) bị chặn 403.

Phòng ban: `phong_ban` là danh sách id phòng (h2o_departments). Phòng đầu tiên là brain
mặc định khi nhân viên đăng nhập; server khoá mọi request của họ vào brain các phòng này.

Model ACL: `models` là danh sách "provider:model" (vd "ollama-local:qwen3:14b",
"anthropic-cli:sonnet") hoặc "provider:*" = mọi model của provider đó.
RỖNG = không hạn chế (admin chưa phân quyền)."""
from __future__ import annotations

import json
import re
import secrets
import time
import unicodedata
from pathlib import Path

import config as cfgmod

PATH = cfgmod.STATE_DIR / "h2o_staff.json"
SESSION_TTL = 30 * 86400                      # 30 ngày, ngang session admin
_SDT_RE = re.compile(r"^[0-9+][0-9 .\-]{4,18}$")
# Chức vụ H2O Studio. "staff"/"lead" là giá trị cũ của bản đầu - giữ trong danh
# sách để hồ sơ đã tạo vẫn hợp lệ, nhưng form mới chỉ cho chọn sáu chức vụ đầu.
ROLES = ("ceo", "giam_doc", "truong_phong", "chuyen_gia", "nhan_vien", "hoc_viec",
         "staff", "lead")                     # admin thực sự vẫn là tài khoản /auth/login


def _doc() -> dict:
    try:
        d = json.loads(PATH.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            d.setdefault("staff", [])
            d.setdefault("sessions", {})
            return d
    except Exception:
        pass
    return {"staff": [], "sessions": {}}


def _save(d: dict) -> None:
    PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "nv"


def norm_sdt(s: str) -> str:
    """SĐT về dạng chỉ số còn +, để "090 123 4567" và "0901234567" là một."""
    return re.sub(r"[^0-9+]", "", str(s or ""))


def _view(s: dict) -> dict:
    """Bản công khai của một hồ sơ: KHÔNG mang pin_hash/salt ra ngoài."""
    return {k: v for k, v in s.items() if k not in ("pin_hash", "pin_salt")}


def list_staff() -> list:
    return [_view(s) for s in _doc()["staff"] if s.get("active", True) or s.get("id")]


def get(sid: str):
    for s in _doc()["staff"]:
        if s.get("id") == sid:
            return s
    return None


def by_sdt(sdt: str):
    sdt = norm_sdt(sdt)
    if not sdt:
        return None
    for s in _doc()["staff"]:
        if norm_sdt(s.get("sdt")) == sdt:
            return s
    return None


def create(ten: str, sdt: str, pin: str, role: str = "staff", models=None, phong_ban=None):
    """(ok, err|record). PIN 4-8 chữ số; SĐT là khoá đăng nhập nên phải duy nhất."""
    ten = str(ten or "").strip()
    sdt_n = norm_sdt(sdt)
    pin = str(pin or "").strip()
    if not ten:
        return False, "Thiếu tên nhân viên"
    if not _SDT_RE.match(sdt_n) and len(sdt_n) < 6:
        return False, "Số điện thoại không hợp lệ"
    if not re.fullmatch(r"\d{4,8}", pin):
        return False, "PIN phải là 4-8 chữ số"
    if role not in ROLES:
        role = "staff"
    d = _doc()
    if by_sdt(sdt_n):
        return False, "Số điện thoại đã có tài khoản"
    sid = "st_" + _slug(ten) + "_" + secrets.token_hex(3)
    h, salt = cfgmod.hash_password(pin)
    rec = {
        "id": sid, "ten": ten, "sdt": sdt_n, "pin_hash": h, "pin_salt": salt,
        "role": role, "models": [str(m) for m in (models or []) if str(m).strip()],
        "phong_ban": _phong_hop_le(phong_ban),
        "active": True, "created": time.time(),
    }
    d["staff"].append(rec)
    _save(d)
    workspace_dir(rec)              # dựng sẵn thư mục làm việc riêng
    return True, _view(rec)


def update(sid: str, ten=None, sdt=None, pin=None, role=None, models=None, active=None,
           phong_ban=None):
    d = _doc()
    for s in d["staff"]:
        if s.get("id") != sid:
            continue
        if ten is not None and str(ten).strip():
            s["ten"] = str(ten).strip()
        if sdt is not None:
            sdt_n = norm_sdt(sdt)
            if not sdt_n:
                return False, "Số điện thoại không hợp lệ"
            other = by_sdt(sdt_n)
            if other and other["id"] != sid:
                return False, "Số điện thoại trùng nhân viên khác"
            s["sdt"] = sdt_n
        if pin is not None:
            pin = str(pin).strip()
            if not re.fullmatch(r"\d{4,8}", pin):
                return False, "PIN phải là 4-8 chữ số"
            s["pin_hash"], s["pin_salt"] = cfgmod.hash_password(pin)
        if role is not None:
            if role not in ROLES:
                return False, "Chức vụ không hợp lệ"
            s["role"] = role
        if models is not None:
            s["models"] = [str(m) for m in models if str(m).strip()]
        if active is not None:
            s["active"] = bool(active)
        if phong_ban is not None:
            s["phong_ban"] = _phong_hop_le(phong_ban)
        _save(d)
        return True, _view(s)
    return False, "Không tìm thấy nhân viên"


def _phong_hop_le(ids) -> list:
    """Chỉ giữ id phòng còn trong sổ phòng ban, bỏ trùng, giữ thứ tự admin chọn (phòng đầu
    là brain mặc định của nhân viên)."""
    try:
        import h2o_departments
        return h2o_departments.valid_ids(ids)
    except Exception:
        return []


def remove(sid: str):
    d = _doc()
    n0 = len(d["staff"])
    d["staff"] = [s for s in d["staff"] if s.get("id") != sid]
    d["sessions"] = {t: v for t, v in d["sessions"].items() if v.get("sid") != sid}
    if len(d["staff"]) == n0:
        return False, "Không tìm thấy nhân viên"
    _save(d)
    _drop_avatar_files(sid)
    return True, None


# ---- Ảnh đại diện (hiện trong khung hologram khi nhân viên gọi Joyce) ----
# File nằm ở STATE_DIR/staff_avatars/<id>.<ext>; record chỉ giữ `avatar_v` (mốc thời
# gian) để trình duyệt bỏ cache khi đổi ảnh. Định dạng nhận diện bằng CHỮ KÝ FILE, không
# tin đuôi tên hay content-type client gửi lên: chỉ ảnh raster, không SVG (SVG mang được
# script, mà ảnh này được phục vụ cùng origin với dashboard).
AVATAR_DIR = cfgmod.STATE_DIR / "staff_avatars"
AVATAR_MAX = 3 * 1024 * 1024
AVATAR_MIME = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}
_ID_RE = re.compile(r"^st_[a-z0-9-]+_[0-9a-f]{6}$")


def _sniff(data: bytes):
    if data[:8] == bytes.fromhex("89504e470d0a1a0a"):
        return "png"
    if data[:3] == bytes.fromhex("ffd8ff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return None


def _drop_avatar_files(sid: str) -> None:
    if not _ID_RE.match(str(sid or "")):
        return
    for ext in AVATAR_MIME:
        try:
            (AVATAR_DIR / f"{sid}.{ext}").unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass


def avatar_file(sid: str):
    """(path, mime) của ảnh nhân viên, hoặc (None, None)."""
    if not _ID_RE.match(str(sid or "")):
        return None, None
    for ext, mime in AVATAR_MIME.items():
        p = AVATAR_DIR / f"{sid}.{ext}"
        if p.is_file():
            return p, mime
    return None, None


def set_avatar(sid: str, data: bytes):
    """(ok, err|record). data rỗng = xoá ảnh."""
    d = _doc()
    rec = next((s for s in d["staff"] if s.get("id") == sid), None)
    if not rec or not _ID_RE.match(str(sid)):
        return False, "Không tìm thấy nhân viên"
    if not data:
        _drop_avatar_files(sid)
        rec.pop("avatar_v", None)
        _save(d)
        return True, _view(rec)
    if len(data) > AVATAR_MAX:
        return False, "Ảnh quá lớn (tối đa 3MB)"
    ext = _sniff(data)
    if not ext:
        return False, "Chỉ nhận ảnh PNG, JPG, WEBP hoặc GIF"
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    _drop_avatar_files(sid)
    (AVATAR_DIR / f"{sid}.{ext}").write_bytes(data)
    rec["avatar_v"] = int(time.time())
    _save(d)
    return True, _view(rec)


def verify(sdt: str, pin: str):
    """SĐT + PIN đúng và tài khoản còn active -> record, sai -> None."""
    s = by_sdt(sdt)
    if not s or not s.get("active", True):
        return None
    h, _ = cfgmod.hash_password(str(pin or ""), s.get("pin_salt"))
    if secrets.compare_digest(h, s.get("pin_hash") or ""):
        return s
    return None


# ---- Phiên nhân viên (cookie h2o_staff) ----
def new_session(sid: str) -> str:
    d = _doc()
    tok = secrets.token_urlsafe(32)
    d["sessions"][tok] = {"sid": sid, "ts": time.time()}
    _save(d)
    return tok


def staff_by_token(token: str):
    """Token -> record nhân viên (còn hạn + còn active), sai -> None."""
    if not token:
        return None
    d = _doc()
    v = d["sessions"].get(token)
    if not v:
        return None
    if time.time() - float(v.get("ts") or 0) > SESSION_TTL:
        d["sessions"].pop(token, None)
        _save(d)
        return None
    s = get(v.get("sid"))
    if not s or not s.get("active", True):
        return None
    return s


def drop_session(token: str) -> None:
    d = _doc()
    if d["sessions"].pop(token, None) is not None:
        _save(d)


def channel_of(staff: dict) -> str:
    """Kênh phiên chat riêng của nhân viên: 'staff:<id>'. Phiên nhân viên chỉ
    hiện trong lịch sử của chính họ (và admin, vì danh sách mặc định không loại
    kênh này - admin vẫn soi được việc của team)."""
    return "staff:" + str((staff or {}).get("id") or "")


def model_allowed(staff: dict, prov: str, model: str) -> bool:
    """Cặp provider:model có nằm trong danh sách được cấp không.
    Danh sách rỗng = admin chưa phân quyền = dùng tất cả (giữ hành vi cũ).
    Mục 'prov:*' = mọi model của provider đó."""
    allowed = [m for m in (staff or {}).get("models") or []]
    if not allowed:
        return True
    prov = str(prov or "").strip()
    model = str(model or "").strip()
    key = prov + ":" + model
    for m in allowed:
        m = str(m).strip()
        if not m:
            continue
        if m.endswith(":*"):
            if m[:-2] == prov:
                return True
        elif m == key:
            return True
    return False


def workspace_dir(staff: dict) -> Path:
    """Thư mục làm việc riêng: STATE_DIR/staff_workspaces/<id>."""
    p = cfgmod.STATE_DIR / "staff_workspaces" / str((staff or {}).get("id") or "")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p
