@echo off
setlocal
cd /d "%~dp0"
if not exist "requirements.txt" (
  echo ERRO: entre na pasta project extraida do ZIP.
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.14 -m venv .venv
  if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt -r gateway\requirements.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" validate_release.py --full
if errorlevel 1 exit /b 1
echo Validacao Python e seguranca local concluidas. SQL, gateway real e builds exigem verificacao adicional.
exit /b 0
