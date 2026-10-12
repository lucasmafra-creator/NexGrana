@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALAR_24_7.ps1" -AtBoot
exit /b %errorlevel%
