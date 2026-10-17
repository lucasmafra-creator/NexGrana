@echo off
setlocal
if "%~1"=="" (
 echo Uso: CONCLUIR_RODADA_QA.cmd "C:\pasta-do-clone-QA\NexGrana" [registrar] [endpoint-loopback-QA]
 exit /b 2
)
set "NEX_QA=%~f1"
set "NEX_QA_PY=%NEX_QA%\.venv\Scripts\python.exe"
if not exist "%NEX_QA_PY%" exit /b 2
if not exist "%~dp0.venv\Scripts\python.exe" exit /b 2
"%NEX_QA_PY%" "%NEX_QA%\VERIFICAR_AMBIENTE_QA.py" --report "%~dp0native-environment-report.json"
if errorlevel 1 (
 echo Build bloqueado. Leia native-environment-report.json e configure ferramentas.
 exit /b 2
)
call "%~dp0VALIDAR_NEXGRANA.cmd" "%NEX_QA%"
if errorlevel 1 exit /b 1
pushd "%~dp0"
".venv\Scripts\python.exe" -m pytest backend\tests -q
if errorlevel 1 (
 popd
 exit /b 1
)
popd
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\verify_nex_assets.py" "%NEX_QA%" --report "%~dp0nex-assets-report.json"
if errorlevel 1 exit /b 1
pushd "%NEX_QA%"
call npm run test:sql
if errorlevel 1 (
 popd
 exit /b 1
)
call COMPILAR_QA.cmd both
set "NEX_QA_RESULT=%errorlevel%"
popd
if not "%NEX_QA_RESULT%"=="0" exit /b %NEX_QA_RESULT%
if /i "%~2"=="registrar" (
 if not exist "%NEX_QA%\dist\latest-successful-build.txt" exit /b 2
 set /p NEX_QA_BUILD=<"%NEX_QA%\dist\latest-successful-build.txt"
 call :registrar "%~3"
 if errorlevel 1 exit /b 1
)
echo Build concluido. Nenhum binario foi instalado ou aberto.
echo Nenhuma migration ou tarefa de boot foi aplicada. Homologacao fisica permanece separada.
exit /b 0

:registrar
set "NEX_QA_API=%~1"
if "%NEX_QA_API%"=="" set "NEX_QA_API=http://127.0.0.1:8000/api/v1"
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\register_latest_build.py" "%NEX_QA_BUILD%" --version 0.24.0-qa-rc8 --target windows --runner-report "%~dp0nexgrana-run-report.json" --endpoint "%NEX_QA_API%" --receipt "%~dp0release-windows-receipt.json"
if errorlevel 1 exit /b 1
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\register_latest_build.py" "%NEX_QA_BUILD%" --version 0.24.0-qa-rc8 --target apk --runner-report "%~dp0nexgrana-run-report.json" --endpoint "%NEX_QA_API%" --receipt "%~dp0release-android-receipt.json"
exit /b %errorlevel%
