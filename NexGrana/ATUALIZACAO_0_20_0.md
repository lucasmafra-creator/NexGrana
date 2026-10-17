# NexGrana 0.20.0 — atualização da candidata

Data técnica desta revisão: 15/09/2026.

## Confiabilidade primeiro

- O refresh de JWT foi centralizado e protegido contra chamadas concorrentes.
- Uma operação falha por token expirado, atualiza a sessão uma vez e repete uma vez.
- Falha de rede preserva a sessão persistida; refresh inválido exige novo login e remove somente a sessão.
- Erros de API, caminhos locais e traceback não aparecem na interface pública.
- O app não devolve cache financeiro antigo quando a autorização falha.

## Finanças e escopo pessoal

- O contrato da RC4 foi preservado: renda soma; despesa reduz no vencimento; futuro apenas projeta.
- Vencimento e pagamento confirmado são estados diferentes.
- Despesas rateadas usam somente a parcela do perfil ativo.
- Início e Nex usam o perfil selecionado por padrão; consolidado familiar é identificado separadamente.
- Metas e aquisições de outra pessoa não entram em simulação pessoal.
- Foram adicionadas regressões exatas para Mafra, Karol, dia 20, rateio e falha sem valor inventado.

## Navegação e produto

- Removidas as abas superiores `Análises / Nex / Renda extra`.
- Desktop: seis destinos claros na lateral.
- Mobile: Início, Transações, Planejamento, Mercado e Nex; Mais fica no cabeçalho.
- Saúde Financeira abre a análise a partir do Início.
- Metas, Aquisições, Investimentos e Renda extra vivem dentro de Planejamento.

## Nex e conversas

- Nex abre direto no chat e todas as ações continuam pelo mesmo dispatcher assíncrono.
- Respostas de saldo, conta, meta e aquisição usam somente o perfil selecionado.
- Cada perfil tem um chat livre e até cinco assuntos fixados.
- Ao tentar fixar o sexto, o usuário escolhe qual conversa arquivar; as mensagens antigas são preservadas.
- O banco aplica limite e troca de forma transacional, com RLS por família, pessoa e usuário autenticado.
- Offline mantém histórico local cifrado quando o cofre está disponível e marca mensagens para sincronização.

## Investimentos e Renda extra

- Nova área educativa de Investimentos sem ordens, cotação, ativo específico ou promessa de retorno.
- Simulador aceita valor inicial, aporte, prazo, taxa hipotética mensal/anual, aporte no início/fim, custos e impostos informados.
- Taxa anual usa equivalência mensal composta e exibe a convenção.
- Simulações nunca criam renda, despesa ou aporte real.
- Trilhas de Renda extra preservam dez etapas, progresso, pausa, custos/notas e lembrete opt-in dentro do app.

## Achados NexGrana

- Mercado recebeu uma seção de ofertas afiliadas independente do cálculo financeiro.
- Seis URLs fornecidas pelo proprietário compõem o catálogo inicial.
- Preço, avaliação, vendedor, desconto e imagem não são inventados.
- Sem preço confiável, a interface exibe `Preço indisponível`/`Consultar oferta`.
- A comissão não participa do ranking ou da análise de compra e o disclosure aparece antes da abertura externa.

## Assets e plataformas

- O `nex_hd.png` canônico permanece com SHA-256 `4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796`.
- O novo `src/assets/icon.png` aprovado tem 1254 × 1254 px e SHA-256 `36296882b0715a91fa0c751cdbc741d1efd1d7c054ec4da002959758d0c3284f`.
- O pin de `cryptography` foi alterado de 50.0.0 para 48.0.0 por disponibilidade do wheel Android no ambiente Flet informado.
- O script de build separa artefatos/logs e oferece Windows, APK, AAB e IPA.
- IPA não é marcado como validado fora do macOS.

## Banco

`MIGRATION_0_20.sql` cria conversas/mensagens do Nex, índices, gatilhos de escopo, RLS, RPCs de fixação e campos do catálogo afiliado. É aditiva, idempotente e não é aplicada automaticamente.

## Fora da alegação desta candidata

- builds e instalação real da 0.20 ainda dependem de autorização e teste do proprietário;
- publicação em Play Store/App Store;
- preço/cotação de mercado em tempo real;
- notificação push em segundo plano;
- LLM externo, ordens de investimento e promessa de retorno;
- animações adicionais do Nex além dos assets estáticos/fallback já seguros.

