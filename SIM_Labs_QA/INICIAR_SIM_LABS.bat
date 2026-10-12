@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0START_SIM_LABS_WINDOWS.ps1"
if errorlevel 1 echo FALHA: leia a mensagem acima e envie um print para o Work.
pause
