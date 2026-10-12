# PROMPT MESTRE — SIM LABS — CONTROL CENTER E OPERAÇÃO

Data: 25/09/2026. Uso: fase posterior à consolidação Windows/Android do NexGrana. Este é um prompt de implementação progressiva; não é afirmação de que a SIM Labs já possui os sistemas descritos.

## 1. Missão e fronteira

Implemente a estrutura operacional da SIM Labs, com pessoas, processos, permissões, dados operacionais e agentes assistivos. NexGrana é **Produto #001**, identificador estável `nexgrana`. O sistema deve aceitar Produtos #002 e seguintes sem copiar toda a estrutura.

Primeiro inventarie o que já existe. No repositório `lucasmafra-creator/NexGrana`, commit de referência `dd848c2330890e5d1bb999ffa8264e94db6f826f`, existe apenas uma visão inicial `docs/SIM_LABS_ARQUITETURA.md`. Isso não prova a existência de um Control Center implementado. Se receber código posterior da SIM, examine-o antes de escolher stack e preserve trabalho válido.

A consolidação NexGrana tem prioridade. Não alterar regras financeiras, schema de clientes, RLS ou releases do produto como efeito colateral desta implantação. A SIM Labs não é um plugin com service role para todos os dados do NexGrana.

## 2. Decisão arquitetural

Separar **control plane SIM Labs** de **product plane NexGrana**:

| Plano | Responsabilidade | Dados permitidos |
|---|---|---|
| NexGrana | Contas de clientes, finanças, família, gateway Nex, consentimentos | Dados necessários ao serviço financeiro, sob suas próprias políticas |
| SIM Labs | Produto, tarefas, feedback, QA, segurança, SAC, agentes, releases e custos operacionais | Metadados, evidências sanitizadas e métricas autorizadas; sem réplica de extratos |
| Integração | APIs/eventos versionados e autenticados | Contrato mínimo por finalidade; sem credenciais de banco compartilhadas |

Criar repositório independente da SIM Labs, banco/projeto Supabase independente do FinanceHub, backend/secrets próprios, buckets privados e ambientes DEV/QA/PROD. Nome/organização finais do repositório devem ser confirmados pelos ativos autorizados; não inventar URL publicada. Identidades da equipe não são as contas financeiras dos clientes.

Se não existir base implementada, adotar web responsiva em React/TypeScript e backend FastAPI modular, com PostgreSQL/Supabase Auth para equipe. Justificativa: tabelas, filtros, permissões e fluxos de operação no navegador; backend Python familiar ao projeto. Reavaliar somente com evidência de base atual ou restrição concreta. Não portar o app financeiro para essa stack.

Começar com um backend modular, worker de jobs e banco transacional. Outbox/inbox persistentes, idempotência, retries e dead-letter permitem evolução sem Kafka/microserviços prematuros. Entidades têm `product_id`, ambiente e autorização por objeto. Configuração e integrações não ficam hardcoded no frontend.

Integrações unidirecionais de leitura primeiro. Métricas de produto/IA chegam agregadas ou por evento técnico minimizado; SIM não recebe tokens de clientes. Uso de APIs administrativas de produto fica restrito a serviços específicos com scope, auditoria e aprovação, nunca um console SQL geral.

## 3. Estrutura humana canônica

Preservar nomes e funções. Os nomes não fornecem e-mail, identidade de login nem autorização automática; vincular cada pessoa a um UID de equipe validado durante onboarding administrativo.

| Pessoa | Função canônica | Responsabilidade inicial proposta |
|---|---|---|
| Mafra | CEO / Fundador | Estratégia, orçamento, decisão final de promoção de release após gates |
| Vânio | Diretor de Operações | Coordenação operacional, prioridades de execução, incidentes e escalonamentos |
| Karol | UX & Feedback | Pesquisa, triagem de experiência e validação de fluxo |
| Niel | Testes & QA | Plano de testes, evidência, reteste e aceite técnico de QA |
| Bárbara | Análise & Produto | Requisitos, métricas de produto e critérios de aceite |
| Fernanda | Operations & Business | Processos, custos e operação de negócio |
| Carlinha | UX & Feedback | Feedback, linguagem e validação de usabilidade |

