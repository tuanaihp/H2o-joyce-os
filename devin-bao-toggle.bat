@echo off
chcp 65001 >nul
title Bat/tat tu bao ket qua Devin ve Telegram
set FLAG=%~dp0server\plugins\devin-bridge\auto_bao.flag
set /p cur=<%FLAG% 2>nul
if "%cur%"=="0" ( echo 1>%FLAG% & echo. & echo  Tu bao Telegram: BAT ) else ( echo 0>%FLAG% & echo. & echo  Tu bao Telegram: TAT )
echo  Bam phim bat ky de dong...
pause >nul
