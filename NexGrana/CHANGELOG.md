# Changelog da estabilização

## 2026-10-09 — V7 one-click QA

- Corrigido o manifesto/preflight para ignorar sidecars transitórios WAL/SHM/journal e validar os mesmos arquivos da raiz.
- O launcher CMD executa inicialização + validação e inicia/acompanha o pipeline local autenticado, sem exigir login/clique/POST manual.
- A automação acompanha execuções ativas, reconcilia conflito/timeout consultando status e nunca repete às cegas um pedido que pode ter sido aceito.
- Adicionados testes para ciclo local simulado, segredo não impresso, associação a execução ativa, HTTP 409 e confirmação perdida.
- Python base agora segue o mínimo `>=3.11` do projeto; instalação segue isolada por clone QA e dependências.
- Build Windows é a primeira porta; Android só é tentado após Windows BUILD PASS e mantém estado próprio. iOS continua na fase posterior.
- Criado prompt de continuidade com escopo, regras financeiras, identidade Nex, processo, critérios e formato de relatório.
- Nenhuma alteração de produto/financeira, migração, publicação ou build nativo foi executada nesta rodada.

## 2026-10-09 — hotfix de estabilidade SIM Labs QA

- Atualizado o clone QA para `0.4.1-qa.2` e o bundle para `RC8-QA-STABILITY-20261009`.
- O launcher mantém uma janela de serviço visível e verifica repetidamente health, fase e identidade da pasta antes de abrir a central; aumentou o limite de espera com progresso.
- A página Gestão de hoje mostra conexão indisponível, tenta reconectar e protege contra execução duplicada quando a resposta se perde.
- O endpoint de status marca execução sem processo/relatório como bloqueada e remove somente o lock da mesma execução concluída.
- O manifesto e o preflight agora ignoram sidecars SQLite e concordam sobre os lançadores da raiz; teste de regressão valida ambos.
- Incluídos testes de regressão para os estados de rede e pipeline. Regras financeiras, migrations e assets do NexGrana não foram alterados.
- Windows real ainda é necessário para confirmar a inicialização e o serviço nesta máquina.

## 2026-10-09 — auditoria do candidato RC8

- Identificada e corrigida uma indentação inválida em `tests/test_privacy_and_skins.py` que impedia a importação de um teste de assets.
- Conferido o fluxo do launcher Windows já existente na raiz, sem alterar o script; ele faz backup seletivo, inicia a cópia QA e valida health/interface/login quando executado no Windows.
- Executadas 210 verificações Python, 117 verificações SQL/PGlite, varredura estática de segurança e validação de 147 imagens.
- Confirmado HTTP 200 no servidor Flet Web local; a tela não foi capturada em browser.
- SIM Labs: 36 testes sem `TestClient` passaram; o servidor QA temporário respondeu HTTP 200 em health, OpenAPI e página inicial, usando SQLite descartável. A suíte completa ainda depende de executar `TestClient` num runtime cujo event loop suporte wakeup entre threads.
- Documentada a persistência da senha local por pasta/instância; nova extração gera outra instância e outra senha de primeiro acesso.
- Reexecutado o bootstrap em clone descartável: a senha foi preservada entre os dois inícios e o arquivo não mudou.
- Nenhuma regra financeira, migration, integração remota ou asset canônico foi alterado.
- Nenhum EXE Windows ou APK Android foi produzido.
- A alteração foi feita apenas na cópia RC8 extraída desta sessão; a branch oficial e a pasta Windows ainda precisam ser confirmadas.