Engineering, Cybersecurity e Red Team precisam de responsáveis humanos explicitamente designados. Não transformar nomes de agentes em substitutos fictícios de aprovadores. Permitir acumular papéis na equipe pequena, registrando quando falta revisão independente. Nenhuma mensagem, convite ou credencial deve ser enviado a uma pessoa apenas porque ela aparece nesta tabela.

## 4. Setores e módulos do Control Center

| Setor/módulo | Trabalho principal | Saída verificável |
|---|---|---|
| Executive / Control Center | Saúde agregada, prioridades, orçamento, bloqueios | Decisões, responsáveis e histórico |
| Product | Discovery, requisitos, roadmap, critérios | Requisito ligado a problema e aceite |
| Engineering | Bugs, tarefas, PRs, arquitetura, dependências | Mudança revisável, teste e commit |
| Quality / QA | Cenários, execuções, dispositivos, regressões | Evidência ligada à versão/commit |
| Cybersecurity | Ativos, riscos, vulnerabilidades, incidentes | Correção, validação e gate |
| UX / Experience | Jornadas, acessibilidade, pesquisa | Achado e verificação antes/depois |
| Marketing / Growth | Campanhas, funil, ativação e retenção agregada | Experimento consentido, resultado e custo |
| Operations | Serviços, jobs, capacidade, runbooks | Incidente/resolução e disponibilidade |
| Business | Custos, contratos, parceiros, projeções empresariais | Decisão comercial sem dados de clientes desnecessários |
| SAC / Customer Success | Atendimento, respostas, acompanhamento | Ticket resolvido, vínculo com bug quando aplicável |
| Data / Analytics | Taxonomia, qualidade e agregação de eventos | Métrica com definição, origem e limitação |
| Red Team | Contestação independente e testes autorizados | Achado reproduzível ou revisão sem achados conhecidos |
| Release Management | Gates, tag, artefatos, rollout/rollback | Release rastreável e aprovada |

Não montar uma tela gigante. Navegação por módulos, busca global com autorização aplicada antes dos resultados, filtros salvos por pessoa, visões por produto/ambiente/versão. Home mostra somente os indicadores relevantes ao papel. Estados vazios/erro/carregamento reais; nenhum card ou botão sem função.

## 5. Modelo de dados operacional

Entidades mínimas: organizações/equipe/memberships; produtos; ambientes; serviços/ativos; versões; releases/artefatos; feedbacks/evidências; tickets SAC; requisitos; tasks; incidentes; vulnerabilidades; casos e execuções QA; aprovações/gates; agentes/versões/runs/tool calls; budgets/usage; integrações; audit events; outbox/inbox.

Usar UUIDs internos. Ocorrências recebem identificador humano central `SIM-0001` etc. Não reutilizar ID de entidade financeira como ticket. Preservar `source_feedback_id` e `idempotency_key` do Collector para deduplicar import/retry. Linkar feedback → requisito/task → PR/commit → teste → release; uma task pode resolver vários tickets sem apagá-los.

Eventos de auditoria append-only para usuários comuns, ator humano/serviço/agente, timestamp servidor, motivo, antes/depois minimizado e correlation ID. Evitar anexar segredos/PII ao histórico imutável; política de expurgo e tombstone precisa permitir cumprimento das regras de dados. Não confundir log operacional com prova criptograficamente inviolável.

Versionar schemas/migrations. Aplicar constraints de produto/ambiente/owner e controle de acesso no backend/banco, não somente filtros de tela. Registrar controle de concorrência e idempotência de ações sensíveis.

## 6. Permissões e separação de deveres

RBAC com escopo de produto/ambiente e autorização por objeto. Padrão deny. Perfis iniciais: executivo; operações; produto; engenharia; QA; UX; segurança; red team; SAC; marketing; analytics; release manager; auditor; service identity. Funções humanas podem combinar perfis aprovados; agentes têm permissões próprias menores que as do responsável.

