# Matriz de requisitos — NexGrana 0.20.0

Atualização: 15/09/2026. “Validado” abaixo significa teste automatizado indicado; teste real de plataforma permanece separado.

| ID | Requisito | Fase | Módulo/evidência | Estado | Teste/resultado | Pendência/responsável |
|---|---|---|---|---|---|---|
| AUTH-01 | Refresh JWT coordenado e uma repetição | 0.20 | `src/cloud.py` | validado | testes de JWT/concorrência OK | dispositivo: proprietário |
| AUTH-02 | Offline não destruir sessão persistida | 0.20 | `src/cloud.py` | validado | falha de rede OK | retomada real: proprietário |
| AUTH-03 | Erro público sem traceback/APIError | 0.20 | `auth.py`, `main.py` | validado | UI/falha OK | revisão visual real |
| FIN-01 | Renda soma por competência | 0.20 | `finance_engine.py` | validado | regressões financeiras OK | nenhuma |
| FIN-02 | Futuro não reduz; vencimento reduz | 0.20 | `expense_status` | validado | dia 19/20 OK | fuso em dispositivo |
| FIN-03 | Vencimento não inventa pagamento | 0.20 | motor + rótulos | validado | confirmação ausente OK | nenhuma |
| FIN-04 | Rateio e soma familiar reconciliados | 0.20 | `member_snapshot` | validado | centavos/rateio OK | nenhuma |
| SCOPE-01 | Perfil pessoal por padrão | 0.20 | Home/Análise/Nex | validado | Mafra/Karol OK | teste com dados reais |
| SCOPE-02 | Família somente como consolidado explícito | 0.20 | Home | implementado | suíte UI OK | teste visual real |
| NAV-01 | Seis destinos desktop | 0.20 | `src/main.py` | validado | todas as rotas OK | navegação manual |
| NAV-02 | Cinco destinos mobile + Mais | 0.20 | `src/main.py` | validado | larguras/rotas OK | Android/iPhone reais |
| NAV-03 | Planejamento reúne quatro áreas | 0.20 | `planning.py` | validado | construção de telas OK | UX manual |
| NEX-01 | Dispatcher único e assíncrono | 0.20 | `nex.py`, `nex_engine.py` | validado | ações/respostas OK | carga real |
| NEX-02 | Resposta financeira rastreável e pessoal | 0.20 | snapshot/contexto | validado | isolamento/falha OK | ambiguidade ampliada |
| CHAT-01 | Um livre + cinco fixados por pessoa | 0.20 | Nex + migration | validado | UI e SQL OK | nenhuma |
| CHAT-02 | Sexta conversa troca atomicamente | 0.20 | RPC `pin_nex_conversation` | validado | limite/troca SQL OK | corrida no Supabase real |
| CHAT-03 | Histórico local cifrado/pending offline | 0.20 | Nex + vault | implementado | suíte UI OK | reconexão em dispositivo |
| CHAT-04 | Paginação, exclusão/tombstone e retenção completa | pós-lançamento | backlog | adiado com justificativa | não aplicável | definir política: proprietário |
| INV-01 | Conteúdo educativo sem ordem/cotação | 0.20 | `investments.py` | implementado | inspeção/suíte UI OK | revisão de conteúdo |
| INV-02 | Simulador com premissas explícitas | 0.20 | `investment_engine.py` | validado | 5 cenários OK | UX manual |
| EXTRA-01 | Trilha de dez etapas sem reiniciar progresso | 0.20 | `extra_income.py` | validado | jornada de 10 etapas OK | migração real |
| EXTRA-02 | Pausa, notas, custos e lembrete opt-in | 0.20 | Renda extra | implementado | telas/diálogos OK | teste manual |
| MARKET-01 | CRUD e conferência financeira preservados | 0.20 | Mercado | validado | atomicidade/nota OK | câmera/galeria reais |
| OFFER-01 | Seis links exatos sem preço inventado | 0.20 | `offers.py`, migration | validado | catálogo inicial OK | elegibilidade comercial |
| OFFER-02 | Disclosure e comissão fora do ranking | 0.20 | Mercado/affiliate | validado | ranking independente OK | revisar termos do programa |
| OFFER-03 | Resolver server-side robusto de links curtos | pré-publicação | backend futuro | não iniciado | — | backend/infra: proprietário |
| ASSET-01 | Master Nex preservado | 0.20 | `nex_hd.png` | validado | SHA-256 confirmado | nenhuma |
| ASSET-02 | Novo ícone de alta resolução aprovado | 0.20 | `src/assets/icon.png` | implementado | 1254 px/hash | gerar/verificar variantes em builds |
| ANIM-01 | Feedbacks animados adicionais com redução de movimento | pós-lançamento | backlog | adiado com justificativa | — | escolher formatos/assets |
| DB-01 | Migration aditiva/idempotente | 0.20 | `MIGRATION_0_20.sql` | validado localmente | PGlite OK | homologação/backup real |
| DB-02 | RLS chat e isolamento familiar | 0.20 | policies/triggers | validado localmente | ataques cruzados bloqueados | Supabase real |
| DEP-01 | Wheel Android de cryptography disponível | 0.20 | pin 48.0.0 | implementado | validação de dependência | build APK/AAB |
| PLAT-01 | Windows 0.20 | pré-publicação | build/checklist | em implementação | fonte aprovada | build/instalação: proprietário |
| PLAT-02 | Android APK/AAB 0.20 | pré-publicação | build/checklist | em implementação | fonte aprovada | build/dispositivo: proprietário |
| PLAT-03 | iOS IPA 0.20 | pré-publicação | macOS/Xcode | bloqueado externamente | comando protegido | Mac/Apple: proprietário |
| CI-01 | Validação automática Python/SQL | 0.20 | GitHub Actions | implementado | workflow criado | confirmar execução no GitHub |
| PERF-01 | p50/p95 local sem dado financeiro | 0.20 | `PerformanceMonitor` | implementado | coletor testado | medir builds reais |
| GROW-01 | Métricas privacy-first sem dados financeiros | 0.20 | analytics local desligado | validado | filtro de payload OK | consentimento/infra futura |
| GROW-02 | Loops virais públicos/indicação | pós-lançamento | backlog | adiado com justificativa | — | legal, consentimento e backend |
| RELEASE-01 | ZIP, manifesto e hashes finais | quando autorizado | empacotamento | não iniciado | — | solicitação explícita do proprietário |

## Critérios de saída

A candidata só pode ser chamada de validada para uma plataforma após: suíte aplicável, migration homologada, artefato construído, instalação/atualização concluída, login/JWT, finanças, Nex, offline e isolamento exercitados sem P0/P1 conhecido.
