# Build status

NEXGRANA STATUS: bloqueio único do run 96c0a5da identificado e corrigido; ainda não GREEN até a suíte e o build passarem novamente no Windows.
VERSÃO: NexGrana 0.24.0 / SIM Labs QA 0.4.1-qa.2 + hotfix de recuperação 2026-10-11.
BRANCH/COMMIT: indisponível no pacote; nenhuma equivalência Git afirmada.
RUN: Windows run 4a786e1a1abf49858b6a4533555d2c58 = BLOCKED; seis grupos passaram, dois falharam; nenhum build ou release foi criado.
TESTES: run Windows 96c0a5da teve 7/8 grupos PASS; o grupo Nex falhou por PNG truncado. Asset restaurado; suíte de skins 8/8 PASS e varredura dos 147 PNGs PASS. Repetição Windows pendente.
REGRAS FINANCEIRAS: testes Python/SQL PASS; staging e validação com sessão real pendentes.
REGRESSÃO: fixtures de processo ajustadas para caminhos Windows; dependências do gateway Nex incluídas e verificadas; asset de foco restaurado do bundle íntegro. Suíte completa do Nex e smoke nativo aguardam a execução corrigida no Windows.
WINDOWS BUILD: BLOCKED — a execução 4a786e1a não chegou ao build; nenhum EXE gerado.
ANDROID BUILD: BLOCKED — etapa separada após Windows; nenhum APK gerado.
BUGS P0: não foi realizada classificação completa de todos os feedbacks; não afirmar zero.
BUGS P1: bloqueadores históricos de inicialização corrigidos; validação Windows ainda necessária.
BUGS RESTANTES: toolchain e smoke Windows/Android; login e navegação autenticada NexGrana em staging; refinamento visual das skins depende de revisão humana.
EVIDÊNCIAS: reports/pipeline, reports/browser-smoke.json e screenshots.
PRÓXIMA AÇÃO: extrair a revisão atualizada sobre a mesma pasta, substituindo os arquivos sem apagar `.runtime`, e executar uma vez `INICIAR.cmd build-windows`.

O registro automático usa o resultado da execução atual e verifica hashes. Envia ZIP da pasta completa do executável, incluindo DLLs, para a central local. Nunca publica, instala nem declara o binário testado. Essa integração foi testada com arquivos sintéticos explicitamente identificados; não houve teste de registro de EXE real nesta sessão.


## Correção de acesso e bloqueios do pipeline — 2026-10-11
A autenticação validada pelo iniciador é reutilizada na interface. O hotfix também corrige os testes de parada que falhavam com caminhos Windows, inclui FastAPI/Uvicorn nas dependências QA do gateway, verifica esses imports antes da suíte e invalida o carimbo do venv quando um arquivo de requirements incluído muda. A suíte de regressão passa a executar com o Python do venv QA do backend.
