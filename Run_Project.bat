@echo off
title AI-DeFi Risk Intelligence v2.0 — Wallet Explorer
cd /d "%~dp0"

echo =========================================================================
echo        AI-DeFi Risk Intelligence Platform v2.0
echo        Wallet Address Explorer  +  Bento Station Dashboard
echo =========================================================================
echo.

IF NOT EXIST "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run 'Install_Setup.bat' first to setup dependencies.
    echo.
    pause
    exit /b
)

echo [1/2] Starting FastAPI backend on http://127.0.0.1:8000 ...
echo       Press CTRL+C to stop the server.
echo.

:: Start the server in the background, wait for it to be ready, then open browser
start "" /B venv\Scripts\python.exe -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload

echo Waiting for server to initialize...
timeout /t 3 /nobreak >nul

echo [2/2] Opening Wallet Explorer in your default browser...
start http://127.0.0.1:8000/

echo.
echo =========================================================================
echo  Server running at:   http://127.0.0.1:8000/
echo  Wallet Explorer:     http://127.0.0.1:8000/dashboard
echo  API Docs (Swagger):  http://127.0.0.1:8000/docs
echo  Health Check:        http://127.0.0.1:8000/api/health
echo =========================================================================
echo.
echo Press any key to stop the server...
pause >nul

:: Kill the uvicorn process when user presses a key
taskkill /F /IM python.exe /FI "WINDOWTITLE eq AI-DeFi*" >nul 2>&1
