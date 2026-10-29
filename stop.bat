@echo off
setlocal
echo ========================================================
echo   Stopping all IoT Lab Vision Pipeline Services
echo ========================================================

REM Free ports 8000 and 3000 using PowerShell
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Write-Host 'Killing PID' $_; Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"

REM Close any CMD windows titled IoT Lab
taskkill /F /FI "WINDOWTITLE eq IoT Lab*" >nul 2>&1

echo.
echo [OK] All services and ports have been cleared.
echo ========================================================
pause
