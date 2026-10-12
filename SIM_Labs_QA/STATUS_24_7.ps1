$ErrorActionPreference='SilentlyContinue'
$Root=Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime=Join-Path $Root '.runtime'
$Port=8000
$PortFile=Join-Path $Runtime 'qa_port.txt'
if(Test-Path -LiteralPath $PortFile){ $Raw=(Get-Content -LiteralPath $PortFile -Raw).Trim(); $Parsed=0; if([int]::TryParse($Raw,[ref]$Parsed) -and $Parsed -ge 1024 -and $Parsed -le 65535){$Port=$Parsed} }
Write-Host ('SIM Labs QA - status local - porta '+$Port) -ForegroundColor Cyan
try{Invoke-RestMethod ('http://127.0.0.1:'+$Port+'/api/v1/health') -TimeoutSec 3 | Format-List}catch{Write-Host 'API QA indisponivel.'}
if(Test-Path (Join-Path $Runtime 'status_24_7.json')){Get-Content (Join-Path $Runtime 'status_24_7.json')}
