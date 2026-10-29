@echo off
title IoT Lab Vision Pipeline - Master Launcher
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =====================================================================
echo          IoT Lab Vision Pipeline - All-In-One Launcher
echo =====================================================================
echo.

REM 1. Determine Python executable (prefer backend virtual environment)
set "PY_EXE=%~dp0backend\venv\Scripts\python.exe"
if not exist "%PY_EXE%" (
    set "PY_EXE=python"
)

echo [*] Checking Python runtime...
"%PY_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python or setup backend\venv.
    pause
    exit /b 1
)
echo [OK] Using Python: %PY_EXE%

REM 2. Check Node.js / NPM
echo [*] Checking Node.js runtime...
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found in PATH! Please install Node.js.
    pause
    exit /b 1
)
echo [OK] Node.js and npm detected.

REM 3. Check / Start Local Ollama LLM Service
echo [*] Checking Ollama LLM service (http://localhost:11434)...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -TimeoutSec 2 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    where ollama >nul 2>&1
    if not errorlevel 1 (
        echo [*] Ollama not running. Launching background Ollama service...
        start "IoT Lab - Ollama Service" /min ollama serve
        timeout /t 2 /nobreak >nul
    ) else (
        echo [WARNING] Ollama CLI not found in PATH. LLM features will use rule fallback.
    )
) else (
    echo [OK] Ollama service is active.
)

REM 4. Launch FastAPI Backend in a dedicated window
echo.
echo [*] Starting FastAPI Computer Vision Backend (Port 8000)...
start "IoT Lab - 1. FastAPI Backend" cmd /k "cd /d ""%~dp0backend"" && title IoT Lab - 1. FastAPI Backend && ""%PY_EXE%"" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM 5. Launch Next.js Dashboard in a dedicated window
echo [*] Starting Next.js Real-Time Telemetry Dashboard (Port 3000)...
start "IoT Lab - 2. Next.js Dashboard" cmd /k "cd /d ""%~dp0frontend"" && title IoT Lab - 2. Next.js Dashboard && npm run dev"

REM 6. Wait for services and launch web browser
echo.
echo [*] Waiting for web dashboard to initialize...
powershell -NoProfile -Command "for ($i = 0; $i -lt 30; $i++) { try { $res = Invoke-WebRequest -Uri 'http://localhost:3000' -TimeoutSec 1 -UseBasicParsing; if ($res.StatusCode -eq 200) { exit 0 } } catch {}; Start-Sleep -Milliseconds 800 }; exit 1" >nul 2>&1

echo [*] Opening browser to http://localhost:3000...
start http://localhost:3000

echo.
echo =====================================================================
echo  [SUCCESS] All components are running!
echo =====================================================================
echo   - Web Dashboard:     http://localhost:3000 (Webcam runs inside browser)
echo   - FastAPI Backend:   http://localhost:8000
echo   - API Swagger Docs:  http://localhost:8000/docs
echo   - Local LLM:         http://localhost:11434 (Qwen 2.5 1.5B)
echo.
echo   To stop all services cleanly at any time, run: stop.bat
echo =====================================================================
echo.
pause
