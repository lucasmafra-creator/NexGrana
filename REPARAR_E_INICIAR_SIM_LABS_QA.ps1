$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $Root "INICIAR.cmd") repair
exit $LASTEXITCODE
