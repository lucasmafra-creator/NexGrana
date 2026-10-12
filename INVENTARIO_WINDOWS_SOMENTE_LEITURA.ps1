[CmdletBinding()]
param([string]$OutputDirectory = (Join-Path $PSScriptRoot 'inventory-output'))

$ErrorActionPreference = 'Continue'
$rows = [System.Collections.Generic.List[object]]::new()
$foundRoots = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
function Add-Row([string]$Component,[string]$Path,[string]$Function,[string]$HasData,[string]$CanClone,[string]$Risk) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    $rows.Add([pscustomobject]@{ COMPONENTE=$Component; CAMINHO=$Path; FUNCAO=$Function; DADOS=$HasData; PODE_CLONAR=$CanClone; RISCO=$Risk })
}
function Add-Root([string]$Path) {
    if (-not [string]::IsNullOrWhiteSpace($Path) -and (Test-Path -LiteralPath $Path -PathType Container)) { [void]$foundRoots.Add((Resolve-Path -LiteralPath $Path).Path) }
}
function Get-ExeFromService([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) { return '' }
    $match = [regex]::Match($Value,'(?i)^\s*"([^\"]+\.exe)"|^\s*(.+?\.exe)(?:\s|$)')
    if ($match.Success) { if ($match.Groups[1].Success) { return $match.Groups[1].Value }; return $match.Groups[2].Value }
    return '[caminho não extraído]'
}

# Process metadata is limited to name, PID and executable path; command lines are not read.
try {
    Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.Name -match '(?i)nexgrana|sim.?labs|collector|observer|bridge|runner|engine' } | ForEach-Object {
        Add-Row 'PROCESSO' $_.ExecutablePath $_.Name 'Não verificado' 'Somente fonte, após revisão' 'Executável ativo; não duplicar nem encerrar nesta auditoria'
        if ($_.ExecutablePath) { Add-Root (Split-Path -Parent $_.ExecutablePath) }
    }
} catch { Add-Row 'PROCESSO' '[consulta indisponível]' 'Win32_Process' 'Não' 'Não' 'Consulta bloqueada ou sem permissão' }

# Services: report only the executable path, never the full service command line or arguments.
try {
    Get-CimInstance Win32_Service -ErrorAction Stop | Where-Object { ($_.Name + ' ' + $_.DisplayName) -match '(?i)nexgrana|sim.?labs|collector|observer|bridge|runner|engine' } | ForEach-Object {
        $exe = Get-ExeFromService $_.PathName
        Add-Row 'SERVIÇO' $exe ("$($_.Name) · $($_.State)") 'Possível acesso a dados' 'Não copiar serviço' 'Instalação ativa; comparar sem parar ou substituir'
        if ($exe -and (Test-Path -LiteralPath $exe -PathType Leaf)) { Add-Root (Split-Path -Parent $exe) }
    }
} catch { Add-Row 'SERVIÇO' '[consulta indisponível]' 'Win32_Service' 'Não' 'Não' 'Consulta bloqueada ou sem permissão' }

# Scheduled tasks: task identity/state only; task actions and arguments may contain secrets.
try {
    Get-ScheduledTask -ErrorAction Stop | Where-Object { ($_.TaskName + ' ' + $_.TaskPath) -match '(?i)nexgrana|sim.?labs|collector|observer|bridge|runner|engine' } | ForEach-Object {
        $state = [string]$_.State
        Add-Row 'TAREFA AGENDADA' ("$($_.TaskPath)$($_.TaskName)") ([string]$state) 'Possível acesso a dados' 'Não copiar tarefa automaticamente' 'Ação/argumentos não exibidos; revisar no Windows'
    }
} catch { Add-Row 'TAREFA AGENDADA' '[consulta indisponível]' 'Agendador de Tarefas' 'Não' 'Não' 'Consulta bloqueada ou sem permissão' }

$userRoot = [Environment]::GetFolderPath('UserProfile')
$programFilesX86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
$candidateRoots = @(
    (Join-Path $env:ProgramFiles 'NexGrana'),(Join-Path $env:ProgramFiles 'SIM Labs'),
    (Join-Path $programFilesX86 'NexGrana'),(Join-Path $programFilesX86 'SIM Labs'),
    (Join-Path $userRoot 'NexGrana'),(Join-Path $userRoot 'SIM Labs'),
    (Join-Path $userRoot 'AppData\Local\NexGrana'),(Join-Path $userRoot 'AppData\Local\SIM Labs'),
    (Join-Path $userRoot 'AppData\Roaming\NexGrana'),(Join-Path $userRoot 'AppData\Roaming\SIM Labs'),
    (Join-Path $userRoot 'Desktop\NexGrana'),(Join-Path $userRoot 'Desktop\SIM Labs')
)
foreach ($candidate in $candidateRoots) { Add-Root $candidate }