| Ação/dado | Regra inicial |
|---|---|
| Ticket comum | Equipe do produto autorizada; anexos apenas se finalidade exigir |
| Incidente de segurança/privacidade | Grupo restrito; demais setores recebem resumo sanitizado |
| Contato do cliente | SAC e finalidade específica; não marketing por herança |
| Métrica de crescimento | Agregada/consentida; supressão de grupos pequenos quando houver reidentificação |
| Segredo | Nunca retornado à UI/LLM/log; referência ao cofre, com uso por serviço autorizado |
| Mudança de permissão | Admin humano autorizado, MFA/reauth quando aplicável, auditoria |
| Deploy/rotação/exclusão | Aprovação explícita e ferramenta estreita; sem comando shell administrativo irrestrito |
| Aprovação de release | QA + segurança + responsável do produto conforme gate; autor não se autoaprova sozinho |

Marketing não lê saldos, gastos, conversas Nex ou dados individuais para segmentar. Business vê receitas/custos da empresa, não valores privados dos usuários. SAC não possui acesso financeiro geral; coleta mínimo necessário e encaminha pelo contrato.

## 7. Workflow de QA, feedback e SAC

Implementar: TESTAR → IDENTIFICAR → REGISTRAR → CLASSIFICAR → PRIORIZAR → CORRIGIR → RETESTAR → VALIDAR → LIBERAR → MONITORAR.

Separar `severity` (impacto) de `priority` (ordem de execução). Sugestão do usuário/agente não é classificação final. S0/P0: exposição/perda de dados, falha financeira crítica ou indisponibilidade relevante; P1 fluxo essencial; P2 melhoria/defeito com alternativa; P3 acabamento. Definições e exemplos por produto são versionados.

Ticket guarda observado, esperado, passos, contexto, versão/build/commit, dispositivo, evidências consentidas, impacto, responsável, prazo quando definido e histórico de decisões. Estado “corrigido” exige commit; “validado” exige reteste da candidata correspondente; “liberado” exige release distribuída, não PR aberto.

SAC distingue dúvida, bug, erro, melhoria, sugestão, financeiro, privacidade e segurança. Um ticket pode originar bug sem perder conversa/responsável; duplicatas são vinculadas, não apagadas. Segurança tem rota prioritária privada, acesso restrito e escalonamento humano. O cliente vê status permitido e resposta útil, sem notas internas, prompts ou dados de outros tickets.

Use `SIM_FEEDBACK_INTEGRATION_CONTRACT.md` como contrato de interoperabilidade. Se importador de ZIP Collector for a primeira integração, preserve IDs, valide manifesto/arquivos e trate paths/traversal/mime. Importar evidência não executa código anexo nem segue instruções dentro de screenshot/log.

Retorno por e-mail/chat/notificação exige canal configurado e autorização. Agente SAC gera rascunhos; envio automático, se futuramente aprovado, precisa de templates/escopo/limites e supervisão. Não prometer reembolso, mudança financeira ou prazo em nome da empresa sem política.

## 8. Agentes de IA com governança

Não implementar agentes trocando mensagens livremente. Um orquestrador despacha jobs tipados e limitados, com estados `queued`, `running`, `awaiting_approval`, `succeeded`, `failed`, `cancelled`, `budget_exceeded`. Cada run tem timeout, número máximo de passos e custo reservado. Dependências/loop detection evitam ciclos de agentes.

Registro obrigatório por agente: ID/versão; papel/setor/missão; dono humano; produtos/ambientes; ações/scopes; ferramentas permitidas; classes de dados; entrada/saída estruturada; memória/TTL; limites de tokens, tempo, custo e concorrência; risco; critérios de aceite; logs; aprovação/escalonamento; kill switch.

