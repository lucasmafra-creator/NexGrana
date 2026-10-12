@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Inicie a Central primeiro para preparar o ambiente.
  exit /b 1
)
if "%~1"=="" (
  echo Uso: REGISTRAR_BUILD.bat "C:\caminho\NexGrana.exe" "0.24.0-RC7" Windows
  exit /b 2
)
".venv\Scripts\python.exe" scripts\register_release.py "%~1" --version "%~2" --platform "%~3"
exit /b %errorlevel%
