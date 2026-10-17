# Nex amplo — fronteira preparada, integração não ativada

O Nex da candidata 0.21 continua local e determinístico. Ele consulta somente o
perfil selecionado, usa o motor financeiro para números e mantém funções básicas
disponíveis sem internet. Não há chave nem SDK de provedor de IA no APK/EXE.

Uma conversa ampla futura deve passar por um gateway HTTPS controlado pelo
NexGrana. `services/nex_gateway.py` já valida o destino e prepara um payload
reduzido. Contexto financeiro só é incluído após consentimento específico e por
lista explícita de campos; identificadores, lançamentos e credenciais são
excluídos. O backend ainda precisará autenticar o JWT do usuário, aplicar limite
por conta, registrar apenas métricas sem conteúdo financeiro, moderar abuso e
guardar a chave do provedor em cofre de servidor.

Nenhum provedor foi escolhido nesta candidata. Portanto, não existe custo por
conversa, limite comercial ou suporte multilíngue externo ativo para declarar.
Essa decisão deve ser feita após medir qualidade em português, latência, política
de retenção e custo nas páginas oficiais do provedor escolhido.
