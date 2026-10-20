"""Tự khởi động cùng Windows: bật rồi mà không chạy thì phải NÓI RA vì sao.

    python tests/run.py autostart      (KHÔNG mạng, không đụng registry thật)

Chủ repo gửi ảnh chụp trình duyệt sau khi mở máy (2026-08-09): `localhost:7777` trả
ERR_CONNECTION_REFUSED, kèm "hình như chức năng mở Joyce cùng máy startup đang không hoạt động".

Cả tính năng này nằm gọn trong một dòng registry `HKCU\\...\\Run` trỏ `wscript start-joyce.vbs`.
Dashboard đọc đúng dòng đó rồi kết luận "Bật". Vấn đề: dòng đó CÒN NGUYÊN trong ít nhất ba
cảnh mà lúc đăng nhập vẫn không có gì chạy, và không cảnh nào để lại lỗi ở đâu:

  1. **Task Manager tắt hộ.** Thẻ Startup không xoá mục trong Run key, nó ghi một cờ 12 byte
     vào `Explorer\\StartupApproved\\Run` rồi Explorer bỏ qua mục đó. Mấy phần mềm "dọn máy,
     tăng tốc khởi động" cũng tắt bằng đúng cờ này. Đây là cảnh im lặng nhất trong ba.
  2. **Thư mục cài đặt đổi chỗ**, lệnh trỏ đường dẫn cũ. Trạng thái đã tính sẵn cờ `stale` từ
     lâu, nhưng trang Cài đặt bỏ qua nó, nên cùng một máy hỏng mà hai trang nói khác nhau.
  3. **Mảnh của dây chuyền biến mất** (`start-joyce.vbs` hoặc `.venv\\Scripts\\python.exe`).
     `wscript` không thấy file .vbs thì im, còn `cmd` ghi lỗi vào `joyce.log` - một file không
     ai mở ra xem bao giờ.

File này canh phần LOGIC (chạy được trên Linux của CI) và canh việc dashboard thật sự hiện lý
do ra. Phần đọc/ghi registry chỉ có trên Windows nên không mô phỏng ở đây; đổi lại, mọi quyết
định đều nằm trong các hàm thuần dưới đây chứ không nhét trong nhánh `winreg`.
"""
from _paths import ROOT, SERVER
import json  # noqa: E402,F401
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("JOYCE_STATE_DIR", tempfile.mkdtemp(prefix="joyce-autostart-"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import main  # noqa: E402

_fails = []


def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        _fails.append(name)


# ============================================================
# 1. Cờ StartupApproved: đọc theo BIT, không so bằng
# ============================================================
def _co(byte_dau):
    return bytes([byte_dau] + [0] * 11)


check("cờ 3 = Task Manager đã tắt mục này", main._autostart_bi_chan(_co(3)) is True)
check("cờ 2 = đang bật", main._autostart_bi_chan(_co(2)) is False)
# Windows dùng cả 6 cho trạng thái bật, nên so bằng 2 là đọc sai một nửa số máy.
check("CANARY: cờ 6 cũng là đang bật (so bằng 2 là đọc sai)",
      main._autostart_bi_chan(_co(6)) is False)
check("không có cờ = chưa ai tắt", main._autostart_bi_chan(None) is False)
check("cờ rỗng cũng là chưa ai tắt", main._autostart_bi_chan(b"") is False)
check("cờ hỏng thì không nổ", main._autostart_bi_chan("linh tinh") is False)


# ============================================================
# 2. Thiếu mảnh nào của dây chuyền khởi động
# ============================================================
_tmp = Path(tempfile.mkdtemp(prefix="joyce-goc-"))
check("thư mục trống -> thiếu cả hai mảnh",
      set(main._autostart_thieu_gi(_tmp)) == {r"tools\joyce_boot.py", r".venv\Scripts\pythonw.exe"})

(_tmp / "tools").mkdir()
(_tmp / "tools" / "joyce_boot.py").write_text("# bo mo phong", encoding="utf-8")
check("có joyce_boot.py rồi -> chỉ còn thiếu pythonw của venv",
      main._autostart_thieu_gi(_tmp) == [r".venv\Scripts\pythonw.exe"])

(_tmp / ".venv" / "Scripts").mkdir(parents=True)
(_tmp / ".venv" / "Scripts" / "pythonw.exe").write_text("x", encoding="utf-8")
check("đủ cả hai -> không thiếu gì", main._autostart_thieu_gi(_tmp) == [])
check("lệnh task: pythonw chạy thẳng joyce_boot.py, không .vbs",
      main._autostart_command(_tmp) == f'"{_tmp / ".venv" / "Scripts" / "pythonw.exe"}" "{_tmp / "tools" / "joyce_boot.py"}"'
      and ".vbs" not in main._autostart_command(_tmp))


# ============================================================
# 2b. Đọc trạng thái task (schtasks /v /fo list) - 1.3.25
# ============================================================
_OUT = """Folder: \
HostName:                             MAY
TaskName:                             \JoyceOS-AutoStart
Next Run Time:                        21/10/2026 7:05:00 AM
Status:                               Ready
Last Run Time:                        21/10/2026 7:00:01 AM
Last Result:                          0
Task To Run:                          "E:\J\.venv\Scripts\pythonw.exe" "E:\J\tools\joyce_boot.py"
Scheduled Task State:                 Enabled
"""
_t = main._autostart_doc_task(_OUT)
check("đọc được Last Run / Last Result / Next Run", _t["last_result"] == "0" and _t["last_run"].startswith("21/10/2026 7:00")
      and _t["next_run"].startswith("21/10/2026 7:05"))
check("đọc được lệnh task + trạng thái bật", "joyce_boot.py" in _t["task_to_run"] and _t["state"] == "Enabled")
check("task bị Disable -> tính là bị chặn", main._autostart_task_tat("Disabled") and not main._autostart_task_tat("Enabled"))
_ly = main._autostart_ly_do({"enabled": True, "legacy": True})
check("còn đường .vbs cũ -> nói rõ 360 tắt và khuyên bật lại", "360" in _ly and "bật lại" in _ly)
_ly = main._autostart_ly_do({"enabled": True, "task": {"exists": True, "last_run": "x", "last_result": "0x80070005"}})
check("task chạy xịt (Access Denied) -> báo mã lỗi", "0x80070005" in _ly)
check("task chưa chạy lần nào (0x41303) không bị coi là lỗi",
      main._autostart_ly_do({"enabled": True, "task": {"exists": True, "last_run": "x", "last_result": "0x41303"}}) == "")


# ============================================================
# 3. Lý do: một câu nói thẳng, và ĐÚNG THỨ TỰ ưu tiên
# ============================================================
check("chưa bật thì không có lý do nào để báo",
      main._autostart_ly_do({"enabled": False, "blocked": True}) == "")

_ly = main._autostart_ly_do({"enabled": True, "blocked": True})
check("bị Windows chặn -> nói rõ chặn ở đâu", "Task Manager" in _ly)
check("và chỉ luôn cách gỡ", "bật lại" in _ly)

_ly = main._autostart_ly_do({"enabled": True, "stale": True})
check("đường dẫn cũ -> nói rõ là đổi chỗ", "đổi chỗ" in _ly and "bật lại" in _ly.casefold())

_ly = main._autostart_ly_do({"enabled": True, "missing": ["start-joyce.vbs"]})
check("thiếu file -> gọi tên đúng file thiếu", "start-joyce.vbs" in _ly)
check("và chỉ luôn cách dựng lại", "setup.bat" in _ly)

check("bật và mọi thứ ổn -> im lặng, không doạ người dùng",
      main._autostart_ly_do({"enabled": True, "blocked": False, "stale": False,
                             "missing": []}) == "")

# Chặn thắng stale: gỡ chặn xong mới tới lượt lo đường dẫn, chứ sửa đường dẫn trong khi
# Windows vẫn chặn thì bấm bao nhiêu lần cũng không chạy.
_ly = main._autostart_ly_do({"enabled": True, "blocked": True, "stale": True,
                             "missing": ["start-joyce.vbs"]})
check("nhiều lỗi cùng lúc -> báo cái phải sửa TRƯỚC", "Task Manager" in _ly)

for _st in ({"enabled": True, "blocked": True}, {"enabled": True, "stale": True},
            {"enabled": True, "missing": ["x"]}):
    check(f"lý do không dùng em dash ({list(_st)[-1]})", "—" not in main._autostart_ly_do(_st))


# ============================================================
# 4. Bật lại phải THẬT SỰ gỡ được chặn, không chỉ ghi lại Run key
# ============================================================
# Ghi lại Run key không đụng gì tới cờ StartupApproved. Thiếu bước gỡ cờ thì nút "Bật tự khởi
# động" trở thành một cái nút không làm gì: bấm xong thẻ vẫn báo bật, mở máy vẫn không có gì.
_MAIN_SRC = (Path(SERVER) / "main.py").read_text(encoding="utf-8")
check("CANARY 1.3.25: bật lại dọn Run key + 2 task .vbs cũ rồi mới cài task mới",
      "winreg.DeleteValue(k, _AUTOSTART_NAME)" in _MAIN_SRC and "_autostart_task_uninstall()" in _MAIN_SRC
      and "_autostart_task_install()" in _MAIN_SRC)
check("task mới cài theo /sc minute /mo 5, không dùng ONLOGON",
      '"/sc", "minute", "/mo", "5"' in _MAIN_SRC and "onlogon" not in _MAIN_SRC.split("def _autostart_task_install", 1)[1][:600].lower())
check("bật mà không tạo được task thì báo lỗi, không im lặng báo Bật",
      "Không tạo được task tự khởi động" in _MAIN_SRC)
check("trạng thái trả về kèm đường dẫn log để còn chỗ mà soi",
      '"log": str(PROJECT_ROOT / "server" / "joyce.log")' in _MAIN_SRC)


# ============================================================
# 5. Dashboard phải HIỆN lý do đó ra, ở CẢ HAI trang
# ============================================================
# Trang Tổng quan và trang Cài đặt cùng đọc một endpoint. Bản trước trang Cài đặt bỏ qua hẳn cờ
# `stale`, nên cùng một máy hỏng mà mở hai trang thì đọc được hai câu trả lời khác nhau.
_JS = (ROOT / "dashboard" / "console.js").read_text(encoding="utf-8")
check("CANARY: cả hai trang đều hiện `ly_do`", _JS.count("j.ly_do") >= 2)
# Nhãn đã vào từ điển i18n (0.55.14). Kiểm hai vế: console.js gọi khoá ở CẢ HAI trang (Tổng
# quan và Hệ thống), và cả hai khoá đều còn nói đúng sự thật "bật nhưng không chạy".
_VI = json.loads((ROOT / "dashboard" / "i18n" / "vi.json").read_text(encoding="utf-8"))
check("nhãn nói thật khi bật mà không chạy được",
      all(k in _JS and "bật nhưng không chạy" in _VI.get(k, "").casefold()
          for k in ("cs.ov_auto_broken", "cs.st_auto_broken")))
check("dashboard KHÔNG tự dựng lại câu lý do (server là nguồn duy nhất)",
      "Task Manager" not in _JS)

# ============================================================
# 6. Đang "bật nhưng không chạy" thì nút phải là BẬT LẠI, không phải Tắt
# ============================================================
# Câu lý do bảo "bấm bật lại để gỡ chặn" mà nút duy nhất trên thẻ ghi "Tắt tự khởi động" thì
# người dùng phải tự đoán ra hai cú bấm Tắt rồi Bật. Máy chủ dự án đứng đúng cảnh này gần hai
# tháng (cờ StartupApproved lật từ 24/07, phát hiện 17/09).
check("cả hai thẻ dùng nhãn Bật lại khi hỏng", _JS.count('"cs.ov_auto_btn_fix"') >= 2)
check("hỏng thì gửi enabled=1 chứ không phải tắt", _JS.count('(on && !hong) ? "0" : "1"') >= 2)
check("nhãn Bật lại có trong từ điển", "cs.ov_auto_btn_fix" in _VI)

if _fails:
    raise SystemExit(f"\nFAIL - test_autostart_windows: {len(_fails)} lỗi")
print("\nOK - test_autostart_windows: tất cả pass")
