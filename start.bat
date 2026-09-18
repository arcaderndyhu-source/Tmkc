@echo off
title SERVER GODCLAN V2 • AUTONOMOUS INSTAGRAM MATRIX
color 0c
echo ================================================================
echo             ⚡ SERVER GODCLAN V2 • AUTONOMOUS MATRIX ⚡
echo                   OWNER PASSWORD: SCAR@12345
echo ================================================================
echo.
echo [*] Checking Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found in PATH. Please install Python 3.10+
    pause
    exit /b 1
)

echo [*] Launching SERVER GODCLAN V2 on Port 10000...
echo [*] Dashboard: http://localhost:10000
echo.
python run.py
pause
