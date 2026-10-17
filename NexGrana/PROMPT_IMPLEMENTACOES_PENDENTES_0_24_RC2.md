# Prompt de implementação — NexGrana 0.24 QA RC2 corretiva

Você é o engenheiro responsável por concluir as lacunas verificadas da candidata
0.24 QA RC1. Trabalhe diretamente na base anexada. Antes de alterar código, leia
`NEXGRANA_ESTADO_ATUAL.md`, `AUDITORIA_LACUNAS_0_24_RC1.md`, o estado oficial
0.23, relatórios, migrations e testes. Não declare uma entrega concluída apenas
porque existe código preparatório ou mock.

## Objetivo

Entregar uma RC2 que resolva prioritariamente: Nex online real, ambiente oficial
de homologação, personalização por usuário e lacunas funcionais já confirmadas.
Preserve o design aprovado, o Golden Nex e todas as regras financeiras.

## P0 — Nex online operacional

1. Diagnostique cliente → URL embutida → HTTPS → gateway → JWT Supabase →
   consentimento → provedor → resposta renderizada.
2. Prepare deploy reproduzível do gateway FastAPI em serviço autorizado. Nunca
   coloque `OPENAI_API_KEY`, service role ou segredo no APK/EXE/repositório.
3. Crie configuração pública de build para a URL `/v1/chat`, sem depender do CMD
   do usuário final. Separe liveness, readiness e smoke autenticado.
4. Confirme issuer/audience/algoritmo do JWT real. O gateway deve derivar o UID
   do token validado e conferir consentimento/espaço no servidor.
5. Implemente ferramentas financeiras server-side tipadas e autorizadas ou
   mantenha respostas financeiras determinísticas no cliente. O LLM nunca pode
   inventar ou confiar em números enviados como verdade pelo cliente.
6. Implemente timeout coerente, uma política consciente de retry, idempotência,
   limite por usuário/global, orçamento de tokens/custo e logs sem mensagens,
   valores ou tokens.
7. Teste com provedor real e conta sintética em Windows e Android. Registre
   endpoint, versão, request ID sanitizado, latência e resultado; não registre
   segredo. Se credencial/hospedagem/custo não forem autorizados, marque
   `BLOQUEADO` e entregue exatamente o passo externo faltante.
8. O Nex deve conversar naturalmente em português brasileiro, entender erros,
   abreviações e gírias, respeitar apelido preferido, manter contexto curto e não
   repetir fallback genérico. Use um corpus de conversas, não uma coleção de `if`.

## P0 — conta oficial de homologação e reset

1. Considere `[e-mail redigido]` apenas como rótulo humano. Autorize o UID
   oficial em tabela/regra server-side `qa_testers`; não confie no e-mail da UI.
2. Crie um workspace sandbox QA exclusivo, descartável e separado de famílias
   reais. Todos os recursos e feature flags da candidata devem ficar disponíveis
   nele: tutorial, temas, Nex Vivo, consentimentos de teste, Nex online quando
   configurado, Mercado/listas, Achados, metas, aquisições e investimentos.
3. Ofereça cenários restauráveis: individual vazio, individual preenchido,
   casal/família sintética, contas futuras, mês apertado, offline/fila e metas.
4. `RESETAR_TESTE` deve restaurar somente o sandbox alvo e funcionar repetidas
   vezes após alternar cenários. Nunca apagar família real, conta Auth, senha,
   dados de terceiros ou assumir propriedade transferida.
5. Resposta de erro deve distinguir migration ausente, UID não autorizado,
   sandbox inexistente, conflito de membros e rede/sessão.
6. Teste conta QA e conta comum: conta comum não vê nem executa painel/RPC;
   QA não ganha privilégios fora do sandbox. Use RLS e testes A/B reais.

## P1 — personalização por usuário

1. Crie “Aparência e Nex” em local descobrível e prévia antes de salvar.
2. Implemente três identidades do mesmo design system, sem duplicar telas:
   `Nex Original` (violeta premium), `Claro Moderno` e `Tech Escuro`.
3. Centralize tokens de fundo, superfície, borda, texto, destaque e estados.
   Elimine cores fixas que impeçam aplicação consistente.
4. Preferência pertence ao usuário autenticado, não à família ou aparelho;
   persiste cifrada localmente, sincroniza quando possível e sobrevive ao
   reinício. Trocar conta não pode herdar o tema privado da conta anterior.
5. Separe tema de skins/acessórios. Skins preservam anatomia, rosto, olhos,
   proporções, cores reconhecíveis e qualidade canônica do Nex.
6. Validar contraste, fonte dinâmica, reduzir movimento, telas/dialogs/estados
   e responsividade em Windows e Android. Testar offline e troca de usuário.

## P1 — Nex Vivo e tutorial

1. Faça eventos reais provocarem reações observáveis: início, renda, despesa,
   meta, conquista, alerta, tutorial e chat. Não use animação constante.
2. Modos Discreto/Normal/Expressivo precisam produzir diferenças demonstráveis;
   “Reduzir movimento” sempre prevalece. Inclua botão de prévia.
