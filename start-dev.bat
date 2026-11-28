@echo off
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
setlocal EnableDelayedExpansion

rem ============================================================
rem  CampusSphere Dev Startup (project root entry)
rem  Delegates to scripts\devctl.py up with --reload (uvicorn hot reload).
rem  Frontend Vite has its own HMR, no extra flag needed.
rem
rem  Usage:
rem    start-dev.bat                     start backend + frontend
rem    start-dev.bat --backend-only      backend only
rem    start-dev.bat --force             kill stale port holders first
rem    start-dev.bat --no-wait           skip health check wait
rem  Any other args are forwarded to devctl.py up.
rem ============================================================

set "ROOT=%~dp0"
python "%ROOT%scripts\devctl.py" up --reload %*
exit /b %ERRORLEVEL%
