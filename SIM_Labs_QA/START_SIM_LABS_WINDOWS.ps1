param([switch]$NoBrowser, [switch]$KeepRunning, [int]$Port = 0)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$ExpectedService = "sim-labs-control-center-qa"
$ExpectedPhase = "Engine 0.4.1-qa.2"
$InstanceText=$Root.Replace('\','/').ToLowerInvariant().TrimEnd('/')
$InstanceId=[System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($InstanceText))).Replace('-','').ToLowerInvariant().Substring(0,16)
$Runtime = Join-Path $Root ".runtime"
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null
$PortFile = Join-Path $Runtime "qa_port.txt"
Write-Host "SIM Labs QA 0.4.1-qa.2 - preparando a central local" -ForegroundColor Cyan
if (Get-Command py -ErrorAction SilentlyContinue) { $Launcher = "py" } elseif (Get-Command python -ErrorAction SilentlyContinue) { $Launcher = "python" } else { throw "Python nao encontrado. Instale Python 3.11+ e habilite o PATH." }
if (-not (Test-Path "backend/.venv/Scripts/python.exe")) {
  if ($Launcher -eq "py") { & py -3 -m venv backend/.venv } else { & python -m venv backend/.venv }
  if ($LASTEXITCODE -ne 0) { throw "Falha ao criar ambiente Python." }
}
$Py = (Resolve-Path "backend/.venv/Scripts/python.exe").Path
$ReqHash = (Get-FileHash "backend/requirements.txt" -Algorithm SHA256).Hash
$Stamp = Join-Path $Runtime "requirements.sha256"
if (-not (Test-Path $Stamp) -or (Get-Content $Stamp -Raw).Trim() -ne $ReqHash) {
  & $Py -m pip install -r backend/requirements.txt
  if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias. Verifique internet e a versao do Python." }
  Set-Content -Path $Stamp -Value $ReqHash -Encoding ASCII
}

function Confirm-LocalLogin {
  & $Py (Join-Path $Root "scripts/validate_qa_startup.py")
  if ($LASTEXITCODE -ne 0) { throw "A instancia respondeu, mas o login local nao foi validado. Use INICIAR.cmd > Reparar acesso; a senha nao foi alterada." }
}

function Test-ExpectedHealth([int]$CandidatePort) {
  try {
    $Health = Invoke-RestMethod -Uri ("http://127.0.0.1:"+$CandidatePort+"/api/v1/health") -TimeoutSec 2
    return ($null -ne $Health -and $Health.status -eq "ok" -and $Health.service -eq $ExpectedService -and $Health.phase -eq $ExpectedPhase -and $Health.instance_id -eq $InstanceId)
  } catch { return $false }
}

function Test-PortAvailable([int]$CandidatePort) {
  $Listener = $null
  try {
    $Listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $CandidatePort)
    $Listener.Start()
    return $true
  } catch { return $false }
  finally { if ($null -ne $Listener) { try { $Listener.Stop() } catch {} } }
}

# Choose a stable QA port without touching another service. Prefer the last QA
# port, then 8000, then a bounded local fallback range.
$Candidates = New-Object System.Collections.Generic.List[int]
if ($Port -gt 0) { $Candidates.Add($Port) }
if (Test-Path -LiteralPath $PortFile) {
  $SavedRaw=(Get-Content -LiteralPath $PortFile -Raw -ErrorAction SilentlyContinue).Trim()
  $SavedPort=0
  if ([int]::TryParse($SavedRaw,[ref]$SavedPort) -and $SavedPort -ge 1024 -and $SavedPort -le 65535 -and -not $Candidates.Contains($SavedPort)) { $Candidates.Add($SavedPort) }
}
if (-not $Candidates.Contains(8000)) { $Candidates.Add(8000) }
for ($p=8011; $p -le 8099; $p++) { if (-not $Candidates.Contains($p)) { $Candidates.Add($p) } }

