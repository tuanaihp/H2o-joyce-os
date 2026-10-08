@echo off
chcp 65001 >nul
title Dung Joyce OS
echo Dang tim va tat Joyce OS...
REM Logic giet nam trong stop-joyce.ps1 (giet theo dung python cua venv + chu port 7777).
REM KHONG dung timeout o day: chay an qua VBS se loi "Input redirection is not supported".
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-joyce.ps1"
REM Don cua so CMD den "Joyce OS" kieu cu con sot (flow moi chay an, khong tao cua so nay).
taskkill /F /FI "IMAGENAME eq cmd.exe" /FI "WINDOWTITLE eq Joyce OS*" >nul 2>&1
REM Tat luon tunnel Cloudflare: khoi dong lai se co link trycloudflare MOI gui qua Telegram.
taskkill /F /IM cloudflared.exe >nul 2>&1
REM Co pause cho watchdog: stop-joyce la hanh dong CO CHU DINH cua nguoi dung nen
REM JoyceOS-Watchdog (10 phut/lan) khong duoc tu song lai. start-joyce.vbs xoa co nay.
echo %DATE% %TIME% > "%~dp0server\.joyce-paused"
echo Xong.
exit /b 0
