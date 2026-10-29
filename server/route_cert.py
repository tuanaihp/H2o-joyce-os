"""Chứng nhận đường thực thi và ghi dữ liệu (B03, Joyce Harness, gói B): bản kê TRUNG THỰC, không phải lời hứa.

Plan (mục B03): mỗi đường mà một lượt agent có thể ghi hay tác động ra ngoài phải có: ai là chủ thể, quyền lấy từ đâu, kiểm ở đâu và test nào
chứng minh. Chưa đủ thì ghi `chua_chung_nhan` kèm khoảng hở, KHÔNG tuyên bố cùng mức bảo vệ chỉ vì engine cũng nối MCP Hub.

Trạng thái:
- `chung_nhan`: có chủ thể, nguồn quyền theo từng thao tác, nơi kiểm và test. Hiện KHÔNG có đường nào đạt (quyền theo thao tác là việc G2).
- `mot_phan`: một lớp (thường là chính sách đường dẫn) có kiểm và test, nhưng chưa có ủy quyền theo thao tác và tham số.
- `chua_chung_nhan`: không có chốt bắt buộc nào do Joyce kiểm, hoặc chưa có bằng chứng.

Bản kê này là dữ liệu cho Sơ đồ và cho test chặn trượt: test dò các route HTTP ghi file trực tiếp và đòi mỗi route phải có tên trong
`ROUTE_GHI_TRUC_TIEP`; thêm một route ghi file mới mà chưa phân loại là test đỏ. Cách dò chỉ thấy ghi TRỰC TIẾP trong thân hàm route,
không lần theo hàm phụ, nên số này là CẬN DƯỚI, không phải toàn bộ bề mặt ghi.
"""
from __future__ import annotations

from typing import Dict, List

TRANG_THAI = ("chung_nhan", "mot_phan", "chua_chung_nhan")

