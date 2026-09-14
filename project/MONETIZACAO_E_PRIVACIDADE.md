# NexGrana — monetização sustentável mantendo o app gratuito

## Decisão
Nesta fase o NexGrana é 100% gratuito para o usuário: sem Premium, assinatura, paywall ou limitação artificial para vender desbloqueio.

## Regra-mãe
O NexGrana ganha quando ajuda. O Nex não vira vendedor e a comissão não entra no cálculo que decide se uma compra é saudável.

## Prioridade
1. afiliados em intenção de compra real;
2. comparação/ofertas contextualizadas;
3. parcerias e conteúdo patrocinado claramente identificado;
4. CPA/CPL apenas por solicitação consciente;
5. B2B futuro, validado comercialmente antes de construir;
6. publicidade tradicional somente se a receita justificar o impacto de UX — sem SDK nesta candidata.

## Arquitetura atual
- ranking de recomendação separado de `AffiliateProvider`/link;
- disclosure visível nas ofertas;
- validação de URL por HTTPS/domínio;
- falta de afiliado não remove recomendação útil;
- analytics remoto desligado por padrão;
- nenhum saldo, renda, despesa, texto de chat, e-mail ou ID familiar deve entrar em evento comercial.

## LGPD / confiança
- não vender dados;
- não enviar contexto financeiro a parceiros;
- consentimentos opcionais separados quando necessários;
- permitir ocultar oferta em evolução futura;
- verificar termos e elegibilidade por plataforma antes de ativar parceiros.
