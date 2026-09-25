# NexGrana

NexGrana é o Produto #001 da SIM Labs: um aplicativo financeiro multiplataforma com foco em Windows e Android nesta fase, preparado arquiteturalmente para iOS na fase seguinte.

## Estado atual

- Base ativa de desenvolvimento: linha 0.24 QA/RC.
- Plataformas prioritárias desta consolidação: Windows e Android.
- iOS: arquitetura obrigatória agora, implementação somente após aprovação da consolidação Windows/Android.
- Supabase oficial: projeto FinanceHub.
- QA oficial: conta de homologação dedicada, isolada por UID/workspace/RLS.
- Nex online: deve operar por gateway HTTPS; nenhum segredo pode existir no APK/EXE.
- Cada release oficial deve manter código-fonte, documentação, testes, migrations, changelog, estado canônico, commit/tag e artefatos coerentes.

## Arquitetura

O NexGrana deve separar:

1. **Camada local** — regras e cálculos determinísticos.
2. **Gateway/backend** — autenticação, autorização, contexto, tools, rate limits, observabilidade e integração com IA.
3. **LLM** — interpretação, conversa e explicação; nunca fonte da verdade para números financeiros.
4. **Supabase** — autenticação, persistência, RLS, QA e dados do produto.
5. **SIM Labs** — control plane corporativo separado do product plane do NexGrana.

## Próxima grande atualização

Esta é a consolidação final de Windows + Android antes da implementação iOS. O escopo inclui Nex online real, gateway, QA/reset, tutorial, Nex Vivo, personalização, Mercado/Listas, Achados, Família, Metas, Aquisições, Investimentos, privacidade, custo de IA, backup, exportação/exclusão, observabilidade, analytics, offline/resiliência, testes, builds e sincronização com GitHub.

O prompt de auditoria e refinamento para o Astra está em:

`docs/PROMPT_ASTRA_CONSOLIDACAO_FINAL_WINDOWS_ANDROID.md`

A visão inicial da SIM Labs está em:

`docs/SIM_LABS_ARQUITETURA.md`

## Regra de release

Nenhum ZIP oficial deve existir sem correspondência com o código versionado. Para cada release:

- atualizar o código-fonte descompactado;
- atualizar testes, migrations e documentação;
- atualizar `NEXGRANA_ESTADO_ATUAL.md`;
- registrar commit SHA e hash do ZIP;
- criar tag;
- publicar GitHub Release quando possível;
- anexar o ZIP oficial à release.

## Segurança

Nunca versionar ou embutir:

- `OPENAI_API_KEY`;
- `SUPABASE_SECRET_KEY`;
- service role;
- tokens;
- credenciais privadas.

Segredos pertencem ao backend/ambiente seguro.
