# SIM Labs QA RC8 — Startup Fix V3

Data: 2026-10-07.

## Causa corrigida

O reparador anterior declarou um parâmetro PowerShell chamado `$Args`, que conflita com a variável automática `$args`. Na execução observada, a lista de argumentos chegou vazia ao Python, fazendo `python.exe` abrir o modo interativo (`>>>`).

A V3 remove essa dependência: as chamadas Python críticas agora passam argumentos explicitamente. Antes de qualquer alteração de runtime há também um teste sentinela de encaminhamento de argumentos; se falhar, o reparador encerra sem iniciar serviços.

## Preservação

O reparador cria cópia de segurança, quando existentes, de `.env`, `.runtime/PRIMEIRO_ACESSO.txt` e `backend/sim_labs.db`. Backups, evidências e dados existentes não são removidos. Logs exibidos em falha são filtrados para não imprimir senha, hash ou token.

## Validações realizadas no pacote fonte

- `compileall` de `backend/app` e `scripts`: aprovado.
- manifesto regenerado e verificado: aprovado.
- suíte backend: 95 testes aprovados; 1 warning conhecido de ZIP duplicado em teste.
- bootstrap local: criação única de credencial, sincronização hash/senha e segunda execução idempotente aprovadas.
- API local em clone temporário: health aprovado com `service=sim-labs-control-center-qa`, `phase=Engine 0.4.1-qa.1` e `instance_id` esperado.
- interface HTTP: aprovada.
- login local usando a credencial armazenada, sem imprimi-la: aprovado.
- supervisor no clone temporário: API, Engine e Worker vivos; validação de health/interface/login aprovada.

## Limite da validação

A execução final do `.cmd` em Windows ainda precisa ocorrer no computador do Mafra. O próprio reparador só imprime `SIM LABS QA: VALIDADO NESTE WINDOWS` depois que health, interface e login passarem no Windows real.
