@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Ambiente .venv ausente. Instale as dependencias fixadas neste projeto.
 exit /b 1
)
if "%~1"=="" (
 echo Uso: COMPILAR_QA.cmd windows ou apk ou both
 exit /b 2
)
".venv\Scripts\python.exe" -m unittest discover -s tests -q
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" build_multiplataforma.py "%~1"
exit /b %errorlevel%
