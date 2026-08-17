@echo off
title Bento Station - AI-DeFi Risk Intelligence v2.0
cd /d "%~dp0"

echo =========================================================================
echo       🛡️ Bento Station — AI-DeFi Risk Intelligence Platform v2.0
echo =========================================================================
echo.
echo Starting fresh Bento Station server...
echo.

:: Kill any stale process listening on port 8000 to ensure fresh code is loaded
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /R /C:":8000 .*LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

ping 127.0.0.1 -n 2 >nul

echo [1/1] Launching Bento Station Server on http://localhost:8000 ...
start "Bento Station Backend" /min "%~dp0venv\Scripts\python.exe" -m uvicorn api.app:app --host 127.0.0.1 --port 8000 --reload

ping 127.0.0.1 -n 3 >nul

:: Open browser automatically to Bento Station UI
start "" "http://localhost:8000/dashboard"

echo.
echo =========================================================================
echo  ✅ Bento Station is Live!
echo     - Bento Dashboard UI:  http://localhost:8000/dashboard
echo     - API Swagger Docs:   http://localhost:8000/docs
echo =========================================================================
echo.