# (id, mô tả, chủ thể, nguồn quyền, nơi kiểm, test, trạng thái, khoảng hở)
_HANG = [
    ("hub_write_file", "Tool joyce_write_file qua MCP Hub (mọi engine)",
     "engine chạy dưới brain đang mở; từ 1.3.43 host đặt ngữ cảnh (run_context) cho lượt của bot, việc giao trợ lý và bước workflow",
     "allowed_effects trong file agent (internal_write) NẾU agent đã khai; agent chưa khai thì chỉ chính sách đường dẫn",
     "mcp_hub._write -> run_context.cho_phep rồi file_policy.deny_reason (giải lại đích, chặn sources/, symlink, tạo độc quyền)",
     "tests/python/test_g2_ngu_canh_quyen.py và tests/python/test_fix03_file_guard.py", "mot_phan",
     "Chỉ agent ĐÃ KHAI allowed_effects mới bị kiểm quyền (phần lớn chưa khai); chat trực tiếp với Joyce và các route khác chạy không ngữ cảnh; chưa có grant theo tham số; deny_reason trả None ngoài brain không phải cho phép."),
    ("hub_other_tools", "Các tool khác của MCP Hub (gửi tin, đặt hàng, đăng bài, Zalo, Messenger...)",
     "engine chạy dưới brain đang mở; từ 1.3.45 lượt chạy của chat, bot, việc và workflow mang ngữ cảnh do host đặt",
     "mức quyền của phiên (suggest, auto, full) VÀ `allowed_effects` của agent nếu đã khai (hub_effect: read, internal_write, external_write, destructive)",
     "mcp_hub._boc_quyen (mọi tool, hỏi lúc GỌI) cùng mức quyền và joyce-guard", "tests/python/test_g2_hub_hoi_quyen.py", "mot_phan",
     "Chỉ agent ĐÃ khai allowed_effects bị kiểm (phần lớn chưa khai); hub phân loại effect thô (read, write, danger), chưa có grant theo tham số; xác nhận tuỳ từng tool."),
    ("run_command", "Tool joyce_run_command (một lệnh shell có rào)",
     "engine chạy dưới brain đang mở", "mức quyền phiên: suggest không chạy, auto theo allowlist, full chạy đầy đủ",
     "run_command.py (allowlist, trần thời gian và output, env lọc)", "", "chua_chung_nhan",
     "Mức full chạy đầy đủ và không đi qua file_policy: có thể ghi vào sources/ hay ngoài brain. Chưa có sandbox chỉ-đọc."),
    ("cli_native", "Công cụ ghi và shell NATIVE của Claude Code, Codex, Grok Build, Antigravity",
     "chính CLI engine", "cấu hình quyền của từng CLI (Joyce truyền cờ cho phép, ví dụ bypassPermissions ở Grok)",
     "không có chốt của Joyce trên đường này", "", "chua_chung_nhan",
     "Không đi qua MCP Hub nên không qua file_policy. Chỉ nên coi là chạy được trên route pilot nếu CLI chạy chỉ-đọc trong sandbox hoặc bị tắt."),
    ("plugin_inproc", "Plugin Python chạy trong tiến trình server",
     "mã plugin (tin cậy)", "người dùng bật JOYCE_ENABLE_USER_PLUGINS; plugin hệ thống đi kèm app",
     "plugins_host (bật tắt, min_mode); hook không kiểm được ghi trực tiếp của plugin", "", "chua_chung_nhan",
     "Plugin ghi file trực tiếp không bị hook chặn. Phải là mã đã audit hoặc cô lập."),
    ("http_dashboard", "Route HTTP của dashboard ghi file trực tiếp (xem ROUTE_GHI_TRUC_TIEP)",
     "chủ đã đăng nhập hoặc nhân viên theo phạm vi brain", "phiên đăng nhập",
     "middleware đăng nhập; từng route tự kiểm đường dẫn", "tests/python/test_b03_chung_nhan_route.py (chỉ bảo đảm phân loại)", "chua_chung_nhan",
     "Không route nào gọi file_policy. Đường ghi gián tiếp qua hàm phụ chưa được lần theo."),
    ("customer_bot", "Bot trả lời khách (Telegram, Zalo, Messenger) và công cụ của nó",
     "agent gắn với bot, quyền theo muc_quyen của bot", "cấu hình bot",
     "chatbot_runtime (muc_quyen, im lặng, tiếp quản), reply policy", "tests/python/test_bot_toan_quyen_khong_lo.py", "chua_chung_nhan",
     "Callback và kênh bot chưa chứng minh không kế thừa quyền chủ qua ngữ cảnh môi trường; chưa có grant theo thao tác."),
    ("loop_reminder", "Loop và nhắc việc chạy nền do Joyce lập",
     "agent của brain, mức quyền full mặc định cho việc chủ giao", "mức quyền ghi trong file loop hoặc nhắc việc",
     "scheduler và hub", "", "chua_chung_nhan",
     "Mặc định full theo quyết định của chủ; chưa có grant theo thao tác."),
]

REGISTRY: List[dict] = [dict(zip(("id", "mo_ta", "chu_the", "nguon_quyen", "noi_kiem", "test", "trang_thai", "khoang_ho"), h)) for h in _HANG]

# Route HTTP có mã ghi file TRỰC TIẾP trong thân hàm (cận dưới). Thêm một route ghi file mới mà không khai ở đây là test đỏ.
ROUTE_GHI_TRUC_TIEP = frozenset({
    "/brain/migrate", "/brains/delete", "/skills/toggle", "/skills", "/skills/delete", "/files/rename", "/hands/profile",
    "/agents/tags/rename", "/plugins/scaffold", "/plugins/source", "/branding/logo", "/branding/logo/reset",
    "/sessions/{session_id}/rename",
})


def tom_tat() -> Dict[str, int]:
    """Đếm cho Sơ đồ: số đường theo trạng thái."""
    out = {"chung_nhan": 0, "mot_phan": 0, "chua_chung_nhan": 0, "tong": len(REGISTRY)}
    for r in REGISTRY:
        out[r["trang_thai"]] += 1
    return out
