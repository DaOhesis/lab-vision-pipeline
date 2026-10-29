@echo off
title IoT Lab - 2. Next.js Dashboard
setlocal enabledelayedexpansion
cd /d "%~dp0frontend"

echo =====================================================================
echo          IoT Lab Vision Pipeline - Next.js Dashboard
echo =====================================================================
echo.
echo [*] Starting Next.js Dev Server on http://localhost:3000 ...
echo.

npm run dev

if errorlevel 1 (
    echo.
    echo [ERROR] Next.js frontend stopped with an error!
    pause
)
