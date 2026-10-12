$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime = Join-Path $Root ".runtime"
foreach ($name in @("worker","api","supervisor","launcher")) {
  $pidFile = Join-Path $Runtime "$name.pid"
  if (Test-Path $pidFile) {
    $p = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($p) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
  }
}
Write-Host "SIM Labs encerrado." -ForegroundColor Yellow
