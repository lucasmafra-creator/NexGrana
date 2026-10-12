$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Py=Join-Path $Root 'backend/.venv/Scripts/python.exe'
if(-not (Test-Path $Py)){
  Write-Host 'Ambiente QA ainda nao instalado; nenhum processo foi encerrado.' -ForegroundColor Yellow
  exit 0
}
# stop_local.py verifies command lines and the Python executable path before
# terminating anything. A PID file alone is never trusted.
& $Py (Join-Path $Root 'backend/stop_local.py')
if($LASTEXITCODE -ne 0){ throw 'Falha ao solicitar parada segura da copia QA.' }
Write-Host 'Somente processos comprovadamente pertencentes a esta copia QA foram solicitados para parada.' -ForegroundColor Yellow
