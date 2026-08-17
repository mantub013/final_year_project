@echo off
title AI-DeFi Risk Intelligence Setup
cd /d "%~dp0"

echo =========================================================================
echo       🛡️ AI-DeFi Risk Intelligence Platform - Installation Setup
echo =========================================================================
echo.

echo [1/3] Checking for Python installation...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH! Please install Python 3.11+.
    pause
    exit /b
)

echo [2/3] Setting up Virtual Environment...
IF NOT EXIST "venv" (
    python -m venv venv
    echo Virtual environment created.
) ELSE (
    echo Virtual environment already exists.
)

echo [3/3] Installing dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\pip.exe install -r requirements.txt
venv\Scripts\pip.exe install matplotlib seaborn

echo.
echo =========================================================================
echo  ✅ Setup Complete!
echo  You can now run 'Run_Project.bat' to start the dashboard.
echo =========================================================================
pause
