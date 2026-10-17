@echo off
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
 echo Primeiro execute INICIAR_SIM_LABS.bat.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m app.backup_local
pause
