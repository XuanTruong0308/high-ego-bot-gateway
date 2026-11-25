@echo off
chcp 65001 >nul
title HEe Discord Suite Manager
color 0C

echo ========================================================
echo    HIGH EGO ESPORT (HEe) — DISCORD BOT SUITE RUNNER
echo ========================================================
echo.

set "ROOT_DIR=D:\bot_disc_hee"

echo [1/3] Khoi dong HEe Gatekeeper (Welcome/Goodbye)...
start "HEe • Gatekeeper" cmd /k "cd /d %ROOT_DIR%\hee_welcome_builder && .venv\Scripts\python.exe bot.py"

timeout /t 2 /nobreak >nul

echo [2/3] Khoi dong HEe Chronicle (Rank & XP)...
start "HEe • Chronicle" cmd /k "cd /d %ROOT_DIR%\hee_rank && .venv\Scripts\python.exe bot.py"

timeout /t 2 /nobreak >nul

echo [3/3] Khoi dong HEe Sentinel (AutoMod & Quick Delete)...
start "HEe • Sentinel" cmd /k "cd /d %ROOT_DIR%\hee_mod && .venv\Scripts\python.exe bot.py"

echo.
echo ========================================================
echo   DA KHOI DONG THANH CONG CA 3 BOT O CAC CUA SO RIENG!
echo   Moi cua so co the xem logs truc tiep.
echo   De tat toan bo bot, chay file: stop_all.bat
echo ========================================================
echo.
pause
