@echo off
chcp 65001 >nul
title Khoi dong Joyce OS
cd /d "%~dp0"

echo Bat Joyce OS chay NEN - khong con cua so den (port 7777)...
REM Viec tat instance cu + chay server AN giao het cho start-joyce.vbs (cua so an hoan toan).
REM Log ghi vao server\joyce.log (mo file do neu can xem loi). Tat server: stop-joyce.bat.
wscript //nologo start-joyce.vbs

echo.
echo Da bat. Cho ~10 giay roi mo http://localhost:7777 va bam Ctrl+Shift+R.
echo (Tat server: chay stop-joyce.bat. Xem loi: mo file server\joyce.log)
timeout /t 4 >nul
