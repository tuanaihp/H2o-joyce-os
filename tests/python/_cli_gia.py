"""Dựng một lệnh CLI giả mà subprocess chạy được trên CẢ Windows lẫn Linux.

Vì sao có file này: file không đuôi có dòng `#!/usr/bin/env python3` chạy ngon trên Linux (CI),
nhưng Windows không hiểu shebang nên ném `WinError 193: %1 is not a valid Win32 application`.
Trên Windows thì ghi `<ten>_impl.py` (mã thật) và `<ten>.cmd` gọi đúng trình Python đang chạy
test. Trả về đường dẫn lệnh để truyền thẳng vào code cần kiểm.
"""
import os
import stat
import sys
from pathlib import Path


def ghi_cli(p: Path, than: str) -> str:
    """Ghi mã `than` thành lệnh chạy được tại `p` (hoặc `p.cmd` trên Windows). Trả về đường dẫn lệnh."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        impl = p.with_name(p.name + "_impl.py")
        impl.write_text(than, encoding="utf-8")
        cmd = p.with_name(p.name + ".cmd")
        # PYTHONUTF8: open() mặc định của Windows là cp1252, nên lệnh giả in tiếng Việt sẽ vỡ.
        # _base_executable: python thật, không qua trampoline của venv. Trampoline giữ bản sao ống
        # stdout nên khi giết .cmd thì lượt đọc vẫn treo tới hết giờ.
        exe = getattr(sys, "_base_executable", None) or sys.executable
        cmd.write_text(f'@echo off\r\nset PYTHONUTF8=1\r\n"{exe}" "{impl}" %*\r\n', encoding="utf-8")
        return str(cmd)
    p.write_text(than, encoding="utf-8")
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return str(p)


def ghi_lai_cli(cli: str, than: str) -> None:
    """Ghi lại mã của một lệnh giả đã dựng bằng ghi_cli (dùng khi test đổi nội dung giữa chừng).
    Trên Windows `cli` là `<ten>.cmd` nên phần mã nằm ở `<ten>_impl.py`."""
    if os.name == "nt" and cli.lower().endswith(".cmd"):
        Path(cli[:-4] + "_impl.py").write_text(than, encoding="utf-8")
        return
    Path(cli).write_text(than, encoding="utf-8")
