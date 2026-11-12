# Gate de IA externa — 2026-11-12

## Resultado

**BLOCKED.** Não há confirmação de que `OPENAI_API_KEY` foi configurada pelo proprietário, não há evidência do consentimento explícito na interface do app e não existe função Edge implantada no projeto Supabase `NexGrana-QA`. Nenhuma chamada à OpenAI ou teste funcional foi feito.

## Evidências somente leitura

- Repositório [lucasmafra-creator/NexGrana](https://github.com/lucasmafra-creator/NexGrana), `main` permanece em `f4ae9704822173c2c39ab1b361257ccebbbbddd1` (último commit listado: 17/10/2026). Nenhuma mudança de fonte observada.
- Projeto Supabase `FinanceHub` (`idiyziffdzxcqmshzsws`) está ativo. A função `nex-chat` consta como `ACTIVE`, versão 2, `verify_jwt=true`. Isso comprova a implantação da função, não a presença do secret nem seu funcionamento.
- O código implantado da função lê `OPENAI_API_KEY` do ambiente e retorna 503 quando falta configuração. Ele exige sessão autenticada e consentimento `external_ai` aprovado para o usuário e household; limita o contexto financeiro a campos permitidos e envia a solicitação ao endpoint OpenAI com `store=false`. O SHA-256 reportado pela plataforma para o código é `3715765df82c4f14da2ffaf2b3f1d96eaa221f0d939841898d634a5caba97c6e`.
- A tabela `public.privacy_consents` tem RLS habilitado, política `own_consent` para `authenticated` restringida a `auth.uid()` e membership no household, e unicidade em `(user_id, household_id, purpose)`. Foram consultados apenas catálogo, colunas, índices e políticas; nenhum registro de consentimento foi lido.
- Projeto separado `NexGrana-QA` (`eofojiplctlohgijqxoz`) está ativo, mas `list_edge_functions` retornou lista vazia.
- Buscas de código no GitHub por `privacy_consents`, `external_ai`, `OPENAI_API_KEY` e termos de consentimento não retornaram arquivos indexados. Isso não prova que o controle de consentimento não exista; o checkout V7 e sua interface não foram confirmados.
- Nenhum valor de secret foi consultado, copiado ou registrado. Nenhuma função foi chamada; nenhum deploy, alteração de banco ou teste em produção ocorreu.

## Revisão de segurança limitada

**Controles observados no código implantado:** JWT obrigatório, autorização de consentimento antes da chamada externa, limite de tamanho, timeout, sanitização de alguns logs e `store=false`.

**Pontos pendentes para validar na fonte canônica:** interface e texto do consentimento; versão/registro de política apresentado ao usuário; restrição CORS (o código observado usa `*`); limite de taxa (o contador é mantido em memória por instância). Estes dois últimos são pontos de hardening a avaliar, não vulnerabilidades confirmadas nesta revisão.

## Próximos passos e gates

1. Mafra confirma que o consentimento de IA externa está visível e explícito na versão do app que será testada; sem habilitar consentimento automaticamente.
2. Confirmar a fonte V7 e o ambiente Supabase QA que será usado. O projeto `NexGrana-QA` ainda não tem `nex-chat`; qualquer deploy exige fonte confirmada e autorização do gate de publicação.
3. O proprietário cadastra `OPENAI_API_KEY` diretamente nos Secrets do projeto QA, sem enviar o valor ao chat ou à Central.
4. Depois da confirmação sem segredo, validar somente a função QA com conta e mensagem sintéticas. Registrar status e evidência sanitizada. Não chamar `FinanceHub` para provar que a chave funciona.
5. Só retomar QA da V7 quando fonte, consentimento e ambiente isolado estiverem confirmados.

## Classificação

| Critério | Estado |
| --- | --- |
| Chave configurada pelo proprietário em ambiente QA | BLOCKED / sem confirmação |
| Valor da chave protegido de chat/log/repositório | PASS / não foi consultado nem exposto nesta revisão |
| Função implantada em QA | BLOCKED / projeto QA sem função |
| Resposta funcional da função QA | NOT RUN |
| Consentimento explícito revisado na interface da fonte V7 | BLOCKED / versão V7 e interface não disponíveis |
| Teste com dados sintéticos | NOT RUN |
| Produção alterada ou testada | Não; somente metadados e catálogo consultados no projeto ativo |
