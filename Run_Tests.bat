@echo off
title AI-DeFi Risk Intelligence v2.0 - Test Suite
cd /d "%~dp0"

echo =========================================================================
echo       🧪 Running AI-DeFi Risk Intelligence v2.0 Test Suite
echo =========================================================================
echo.

IF NOT EXIST "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found! Please run Install_Setup.bat first.
    pause
    exit /b
)

set PYTHONPATH=.
venv\Scripts\python.exe -m pytest tests/ -v --tb=short

echo.
echo =========================================================================
echo  ✅ Test Run Complete.
echo =========================================================================
pause
