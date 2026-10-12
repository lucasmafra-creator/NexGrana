@echo off
setlocal
cd /d "%~dp0"
call VALIDAR_0_24.cmd
if errorlevel 1 exit /b 1
if not defined NEX_FLUTTER_ROOT set "NEX_FLUTTER_ROOT=%USERPROFILE%\flutter\3.44.8"
if not exist "%NEX_FLUTTER_ROOT%\bin\flutter.bat" (
  echo Flutter nao encontrado. Confira a pasta NEX_FLUTTER_ROOT.
  exit /b 1
)
".venv\Scripts\python.exe" build_multiplataforma.py windows --flutter "%NEX_FLUTTER_ROOT%" --timeout 7200
if errorlevel 1 exit /b 1
echo Confira o executavel e os logs na pasta dist antes de distribuir.
exit /b 0
