# NexGrana 0.19.0 SOL — changelog da Virada

## P0 / funcionamento
- Unificado o caminho de envio do Nex para texto, submit, seta, sugestões e ações contextuais.
- Cada solicitação usa identidade própria e escopo capturado; respostas tardias de perfil/família/mês diferente são descartadas.
- Erro de Nex passa a gerar mensagem explícita em vez de ação silenciosa.
- Layout de chat mobile reduz conteúdo não essencial durante foco e preserva o composer acima da navegação do app.
- Logout agora invalida referências de host/chat para evitar atualizar árvore Flet destacada após nova sessão.

## Performance
- Navegação deixa de limpar toda a `Page` a cada rota e passa a reutilizar host principal.
- Poll de sincronização alterado de 8 s para 15 s.
- Microanimação do Nex não troca textura/source repetidamente.
- Assets degradados `clean/clean2/display/animations/actions/expressions` foram removidos do runtime; nenhum era referenciado pelo código atual.
- Assets canônicos derivados por tamanho evitam usar a textura 1254×1254 em avatares pequenos.
- Monitor local de performance adicionado sem telemetria remota.

## Nex / produto
- `Context` do Nex carrega `request_id`, `conversation_id` e snapshot de escopo.
- Ações determinísticas: resumo do mês, próximas contas, orientação de economia, aquisição e simulação de meta.
- Trilha Nex passa para 10 etapas também nas respostas legadas.
- Diagnóstico de Renda Extra passa a 8 dimensões.

## UI / responsividade
- Design tokens centralizados.
- Diálogos principais de Trilha, Renda Extra, câmera e Privacidade passam a limitar largura/altura pelo viewport.
- Análise do mês atual compara período equivalente do mês anterior.

## Monetização sem cobrança
- Sem Premium, assinatura ou paywall.
- Contratos mínimos para `Recommendation`, `Offer`, `OfferSource`, `AffiliateProvider`, `AffiliateLink`, `SponsoredContent` e `ClickEvent`.
- Ranking de recomendação não possui comissão como entrada.
- URLs de ofertas são validadas por HTTPS/domínio e a abertura passa por disclosure já presente na UI.
- Analytics privacy-first existe somente como adaptador local e fica desligado por padrão.

## Banco
- `MIGRATION_0_19.sql` amplia progresso da Trilha para 10 e acrescenta metadados opcionais às ofertas de forma aditiva.
- A migration NÃO é aplicada automaticamente.
