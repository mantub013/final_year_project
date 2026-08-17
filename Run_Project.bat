@echo off
title AI-DeFi Risk Intelligence - Streamlit Dashboard
cd /d "%~dp0"

echo =========================================================================
echo       🛡️ AI-DeFi Risk Intelligence Platform (Streamlit)
echo =========================================================================
echo.
echo Starting the Streamlit Dashboard...
echo.

venv\Scripts\streamlit.exe run app.py

echo.
pause
