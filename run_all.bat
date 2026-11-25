@echo off
chcp 65001 >nul
title HEe Discord Suite Manager
color 0C

echo ========================================================
echo    HIGH EGO ESPORT (HEe) — DISCORD BOT SUITE RUNNER
echo ========================================================
echo.

set "ROOT_DIR=D:\bot_disc_hee"

echo [1/5] Khoi dong HEe Gatekeeper (Welcome/Goodbye)...
start "HEe • Gatekeeper" cmd /k "cd /d %ROOT_DIR%\hee_welcome_builder && .venv\Scripts\python.exe bot.py"

timeout /t 2 /nobreak >nul

echo [2/5] Khoi dong HEe Chronicle (Rank & XP)...
start "HEe • Chronicle" cmd /k "cd /d %ROOT_DIR%\hee_rank && .venv\Scripts\python.exe bot.py"

timeout /t 2 /nobreak >nul

echo [3/5] Khoi dong HEe Sentinel (AutoMod & Penalty Tier)...
start "HEe • Sentinel" cmd /k "cd /d %ROOT_DIR%\hee_mod && .venv\Scripts\python.exe bot.py"

timeout /t 2 /nobreak >nul

echo [4/5] Khoi dong HEe Tribunal (Ticket Support)...
start "HEe • Tribunal" cmd /k "cd /d %ROOT_DIR%\hee_ticket && .venv\Scripts\python.exe bot.py"

timeout /t 2 /nobreak >nul

echo [5/5] Khoi dong HEe Vault (Economy & Daily 1k/diem)...
start "HEe • Vault" cmd /k "cd /d %ROOT_DIR%\hee_economy && .venv\Scripts\python.exe bot.py"

echo.
echo ========================================================
echo   DA KHOI DONG THANH CONG CA 5 BOT O CAC CUA SO RIENG!
echo   Moi cua so co the xem logs truc tiep.
echo   De tat toan bo bot, chay file: stop_all.bat
echo ========================================================
echo.
pause
