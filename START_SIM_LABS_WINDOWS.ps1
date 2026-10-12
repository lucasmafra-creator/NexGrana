param([switch]$NoBrowser, [switch]$KeepRunning)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$InstanceText=$Root.Replace('\','/').ToLowerInvariant().TrimEnd('/')
$InstanceId=[System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($InstanceText))).Replace('-','').ToLowerInvariant().Substring(0,16)
$Runtime = Join-Path $Root ".runtime"
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
Write-Host "SIM Labs integrado 0.4.0 - preparando a central local" -ForegroundColor Cyan
if (Get-Command py -ErrorAction SilentlyContinue) { $Launcher = "py" } elseif (Get-Command python -ErrorAction SilentlyContinue) { $Launcher = "python" } else { throw "Python nao encontrado. Instale Python 3.11+ e habilite o PATH." }
if (-not (Test-Path "backend/.venv/Scripts/python.exe")) {
  if ($Launcher -eq "py") { & py -3 -m venv backend/.venv } else { & python -m venv backend/.venv }
  if ($LASTEXITCODE -ne 0) { throw "Falha ao criar ambiente Python." }
}
$Py = (Resolve-Path "backend/.venv/Scripts/python.exe").Path
$ReqHash = (Get-FileHash "backend/requirements.txt" -Algorithm SHA256).Hash
$Stamp = Join-Path $Runtime "requirements.sha256"
if (-not (Test-Path $Stamp) -or (Get-Content $Stamp) -ne $ReqHash) {
  & $Py -m pip install -r backend/requirements.txt
  if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias. Verifique internet e a versao do Python." }
  Set-Content $Stamp $ReqHash
}
# Do not stop arbitrary PIDs: ask the running API if this same service is already up.
try {
 $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 2
 if ($Health.service -eq "sim-labs-control-center" -and $Health.phase -eq "Engine 0.4.0" -and $Health.instance_id -eq $InstanceId) {
   Write-Host "A central ja esta aberta." -ForegroundColor Green
   if (Test-Path "$Runtime/PRIMEIRO_ACESSO.txt") { Get-Content "$Runtime/PRIMEIRO_ACESSO.txt" }
   if (-not $NoBrowser) { Start-Process "http://127.0.0.1:8000" }
   if ($KeepRunning -and (Test-Path "$Runtime/supervisor.pid")) {
     $OwnedPid=[int](Get-Content "$Runtime/supervisor.pid")
     $OwnedCmd=(Get-CimInstance Win32_Process -Filter "ProcessId=$OwnedPid").CommandLine
     if ($OwnedCmd -like "*$Root*" -and $OwnedCmd -like "*app.supervisor*") { Wait-Process -Id $OwnedPid -ErrorAction SilentlyContinue }
   }
   exit 0
 }
 throw "A porta 8000 pertence a outro servico. Pare esse servico ou a versao antiga antes de iniciar."
} catch {
 if ($_.Exception.Message -like "A porta 8000*") { throw }
}
Push-Location backend
& $Py -m app.bootstrap
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Falha na preparacao do banco. Consulte a mensagem acima." }
Pop-Location
$Out = Join-Path $Runtime "supervisor.log"
$Err = Join-Path $Runtime "supervisor.err.log"
$Proc = Start-Process -FilePath $Py -ArgumentList "-m","app.supervisor" -WorkingDirectory (Join-Path $Root "backend") -WindowStyle Hidden -RedirectStandardOutput $Out -RedirectStandardError $Err -PassThru
$Ok = $false
for ($i=0; $i -lt 30; $i++) {
 Start-Sleep -Seconds 1
 try { $Health=Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/health" -TimeoutSec 2; if ($Health.phase -eq "Engine 0.4.0" -and $Health.instance_id -eq $InstanceId) { $Ok=$true; break } } catch {}
}
if (-not $Ok) { throw "Nao foi possivel iniciar a API. Veja .runtime/api.err.log e .runtime/supervisor.err.log." }
Write-Host "Central pronta: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Use ABRIR_COLLECTOR.bat para enviar feedbacks com evidencias." -ForegroundColor Green
Write-Host "Fechar esta janela ou o navegador nao para a central. Use PARAR_SIM_LABS.bat." -ForegroundColor DarkGray
if (-not $NoBrowser) { Start-Process "http://127.0.0.1:8000" }

if ($KeepRunning) { Wait-Process -Id $Proc.Id -ErrorAction SilentlyContinue; exit 1 }
