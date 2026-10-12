# Auditoria de lacunas — NexGrana 0.24 QA RC1

Data: 2026-09-23. Esta auditoria compara o prompt mestre da 0.24 com o código
empacotado. `FEITO` significa comprovado por código e teste local; não significa
validação em dispositivo ou serviço externo.

| Área | Status | Evidência atual | O que falta |
| --- | --- | --- | --- |
| Regras financeiras e isolamento | FEITO local | suíte automatizada e motor canônico | smoke com Supabase e builds reais |
| Tutorial de 13 atividades | PARCIAL | superfícies distintas, sandbox e promoção seletiva | chat real no tutorial, QA visual/teclado, roteiro antes/depois e componentes mais próximos das telas reais |
| Nex online | BLOQUEADO | cliente e gateway defensivos existem | hospedar, configurar secrets/URL, consentimento real, ferramenta financeira server-side e smoke com provedor |
| Conversação natural | PARCIAL | contexto curto, respostas locais determinísticas e gateway | LLM real, corpus conversacional amplo, continuidade e custo/limites testados |
| Nex Vivo | PARCIAL | controlador/eventos e arte HD preservados; loop que sobrescrevia reação corrigido | prévia clara por intensidade, mais eventos reais, QA visual/FPS e reduzir movimento em dispositivo |
| Personalização por usuário | PENDENTE | apenas claro/escuro legado | três identidades por tokens, prévia, persistência por usuário, skins separadas e testes de troca de conta |
| Mercado/listas | PARCIAL | CRUD básico, orçamento e itens isolados por espaço | editar/excluir lista, unidades, quantidades parciais, matching arroz→produto, confirmar/desfazer e integração segura com compra |
| Achados | PARCIAL | busca/filtros, seis links e painel existente; subaba separada | rota/área independente, retorno preservando carrinho, consentimento contextual e QA do painel real |
| Aquisições x metas | PARCIAL | textos e hierarquia diferenciados; não debitam saldo | migração/compatibilidade legada e avaliação visual completa |
| Família | PARCIAL | saldo pessoal e consolidado separados na UI | RLS A/B, permissões por papel e testes reais de compartilhamento/rateio |
| Conta QA/reset | FALHA CONHECIDA | RPC exige autorização, espaço explícito e protege terceiros | sandbox permanente para UID QA, recursos experimentais habilitados, cenários prontos e reset repetível sem família real |
| Consentimentos | PARCIAL | persistência local/remota e checagem fail-closed no gateway | fluxo real contextual, revogação E2E e sincronização testada em dois dispositivos |
| Offline/persistência | PARCIAL | cache cifrado e fila já existentes | concorrência multi-dispositivo, encerramento/reabertura em APK/Windows e migrations reais |
| Nex no Android/composer | PARCIAL | há navegação de retorno no código | validar teclado, voltar sem enviar, rotação e rascunho em aparelho físico |
| Performance | PENDENTE DE PROVA | algumas chamadas/rebuilds foram reduzidos | métricas de inicialização, navegação, memória, FPS e rede fraca |
| Segurança | PARCIAL | scan estático, JWT/consentimento e sem chave no cliente | RLS real, pentest autorizado, limites distribuídos, revisão de exportação/logs e deploy seguro |
| Scripts de build | PARCIAL | validação e dois scripts de compilação | seis wrappers/preflight, lock, diagnósticos, testes negativos em CMD e abrir downloads |
| CI/build automático | PENDENTE | inexistente | workflow QA manual com jobs Windows/Android e artefatos, sem publicar sem autorização |
| Builds e instalação | BLOQUEADO NESTE AMBIENTE | ZIP fonte validado após extração | Windows/APK reais, hashes, instalação, reabertura e assinatura QA |
| iOS | FORA DESTA FASE | somente planejamento | Mac/Xcode/assinatura e validação própria |
| Documentação completa solicitada | PARCIAL | README, changelog, teste/build e memória candidata | guias de gateway/admin/build, matriz formal, segurança/performance e relatórios dos testes externos |

## Conclusão

A 0.24 RC1 é uma candidata parcial. Além do Nex online, personalização e reset
QA já apontados por Mafra, ainda não estão completos: matching de listas,
Nex Vivo com prova real, rota independente de Achados, QA real de família/RLS,
workflow e wrappers de build, métricas de performance, pentest e builds/smokes.
Não promover esta versão para oficial nem publicação.
