# SIM Labs 0.4.0 — relatório de entrega da candidata

Data: 2026-10-03. Base: SIM Labs Integrado 0.3.0. Status geral: **CANDIDATA OPERACIONAL / DoD integral BLOCKED**.

A validação manual da 0.3 no Windows foi informada por Mafra no prompt. Os resultados abaixo foram executados nesta entrega em Linux/Python 3.12/Node 24, com dados temporários TEST. Não comprovam Windows, APK, serviço após reboot ou uma operação contínua de 24 horas.

## 1. Mudanças concretas

- Migração aditiva `0004_engine`: seis tabelas, sem migração financeira.
- `app.engine`: scheduler persistente, fila deduplicada, claims transacionais, duas execuções simultâneas, subprocessos com limite de 90s, três tentativas, backoff e recuperação. Pedidos manuais têm prioridade sobre revisão de assets, que precede auditorias periódicas.
- Nove workers com especialidade, pausa, última execução, erro e contador. Executam auditorias de registros ou arquivos; não implementam código autonomamente.
- Ciclos de 1h, 6h, 24h, 7 dias e 30 dias, configuráveis. Na primeira execução cada ciclo gera uma rodada; não reexecuta todos os ciclos perdidos enquanto o PC esteve desligado.
- Supervisor com trava por pasta, API/worker/engine separados, heartbeat/saúde, reinício limitado, backoff e incidente após esgotar tentativas. Não usa encerramento global de Python.
- Painel Operação 24/7: heartbeat, fila, execução manual, pausa/retomada, horários, incidentes, relatórios privados com hashes e anotações DIO/laboratório.
- Revisão de ZIPs com assets Nex: inventário, decodificação, resolução, alpha, hashes, limites de tamanho e plano de retrabalho. Sem avaliador visual, identidade/estética permanecem BLOCKED.
- Auditoria de integridade das últimas 200 evidências: desvio cria incidente P0, missão de segurança e decisão. Arquivos ausentes/alterados não podem ser baixados como evidência íntegra nem usados para novo PASS/encerramento. Aprovação de release confere novamente arquivos e hashes.
- Daily passou de contadores acumulados para janela do dia em America/Sao_Paulo. Encerramentos são identificados pelo estado done e última atualização no dia; o histórico contém os eventos.
- Scripts Windows para iniciar/parar/status/instalar/desinstalar, migração de dados e geração opcional de EXE iniciador.
- Candidata visual de Natal com alpha, original e referência; não aplicada ao NexGrana.

## 2. O que foi preservado

Login local privado, migrações anteriores, seed, papéis, IDs humanos, produtos, projetos, Collector/anexos, deduplicação de feedbacks, triagem/missões, canal `/resumo`, encerramento com evidência e regressão, histórico, releases, checklist Windows/Android, gates e decisão do CEO. Adaptador Ollama opcional continua sem ativação ou download automático. Interface pré-compilada continua dispensando Node no PC.

O NexGrana e seu banco financeiro não foram modificados. Não foi feita publicação, push, ação em loja, consumo de API paga ou alteração de segredos do usuário. Backups e migração lidam apenas com dados operacionais do SIM Labs.

## 3. Migração e recuperação

A cópia para pasta nova, antes da primeira inicialização, evita sobrescrever a instalação 0.3. O copiador exige revisão `0003_integrated`, banco SQLite operacional padrão e evidências dentro da pasta de origem. Usa backup SQLite consistente, preserva origem, copia configuração/dados, ajusta caminhos de Evidence/Artifact e referências locais do Collector. Caminhos externos/banco personalizado bloqueiam a cópia.

O bootstrap cria backup antes de `alembic upgrade head`. Migração 0004 só adiciona tabelas. Downgrade automático foi bloqueado para impedir descarte da memória operacional. Rollback usa a pasta antiga preservada, não o banco migrado. A cópia de arquivos exige parar a versão antiga antes, para manter consistência com o snapshot.