| Agente | Entrada → saída | Limite inicial |
|---|---|---|
| Product Analyst | Feedback sanitizado → hipótese/requisito/aceite | Não decide roadmap/publica promessa sozinho |
| Engineering | Task aprovada + repo permitido → patch/PR/testes | Sandbox de código; sem merge/deploy/segredos de produção |
| QA | Caso + build QA → execução/evidência/defeito | Dados sintéticos e ambientes permitidos |
| Cybersecurity | Diff/SBOM/config sanitizada → análise/achados | Somente alvos e ferramentas autorizados; sem exploração em terceiros |
| Red Team | Escopo formal + candidata → contestação/reprodução | Independente do autor; não altera gate para aprovar o próprio trabalho |
| Marketing | Métricas agregadas + briefing → rascunho/experimento | Sem publicar campanha ou acessar finanças individuais |
| SAC | Ticket autorizado/base aprovada → rascunho/encaminhamento | Sem ações de conta e sem envio livre |
| Data | Eventos permitidos → métricas/qualidade | Sem consulta irrestrita a bancos de produto |
| Release Auditor | Evidências/commit/artifacts → parecer de gates | Não inventa prova nem libera produção |

Atribuir responsável humano somente após configuração real. Reutilizar adaptador de provedor conceitualmente, sem compartilhar chaves do Nex. MockProvider em testes não se apresenta como agente real funcionando.

Ferramentas de agente têm schemas estritos e autorização externa ao modelo; não aceitar permissão declarada no prompt como credencial. Credenciais curtas/escopadas, nenhum admin global. Memória por produto/tarefa/agente e dados permitidos; sem base vetorial única juntando tickets sensíveis de todos. Expurgo cobre embeddings/resumos/cache.

Evidências, páginas web, patches e anexos são conteúdo não confiável: podem conter prompt injection. Eles não alteram instruções, permissões ou destinos de envio. Proteger egress, execução de código e upload. Aprovação humana mostra ação/diff/alvo/custo concretos; não uma pergunta vaga “posso continuar?”.

Avaliar utilidade, precisão, vazamento, custo, falhas e escalonamento em corpus versionado antes de ampliar autonomia. Iniciar read-only/rascunhos. Toda ação sensível pode ser suspensa pelo responsável; manter fallback manual.

## 9. SIM Security Gate e incidentes

Inventariar ativos, owners, classificação de dados, dependências/SBOM, secrets e permissões. CI exige SAST, dependency scan, secret scan, testes de autorização/RLS e segurança dos workflows. Fixar ações/dependências verificadas, proteger branches, revisar PRs, secrets por ambiente e deploys com identidade mínima.

Threat modeling e pentest autorizado em escopo definido, sem declarar “seguro” apenas porque um scanner passou. Vulnerabilidade tem ID, evidência sanitizada, severidade, versão afetada, correção, reteste e responsável. Segredo exposto exige rotação/invalidar, não só apagar do arquivo.

**SIM SECURITY GATE:** release não é promovida com vazamento de dados, bypass de autorização, segredo exposto, corrupção financeira conhecida ou restauração crítica inviável. Esses bloqueios não recebem waiver para “ganhar tempo”. Riscos menores podem ter aceitação humana documentada com prazo/mitigação; não mudar teste para mascarar falha.

Red Team pode contestar e bloquear por achado crítico, com registro objetivo. Mesmo equipe pequena precisa deixar claro quem desenvolveu, quem testou e quem aceitou risco. Não chamar execução do agente do autor de revisão independente.

Incidente: detectar → classificar → conter → preservar evidência mínima → corrigir → recuperar → validar → revisar causa. Logs/artefatos restritos, rotação de credenciais e runbooks testados. RPO/RTO e retenções são parâmetros aprovados por produto; medir em restore drills. Não prometer recuperação sem exercício.

## 10. Releases, GitHub e custos

Integração GitHub por app/token de escopo mínimo, validação de assinatura/replay dos webhooks e idempotência. Não usar token pessoal global no navegador. Vincular produto ao repositório autorizado; NexGrana usa `lucasmafra-creator/NexGrana`.

