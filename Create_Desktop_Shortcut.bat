@echo off
title Create Desktop Shortcut - AI-DeFi Risk Intelligence v2
cd /d "%~dp0"

echo =========================================================================
echo       🔗 Creating Desktop Shortcut for AI-DeFi Risk Intelligence v2
echo =========================================================================
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0create_shortcut.ps1"

echo.
echo =========================================================================
echo  ✅ Process Finished.
echo =========================================================================
echo.
pause