Recuperação: jobs do engine expiram após aproximadamente 120s; auditoria legada após 230s, com lease do líder de 210s. Reinício do supervisor não limpa banco ou fila. Falhas repetidas encerram a tentativa e registram incidente. Logs e PIDs ficam em `.runtime`; backup inclui arquivos privados e configuração, por isso não deve ser compartilhado.

O Agendador inicia no login do usuário, com wrapper que aguarda o supervisor e tentativas limitadas de recuperação. Parada encerra a tarefa ativa antes dos processos, evitando retomada acidental imediata. Desinstalação remove somente a tarefa desta pasta; não apaga dados. Antes do login, desligado ou suspenso, este mecanismo não opera.

## 4. Evidências executadas

| Verificação | Resultado | Evidência |
|---|---|---|
| Backend, contratos anteriores e engine | PASS — 50 testes | `evidence/BACKEND_TESTS_0_4.txt` |
| Collector: contrato, hashes, traversal | PASS — 3 testes | `evidence/COLLECTOR_TESTS_0_4.txt` |
| TypeScript e build Vite | PASS | `evidence/FRONTEND_BUILD_0_4.txt` |
| HTTP real: login, Collector, anexo, retry/dedup, triagem, inspeção, download, canal e gate | PASS | `evidence/HTTP_E2E_0_4.txt` |
| Job em processo isolado, relatório/evidência e pausa após reinício do engine | PASS em Linux | mesmo probe HTTP |
| Encerrar worker criado pelo teste e verificar novo PID, mantendo engine vivo | PASS em Linux | `evidence/WATCHDOG_PROCESS_0_4.txt` |
| Migração 0002→0004 preservando feedback | PASS | teste de migração na suíte |
| Migração 0003→0004 comparando todas as tabelas anteriores | PASS, incluindo fixtures de release/canal/config | teste de migração na suíte |
| Scheduler/dedup/pausa/fence/retries/worker independente/prioridade | PASS com cenários determinísticos | `backend/tests/test_engine.py` |
| Evidência alterada depois do upload | PASS: download responde 409 | teste de integridade na suíte |
| Revisão de assets da fonte RC6 disponível | 74 imagens examinadas, 0 corrompidas, identidade BLOCKED | `evidence/ASSET_REVIEW_RC6.json` |
| Candidata de Natal | PNG 1254×1254 RGBA, alpha 0–255; inspeção visual feita na conversa, aprovação pendente | `asset_candidates/` |

Os testes positivos de gate usam arquivos explicitamente TEST DATA, não builds executáveis reais. Provam o contrato de promoção/imutabilidade; não homologação de Windows/Android. Avisos: depreciação do transporte httpx do TestClient; ZIP com entrada duplicada intencional em teste de rejeição.

Falhas encontradas e corrigidas durante o desenvolvimento: chamada de auditoria incompleta no endpoint de pausa, backlog periódico atrasando missão manual, fixture de hashes duplicados. Nova proteção cobre arquivo de evidência adulterado. Não se afirma que bugs específicos do aplicativo NexGrana foram corrigidos sem sua última build e execução de regressão.

## 5. Avaliação dos assets

A fonte disponível é RC6; não foi confirmado que é a última build usada por Mafra. Os cards existentes incluem imagens RGB pequenas, como o Natal em 163×177px, com texto embutido observado visualmente. Isso limita nitidez e adaptação de texto/acessibilidade. A skin de Consciência Negra inspecionada também altera a silhueta com cabelo; revisão de identidade e contexto social requer avaliação humana.

Recomendação: personagem transparente separado do componente de card; título/descrição renderizados pelo app, preservando identidade, anatomia e permitindo acessibilidade. Roupas e acessórios expressam tema sem trocar espécie. A candidata de Natal foi gerada com as duas referências pelo recurso de imagem desta conversa, preservada em arquivo separado. O engine local NÃO ganhou acesso a esse gerador. A candidata aguarda aprovação e teste na tela real. Não foram remodeladas todas as 36 skins.

## 6. Cobertura do prompt e bloqueios

