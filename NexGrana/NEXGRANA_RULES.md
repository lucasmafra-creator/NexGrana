# Regras canônicas do NexGrana

Estas regras são invariantes do produto. Uma correção visual ou técnica não pode alterá-las sem requisito aprovado e testes financeiros correspondentes.

## Saldo e lançamentos

- Não inventar saldo, renda, despesa, preço, pagamento ou resultado para preencher a interface real.
- Renda entra no período conforme competência informada; a ausência de data não autoriza inventar um dia. Um registro sem competência e sem data deve ser rejeitado.
- Despesa futura permanece futura. O saldo só muda na data de vencimento conforme o motor financeiro vigente; um indicador “paga” não antecipa débito.
- Despesas canceladas não reduzem saldo; IDs repetidos contam uma vez.
- Erro de leitura, cache ausente ou falha de sincronização não pode virar saldo zero nem lista vazia apresentada como dado real.
- Lançamentos financeiros devem manter valor, perfil, competência e idempotência. Reenvio não pode duplicar lançamento.
- Previsões, simulações e dados de treino precisam ser identificados e nunca promovidos silenciosamente ao ledger real.

## Perfis e privacidade

- O usuário vê somente dados que pertencem ao perfil e espaço ativos e para os quais está autorizado.
- Isolamento de família, integrante, usuário, conversas e workspace QA é obrigatório no cliente e no servidor.
- Não enfraquecer RLS, autorização, consentimento ou escopo de reset para fazer uma tela funcionar.
- Logs e evidências não devem conter tokens, senhas, saldos, mensagens privadas ou dados de conta identificáveis.

## Dados e homologação

- Não substituir dados persistidos por mocks para fazer a interface parecer funcional.
- Mocks são permitidos em teste isolado quando identificados como dados sintéticos.
- Não apagar, recriar ou migrar banco real durante QA sem backup e autorização específica.
- PGlite local comprova cenários locais; não comprova RLS, autenticação ou migrations em Supabase hospedado.

## Identidade do Nex

- Nex é a coruja roxa reconhecível. Preservar espécie, rosto, proporções, óculos, bico e assinatura visual canônica.
- Roupas, skins e temas podem variar sem transformar a experiência financeira em jogo infantil.
- O master validado no candidato usa SHA-256 `4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796`.
- Skins sociais e sazonais devem ser respeitosas e ativadas conforme as preferências/autorização já testadas.
