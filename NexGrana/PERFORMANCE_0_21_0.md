# Performance — NexGrana 0.21.0 QA

## Mudança arquitetural

A navegação usa cache cifrado depois que a sessão foi autenticada. Atualizações remotas ocorrem no loop de sincronização em segundo plano. Falhas aumentam a espera de 2 até 60 segundos, evitando polling agressivo. O build mostra o progresso do Flet no terminal e continua gravando o log.

## Metas de homologação no Android real

- feedback ao toque: até 100 ms;
- troca de aba com cache: p95 até 300 ms;
- conteúdo local utilizável na abertura: até 2 segundos;
- compositor do Nex sempre acima do teclado;
- nenhum gesto de navegação deve aguardar uma consulta Supabase.

Registre aparelho, versão Android, tamanho do dataset, abertura fria/quente e condição da rede. Teste online, latência de 200–500 ms, perda, timeout, modo avião e reconexão. Os números acima são metas e ainda não são medições comprovadas.