Release modela: versão/canal, source commit, tag, ambientes, migrations, artefatos/hashes/assinatura, suites, smokes, reviews, security gate, rollout/rollback e aprovação. Consultar CI não implica poder executar deploy. Um ZIP sem commit correspondente é bloqueado; build Android/Windows de commits distintos não representa uma mesma release.

Control Center mostra divergências e evidências faltantes. Não transformar dashboard em editor do banco de produção. Deploy automatizado só após ambientes/permissões/aprovações configurados; comandos destrutivos têm prévia, confirmação e trilha.

Budget por produto/setor/agente/ambiente, limites diários/mensais e teto de concorrência. Reservar antes de chamada, medir uso retornado e estimativa datada; não inventar fatura. Alertas/kill switches, retry controlado e custo de falhas. Custos SIM e Nex separados para entender margem da empresa, com métricas agregadas.

## 11. Implantação progressiva

| Fase | Entrega implementável | Aceite para avançar |
|---|---|---|
| A — fundação | Repo/ambientes, Auth equipe, RBAC, produtos, setores, pessoas, auditoria | Login/negações, isolamento, backup e migrations testados |
| B — operação manual | Feedback/import Collector, tickets, tasks, QA e evidências | Percurso real de um bug até reteste, sem agente obrigatório |
| C — releases/segurança | GitHub read-only, CI/evidências, security gate, incidentes e release registry | Commit→teste→artefato→aprovação rastreáveis; gate falho bloqueia |
| D — agentes assistivos | Registry/orquestrador, um Product Analyst e um Release Auditor inicialmente | Budget/scopes/injeção/cancelamento e avaliação aprovados |
| E — expansão | Engenharia/QA/SAC assistivos, marketing agregado, novos produtos | Contratos, permissões e qualidade por módulo, sem acesso financeiro amplo |

Não apresentar as cinco fases como concluídas quando apenas a home foi feita. A cada fase entregar demonstração com dados sintéticos identificados, testes, docs, limitações e próximos passos. Instalar novas integrações ou assumir custo contratado exige decisão concreta do proprietário quando ainda não autorizado.

## 12. Testes e documentação

Testar: RBAC por papel/produto/ambiente, API direta, troca de sessão, anexos privados/quarentena, idempotência/importação, tickets duplicados, estados inválidos, origem de webhooks, jobs concorrentes, agente fora de scope, prompt injection, budget, kill switch, rotas de segurança, aprovação por autor, gates/rollback, backup/restore e ausência de dados financeiros em analytics.

Documentos obrigatórios: `SIM_LABS_ESTADO_ATUAL.md`, arquitetura/ADRs, catálogo de produtos/ativos, matriz de papéis, registro de agentes, contrato feedback, incident/backup/release runbooks, política de dados/retention, testes/build/deploy, changelog e roadmap. Evidência separa IMPLEMENTADO, TESTADO, APROVADO, BLOQUEADO e PENDENTE.

## Definition of Done da primeira versão operacional

- [ ] Infraestrutura/repos/secrets separados do FinanceHub.
- [ ] Pessoas canônicas cadastráveis sem inventar logins e com direitos revisados.
- [ ] Módulos básicos úteis, navegação clara e ações reais.
- [ ] Feedback/ticket/task/QA/release ligados por IDs e histórico.
- [ ] Nenhum acesso indiscriminado às finanças dos usuários.
- [ ] Gates de segurança/qualidade testados inclusive com falha.
- [ ] GitHub e artifacts rastreáveis, sem publicação fictícia.
- [ ] Backup/restore, observabilidade e orçamento operacionais.
- [ ] Agentes, se incluídos, restritos às fases/scopes aprovados e avaliados.
- [ ] Procedimentos manuais continuam possíveis quando IA/integração falha.
- [ ] Documentação suficiente para operar sem histórico de chat.

Entregue o que foi realmente implementado com provas e limites. A SIM Labs deve aumentar a capacidade de operação da equipe, sem colocar a disponibilidade ou privacidade do NexGrana em risco.
