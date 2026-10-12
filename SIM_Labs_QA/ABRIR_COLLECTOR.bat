@echo off
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
 echo Primeiro execute INICIAR_SIM_LABS.bat.
 pause
 exit /b 1
)
"backend\.venv\Scripts\python.exe" Collector\src\main.py
if errorlevel 1 pause
