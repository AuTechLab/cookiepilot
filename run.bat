@echo off
chcp 65001 >nul
title CookiePilot
echo ===================================================
echo   Starting CookiePilot...
echo ===================================================
cd /d "%~dp0"

py gui.py
if %ERRORLEVEL% NEQ 0 (
    python gui.py
)
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Could not start CookiePilot.
    pause
)
