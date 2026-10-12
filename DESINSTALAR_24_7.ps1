$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$File=Join-Path $Root '.runtime/task_name.txt'
$Hash=[System.BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Root))).Replace('-','').Substring(0,10)
$Expected="SIMLabs24_7_$Hash"
if(Test-Path $File){$Name=(Get-Content $File).Trim();if($Name -notmatch '^SIMLabs24_7_[A-F0-9]{10}$'){throw 'Nome de tarefa invalido.'};Unregister-ScheduledTask -TaskName $Name -Confirm:$false;Remove-Item $File}
Write-Host 'Autoinicio removido. Banco, evidencias e processos existentes preservados; use PARAR_24_7.bat para parar.'
