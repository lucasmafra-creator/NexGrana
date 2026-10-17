# Relatório de QA — candidato RC8, 2026-10-09

## Complemento V7 — automação de um clique

- Corrigido o escopo do manifesto para excluir sidecars SQLite em uso (`.db-wal`, `.db-shm`, `.db-journal`, equivalentes `.sqlite-*`); o verificador de preflight usa o mesmo conjunto e inclui os lançadores da raiz.
- A execução de `REPARAR_E_INICIAR_SIM_LABS_QA.cmd` agora valida/inicia a central e dispara ou acompanha automaticamente um único pipeline autenticado. A credencial só é lida de `.runtime/PRIMEIRO_ACESSO.txt`, enviada ao loopback e nunca impressa.
- Estado atual da automação: 9 testes `unittest` passaram, incluindo fluxo local simulado de login/início único/relatório, execução já ativa, conflito HTTP 409, resposta perdida, HTTP 5xx, integridade do manifesto com sidecars SQLite e critério Windows-first. Mais 7 verificações do guard QA e 2 casos de estado UI passaram. O teste Windows/PowerShell real ainda precisa ser executado na máquina do usuário.
- A escolha do Python agora segue `NexGrana/pyproject.toml` (`>=3.11`, somente release estável), em vez de exigir exclusivamente 3.12. Compatibilidade final de dependências ainda é determinada pela instalação e pelo teste do ambiente QA.
- Build agora respeita a ordem: Windows primeiro; Android depois e com status separado. A aprovação geral deste pipeline requer os testes locais e Windows BUILD PASS. Android não é promovido para PASS sem build real.
- ZIP contém fontes e automação; nenhum EXE/APK foi gerado ou instalado nesta sessão. Nenhuma regra financeira, banco de produção, migration, saldo, perfil ou identidade canônica Nex foi alterada.

**Classificação V7:** AMBER. A validação simulada, integridade de manifesto (783 arquivos) e os testes de UI disponíveis neste host passaram; não substituem execução Windows/PowerShell, screenshot nativo ou build real. A automação deste host não abriu porta local: o fluxo de rede foi exercitado por cliente de API falso em memória.

## Hotfix de estabilidade do SIM Labs QA incluído no pacote

- Versão do clone QA: `0.4.1-qa.2`; bundle `RC8-QA-STABILITY-20261009`.
- Corrigida a recuperação de pipeline encerrado: a tela não mantém `RUNNING` sem processo vivo/relatório; o lock só é liberado quando pertence ao mesmo `run_id` e PID.
- Corrigido o estado da tela diante de falha de rede e de resposta perdida após o POST; a reconexão é automática e não libera um segundo disparo enquanto a confirmação está pendente.
- Adicionados testes de regressão de UI e backend. O teste UI e as verificações de sintaxe foram executados neste host; os testes de backend e a validação PowerShell dependem do ambiente completo/Windows.
- O preflight do pipeline foi alinhado ao gerador do manifesto para incluir os dois lançadores da raiz e ignorar arquivos SQLite WAL/SHM/journal. Um teste automatizado reproduz esses sidecars e confirma que o manifesto continua íntegro.
- O reparador agora mantém uma janela local de serviço, aguarda até 10 minutos para a API ficar saudável e mostra progresso. Isso evita declarar pronto apenas porque o processo foi disparado.
- Este hotfix não altera regras financeiras, banco NexGrana, Supabase, migrations ou assets do mascote. Nenhum EXE/APK foi gerado.
- Status permanece **AMBER até a própria validação automática ser executada no Windows do usuário**. Este ambiente Linux não confirma a estabilidade gráfica/Windows.

## Resultado

**Status geral: AMBER / NÃO GREEN.** Os testes locais passaram depois de corrigir um erro de sintaxe na própria suíte. A árvore Git oficial e o Windows do Mafra não estavam disponíveis; execução visual nativa e builds permanecem bloqueados.

## Fonte e versão

- Fonte analisada: pacote `NexGrana_SIM_Labs_QA_RC8_QA_2026-10-07_STARTUP_FIXED_V5.zip`.
- `bundle_id`: `RC8-QA-EXEC-20261007`.
- Versão do app em `pyproject.toml`: `0.24.0`.
- SHA-256 do ZIP de entrada: `e6c543482a7cf1f3c81d3ab12839d32831cc4b5502919dc2c01f8f0ac88032ea`.
- Sem `.git` no workspace ou no pacote. Branch/commit oficiais não identificáveis.

## Causa encontrada e correção

`tests/test_privacy_and_skins.py`, linha 65, tinha um `with Image.open(...)` fora do bloco `with self.subTest(...)`. O arquivo não podia ser analisado/importado. A indentação foi corrigida somente na cópia de QA extraída. O ZIP de entrada e o caminho Windows oficial não foram alterados.

## Execuções