| Área pedida | Entrega atual / limite |
|---|---|
| Engine independente do navegador | Implementado e testado em processos Linux |
| Empresa com workers reais | Subprocessos reais de auditoria; não agentes de implementação autônoma |
| Scheduler, fila, retries, watchdog | Implementados; cobertura em suíte e probes, sem teste prolongado de 24h |
| Operação Windows após reboot | Scripts preparados; BLOCKED até testar no Windows |
| `simlabs_worker.exe`/serviço antes do login | NÃO IMPLEMENTADO; opção atual é tarefa no login e Python instalado |
| EXE de teste | Script para gerar iniciador Windows; compilação/assinatura/execução NÃO VALIDADAS |
| QA contínuo no app | Inspeção estática/registros e biblioteca manual; testes de UI/device/duas contas/offline BLOCKED |
| Regras financeiras | Banco separado; preservadas como critérios. Comportamento do NexGrana não foi testado nesta rodada |
| Segurança/RLS/auth do NexGrana | Integridade operacional implementada; auditoria dinâmica do app/RLS BLOCKED |
| Produto/marketing/red team/engenharia | Relatórios de registros e recomendações/hypóteses; não pesquisa de mercado ou patches executados |
| Performance | Nenhum ganho medido; baseline e comparação no app BLOCKED |
| Melhoria automática de estética | Inventário/plano automáticos; geração/avaliação local e aplicação BLOCKED |
| DIO/TryHackMe | Registro de aprendizado aplicado; sem alegação de curso/room concluído |
| Gates Windows/APK | Preservados e mais rígidos nos hashes; execução real dessas builds BLOCKED |
| Mesa do CEO | Decisões de release e desvios de integridade; sem publicação automática |
| Auditoria e evidências | Implementadas; logs não têm rotação automática e precisam de acompanhamento de disco |
| Migração preservando toda memória real | Teste de todas as tabelas anteriores, com parte povoada. Cópia da instalação real Windows ainda precisa ser validada |

Não há ambiente Windows, dispositivo Android, última build confirmada, sandbox de execução da fonte importada nem provedor local de edição/avaliação de imagem configurado nesta sessão. Esses bloqueios impedem homologação integral; não justificam inventar PASS. O mecanismo atual é local, não acesso remoto/produção.

## 7. Checklist de Mafra — teste real de 15 minutos

Inicialmente todos os itens abaixo são **NÃO VALIDADOS nesta entrega**:

- [ ] Backup da 0.3 abre e contém banco/evidências/configuração.
- [ ] Cópia 0.3→0.4 preserva senha, histórico, releases e downloads.
- [ ] `INICIAR_24_7.bat` abre central e heartbeat do engine avança.
- [ ] Rodar QA agora gera relatório privado que pode ser baixado.
- [ ] Pausar scheduler deixa fila pendente; retomada conclui novos jobs.
- [ ] Fechar navegador não interrompe heartbeat; reabrir preserva dados.
- [ ] Enviar a última fonte gera revisão de assets e mantém estética BLOCKED quando não avaliada.
- [ ] Enviar Collector duas vezes não duplica missão nem anexo.
- [ ] Encerramento sem evidência é recusado; gate incompleto impede aprovação.
- [ ] Comparar original/referência/candidata Natal e testar em claro/escuro, tamanhos reais e 360/390/412px.
- [ ] Instalar tarefa, reiniciar Windows, fazer login e conferir central/engine.
- [ ] Parar, retomar e desinstalar tarefa preservam banco e arquivos.
- [ ] Gerar EXE iniciador e validar seu funcionamento na pasta completa.
- [ ] Executar Windows build e APK reais, cenários críticos e anexar evidências correspondentes.

**DoD integral: BLOCKED** até implementar autonomia de patch/avaliação visual e cumprir as validações obrigatórias do prompt. Consulte `LEIA_PRIMEIRO.md` para comandos e recuperação, e `PROMPT_PROXIMA_EXECUCAO.md` para a continuação de implementação.
