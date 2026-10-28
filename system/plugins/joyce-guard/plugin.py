"""Plugin bundled: chốt chặn bằng LUẬT CỐ ĐỊNH chạy trước mỗi lời gọi tool (hook pre_tool_call).

Chuẩn Joyce Harness mục 9 và rollout giai đoạn 0A (chủ chốt 28/10/2026). Không gọi model, không tốn
quota: mỗi luật là một phép so chuỗi hoặc đếm. Hook bọc MỌI tool đi qua MCP Hub (tool của Joyce,
plugin, MCP đã nối), ở mọi engine. Tool native của CLI (Bash, Write của Claude Code) không đi qua
đây; ranh giới đó do quyền của phiên lo.

Ba luật:
1. File: `sources/` là tài liệu gốc bất biến. Ghi file MỚI vào đó được (skill notes cần), ghi ĐÈ
   file đã có thì không. Ghi vào `Memory/` viết hoa bị chặn: trên Linux đó là thư mục khác với
   `memory/`, ghi vào là mất trí nhớ trong im lặng.
2. Zalo: người không phải chủ (tin từ kênh ngoài) gửi tối đa 3 tin mỗi 10 phút; việc nền không rõ
   người gọi tối đa 30 tin mỗi 10 phút mỗi brain (phanh vòng lặp chạy loạn). Chủ không bị giới hạn.
3. Sổ Shop: khoản chi từ 5 triệu đồng phải gắn hợp đồng (`khach`) hoặc ghi rõ `hang_muc`, để Đối
   Soát còn biết khoản đó thuộc đâu.

Luật lỗi thì tool vẫn chạy (plugins_host fail-open có chủ ý); mỗi luật tự bắt lỗi của mình.
"""
from __future__ import annotations

import re
import threading
import time
from collections import deque

ZALO_CUA_KHACH = 3          # tin mỗi cửa sổ, người không phải chủ
ZALO_VIEC_NEN = 30          # tin mỗi cửa sổ, việc nền không rõ người gọi, mỗi brain
ZALO_CUA_SO_S = 600
CHI_LON = 5_000_000         # đồng
_ZALO_GUI = re.compile(r"(?:^|_)zalo_send_(?:message|image|mention)$")


def luat_file(args, vault_root):
    """Lời báo SỚM cho model. Chốt bắt buộc nằm ở `mcp_hub._write` (FIX-03): hook này fail-open theo thiết kế của
    plugins_host nên không được là chốt duy nhất. Cả hai dùng CHUNG `file_policy` và CHUNG bộ giải đường dẫn của
    tool ghi (`mcp_hub._safe_path`), để mọi cách viết cùng một file cho cùng một kết quả."""
    if not vault_root:
        return None
    raw = (args or {}).get("path")
    if not str(raw or "").strip():
        return None
    try:
        import file_policy
        import mcp_hub
    except Exception:      # noqa: BLE001 - không nạp được chính sách thì TỪ CHỐI, không đoán
        return "Không nạp được chính sách ghi file nên từ chối để an toàn."
    try:
        dich = mcp_hub._safe_path(vault_root, raw)
    except ValueError:
        return None        # ngoài brain: tool ghi tự quyết (thư mục làm việc của phiên Coding)
    except Exception:      # noqa: BLE001
        return file_policy.MSG_KHONG_XAC_DINH
    return file_policy.deny_reason(vault_root, dich)


class _DemZalo:
    def __init__(self):
        self._lock = threading.Lock()
        self._q: dict = {}

    def thu(self, khoa, tran, now=None) -> bool:
        """Còn hạn mức thì ghi một lượt và trả True; hết thì trả False, không ghi."""
        now = time.time() if now is None else now
        with self._lock:
            q = self._q.setdefault(khoa, deque())
            while q and now - q[0] > ZALO_CUA_SO_S:
                q.popleft()
            if len(q) >= tran:
                return False
            q.append(now)
            return True


def luat_zalo(dem: _DemZalo, turn, vault_root, now=None):
    if turn and turn.get("la_chu"):
        return None
    if turn:
        khoa = ("khach", str(turn.get("kenh") or ""), str(turn.get("sender_id") or turn.get("chat_id") or ""))
        if not dem.thu(khoa, ZALO_CUA_KHACH, now):
            return (f"Người không phải chủ chỉ được nhờ gửi tối đa {ZALO_CUA_KHACH} tin Zalo mỗi "
                    f"{ZALO_CUA_SO_S // 60} phút. Không gửi thêm; báo người hỏi rằng chủ sẽ xem và gửi.")
        return None
    if not dem.thu(("nen", str(vault_root or "")), ZALO_VIEC_NEN, now):
        return (f"Việc nền đã gửi {ZALO_VIEC_NEN} tin Zalo trong {ZALO_CUA_SO_S // 60} phút, dấu hiệu "
                "vòng lặp chạy loạn. Dừng gửi, ghi lại danh sách còn lại vào báo cáo để chủ xem.")
    return None


def _so(v) -> float:
    try:
        return float(str(v).replace(".", "").replace(",", "")) if isinstance(v, str) else float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def luat_shop(args):
    a = args or {}
    if str(a.get("op") or "").strip().lower() != "ghi":
        return None
    sk = a.get("su_kien")
    if isinstance(sk, dict):
        sk = [sk]
    if not isinstance(sk, list):
        return None
    thieu = []
    for e in sk:
        if not isinstance(e, dict) or str(e.get("loai") or "").strip().lower() != "chi":
            continue
        if _so(e.get("so_tien")) < CHI_LON:
            continue
        if str(e.get("khach") or "").strip() or str(e.get("hang_muc") or "").strip():
            continue
        thieu.append(f"{_so(e.get('so_tien')):,.0f}đ".replace(",", "."))
    if not thieu:
        return None
    return (f"Khoản chi {', '.join(thieu)} từ {CHI_LON // 1_000_000} triệu trở lên mà chưa gắn hợp đồng "
            "(khach: mã HD, số điện thoại hoặc tên khách) và chưa có hang_muc. Hỏi lại người báo khoản "
            "này thuộc hợp đồng nào; nếu là chi chung (mặt bằng, điện, lương) thì ghi rõ hang_muc rồi gọi lại.")


def register(ctx):
    dem = _DemZalo()

    def _pre(tool_name="", args=None, vault_root=None, turn=None, **_):
        fn = str(tool_name or "")
        if fn == "joyce_run_tool":      # lời gọi thật bên trong cũng đi qua hook, luật áp ở đó
            return None
        ly_do = None
        try:
            if fn == "joyce_write_file":
                ly_do = luat_file(args, vault_root)
            elif _ZALO_GUI.search(fn):
                ly_do = luat_zalo(dem, turn, vault_root)
            elif fn == "joyce_shop":
                ly_do = luat_shop(args)
        except Exception:  # noqa: BLE001 - luật hỏng không khoá tool
            return None
        return {"deny": "[joyce-guard] " + ly_do} if ly_do else None

    ctx.register_hook("pre_tool_call", _pre)
