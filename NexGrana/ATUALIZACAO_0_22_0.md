# NexGrana 0.22.0 QA RC1 — atualização

## Implementado

- textos adaptativos para espaço individual/familiar;
- tutorial compacto de sete passos, com benefício, ação prática e progresso;
- Trilhas Nex específicas para atividades selecionadas, XP, níveis e conquistas derivadas do progresso;
- Nex híbrido com ferramentas financeiras locais e gateway online opt-in;
- cliente do gateway com HTTPS público, JWT, timeout, limite de histórico/contexto e fallback honesto;
- backend FastAPI separado com validação JWT via JWKS, rate limit, logs sem conteúdo e chave somente no servidor;
- melhor compreensão local de saudações/gírias e orientação inicial de programação;
- chat móvel com botão Voltar textual, estado local/online, renomear e excluir conversas fixadas;
- painel privado de Achados com busca, filtros, prévia, imagem acessível, preço opcional, publicar/desativar e excluir;
- migration 0.22 com defesa em profundidade para URL de imagem, título, validade, tags, ordem e auditoria;
- testes do painel, gateway, experiência individual/familiar e gamificação.

## Não ativado automaticamente

- o gateway fica desligado até `NEX_GATEWAY_URL`/`NEXGRANA_NEX_GATEWAY_URL` apontar para HTTPS real;
- conversa externa exige consentimento “IA externa” do usuário;
- pesquisa web com fontes ainda não foi conectada; não é anunciada no produto;
- imagens dos seis produtos não foram inventadas nem copiadas sem origem autorizada.

O contrato financeiro permanece inalterado: renda válida soma, despesa da competência só reduz o saldo quando a data chega, e futuro aparece apenas no projetado.
