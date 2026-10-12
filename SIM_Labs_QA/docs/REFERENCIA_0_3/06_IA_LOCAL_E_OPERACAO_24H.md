# IA opcional e operação contínua

## Canal atual

O canal funciona com regras sem depender de modelo: mensagem registrada, `/resumo` consulta registros e “Criar missão” gera tarefa. Não há despesa de API de IA na configuração padrão.

## Consultor local opcional

Foi implementado um adaptador para Ollama local, em `backend/app/ai_advisor.py`. Ele usa a API local de chat e respostas sem streaming. Referência oficial: [Ollama — API](https://docs.ollama.com/api) e [contrato de chat](https://github.com/ollama/ollama/blob/main/docs/api.md).

Ollama/modelos não estão incluídos no ZIP e nenhum modelo foi baixado ou executado nesta sessão. O adaptador foi testado com respostas MOCK e falha de transporte; isso não homologa qualidade/desempenho de um modelo.

Se você já tiver Ollama e um modelo disponível no mesmo computador, pode ativar a consulta textual:

1. Pare o SIM Labs.
2. Faça backup da configuração local.
3. Edite **somente** estas linhas no `.env` da central, usando o nome real de um modelo que seu serviço já possui:

```dotenv
SIM_AI_PROVIDER=ollama
SIM_AI_MODEL=NOME_REAL_DO_MODELO_INSTALADO
SIM_AI_URL=http://127.0.0.1:11434
```

4. Reinicie a central.
5. No canal, envie uma mensagem de consulta, por exemplo: “Como organizar o teste de fluidez do chat Android?”.

Esperado: se o modelo responder, aparece **AGENTE IA · LOCAL** e “proposta não verificada”. Se estiver indisponível, a mensagem é preservada e a automação explica o bloqueio. `/resumo` continua consultando dados reais sem chamar o modelo.

O adaptador só aceita URL HTTP de loopback. Não segue redirects, não repassa segredo ou anexo, não fornece ferramentas, não executa comando e não aprova release. O contexto enviado é um conjunto pequeno de contadores operacionais do projeto selecionado mais sua própria mensagem. Não envia a base financeira nem o chat do NexGrana.

Resposta pode levar até 45 segundos; modelo local depende do hardware. Nenhum modelo específico foi escolhido por presumir capacidade do seu notebook. Para desligar, use `SIM_AI_PROVIDER=none` e reinicie.

A configuração padrão fica desligada para preservar seu teste inicial e o limite de custos já definido para os projetos. Provedor pago futuro precisa de integração própria, orçamento e decisão explícita.

## O que significa 24/7 nesta entrega

A API e o worker são processos locais supervisionados. Fechar a aba não os encerra. Desligar/suspender o PC, encerrar a sessão ou parar os processos interrompe a operação. Jobs persistidos são retomados após inicialização; leases e tentativas tratam interrupções da fila.

A rotina diária usa data de America/Sao_Paulo. Os contadores do relatório são acumulados até a geração, não foram vendidos como total de tarefas realizadas naquele dia. Agregação histórica mais precisa é uma evolução futura.

## Para funcionar com seu PC desligado

É necessário hospedar API/worker/banco/arquivos em infraestrutura disponível continuamente. Uma página estática sozinha não roda os testes, não mantém worker Python e não instala APK.

Ordem:

1. Homologar a entrega local no Windows.
2. Fixar autenticação de produção e autorização por projeto/papel/ambiente.
3. Definir servidor e armazenamento privado, domínio/HTTPS e backup.
4. Criar banco operacional separado e testar migração/restauração.
5. Publicar API e worker com observabilidade e segredos próprios.
6. Configurar frontend para a URL HTTPS do servidor; não usar localhost do visitante.
7. Provisionar runners autorizados para Windows/Android, com isolamento e capacidade.
8. Configurar notificação externa somente no canal escolhido por Mafra.

Nenhum serviço remoto foi criado, nenhum plano pago contratado e nenhum webhook externo ativado nesta entrega.

## Docker local opcional

Dockerfile/compose foram atualizados para a central compilada e SQLite em volume, com porta exposta apenas em 127.0.0.1. São preparação para evolução; não foram construídos/executados nesta sessão.

A opção de Docker usa seu próprio `docker-data`; ela não compartilha automaticamente o SQLite da instalação Windows. Não alternar instalações supondo que apontam para a mesma base. Para hoje, use os iniciadores Windows.
