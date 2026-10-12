@echo off
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
 echo Execute INICIAR_SIM_LABS.bat primeiro.
 pause
 exit /b 1
)
backend\.venv\Scripts\python.exe -m pip install pyinstaller
if errorlevel 1 exit /b 1
backend\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --name SIM_Labs --distpath . --workpath .runtime\exe-build --specpath .runtime scripts\windows_launcher.py
if errorlevel 1 exit /b 1
echo Executavel gerado: SIM_Labs.exe. E um iniciador; mantenha a pasta completa.
pause