# Inspect likely app roots plus roots discovered from active processes/services, to depth 5.
$seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($root in @($foundRoots)) {
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
    $queue = [System.Collections.Generic.Queue[object]]::new()
    $queue.Enqueue(@($root,0))
    while ($queue.Count -gt 0) {
        $item = $queue.Dequeue(); $current = [string]$item[0]; $depth = [int]$item[1]
        if (-not $seen.Add($current)) { continue }
        $leaf = Split-Path -Leaf $current
        if ($leaf -match '(?i)^\.env($|\.)') { Add-Row '.ENV' $current 'Configuração; conteúdo não foi lido' 'Possível segredo' 'NÃO' 'Nunca copiar para clone QA; segredos não são exibidos' }
        elseif ($leaf -match '(?i)\.runtime$') { Add-Row '.RUNTIME' $current 'Estado/credenciais/logs possíveis' 'Sim' 'NÃO' 'Contém estado local; preservar na instalação oficial' }
        elseif ($leaf -match '(?i)^(data|database|db|evidence|uploads)$') { Add-Row 'DIRETÓRIO DE DADOS' $current 'Banco, evidências ou estado provável' 'Sim' 'NÃO' 'Não copiar dados pessoais/financeiros' }
        elseif ($leaf -match '(?i)^(logs?|log)$') { Add-Row 'LOGS' $current 'Registros operacionais' 'Possível dado sensível' 'Só após sanitização' 'Não copiar sem revisar e remover segredos' }
        elseif ($leaf -match '(?i)nexgrana|sim.?labs|collector|observer|bridge|runner|engine') { Add-Row 'DIRETÓRIO DE APLICATIVO' $current 'Fonte/build/configuração a classificar' 'Desconhecido' 'Código pode ser clonado isolado' 'Revisar .env, banco, runtime e tarefas antes de copiar' }
        if ($depth -lt 5) {
            try {
                Get-ChildItem -LiteralPath $current -Force -Directory -ErrorAction SilentlyContinue | Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) } | ForEach-Object { $queue.Enqueue(@($_.FullName,$depth+1)) }
            } catch { }
        }
        try {
            Get-ChildItem -LiteralPath $current -Force -File -ErrorAction SilentlyContinue | ForEach-Object {
                $file = $_
                if ($file.Name -match '(?i)^\.env($|\.)' -and $file.Name -notmatch '(?i)^\.env\.(example|sample|template)$') {
                    Add-Row '.ENV' $file.FullName 'Configuração; conteúdo não foi lido' 'Possível segredo' 'NÃO' 'Não copiar credenciais para QA'
                }
                if ($file.Name -match '(?i)\.(db|sqlite|sqlite3)(-|$)' -or $file.Extension -match '(?i)^\.(db|sqlite|sqlite3)$') {
                    Add-Row 'BANCO SQLITE' $file.FullName 'Banco/estado local; conteúdo não foi lido' 'Sim, possivelmente pessoal/financeiro' 'NÃO' 'Não copiar para QA nem abrir durante inventário'
                }
                if ($file.Extension -match '(?i)^\.log$' -or $file.Name -match '(?i)^log') {
                    Add-Row 'LOG' $file.FullName 'Registro local; conteúdo não foi lido' 'Possível dado sensível' 'Só após sanitização' 'Não compartilhar sem revisar'
                }
                if ($file.Name -match '(?i)(settings|config|preferences)\.(json|ini|toml|yaml|yml)$') {
                    Add-Row 'CONFIGURAÇÃO' $file.FullName 'Configuração local; conteúdo não foi lido' 'Possível segredo' 'Só após inspeção' 'Verificar URLs e tokens antes de qualquer cópia'
                }
                if ($file.Name -match '(?i)^(nexgrana|sim.?labs|collector|observer|bridge|runner|engine).*\.(exe|msi|msix|apk)$') {
                    Add-Row 'ARTEFATO' $file.FullName $file.Extension 'Não determinado' 'Sim, para inspeção offline' 'Não executar nem instalar como parte do inventário'
                }
            }
        } catch { }
    }
}

# Startup locations are listed by key/value name only, not by contents.
foreach ($location in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Run','HKLM:\Software\Microsoft\Windows\CurrentVersion\Run','HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run')) {
    if (Test-Path $location) {
        try { (Get-ItemProperty -LiteralPath $location).PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' -and $_.Name -match '(?i)nexgrana|sim.?labs|collector|observer|bridge|runner|engine' } | ForEach-Object { Add-Row 'INICIALIZAÇÃO AUTOMÁTICA' ("$location\$($_.Name)") 'Entrada de inicialização; valor omitido' 'Possível' 'Não copiar automaticamente' 'Não alterar o Registro nesta auditoria' } } catch { }
    }
}

$out = [IO.Path]::GetFullPath($OutputDirectory)
[void](New-Item -ItemType Directory -Path $out -Force)
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$csv = Join-Path $out "inventario_nex_sim_$stamp.csv"
$json = Join-Path $out "inventario_nex_sim_$stamp.json"
$rows | Sort-Object COMPONENTE,CAMINHO -Unique | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
$metadata = [pscustomobject]@{ generated_at=(Get-Date).ToUniversalTime().ToString('o'); computer_name=$env:COMPUTERNAME; read_only=$true; values_read=['process names and executable paths','service names/states/executable paths','task names/states','directory and file names']; secret_contents_read=$false; rows=$rows.Count; csv=(Split-Path -Leaf $csv) }
$metadata | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $json -Encoding UTF8
Write-Output "Inventário somente leitura concluído. Registros: $($rows.Count)"
Write-Output "CSV: $csv"
Write-Output "Metadados JSON: $json"
Write-Output 'Nenhum serviço, processo, tarefa, arquivo, credencial ou instalação foi alterado.'
