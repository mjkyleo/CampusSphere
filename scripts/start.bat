@echo off
chcp 65001 >nul
rem CampusSphere 一键启动（Windows 快捷入口）
rem 实际逻辑见 scripts\devctl.py，本文件仅做转发，参数原样透传。
rem 例：scripts\start.bat --backend-only --wait-timeout 120

set "ROOT=%~dp0.."
python "%ROOT%\scripts\devctl.py" up %*
exit /b %ERRORLEVEL%
