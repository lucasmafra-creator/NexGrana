# Performance — NexGrana 0.20.0

## Instrumentação existente

`PerformanceMonitor` mede cada montagem de rota em memória, mantém no máximo 120 amostras por métrica e calcula p50, p95 e máximo. Nenhum conteúdo, saldo ou identificador financeiro é enviado para telemetria.

A 0.20 preserva o shell Flet entre rotas, evita limpar/recriar toda a página a cada navegação, atualiza o chat sem remontar toda a tela e usa variantes reduzidas do Nex para avatar/card/dock.

## Metas de aceite

| Medida | Windows | Android/iOS |
|---|---:|---:|
| Navegação quente p95 | até 250 ms | até 350 ms |
| Primeiro conteúdo local útil p95 | até 2 s | até 3 s |

## Estado honesto

Os testes automatizados comprovam o coletor e a reutilização do shell, mas não substituem profiling real. As metas acima permanecem pendentes até serem medidas em build instalada, com dispositivo identificado, modo release e pelo menos 30 amostras por rota crítica.

Rotas mínimas: Início, Transações, Planejamento, Mercado, Nex e Mais. Cenários adicionais: teclado do chat, troca de perfil, reconexão e abertura dos assets do Nex.
