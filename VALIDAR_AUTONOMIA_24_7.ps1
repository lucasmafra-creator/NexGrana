$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Runtime=Join-Path $Root '.runtime'
$ExpectedService='sim-labs-control-center-qa'
$ExpectedPhase='Engine 0.4.1-qa.2'
$InstanceText=$Root.Replace('\','/').ToLowerInvariant().TrimEnd('/')
$InstanceId=[System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($InstanceText))).Replace('-','').ToLowerInvariant().Substring(0,16)

function Fail([string]$Message) {
  Write-Host ('AUTONOMIA_24_7=FAIL '+$Message) -ForegroundColor Red
  exit 1
}
function Get-Health([int]$Port) {
  try { return Invoke-RestMethod -Uri ('http://127.0.0.1:'+$Port+'/api/v1/health') -TimeoutSec 2 } catch { return $null }
}
function Is-OwnedSupervisor([int]$ProcessId) {
  if($ProcessId -le 0){ return $false }
  $p=Get-CimInstance Win32_Process -Filter ('ProcessId='+$ProcessId) -ErrorAction SilentlyContinue
  if(-not $p){ return $false }
  return ($p.CommandLine -like ('*'+$Root+'*') -and $p.CommandLine -like '*app.supervisor*')
}

if(-not (Test-Path (Join-Path $Runtime 'task_name.txt'))){ Fail 'task_name.txt ausente' }
if(-not (Test-Path (Join-Path $Runtime 'qa_port.txt'))){ Fail 'qa_port.txt ausente' }
$TaskName=(Get-Content (Join-Path $Runtime 'task_name.txt') -Raw).Trim()
$Port=[int]((Get-Content (Join-Path $Runtime 'qa_port.txt') -Raw).Trim())
$Task=Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if(-not $Task){ Fail 'tarefa agendada nao encontrada' }

# Reload the scheduled action so it uses the current START_SIM_LABS_WINDOWS.ps1.
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5

if(-not (Test-Path (Join-Path $Runtime 'supervisor.pid'))){ Fail 'supervisor.pid ausente antes do teste' }
$OldPid=[int]((Get-Content (Join-Path $Runtime 'supervisor.pid') -Raw).Trim())
if(-not (Is-OwnedSupervisor $OldPid)){ Fail ('PID '+$OldPid+' nao confirmado como supervisor desta copia QA') }
$Before=Get-Health $Port
if(-not $Before -or $Before.status -ne 'ok' -or $Before.service -ne $ExpectedService -or $Before.phase -ne $ExpectedPhase -or $Before.instance_id -ne $InstanceId){ Fail 'health inicial nao corresponde a esta copia QA' }

$StatusPath=Join-Path $Runtime 'status_24_7.json'
if(-not (Test-Path $StatusPath)){ Fail 'status_24_7.json ausente' }
$Status=Get-Content $StatusPath -Raw | ConvertFrom-Json
$Names=@('api','worker','engine')
foreach($Name in $Names){
  $Child=$Status.children.$Name
  if(-not $Child -or -not $Child.alive){ Fail ('filho '+$Name+' nao estava vivo antes do teste') }
}

Write-Host ('SUPERVISOR_ANTIGO='+$OldPid)
Write-Host 'Interrompendo somente o supervisor comprovadamente pertencente a esta copia QA...'
Stop-Process -Id $OldPid -Force

$Deadline=(Get-Date).AddSeconds(150)
$Pass=$false
$NewPid=0
while((Get-Date) -lt $Deadline){
  Start-Sleep -Seconds 2
  if(-not (Test-Path $StatusPath)){ continue }
  try { $Current=Get-Content $StatusPath -Raw | ConvertFrom-Json } catch { continue }
  $Candidate=[int]$Current.supervisor
  if($Candidate -le 0 -or $Candidate -eq $OldPid){ continue }
  if(-not (Is-OwnedSupervisor $Candidate)){ continue }
  $Health=Get-Health $Port
  if(-not $Health -or $Health.status -ne 'ok' -or $Health.service -ne $ExpectedService -or $Health.phase -ne $ExpectedPhase -or $Health.instance_id -ne $InstanceId){ continue }
  $AllAlive=$true
  foreach($Name in $Names){
    $Child=$Current.children.$Name
    if(-not $Child -or -not $Child.alive){ $AllAlive=$false; break }
  }
  $BlockedCount=0
  if($null -ne $Current.blocked){ $BlockedCount=@($Current.blocked).Count }
  if($AllAlive -and $BlockedCount -eq 0){ $Pass=$true; $NewPid=$Candidate; break }
}

$Task=Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
$Info=Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
if($Pass){
  Write-Host ('SUPERVISOR_NOVO='+$NewPid)
  Write-Host ('TASK_STATE='+$Task.State)
  Write-Host ('LAST_RESULT='+$Info.LastTaskResult)
  Write-Host ('HEALTH_QA=PASS porta='+$Port)
  Write-Host 'FILHOS_QA=PASS api/worker/engine vivos'
  Write-Host 'AUTONOMIA_24_7=PASS supervisor recuperado pelo Windows Task Scheduler' -ForegroundColor Green
  exit 0
}

Write-Host ('TASK_STATE='+$Task.State)
Write-Host ('LAST_RESULT='+$Info.LastTaskResult)
if(Test-Path $StatusPath){
  try {
    $Current=Get-Content $StatusPath -Raw | ConvertFrom-Json
    Write-Host ('STATUS_SUPERVISOR='+$Current.supervisor)
    Write-Host ('STATUS_PORT='+$Current.port)
    Write-Host ('STATUS_BLOCKED='+(@($Current.blocked) -join ','))
  } catch {}
}
Fail 'supervisor nao recuperado com stack saudavel dentro de 150 segundos'
