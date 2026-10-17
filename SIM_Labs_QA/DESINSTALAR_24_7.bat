@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0DESINSTALAR_24_7.ps1"
pause
