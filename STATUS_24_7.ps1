$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$File=Join-Path $Root '.runtime/status_24_7.json'
if(Test-Path $File){Get-Content $File;Write-Host ('Idade do status em segundos: '+[math]::Round(((Get-Date)-(Get-Item $File).LastWriteTime).TotalSeconds))}else{Write-Host 'Sem status: motor ainda nao iniciou.'}
try{Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health' -TimeoutSec 3 | Format-List}catch{Write-Host 'API indisponivel.'}
$Task=Join-Path $Root '.runtime/task_name.txt'
if(Test-Path $Task){Get-ScheduledTaskInfo -TaskName (Get-Content $Task).Trim() | Format-List}
