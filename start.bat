@echo off
setlocal
cd /d "%~dp0"

REM Prefer virtual environment Python if available
set "PY_EXE=%~dp0backend\venv\Scripts\python.exe"
if not exist "%PY_EXE%" (
    set "PY_EXE=python"
)

REM Run the unified launcher passing all arguments
"%PY_EXE%" "%~dp0start.py" %*
