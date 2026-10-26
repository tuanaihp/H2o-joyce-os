@echo off
chcp 65001 >nul
title Joyce Xe Hoi - server + tunnel mot cu bam
cd /d "%~dp0"

REM ============================================================
REM  JOYCE XE HOI: truoc khi ra xe, double-click file nay.
REM    1) Joyce OS tu chay nen neu chua bat (y het "Joyce OS.bat").
REM    2) Mo tunnel Cloudflare -> in link https://....trycloudflare.com
REM  Mo link do tren dien thoai (Chrome/Safari), dang nhap, bam mic
REM  goi Joyce; cap Bluetooth xe de Joyce noi qua loa xe.
REM  CU SO NAY PHAI MO SUOT - dong no la link chet. Link doi moi lan chay.
REM ============================================================

if "%JOYCE_PORT%"=="" set JOYCE_PORT=7777
set "URL=http://127.0.0.1:%JOYCE_PORT%"

curl -sf -m 2 -o nul %URL%/health 2>nul
if %errorlevel%==0 goto :tunnel

echo Dang bat Joyce OS (chay nen, log o server\joyce.log)...
wscript //nologo start-joyce.vbs

echo Cho server len (toi da ~45 giay)...
set /a _w=0
:wait
curl -sf -m 2 -o nul %URL%/health 2>nul
if %errorlevel%==0 goto :tunnel
set /a _w+=1
if %_w% gtr 45 goto :fail
timeout /t 1 /nobreak >nul
goto :wait

:fail
echo.
echo  KHONG BAT DUOC SERVER - mo "Joyce OS.bat" tren may tinh de xem loi.
pause
exit /b 1

:tunnel
echo.
echo  Dang mo tunnel + gui link vao Telegram (tools\tunnel_notify.py)...
.venv\Scripts\python.exe tools\tunnel_notify.py
echo.
echo  ================================================================
echo   Link moi nhat (neu chua thay):
type tools\tunnel-last.json 2>nul | findstr trycloudflare
echo.
echo   Link cung DA BAY VAO TELEGRAM - mo tele tren dien thoai bam link.
echo   Dang nhap Joyce -> bam MIC goi. Cat Bluetooth xe de noi qua LOA XE.
echo  ================================================================
pause
