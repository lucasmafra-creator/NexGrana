# Performance — NexGrana 0.23.0 QA

- shell reutilizável evita desmontar a página a cada navegação;
- chat atualiza lista/composer sem reconstrução completa durante resposta;
- rede e Nex usam `asyncio.to_thread`, preservando o gesto de navegação;
- histórico online tem limite de 24 mensagens e 12 mil caracteres;
- Nex usa derivados 96/160/256/512 e carrega o master 1254 somente como referência/fallback;
- nenhuma animação raster nova foi carregada; microanimações transformam o controle existente;
- redução de movimento zera transformações;
- tutorial mantém somente uma sessão/sandbox por escopo ativo.

Pendente em aparelho: p50/p95 de navegação/gateway, memória, uso de CPU, queda de frames e teste Android de entrada/saída do teclado.

