@echo off
title AI-DeFi Risk Intelligence - Test Suite
cd /d "%~dp0"

echo =========================================================================
echo       🧪 Running AI-DeFi Risk Intelligence Test Suite
echo =========================================================================
echo.

IF NOT EXIST "venv\Scripts\pytest.exe" (
    echo [ERROR] pytest is not installed! Please run Install_Setup.bat first.
    pause
    exit /b
)

set PYTHONPATH=.
venv\Scripts\pytest.exe tests/ -v --tb=short

echo.
echo =========================================================================
echo  ✅ Test Run Complete.
echo =========================================================================
pause
