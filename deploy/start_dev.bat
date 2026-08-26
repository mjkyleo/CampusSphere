@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

rem ============================================================
rem  CampusSphere - One-click Dev Startup Script
rem  - Kills stale processes occupying ports 8000 / 5173
rem  - Starts backend (uvicorn) + frontend (Express/Vite proxy)
rem ============================================================

set "ROOT=%~dp0.."
set "BACKEND_DIR=%ROOT%\backend"
set "FRONTEND_DIR=%ROOT%\frontend"

echo [1/4] Checking runtime prerequisites...
where python >nul 2>&1 || (echo [ERROR] python not found in PATH & exit /b 1)
where npm >nul 2>&1 || (echo [ERROR] npm not found in PATH & exit /b 1)

echo [2/4] Stopping stale processes on ports 8000 / 5173 ...
call :kill_port 8000
call :kill_port 5173
call :kill_log_holders
ping -n 2 127.0.0.1 >nul

echo [3/4] Starting backend + frontend (logs: backend\uvicorn.log / frontend\vite.log)...
start "campus-backend" /b cmd /c "cd /d %BACKEND_DIR% && python -m uvicorn app.asgi:app --host 127.0.0.1 --port 8000 >> uvicorn.log 2>&1"
start "campus-frontend" /b cmd /c "cd /d %FRONTEND_DIR% && npm run dev >> vite.log 2>&1"

echo [4/4] Waiting for services to become healthy...
set /a tries=0
:wait_backend
set /a tries+=1
if !tries! gtr 40 (echo [ERROR] Backend failed to start. Check backend\uvicorn.log & exit /b 1)
powershell -NoProfile -Command "$r=try{(Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2).StatusCode}catch{0}; if($r -eq 200){exit 0}else{exit 1}" >nul 2>&1
if errorlevel 1 (ping -n 2 127.0.0.1 >nul & goto wait_backend)

set /a tries=0
:wait_frontend
set /a tries+=1
if !tries! gtr 80 (echo [ERROR] Frontend failed to start. Check frontend\vite.log & exit /b 1)
powershell -NoProfile -Command "$r=try{(Invoke-WebRequest -Uri 'http://127.0.0.1:5173' -UseBasicParsing -TimeoutSec 2).StatusCode}catch{0}; if($r -eq 200){exit 0}else{exit 1}" >nul 2>&1
if errorlevel 1 (ping -n 2 127.0.0.1 >nul & goto wait_frontend)

echo.
echo ============================================================
echo  CampusSphere is ready:
echo    Frontend : http://localhost:5173
echo    Backend  : http://127.0.0.1:8000  (API docs: /docs)
echo    Admin    : admin / admin123  (change password after login)
echo    Verify code: dev mode auto-fills on the login page
echo    Logs     : backend\uvicorn.log / frontend\vite.log
echo ============================================================
pause
exit /b 0

:kill_port
set "port=%~1"
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%port% " ^| findstr "LISTENING"') do (
  echo   Killing stale PID %%p on port %port%
  taskkill /F /PID %%p >nul 2>&1
)
exit /b 0

::kill_log_holders
rem Kill stale wrapper cmd/python processes that still hold uvicorn.log / vite.log handles.
set "PS1=%TEMP%\cs_kill_log_holders.ps1"
> "%PS1%" echo $p = Get-CimInstance Win32_Process ^| Where-Object { $_.Name -in 'cmd.exe','python.exe' -and $_.CommandLine -match 'uvicorn\.log|vite\.log' } ^| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" >nul 2>&1
del "%PS1%" >nul 2>&1
exit /b 0