| Check | Resultado | Observação |
|---|---:|---|
| Sintaxe Python no pacote | PASS, 222 arquivos | 0 erros de AST após a correção do teste. |
| `validate_release.py --full` | PASS, 210/210 | `pip check`, manifesto/versão, assets, compileall, testes e `security_scan.py` concluíram. |
| Regras financeiras e isolamento | PASS local | Incluídos na suíte Python e nos cenários PGlite; não exercidos contra Supabase hospedado. |
| `npm run test:sql` | PASS, 117 verificações | PGlite 0.5.8; nenhum banco remoto tocado. |
| `security_scan.py` | PASS | Sem segredos/artifacts conhecidos no escopo examinado. |
| Assets | PASS estático | 147 imagens abriram sem erro. Teste dedicado valida dimensão/transparência/recorte das 36 skins. |
| `flet run --web` | PARCIAL | Servidor local respondeu `HTTP 200`; Chrome disponível está em outra rede isolada e não abriu o loopback. Não há screenshot. |
| Smoke test manual de telas | BLOCKED | Sem navegador local/headless e sem build nativo nesta sessão. Testes de árvore de controles não provam renderização. |
| Build Windows | BLOCKED | Executor Linux; não foi gerado nem instalado `.exe`. |
| Build Android | BLOCKED | Flutter, Android SDK e `adb` ausentes. |

## Ressalva do executor Python

Importar Flet e chamar `asyncio.run()` com `asyncio.to_thread()` fez o executor padrão desta sessão ficar preso durante o encerramento. A falha foi reproduzida com uma tarefa simples, fora do NexGrana. Para executar os 210 testes, foi aplicado um hook temporário em `/tmp` que muda somente o shutdown do executor durante o processo de QA; ele não altera o projeto. Sem esse hook, o comando padrão fica preso ao encerrar a rotina de autenticação simulada. Esse comportamento precisa ser repetido no Windows Python 3.14 antes de classificar o runner padrão como aprovado.

## SIM Labs incluído no pacote

- `qa_pipeline.py` importa `from .integrated import ceo`, e `routers/integrated.py` existe no candidato. A referência antiga `app.integrated` não aparece nesse arquivo.
- O par da raiz REPARAR_E_INICIAR_SIM_LABS_QA.cmd + .ps1 existe no ZIP. O fluxo cria backup seletivo, verifica Python/PowerShell/manifesto, inicia o script aninhado e roda validate_qa_startup.py para health/interface/login. O fluxo foi inspecionado, mas não executado no Windows desta sessão. O erro de caminho apresentado anteriormente é compatível com executar START_SIM_LABS_WINDOWS.ps1 a partir do diretório pai; o arquivo fica em SIM_Labs_QA\START_SIM_LABS_WINDOWS.ps1.
- A validação AST dos 222 arquivos Python do pacote passou.
- A suíte descobriu 95 casos. **36 testes que não dependem do fixture `TestClient` passaram** (31 funções de teste, com parametrizações). A suíte completa bloqueia ao iniciar `TestClient`; o bloqueio foi reproduzido com um FastAPI mínimo e com asyncio puro: neste executor, `loop.call_soon_threadsafe()` não acorda o selector numa thread à parte. Isso não foi atribuído ao backend NexGrana/SIM Labs.
- Para verificar o servidor sem `TestClient`, rodei Uvicorn em `127.0.0.1:8765`, com `APP_ENV=test`, banco SQLite descartável sob `/tmp` e credenciais sintéticas. `/api/v1/health`, `/openapi.json` e `/` responderam HTTP 200; a resposta identificou `sim-labs-control-center-qa`, fase `Engine 0.4.1-qa.1`. O processo foi encerrado após o smoke test.
- Bootstrap da credencial executado duas vezes em clone descartável com banco temporário: primeiro created-once, segundo preserved; o arquivo PRIMEIRO_ACESSO.txt permaneceu byte a byte igual. O código sincroniza divergência do hash sem gerar outra senha quando o arquivo existe. Cada extração/caminho sem .runtime inicia uma instância nova. O ciclo Windows ainda precisa ser confirmado.
- O processo Windows, a abertura gráfica da central e o uso do banco da cópia do Mafra não foram testados aqui. Nenhum banco original foi modificado.
- Não foram lidos nem publicados segredos, senhas ou dados privados do runtime.

## Pendências bloqueadoras

1. Confirmar a árvore ativa `C:\NG24_RC6_WORK\NexGrana` e sua branch/commit Git.
2. Aplicar/revisar o conserto de sintaxe na árvore oficial, caso o arquivo ainda esteja igual.
3. Executar no Windows os scripts de validação, abrir o aplicativo e testar login, dashboard, renda, despesas, saldo, futuras, abas, investimentos, Nex, finanças, perfis, navegação e persistência.
4. Capturar screenshots reais em desktop e conferir recortes/estados visuais.
5. Gerar EXE Windows, instalar/abrir e registrar SHA-256 e log.
6. Depois estabilizar Android em etapa própria, com Flutter/SDK/ADB e aparelho de teste.
7. Validar RLS e migrations num Supabase de QA autorizado; não aplicar em produção.

Sem essas evidências, manter o resultado como **AMBER**, nunca GREEN.
