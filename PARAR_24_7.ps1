$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$TaskFile=Join-Path $Root '.runtime/task_name.txt'
$Hash=[System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Root))).Replace('-','').Substring(0,10)
$Expected="SIMLabs24_7_$Hash"
if(Test-Path $TaskFile){$Name=(Get-Content $TaskFile).Trim();if($Name -ne $Expected){throw 'Tarefa nao pertence a esta pasta.'};Stop-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue}
$Py=Join-Path $Root 'backend/.venv/Scripts/python.exe'
if(Test-Path $Py){& $Py (Join-Path $Root 'backend/stop_local.py')}else{Write-Host 'Ambiente ainda nao instalado.'}
Write-Host 'Operacao parada; autoinicio no proximo login permanece instalado. Para remover, DESINSTALAR_24_7.bat.'
