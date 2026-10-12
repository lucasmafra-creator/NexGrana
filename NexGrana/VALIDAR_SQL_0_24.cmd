@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>&1
if errorlevel 1 (
  echo Node.js nao encontrado. Instale Node.js antes do teste SQL local.
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 exit /b 1
if not exist "node_modules\@electric-sql\pglite" (
  call npm ci --ignore-scripts
  if errorlevel 1 exit /b 1
)
call npm run test:sql
if errorlevel 1 exit /b 1
echo Migrations e isolamento local testados em PGlite. Ainda aplique e teste no Supabase QA.
exit /b 0
