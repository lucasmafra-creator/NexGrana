# Mafra — instalação e teste de hoje

Tempo sugerido: 10–15 minutos depois da primeira instalação, que depende da internet e do Python disponível.

## Preparação

Extraia o ZIP em uma pasta nova, por exemplo Downloads. Não substitua seu NexGrana nem seu Collector antigo. Deixe o pacote antigo intacto durante o primeiro teste.

Se a central 0.2 estiver aberta na porta 8000, pare-a pelo iniciador da versão antiga antes de iniciar a 0.3. O novo iniciador não mata processos arbitrários nem toma a porta de outro serviço.

Tenha Python 3.11+ no PATH ou o comando `py`. O pacote foi testado em Linux/Python 3.12; o CMD, PowerShell e as janelas Tkinter no Windows precisam do seu teste real. A instalação inicial baixa dependências com versões fixadas. O painel já está compilado: não precisa de Node/React na sua máquina.

## Abrir

1. Execute `INICIAR_SIM_LABS.bat`.
2. Aguarde concluir instalação, migração e seed. Se ocorrer erro, a janela permanece para leitura.
3. Guarde a senha local mostrada. Ela também fica em `.runtime/PRIMEIRO_ACESSO.txt` no seu computador.
4. Entre em `http://127.0.0.1:8000`.
5. Abra `ABRIR_COLLECTOR.bat`.

A conexão do Collector com a central é gerada pelo iniciador. Não há token fixo embutido no ZIP. Use a senha somente na central local. Credenciais de usuário/equipe em servidor são outra configuração.

## Teste 1 — canal

Em **Canal com Mafra**, envie `/resumo` como mensagem/consulta.

Esperado: sua mensagem aparece como HUMANO; o resumo aparece como AUTOMAÇÃO, com números da base atual. Não deve aparecer “Niel fez um teste” sem execução registrada.

Envie depois um pedido usando **Criar missão**.

Esperado: uma missão real aparece na aba Missões. A resposta deve dizer que foi registrada, não que foi executada.

## Teste 2 — Collector conectado

No Collector, crie e SALVE um feedback de teste explicitamente identificado como **TEST DATA**, com título, descrição, plataforma e uma captura de teste sem dados reais.

Clique **Enviar para a Central**.

Esperado: aviso de envio concluído; item na Inbox com ID original e anexo. Após a rodada do worker, uma missão é aberta no setor correspondente.

A conexão não fica consultando o Work e não envia para pessoas externas. É transporte direto entre seu Collector e sua central.

## Teste 3 — reenvio

Envie novamente o mesmo conjunto.

Esperado: aviso de reenvio reconhecido; o mesmo item e a mesma tarefa continuam; o anexo não duplica.

Modifique a descrição, salve e envie novamente.

Esperado: item atualizado, ID preservado e tarefa mantida. O histórico registra a importação/atualização.

## Teste 4 — pacote em partes

Na Inbox do painel, importe cada ZIP do seu pacote de feedback, um por vez.

Esperado: partes complementam anexos e preservam IDs. Uma parte que contém o manifesto e referências mas não os arquivos pode registrar os itens primeiro; o anexo aparece quando sua parte chega. Se um caminho nunca vier no pacote, não inventar o arquivo.

Limites: até 450 MB por envio; 1 GB expandido por ZIP; até 200 MB por entrada; até 1000 feedbacks por pacote. O envio direto do Collector omite anexos acima dos limites e mostra a lista. Envie esses anexos em partes menores; vídeos grandes podem ser divididos pelo fluxo de exportação já existente.

## Teste 5 — versão e fonte

Crie uma candidata em **Releases & QA** com o rótulo que realmente está testando. Envie um ZIP de fonte em **Fonte**, ou o EXE/APK correspondente na plataforma correta.

Esperado: arquivo na fila, hash disponível e relatório após processamento. Um ZIP de fonte não é um EXE nem um APK homologado.

A versão detectada pode ser `0.24.0` e o rótulo ser `RC6`: isso é exibido para conferência, sem alterar a versão dentro do pacote.

## Teste 6 — auditoria

Expanda o resultado do artefato.

