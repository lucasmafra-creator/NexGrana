# SIM Labs 0.4 — teste da operação persistente

Esta é uma candidata operacional. O prompt completo de uma empresa que corrige código e estética autonomamente **ainda não está integralmente atendido**. Nesta entrega há processos reais, fila persistente, recuperação, auditorias de arquivos/registros e evidências. Os workers de setor não são agentes que implementam patches: geram relatórios e recomendações explicitamente identificados.

## Começar no Windows

Requer Python 3.11+ no PATH e internet na primeira instalação das dependências. O site já está compilado: não precisa instalar Node.

1. Extraia a pasta inteira para um local permanente, por exemplo `C:\SIMLabs\SIM_Labs_0_4_0_24_7`.
2. Se quiser preservar sua 0.3, siga **Migração** abaixo ANTES de iniciar a nova pasta.
3. Abra o CMD nesta pasta e execute:

```cmd
INICIAR_24_7.bat
```

A janela informa a senha e abre `http://127.0.0.1:8000`. Ela também fica em `.runtime\PRIMEIRO_ACESSO.txt`, privado. Não compartilhe esse arquivo. Fechar o navegador não para a operação.

4. Faça login, abra **Operação 24/7**, confira o heartbeat e clique em **Rodar agora** no worker QA. Aguarde o resultado e baixe sua evidência.
5. Para iniciar automaticamente no login do Windows, execute:

```cmd
INSTALAR_24_7.bat
```

É uma tarefa do Agendador, vinculada a esta pasta e usuário. O wrapper permanece monitorando o supervisor; a tarefa tenta reiniciar após falha. Não é um serviço antes do login. Computador desligado ou suspenso não executa trabalhos. Essa instalação precisa ser validada no seu Windows.

## Migração da 0.3, mantendo a senha e o histórico

1. Na pasta antiga, execute `BACKUP_SIM_LABS.bat` e depois `PARAR_SIM_LABS.bat`. Mantenha a pasta e o backup antigos.
2. Na pasta **nova, ainda não inicializada**, execute:

```cmd
MIGRAR_0_3.bat "C:\caminho\SIM_Labs_Integrado_0_3_0"
INICIAR_24_7.bat
```

O copiador usa snapshot SQLite, copia dados/evidências/configuração e ajusta caminhos internos dos arquivos. A origem fica preservada. O primeiro início cria outro backup e aplica somente seis tabelas operacionais novas. Não acessa o banco financeiro do NexGrana. Banco personalizado ou evidência fora da pasta de origem bloqueiam a cópia para revisão. Se falhar durante a cópia, preserve a pasta parcial e extraia uma nova para tentar novamente; não execute sobre ela sem revisar.

Para voltar à 0.3: pare a nova versão e inicie a pasta antiga preservada. Não aponte a 0.3 para o banco já migrado da 0.4. Desinstale a tarefa nova se for voltar de forma permanente.

## Enviar sua última atualização

Em **Releases & QA**, registre a versão e envie ZIP da fonte/build, EXE instalável ou APK. ZIPs recebem inspeção estrutural e revisão adicional dos assets Nex. No **Collector Inbox**, importe feedbacks com capturas; ou use `ABRIR_COLLECTOR.bat` e **Enviar para a Central**. No **Canal com Mafra**, `/resumo` traz registros reais e **Criar missão** encaminha seu pedido.

Não há pasta monitorada de atualizações nem leitura automática de repositórios externos. A atualização entra pelos fluxos acima. Fonte recebida não é executada automaticamente.

## O que funciona automaticamente

- Supervisor mantém API, operações legadas e engine em processos distintos; reinícios com backoff e limite de cinco falhas consecutivas. Só controla seus próprios filhos.
- Scheduler persistente: hora, 6h, dia, semana e ciclo de 30 dias. O mensal é intervalo fixo, não mês de calendário. Horários configuráveis no painel; pausa impede novas escalas e claims, deixando trabalhos em execução terminar.
- Fila com deduplicação, claims transacionais, duas execuções isoladas simultâneas, timeout de 90s, até três tentativas e recuperação de leases.
- Workers pausáveis de QA, segurança, UX, produto, engenharia, marketing, performance, red team e release. Permissão operacional: auditorias locais e geração de relatório, sem shell arbitrário, deploy ou alterações financeiras.
- Upload de ZIP com assets gera inventário, hashes, decodificação, resolução, alpha e orientação de retrabalho. A estética/identidade ficam **BLOCKED** sem avaliação visual.
- Segurança confere integridade das últimas 200 evidências do projeto; desvios criam P0, missão, incidente e decisão. Downloads, registros de homologação/encerramento e aprovação verificam hashes.
- Evidências privadas e auditadas; Daily com contadores da janela do dia em São Paulo. Cenários de regressão manuais permanecem separados de testes automatizados.
- Aprendizado DIO/TryHackMe pode ser registrado no painel, com conceito e aplicação. Isso não comprova conclusão de curso ou execução de laboratório.

## Melhoria de asset para avaliar

Abra `asset_candidates\Nex_Natal_original.png`, `Nex_referencia.png` e `Nex_Natal_candidata_v2.png`. A candidata foi gerada nesta conversa; não pelo engine local. Tem alpha real e identidade visual mais próxima da referência inspecionada, mas aguarda sua avaliação no app. Nenhum arquivo do NexGrana foi substituído. Há prompt e critérios em `asset_candidates\LEIA_ME.md`.

## Executável opcional

```cmd
GERAR_EXECUTAVEL_WINDOWS.bat
```

Execute depois do primeiro início. Instala PyInstaller e gera `SIM_Labs.exe` no Windows. É um **iniciador** da pasta completa, não um aplicativo portátil independente e não `simlabs_worker.exe`. Não há EXE compilado/assinado/validado nesta entrega, pois os testes foram feitos em Linux. O BAT é o caminho disponível para testar agora.

## Controle e diagnóstico

| Comando | Uso |
|---|---|
| `STATUS_24_7.bat` | API, status de processos, idade do status e tarefa instalada |
| `PARAR_24_7.bat` | Parar processos desta pasta; não apagar dados |
| `INICIAR_24_7.bat` | Retomar; filas e configurações persistem |
| `TESTAR_SIM_LABS.bat` | Suíte em banco TEST separado |
| `BACKUP_SIM_LABS.bat` | Backup local, incluindo segredos; guardar privado |
| `DESINSTALAR_24_7.bat` | Remover somente a tarefa registrada desta pasta |

Se parar manualmente, não iniciar a tarefa do Agendador até querer retomar. Os logs ficam em `.runtime`. Se o limite de reinícios for atingido, corrigir a causa e reiniciar a central; não resetar o banco. A tarefa do Windows tem três tentativas adicionais de recuperação do wrapper, também limitadas.

O heartbeat é diferente da configuração habilitada. Sem heartbeat recente, a operação não está comprovadamente ativa. Processos interrompidos podem precisar de até cerca de 4 minutos para expirar a lease da auditoria legada; jobs do engine recuperam após cerca de 2 minutos.

## Limites que continuam BLOCKED

Correção automática de código; avaliação visual automática; geração local automática de todas as skins; testes reais no NexGrana Windows/Android; medição de performance; execução de RLS/duas contas; serviço antes do login; acesso remoto; aprovação/publicação de produção; validação Windows desta versão; teste prolongado de 24h; navegação visual desta interface. Nenhuma publicação, chave de API ou cobrança é ativada.

Veja `SIM_LABS_0_4_0_REPORT.md` para evidências e o checklist manual. Documentos de versões antigas foram mantidos para referência e não prevalecem sobre este guia.
