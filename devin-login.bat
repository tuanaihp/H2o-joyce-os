@echo off
chcp 65001 >nul
title Dang nhap Devin CLI (lam 1 lan)
echo.
echo  Chon "1 - Log in with browser" - trinh duyet se mo, dang nhap xong quay lai day.
echo  Chi can lam MOT LAN, credentials luu lai dung cho Joyce goi Devin nen.
echo.
"E:\CLAUDECODE\DEVIN\Devin\resources\app\extensions\windsurf\devin\bin\devin.exe" auth login
echo.
"E:\CLAUDECODE\DEVIN\Devin\resources\app\extensions\windsurf\devin\bin\devin.exe" auth status
pause
