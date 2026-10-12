[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$SourceRoot,
  [Parameter(Mandatory=$true)][string]$DestinationRoot
)

$ErrorActionPreference = 'Stop'
$source = (Resolve-Path -LiteralPath $SourceRoot).Path.TrimEnd('\')
$destination = [IO.Path]::GetFullPath($DestinationRoot).TrimEnd('\')
$sourceUri = [Uri]($source + '\')
if (-not (Test-Path -LiteralPath $source -PathType Container)) { throw 'SourceRoot precisa apontar para uma pasta existente.' }
if (Test-Path -LiteralPath $destination) { throw 'Destino já existe. Este script nunca sobrescreve um clone ou instalação.' }
if ($destination.StartsWith($source + '\',[StringComparison]::OrdinalIgnoreCase) -or $source.StartsWith($destination + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Origem e destino não podem estar um dentro do outro.' }

$skipDirectories = @('.git','.venv','venv','node_modules','__pycache__','.pytest_cache','.runtime','data','database','db','evidence','uploads','logs','backups','backup','build','dist')
$skipExtensions = @('.exe','.msi','.msix','.apk','.dll','.so','.dylib','.pyd','.whl','.db','.sqlite','.sqlite3','.log','.pem','.pfx','.p12','.key','.bak')
$copied = [System.Collections.Generic.List[string]]::new()
$skipped = [System.Collections.Generic.List[object]]::new()
[void](New-Item -ItemType Directory -Path $destination)

function Copy-ReviewedTree([string]$From,[string]$To) {
  foreach ($entry in Get-ChildItem -LiteralPath $From -Force -ErrorAction Stop) {
    $relative = [Uri]::UnescapeDataString($sourceUri.MakeRelativeUri([Uri]$entry.FullName).ToString()).Replace('/','\')
    if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { $skipped.Add([pscustomobject]@{path=$relative;reason='reparse point/link'}) ; continue }
    if ($entry.PSIsContainer) {
      if ($skipDirectories -contains $entry.Name.ToLowerInvariant()) { $skipped.Add([pscustomobject]@{path=$relative;reason='runtime/data/generated directory'}) ; continue }
      [void](New-Item -ItemType Directory -Path (Join-Path $To $entry.Name))
      Copy-ReviewedTree $entry.FullName (Join-Path $To $entry.Name)
      continue
    }
    $name = $entry.Name.ToLowerInvariant()
    $sensitiveName = $name -match '(?i)(^\.env($|\.)|\.env($|\.)|secret|credential|password|token|service.?role)'
    if ($sensitiveName -or $skipExtensions -contains $entry.Extension.ToLowerInvariant()) { $skipped.Add([pscustomobject]@{path=$relative;reason='secret/configuration, runtime or binary excluded'}) ; continue }
    $target = Join-Path $To $entry.Name
    Copy-Item -LiteralPath $entry.FullName -Destination $target
    $copied.Add($relative)
  }
}

try {
  Copy-ReviewedTree $source $destination
  $receipt = [pscustomobject]@{
    schema='sim-labs.qa-clone/1.0'; created_at=(Get-Date).ToUniversalTime().ToString('o')
    source_root=$source; destination_root=$destination; read_only_source=$true
    excluded_data=['.env/config secrets','SQLite/database files','data/evidence/uploads','runtime/logs','installed binaries','reparse points']
    copied_files=$copied.Count; skipped_items=$skipped.Count
    copied_sha256=@($copied | ForEach-Object { $file=Join-Path $destination $_; [pscustomobject]@{path=$_;sha256=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()} })
    skipped=$skipped
  }
  $notice = @'
CLONE QA ISOLADO — SOMENTE CÓDIGO/FONTE COPIADOS

Este clone foi criado sem .env, credenciais, banco SQLite, runtime, logs,
evidências privadas, tarefas do Agendador ou executáveis instaláveis.
Confira clone_manifest.json e configure dados QA sintéticos antes de iniciar.
Não aponte o clone para o banco/credenciais do ambiente oficial.
'@
  $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $destination 'clone_manifest.json') -Encoding UTF8
  Set-Content -LiteralPath (Join-Path $destination 'LEIA_PRIMEIRO_CLONE_QA.txt') -Value $notice -Encoding UTF8
  Write-Output "Clone QA criado em: $destination"
  Write-Output "Arquivos copiados: $($copied.Count) · itens excluídos: $($skipped.Count)"
  Write-Output 'A origem não foi alterada; o script recusou sobrescrever qualquer destino preexistente.'
} catch {
  Write-Error "Clone incompleto em $destination; preserve a pasta para revisão e crie novo destino após inspeção. Origem não alterada. Detalhe: $($_.Exception.Message)"
  throw
}
