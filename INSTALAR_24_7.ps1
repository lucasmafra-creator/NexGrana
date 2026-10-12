param([switch]$AtBoot)
$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Hash=[System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Root))).Replace('-','').Substring(0,10)
$Name="SIMLabs24_7_$Hash"
$Action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $Root 'START_SIM_LABS_WINDOWS.ps1')+'" -NoBrowser -KeepRunning') -WorkingDirectory $Root
$User=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Trigger=New-ScheduledTaskTrigger -AtLogOn -User $User
$Principal=New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited
if ($AtBoot) {
    $Identity=[System.Security.Principal.WindowsIdentity]::GetCurrent()
    $IsAdmin=(New-Object System.Security.Principal.WindowsPrincipal($Identity)).IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $IsAdmin) { throw 'Abra o CMD como administrador para registrar o gatilho de boot. O processo continuará com privilégios limitados.' }
    $Trigger=@((New-ScheduledTaskTrigger -AtStartup),(New-ScheduledTaskTrigger -AtLogOn -User $User))
    $Principal=New-ScheduledTaskPrincipal -UserId $User -LogonType S4U -RunLevel Limited
}
& (Join-Path $Root 'START_SIM_LABS_WINDOWS.ps1') -NoBrowser
if ($LASTEXITCODE -ne 0) { throw 'Preparacao falhou.' }
$Settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description 'SIM Labs local - computador ligado, sem suspensao; consultar modo registrado.' -Force | Out-Null
Set-Content (Join-Path $Root '.runtime/task_name.txt') $Name
Set-Content (Join-Path $Root '.runtime/task_mode.txt') $(if($AtBoot){'BOOT_S4U_LOCAL_ONLY'}else{'INTERACTIVE_LOGON'})
Write-Host "Instalado: $Name. Modo boot: $AtBoot. Valide a recuperação no Windows. S4U não fornece credenciais de rede nem acesso a arquivos EFS. PC desligado ou suspenso não executa tarefas."