Confira: integridade, caminhos, hashes, sintaxe Python, metadados de imagens e itens BLOCKED. Havendo uma estável comparável da mesma plataforma, verá adicionados/removidos/alterados e foco recomendado de reteste.

Esperado: “sem estável comparável” na primeira rodada. Não presumir regressão inexistente nem equivalência funcional pela comparação de arquivos.

## Teste 7 — evidência e checklist

Abra o NexGrana no dispositivo real de teste. Teste especialmente Android/chat: teclado aberto → enviar → histórico → conversa fixada → voltar → nova mensagem. Grave/capture o comportamento real.

Na aba Evidências, escolha a candidata e envie a captura ou relatório. Em Releases, registre o cenário correspondente, plataforma, nota e resultado.

Esperado: PASS sem evidência é recusado; evidência de outra release é recusada. FAIL/BLOCKED ficam explícitos.

Não use registros TEST DATA para declarar uma release real homologada.

## Teste 8 — decisão do CEO

Solicite uma decisão para a candidata. Na Mesa do CEO, tente aprovar antes de concluir os gates.

Esperado: bloqueio por builds/checklists/pendências. Você pode solicitar alterações ou adiar, com motivo.

O gate atual exige builds instaláveis Windows e Android, checklists de ambas as plataformas com evidência e ausência de tarefas P0/P1 abertas no projeto. O gate é conservador; para produtos de outra plataforma, a parametrização dos gates é a próxima evolução descrita no prompt. Não aprove um site usando o gate do NexGrana por engano.

## Teste 9 — fechar missão / progresso

Para uma missão que você comprovou, escolha **Encerrar com evidência**, informe arquivo, passos de reteste e esperado.

Esperado: missão encerrada, +10 XP uma única vez e cenário em Histórico & regressão. Cenário manual registrado não é um teste de código automatizado.

## Teste 10 — persistência e backup

Feche somente a aba do navegador e abra o endereço novamente. Confira mensagens, itens e arquivos. Faça `BACKUP_SIM_LABS.bat`.

Esperado: dados preservados e backup completo em `backups`. Use `PARAR_SIM_LABS.bat` para parar os processos. Reinicie e confira novamente.

## Trazer dados do seu Collector antigo

1. Feche o Collector antigo e o novo.
2. Faça uma cópia da pasta de dados antiga, incluindo `collector.json`, `settings.json`, rascunhos e evidências.
3. Cole a cópia em `Collector/data` da versão nova **antes de criar itens novos nessa pasta**. Se já houver itens novos, preserve as duas cópias e faça conciliação por exportação/importação; não sobrescreva silenciosamente.
4. Se a versão antiga for EXE, os dados podem estar em `%LOCALAPPDATA%\NexGranaUpdateCollector`. O caminho efetivo deve ser confirmado no seu computador.
5. Anexos antigos podem referenciar caminhos absolutos: preserve esses arquivos para que sejam enviados.
6. Alternativamente, importe na central os ZIPs exportados do Collector antigo; isso evita mexer no armazenamento antigo.

## Quando der erro

| Sintoma | Próximo passo |
|---|---|
| Python não encontrado | Confira `py -3 --version` ou `python --version`; use Python 3.11+ disponível no PATH |
| Erro no pip | Registre a mensagem completa; verifique internet e versão do Python; não apague seus dados |
| Porta 8000 ocupada | Pare a central antiga ou o serviço identificado; o iniciador não encerra serviço desconhecido |
| Senha não aparece | Abra `.runtime/PRIMEIRO_ACESSO.txt`; não mande sua senha no chat |
| Collector não conecta | Confirme a central aberta e que usou o Collector incluído neste pacote; reenvie após iniciar |
| Worker offline | Confira `.runtime/worker.err.log` e `worker.log`; reinicie pelo iniciador após parada |
| Arquivo sem evidência | Confira se o anexo existe e se a parte que o contém foi importada |
| Aprovação bloqueada | Leia os gates; isso é o comportamento esperado quando falta homologação |

Para pedir ajuda, envie o erro e a descrição do passo, ocultando qualquer credencial. Não mande `.env` nem o arquivo de primeiro acesso.
