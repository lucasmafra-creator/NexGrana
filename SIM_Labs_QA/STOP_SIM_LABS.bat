@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0STOP_SIM_LABS_WINDOWS.ps1"
if errorlevel 1 echo FALHA: parada QA nao concluida.
pause
