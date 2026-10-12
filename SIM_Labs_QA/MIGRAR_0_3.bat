@echo off
cd /d "%~dp0"
if "%~1"=="" (
 echo Uso: MIGRAR_0_3.bat "C:\pasta\SIM_Labs_Integrado_0_3_0"
 pause
 exit /b 1
)
if exist "backend\.venv\Scripts\python.exe" (
 "backend\.venv\Scripts\python.exe" scripts\migrate_03.py "%~1"
) else (
 py -3 scripts\migrate_03.py "%~1"
)
pause
