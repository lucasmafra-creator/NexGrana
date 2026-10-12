@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.14 -m venv .venv 2>nul
  if errorlevel 1 py -3 -m venv .venv
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
".venv\Scripts\pyinstaller.exe" --noconfirm --clean --onefile --windowed --name "NexGranaUpdateCollector" src\main.py
echo Build em: %CD%\dist\NexGranaUpdateCollector.exe
pause