$SelectedPort=0
foreach ($Candidate in $Candidates) {
  if ($Candidate -lt 1024 -or $Candidate -gt 65535) { continue }
  if (Test-PortAvailable $Candidate) { $SelectedPort=$Candidate; break }
  if (Test-ExpectedHealth $Candidate) {
    Set-Content -LiteralPath $PortFile -Value $Candidate -Encoding ASCII
    Write-Host ("A central QA desta pasta ja esta aberta na porta "+$Candidate+".") -ForegroundColor Green
    Write-Host "Credencial local preservada em .runtime\PRIMEIRO_ACESSO.txt (valor nao exibido)." -ForegroundColor DarkGray
    Confirm-LocalLogin
    if (-not $NoBrowser) { Start-Process ("http://127.0.0.1:"+$Candidate) }
    if (-not $KeepRunning) { exit 0 }

    # In 24/7 mode the scheduled-task wrapper must remain attached to the
    # supervisor. If the supervisor dies, exit non-zero so Task Scheduler can
    # honor RestartCount/RestartInterval. If the API is still alive but the
    # recorded supervisor is gone, treat the children as QA-owned orphans:
    # stop only processes verified by stop_local.py, then rebuild the stack.
    $Owned=$null
    $OwnedPid=0
    if (Test-Path "$Runtime/supervisor.pid") {
      $PidRaw=(Get-Content "$Runtime/supervisor.pid" -Raw -ErrorAction SilentlyContinue).Trim()
      [void][int]::TryParse($PidRaw,[ref]$OwnedPid)
      if ($OwnedPid -gt 0) { $Owned=(Get-CimInstance Win32_Process -Filter "ProcessId=$OwnedPid" -ErrorAction SilentlyContinue) }
    }
    $OwnedCmd=if($Owned){$Owned.CommandLine}else{""}
    if ($Owned -and $OwnedCmd -like "*$Root*" -and $OwnedCmd -like "*app.supervisor*") {
      Write-Host ("Modo 24/7 acompanhando supervisor PID "+$OwnedPid+".") -ForegroundColor DarkGray
      Wait-Process -Id $OwnedPid -ErrorAction SilentlyContinue
      Write-Host "Supervisor QA encerrou; solicitando reinicio da tarefa agendada." -ForegroundColor Yellow
      exit 1
    }

    Write-Host "Health QA ativo sem supervisor valido; recuperando somente processos desta copia QA." -ForegroundColor Yellow
    & $Py (Join-Path $Root "backend/stop_local.py")
    if ($LASTEXITCODE -ne 0) { throw "Falha ao limpar processos QA orfaos com verificacao de propriedade." }
    $Freed=$false
    for ($w=0; $w -lt 20; $w++) {
      if (Test-PortAvailable $Candidate) { $Freed=$true; break }
      Start-Sleep -Seconds 1
    }
    if (-not $Freed) { throw ("A porta "+$Candidate+" continua ocupada apos a recuperacao segura; nada externo foi encerrado.") }
    $SelectedPort=$Candidate
    break
  }
}
if ($SelectedPort -eq 0) { throw "Nenhuma porta local segura disponivel entre 8000 e 8099 para esta copia QA." }
if ($SelectedPort -ne 8000) { Write-Host ("Porta 8000 ocupada por outro servico/copia. QA usara porta "+$SelectedPort+" sem encerrar o outro processo.") -ForegroundColor Yellow }
Set-Content -LiteralPath $PortFile -Value $SelectedPort -Encoding ASCII
$env:SIM_LABS_PORT=[string]$SelectedPort
$BaseUrl="http://127.0.0.1:"+$SelectedPort

Push-Location backend
try {
  & $Py -m app.bootstrap
  if ($LASTEXITCODE -ne 0) { throw "Falha na preparacao local QA. Consulte os logs sem expor segredos." }
} finally { Pop-Location }

$Out = Join-Path $Runtime "supervisor.log"
$Err = Join-Path $Runtime "supervisor.err.log"
$Proc = Start-Process -FilePath $Py -ArgumentList "-m","app.supervisor" -WorkingDirectory (Join-Path $Root "backend") -WindowStyle Hidden -RedirectStandardOutput $Out -RedirectStandardError $Err -PassThru
$Ok = $false
$StartupTimeoutSeconds = 180
for ($i=0; $i -lt $StartupTimeoutSeconds; $i++) {
  $Proc.Refresh()
  if ($Proc.HasExited) { throw "Supervisor QA encerrou antes da API ficar pronta. Revise os logs seguros exibidos pelo reparador." }
  Start-Sleep -Seconds 1
  try {
    $Health=Invoke-RestMethod -Uri ($BaseUrl+"/api/v1/health") -TimeoutSec 2
    if ($Health.status -eq "ok" -and $Health.service -eq $ExpectedService -and $Health.phase -eq $ExpectedPhase -and $Health.instance_id -eq $InstanceId) { $Ok=$true; break }
  } catch {}
  if (($i % 15) -eq 0) { Write-Host ("Aguardando API QA ficar pronta... ("+$i+"/"+$StartupTimeoutSeconds+" s)") -ForegroundColor DarkGray }
}
if (-not $Ok) { throw ("API QA nao ficou saudavel em "+$StartupTimeoutSeconds+" segundos na porta "+$SelectedPort+". O reparador exibira os ultimos logs seguros.") }
Write-Host ("Central QA pronta: "+$BaseUrl) -ForegroundColor Green
Write-Host "Health, service, phase e instance_id desta pasta confirmados." -ForegroundColor Green
Write-Host "Credencial local preservada em .runtime\PRIMEIRO_ACESSO.txt (valor nao exibido)." -ForegroundColor DarkGray
Confirm-LocalLogin
if (-not $NoBrowser) { Start-Process $BaseUrl }
if ($KeepRunning) { Wait-Process -Id $Proc.Id -ErrorAction SilentlyContinue; exit 1 }
