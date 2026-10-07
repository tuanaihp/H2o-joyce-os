@echo off
chcp 65001 >nul
title Tu khoi dong Joyce OS
REM Tu khoi dong Joyce cung Windows. Dung: joyce-autostart.bat install | uninstall | status
REM Logic nam trong joyce-autostart.ps1 (ghi/xoa Run key HKCU "JoyceOS" - CUNG entry voi
REM cong tac "Tu bat Joyce" trong trang Cai dat, khong can quyen admin). Bat roi thi dang
REM nhap may, sau 5 phut server tu chay nen (start-joyce-delayed.vbs ngu 300s roi moi goi
REM start-joyce.vbs).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0joyce-autostart.ps1" %1
