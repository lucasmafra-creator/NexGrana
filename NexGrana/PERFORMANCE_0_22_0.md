# Performance — NexGrana 0.22.0 QA

## Preservado/implementado

- cache cifrado renderizado antes do refresh remoto;
- sincronização em segundo plano com backoff;
- host de UI reutilizado entre telas;
- chat atualiza apenas lista/composer durante resposta;
- ativos do Nex recortados por função e sem troca contínua de imagem;
- painel e filtros de Achados locais após o carregamento;
- gateway executado em thread fora da UI, com timeout máximo de 45 segundos.

## Medição pendente em aparelho

Metas de produto, ainda não declaradas como resultado: feedback de toque até 100 ms e troca com cache até 300 ms. Medir p50/p95 em Android de referência, Windows, rede boa/mediana/offline, histórico cheio e teclado aberto. Separar latência local, gateway e provedor. Registrar memória, frame drop e consumo das animações.
