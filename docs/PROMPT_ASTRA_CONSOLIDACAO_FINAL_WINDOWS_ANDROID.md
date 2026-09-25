# PROMPT ASTRA — CONSOLIDAÇÃO FINAL WINDOWS/ANDROID + BASE iOS + SIM LABS

## Papel

Atue como auditor sênior, arquiteto de software, produto, segurança e operações. Audite a base real antes de propor implementação. Não reinicie o projeto, não restaure versões antigas e não marque funcionalidades como prontas sem evidência.

## Objetivo

Esta é a grande consolidação final do NexGrana para Windows e Android antes da etapa iOS. Depois desta atualização, se testes, builds, UX, Supabase, backend e regressões forem aprovados, a próxima fase será a implementação iOS.

iOS não deve ser implementado agora, mas deve ser arquitetado de forma completa para evitar refatoração estrutural posterior.

## Auditoria obrigatória

Inspecione a base mais recente, incluindo código, `NEXGRANA_ESTADO_ATUAL.md`, manifests, changelogs, migrations, testes, relatórios, dependências, gateway/backend, Flet/Flutter, Supabase, persistência, scripts de build, feedbacks, imagens, vídeos e evidências de bugs.

Classifique itens como IMPLEMENTADO, TESTADO, APROVADO, BLOQUEADO ou PENDENTE. Não use "pronto" sem evidência.

## Escopo funcional obrigatório

Auditar, completar e validar:

- Nex online real via gateway HTTPS.
- JWT Supabase, consentimento e autorização.
- Ferramentas financeiras determinísticas; o LLM nunca deve inventar números.
- Arquitetura desacoplada de provedor de IA.
- QA oficial isolado por UID/workspace/RLS.
- Reset seguro de QA.
- Ambientes DEV/QA/PROD.
- Migrations versionadas.
- Tutorial interativo completo.
- Nex Vivo e seus estados.
- Personalização por usuário e temas.
- Mercado/Listas e matching assistido.
- Achados.
- Família e permissões.
- Metas e Aquisições como conceitos distintos.
- Investimentos e regressões matemáticas.
- Privacidade e consentimento.
- Controle de custo da IA.
- Backup e recuperação.
- Exportação/exclusão de dados.
- Logs e observabilidade sem dados sensíveis.
- Analytics com privacidade.
- Offline, fila, retry, conflitos e idempotência.
- UX/UI profissional, consistente e sem aparência de template gerado por IA.
- Performance medida.
- Build e smoke tests Windows.
- Build e smoke tests Android.
- APK e, se fizer sentido, AAB.

## Arquitetura do Nex

Separar claramente:

LOCAL
- cálculos;
- regras financeiras;
- validações.

SERVER
- autenticação;
- autorização;
- contexto;
- tools;
- rate limiting;
- segurança;
- observabilidade.

LLM
- interpretação;
- linguagem natural;
- explicação.

O modelo conversa. O motor financeiro calcula.

Prever interface de provedor, por exemplo:
- AIProvider;
- OpenAIProvider;
- FutureProvider;
- MockProvider.

Criar/validar tools financeiras como saldo atual, resumo mensal, contas futuras, progresso de metas, resumo familiar, gastos por categoria, gasto seguro, aquisições e lista de mercado.

## Gateway

Preparar backend para Render ou infraestrutura equivalente, com variáveis de ambiente e healthcheck. Implementar timeout, retry controlado, idempotência, rate limit, tratamento de 429/5xx, logs estruturados, request/correlation ID, validação JWT e versionamento de API.

Nenhuma chave secreta deve ir para APK, EXE ou GitHub.

## Supabase

Usar o projeto oficial FinanceHub. Identidade principal por `auth.users.id`, não por e-mail. QA pode permanecer no mesmo Supabase nesta fase desde que haja isolamento real por UID/workspace/RLS.

Toda mudança de schema deve ser migration versionada. Evitar alterações manuais sem histórico e evitar operações destrutivas sem estratégia de migração e recuperação.

## GitHub — regra obrigatória a partir desta versão

O repositório correto é este projeto NexGrana, não o projeto DIO.

Cada ZIP oficial deve corresponder ao GitHub:

