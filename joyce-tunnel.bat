@echo off
chcp 65001 >nul
title Joyce Tunnel - mo dashboard ra internet
cd /d "%~dp0"

echo.
echo  Dang mo tunnel Cloudflare ve http://localhost:7777 ...
echo.
echo  TIM DONG "https://....trycloudflare.com" BEN DUOI - do la link mo tu dien thoai.
echo  Cua so nay phai mo suot - dong no la link chet. Link doi moi lan chay.
echo.
"%~dp0tools\cloudflared.exe" tunnel --url http://localhost:7777
pause
