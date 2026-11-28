@echo off
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
setlocal EnableDelayedExpansion

rem ============================================================
rem  CampusSphere Dev Shutdown (project root entry)
rem  Delegates to scripts\devctl.py down: graceful stop first, then
rem  force kill on timeout, and verifies ports 8000 / 5173 released.
rem
rem  Usage:
rem    stop-dev.bat                      stop backend + frontend
rem    stop-dev.bat --force              skip graceful stop, force kill
rem    stop-dev.bat --purge-logs         also delete run logs
rem    stop-dev.bat --backend-only       backend only
rem  Any other args are forwarded to devctl.py down.
rem ============================================================

set "ROOT=%~dp0"
python "%ROOT%scripts\devctl.py" down %*
exit /b %ERRORLEVEL%
