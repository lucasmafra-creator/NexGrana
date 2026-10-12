@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0SIM_Labs_QA\scripts\control_center.py" (
 echo Extraia TODOS os arquivos do ZIP antes de executar INICIAR.cmd.
 pause
 exit /b 2
)
set "PYTHONUTF8=1"
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%~dp0SIM_Labs_QA\scripts\control_center.py" %*
goto done
:python_fallback
where python >nul 2>nul
if errorlevel 1 (
 echo Python nao encontrado. Instale Python 3.11 ou superior com PATH.
 pause
 exit /b 2
)
python "%~dp0SIM_Labs_QA\scripts\control_center.py" %*
:done
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" pause
exit /b %RESULT%
