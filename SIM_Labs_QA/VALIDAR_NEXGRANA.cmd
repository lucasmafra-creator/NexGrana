@echo off
setlocal
if "%~1"=="" (
 echo Uso: VALIDAR_NEXGRANA.cmd "C:\NG24_RC6_WORK\NexGrana"
 exit /b 2
)
set "NEX_DIR=%~f1"
set "NEX_PY=%NEX_DIR%\.venv\Scripts\python.exe"
if not exist "%NEX_PY%" (
 echo Ambiente Python do NexGrana ausente. Prepare .venv com as dependencias fixadas.
 exit /b 1
)
if not exist "%~dp0.venv\Scripts\python.exe" (
 echo Prepare o ambiente do SIM Labs primeiro.
 exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\nexgrana_runner.py" "%NEX_DIR%" --python "%NEX_PY%" --allow-trusted-code --report "%~dp0nexgrana-run-report.json"
exit /b %errorlevel%
