# Estado do NexGrana — 2026-10-09

## Atualização V7 — launcher e pipeline integrado

O pacote de QA agora usa o `REPARAR_E_INICIAR_SIM_LABS_QA.cmd` como entrada única. Ele valida e inicia a central, autentica o pipeline com a credencial local salva, dispara uma vez ou acompanha o `run_id` ativo e registra o resultado. WAL/SHM/journal do SQLite foram retirados do manifesto fonte e o preflight foi alinhado. Testes simulados cobrem o início único, execução já ativa, HTTP 409, resposta ambígua e segredo não impresso. Windows é o primeiro gate; Android mantém status separado. A validação PowerShell/Windows real ainda não ocorreu nesta sessão.

## Atualização de estabilidade do pacote QA

O clone SIM Labs QA incluído neste pacote foi atualizado para `0.4.1-qa.2` para corrigir inicialização instável, execução presa em `RUNNING` e falha de reconexão na tela de Gestão de hoje. Esta alteração fica restrita ao clone de QA e aos scripts de inicialização. Regras financeiras, dados do NexGrana, migrations e assets não foram modificados nesta correção. O Windows do usuário ainda precisa executar a validação automática do reparador antes de qualquer status verde.

## Situação

**AMBER / candidato de QA.** O código-fonte disponível passa as verificações Python e SQL locais após uma correção de sintaxe em teste. O app respondeu com HTTP 200 no servidor Flet Web. A árvore autoritativa do Windows, a branch/commit e os builds nativos não puderam ser confirmados nesta sessão.

## Fonte inspecionada

- Pacote: `NexGrana_SIM_Labs_QA_RC8_QA_2026-10-07_STARTUP_FIXED_V5.zip`.
- Bundle: `RC8-QA-EXEC-20261007`.
- Versão declarada no `pyproject.toml`: `0.24.0`.
- Migração mais recente declarada no manifesto do pacote: `0.25.6`; verificada ali com PGlite, sem aplicação em Supabase de staging.
- SHA-256 do ZIP de entrada: `e6c543482a7cf1f3c81d3ab12839d32831cc4b5502919dc2c01f8f0ac88032ea`.
- O pacote e o workspace não contêm metadados Git. Branch e commit: **desconhecidos**.
- O caminho Windows informado anteriormente, `C:\NG24_RC6_WORK\NexGrana`, não está montado neste ambiente.

Este documento descreve o candidato extraído para QA. Ele não o declara como a árvore oficial do produto.

## Alteração feita nesta cópia de QA

- Corrigida a indentação do `with Image.open(...)` em `tests/test_privacy_and_skins.py`, que impedia a suíte de importar o arquivo.
- Não houve alteração no comportamento financeiro, no backend, nas migrations, no Supabase ou nos assets canônicos.
- O ZIP de entrada permanece intacto; a correção existe somente nesta cópia de trabalho.

## Evidência atual

- Testes Python: 210 aprovados sob o executor temporário descrito em `QA_REPORT.md`.
- SQL/PGlite: 117 verificações aprovadas localmente.
- Segurança estática: aprovada.
- Imagens de asset: 147 arquivos decodificáveis; os testes verificaram dimensões, transparência e recorte dos conjuntos de skins.
- Flet Web: servidor local iniciou e retornou HTTP 200.
- SIM Labs incluído: 36 testes sem `TestClient` passaram; API QA temporária respondeu HTTP 200 em health, OpenAPI e página principal, com SQLite descartável.
- O pacote já traz o reparador Windows na raiz (REPARAR_E_INICIAR_SIM_LABS_QA.cmd + .ps1); a rota chama o inicializador QA aninhado e valida health/interface/login. Foi inspecionado, mas não executado no Windows.
- V7 acrescenta fluxo de um clique até iniciar/acompanhar o pipeline autenticado; nove testes `unittest`, sete verificações do guard QA e dois testes UI passaram no host Linux. A simulação de rede usa API falsa em memória; isso comprova decisões de idempotência, não a execução real do Windows.
- Manifesto e verificador de preflight passaram com sidecars de SQLite simulados ativos. Python base do pipeline agora aceita releases estáveis `>=3.11`, conforme a metadata do NexGrana.
- O restante da suíte SIM Labs (95 casos coletados no total) para no primeiro teste que usa `TestClient`, pois o executor desta sessão não acorda o event loop entre threads; a mesma falha ocorre num FastAPI mínimo.
- Bootstrap da senha validado duas vezes em clone descartável: created-once no primeiro início, preserved no segundo, arquivo salvo idêntico; nova extração sem .runtime cria outra instância.
- Captura visual em navegador, smoke test manual, EXE Windows e APK Android: pendentes.

## Critério de conclusão

Este candidato **não está GREEN**. Para avançar: aplicar o ZIP V7 por cima da pasta ativa preservando `.runtime` e dados, executar o launcher uma vez, revisar o relatório único gerado, confirmar a árvore Git oficial, abrir as telas no Windows, capturar evidência real e gerar Windows BUILD PASS. Android mantém status separado; iOS continua adiado.
