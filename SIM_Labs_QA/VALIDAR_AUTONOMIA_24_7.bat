@echo off
setlocal EnableExtensions
cd /d "%~dp0"
net session >nul 2>&1
if errorlevel 1 (
  echo Solicitando permissao de administrador para validar a tarefa 24/7...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File ""%~dp0VALIDAR_AUTONOMIA_24_7.ps1""'"
  set "RC=%ERRORLEVEL%"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0VALIDAR_AUTONOMIA_24_7.ps1"
  set "RC=%ERRORLEVEL%"
)
echo.
if "%RC%"=="0" (
  echo RESULTADO: autonomia 24/7 aprovada.
) else (
  echo RESULTADO: autonomia 24/7 nao aprovada. Nenhum processo externo deve ter sido encerrado.
)
pause
exit /b %RC%
