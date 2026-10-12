# Performance
Não há amostras nativas suficientes para afirmar melhoria percentual ou FPS. Os ~517 ms citados para Home são hipótese a medir, não bug confirmado. Durações de results.json medem comandos de teste, não interação mobile.

Composer do chat permanece montado em refresh; avatar recebe arquivo menor. Impactos em teclado, consumo de memória e leitura das novas imagens precisam de medição real. 36 variantes completas + compactas somam 18.841.647 bytes; mantém custo de pacote visível. Fechamento familiar enfileira a mesma RPC atômica por perfil para compatibilidade do cache: idempotente, mas pode repetir tráfego.

Próxima medição: registrar 30 amostras por fluxo em Moto G22, p50/p95, memória, entrada fria/quente, teclado e offline. Comparar baseline e candidata com mesmo conjunto sintético e redução de movimento. Sem telemetria pessoal automática nesta rodada.
