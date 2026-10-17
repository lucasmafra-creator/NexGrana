$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Root "START_SIM_LABS_WINDOWS.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Script`" -NoBrowser"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName "SIM Labs LiveOps" -Action $action -Trigger $trigger -Settings $settings -Description "Mantém o SIM Labs Control Center e worker ativos após login." -Force | Out-Null
Write-Host "Inicialização automática instalada para o usuário $env:USERNAME." -ForegroundColor Green
