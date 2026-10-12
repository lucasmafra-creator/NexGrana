@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Primeiro prepare a copia isolada do SIM Labs conforme o roteiro.
 exit /b 1
)
".venv\Scripts\python.exe" scripts\publish_offer_catalog.py
exit /b %errorlevel%