3. Preserve o PNG canônico; se animação reduzir nitidez/FPS, use estático.
4. No tutorial, use conversa real quando online e fallback de treino claramente
   identificado quando offline. Validar teclado e voltar sem enviar no Android.
5. Finalize as 13 experiências próprias e teste prática, progresso,
   manter/descartar/cancelar e promoção parcial idempotente.

## P2 — Mercado, listas e Achados

1. Completar listas: editar/excluir lista, unidades, quantidade parcial,
   comprados/faltantes, orçamento/restante e estados offline/conflito.
2. Implementar matching assistido: item “Arroz” e compra “Arroz Solito 5kg”
   geram sugestão “Marcar Arroz como comprado?”. Nunca assumir silenciosamente.
   Permitir confirmar, rejeitar e desfazer sem duplicar despesa ou item.
3. Integrar lista e carrinho preservando regra: somente confirmação explícita
   cria despesa real.
4. Transformar Achados em área/rota coerente separada da operação de Mercado,
   com retorno preservando carrinho/lista. Manter busca, filtros, seis links,
   divulgação de afiliado e ranking independente de comissão.
5. Validar painel administrativo real; somente administradores autorizados no
   backend podem alterar links. Nunca usar `service_role` no app/painel cliente.

## P2 — família, metas e aquisições

1. Validar no Supabase real saldo pessoal, consolidado, rateios, papéis e RLS
   com duas contas. UI nunca promete acesso maior que a regra do banco.
2. Preservar aquisição como desejo sem compromisso; meta possui prazo/progresso.
   Compatibilizar dados antigos e impedir débito/duplicação.
3. Revisar estados vazios, erro, loading e offline de todas as telas afetadas.

## Engenharia, segurança e entrega

1. Aplicar migrations somente em Supabase QA após backup. Testar upgrade 0.23 →
   0.24/RC2, rollback seguro e RLS A/B. Não alterar produção automaticamente.
2. Executar revisão de secrets, logs, exportação, cache cifrado, fila,
   concorrência, idempotência e teste de abuso autorizado. “Scan OK” não é pentest.
3. Medir inicialização, troca de telas, queries, rede fraca, memória e FPS;
   registrar baseline e resultado.
4. Criar wrappers na raiz: `00_VERIFICAR_AMBIENTE.cmd`, `01_PREPARAR.cmd`,
   `02_TESTAR.cmd`, `03_ABRIR_APP.cmd`, `04_GERAR_WINDOWS.cmd`,
   `05_GERAR_ANDROID.cmd`, `06_ABRIR_DOWNLOADS.cmd`. Eles devem derivar `%~dp0`,
   suportar caminhos com espaços, manter logs, falhar com código não zero,
   encerrar apenas sua árvore de processos e nunca declarar artefato inexistente.
5. Preparar workflow QA manual com jobs de teste, Windows e Android. Não fazer
   push, publicar release, ativar custo ou cadastrar secrets sem autorização.
6. Gerar e testar pacote Windows e APK reais; instalar/abrir, persistir dado
   sintético, fechar/reabrir e verificar gateway/sandbox. Registrar hashes e
   assinatura QA. Se o host não permitir, marcar bloqueado sem falsificar êxito.

## Testes obrigatórios mínimos

- regressões financeiras existentes;
- reset QA repetido e isolamento contra conta comum/família real;
- três temas, troca de usuário, reinício e offline;
- gateway: consentimento concedido/revogado, JWT inválido/expirado, URL ausente,
  401/403/429/5xx, timeout, idempotência e provedor real separado dos mocks;
- corpus conversacional com gírias, erros, continuidade, ambiguidade e perguntas
  gerais seguras; valores financeiros sempre determinísticos;
- matching de lista com confirmação/rejeição/desfazer/quantidade parcial;
- 13 etapas do tutorial, teclado/voltar, Nex Vivo e reduzir movimento;
- individual/família, RLS A/B, consentimentos e persistência após reabrir;
- scripts CMD em falhas negativas e artefatos de versão antiga;
- builds, instalação e smoke em Windows/Android.

## Documentação e Definition of Done

Atualize `NEXGRANA_ESTADO_ATUAL.md`, auditoria/matriz, TEST_REPORT, BUILD_REPORT,
CHANGELOG, README_RELEASE, guias de gateway/admin/build, SECURITY_REVIEW e
PERFORMANCE_REPORT. Cada requisito deve apontar para código + teste + evidência
ou ficar `PENDENTE/BLOQUEADO` com causa e responsável.

Não considerar concluído enquanto faltar qualquer P0. Não chamar gateway
“online” sem resposta real no app. Não chamar personalização de “implementada”
com apenas claro/escuro. Não chamar reset de “funcional” se o teste oficial
continua recebendo recusa. Não chamar ZIP fonte de build.

Ao final, entregar código incremental, migrations, relatórios, pacote limpo,
manifesto, SHA-256 e binários reais somente quando gerados. Extrair o ZIP final
em pasta limpa, repetir os testes e conferir inventário. O estado oficial 0.23
só é promovido após a aprovação explícita de Mafra.
