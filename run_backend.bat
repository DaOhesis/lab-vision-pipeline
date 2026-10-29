@echo off
title IoT Lab - 1. FastAPI Backend
setlocal enabledelayedexpansion
cd /d "%~dp0backend"

echo =====================================================================
echo          IoT Lab Vision Pipeline - FastAPI Backend Server
echo =====================================================================
echo.

set "PY_EXE=%~dp0backend\venv\Scripts\python.exe"
if not exist "%PY_EXE%" (
    set "PY_EXE=python"
)

echo [*] Using Python: "%PY_EXE%"
echo [*] Starting Uvicorn on http://0.0.0.0:8000 ...
echo.

"%PY_EXE%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

if errorlevel 1 (
    echo.
    echo [ERROR] FastAPI Backend stopped with an error!
    pause
)