1. código-fonte descompactado atualizado;
2. documentação atualizada;
3. migrations atualizadas;
4. testes atualizados;
5. `NEXGRANA_ESTADO_ATUAL.md` atualizado;
6. changelog atualizado;
7. commit claro;
8. tag de versão;
9. GitHub Release quando possível;
10. ZIP oficial anexado à release quando possível;
11. registro de commit SHA e hash do ZIP.

Não usar a branch principal como simples depósito de ZIPs. O source of truth deve ser o código-fonte versionado.

Se não houver permissão para uma ação externa, não fingir que foi executada; registrar a pendência e fornecer comandos/arquivos exatos.

## iOS — arquitetar, não implementar

Produzir `IOS_ARCHITECTURE_PLAN.md` cobrindo compatibilidade de dependências/plugins, secure storage, permissões, safe areas, teclado, navegação, picker, câmera/galeria, notificações, deep links, Supabase, OAuth se houver, Nex online, offline/cache, persistência, assinatura, Bundle ID, certificados, provisioning, GitHub Actions macOS, TestFlight, App Store e checklist de testes.

A próxima fase, após aprovação Windows/Android, será iOS.

## Feedback e SIM Labs

O NexGrana é Produto #001 da SIM Labs.

Arquitetar a SIM Labs como control plane separado do product plane do NexGrana. Não misturar indiscriminadamente dados financeiros dos usuários com sistemas internos da empresa.

O app de feedback deve futuramente integrar:
Usuário/QA → Feedback → SIM Labs → triagem → severidade → setor → task → correção → reteste → validação → release.

Prever múltiplas imagens, vídeo, contexto, versão, plataforma, logs permitidos e classificação.

Produzir `SIM_FEEDBACK_INTEGRATION_CONTRACT.md`.

## SIM Labs

Produzir um segundo prompt separado, `PROMPT_MESTRE_SIM_LABS.md`, para profissionalização da empresa e central de comando.

A central deve prever setores como Executive/Control Center, Product, Engineering, QA, Cybersecurity, UX, Marketing/Growth, Operations, Business, SAC/Customer Success, Data/Analytics, Red Team e Release Management.

Preservar a estrutura humana canônica já definida pelo projeto, mas permitir expansão futura.

## Agentes de IA da empresa

Arquitetar agentes com ID, papel, setor, missão, permissões, ferramentas, dados permitidos, limites, responsável humano, entradas, saídas, critérios de aceite, logs, custo, risco e escalonamento humano.

Aplicar menor privilégio. Nenhum agente deve possuir acesso administrativo global por conveniência.

Prever Product Analyst Agent, Engineering Agent, QA Agent, Cybersecurity Agent, Marketing Agent, SAC Agent, Data Agent, Release Auditor e Red Team Agent.

## Segurança SIM Labs

Prever inventário de ativos, secrets management, SAST, dependency scanning, RLS tests, threat modeling, RBAC, auditoria, incidentes, backups, restore drills, rotação de chaves, CI/CD seguro, proteção de branches e security gate de release.

## Entregáveis do Astra

Gerar separadamente:

1. Auditoria executiva da base real.
2. `PROMPT_FINAL_SOL_NEXGRANA.md` — prompt executável e refinado para o Sol/Work.
3. `PROMPT_MESTRE_SIM_LABS.md`.
4. `IOS_ARCHITECTURE_PLAN.md`.
5. `SIM_FEEDBACK_INTEGRATION_CONTRACT.md`.

## Definition of Done

A atualização só pode ser candidata a aprovação quando houver evidência para regressões financeiras, Supabase, RLS, QA, reset, gateway, Nex online, consentimento, tutorial, Nex Vivo, personalização, Mercado, Achados, Família, Metas, Aquisições, Investimentos, offline, persistência, segurança, performance, Windows build, APK, smoke tests, documentação, GitHub sincronizado, hash, estado canônico e plano iOS.

Se algo falhar, marcar PENDENTE.

## Filosofia

O NexGrana deve sair desta atualização mais simples para o usuário, mais sólido internamente, mais bonito, coerente, seguro, previsível, sustentável e preparado para iOS.

A SIM Labs deve ser concebida como sistema operacional da empresa: pessoas + agentes + processos + produtos + feedback + segurança + qualidade + dados + releases.

Audite primeiro. Decida segundo. Refine terceiro. Só então gere os prompts finais.
