# Performance — NexGrana 0.19.0

## Gargalos observados/endereçados estruturalmente
- reconstrução global da página em navegação;
- decode/troca repetida de assets do Nex;
- assets raster legados de qualidade ruim ainda empacotados;
- polling frequente;
- rebuild completo do chat a cada mensagem.

## Alterações
- host Flet persistente para navegação autenticada;
- atualização parcial do histórico/composer do Nex;
- imagens derivadas por tamanho;
- remoção dos diretórios de GIFs/PNGs degradados não usados;
- poll de snapshot em 15 s;
- `PerformanceMonitor` local em memória.

## Metas de engenharia vindas da especificação
Estas são metas, **não medições**:
- feedback após toque p95 ≤100 ms;
- navegação quente p95 ≤200 ms Windows / ≤300 ms Android;
- primeiro conteúdo local p95 ≤2 s Windows / ≤3 s Android;
- resposta determinística local do Nex p95 ≤500/700 ms;
- ≥95% dos frames dentro do orçamento de 60 Hz;
- crescimento sustentado de memória após ciclos de navegação ≤10%.

## Pendência
Este runtime não possui Flet e não representa o notebook/telefone do usuário. Registrar antes/depois em build profile/release no mesmo hardware antes de afirmar ganho percentual.
