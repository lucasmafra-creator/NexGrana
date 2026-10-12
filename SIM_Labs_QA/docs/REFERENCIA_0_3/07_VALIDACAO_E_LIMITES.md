# Validação 0.3.0

Data: 02/10/2026. Ambiente: Linux/Python 3.12, Node 24. Não foram usados Windows, dispositivo Android, banco Supabase remoto ou conta real do NexGrana.

| Verificação | Resultado |
|---|---|
| Backend | **41 testes aprovados**; suíte antiga preservada e novos contratos |
| Collector: núcleo local | **3 testes aprovados** |
| API + Collector por HTTP real | **Aprovado** em banco temporário TEST DATA |
| Migração 0002 → 0003 | **Aprovada**, preservando produto e feedback anteriores |
| Bootstrap | Migrations e seed **executados em Linux** |
| Frontend | TypeScript + Vite build **aprovados**; painel compilado incluído |
| Sintaxe Python | compileall **aprovado** para central/Collector |
| Backup | Contrato de DB + configuração + evidência no ZIP **testado** |
| Consultor IA local | Adaptador testado com **MOCK** e falha de transporte; nenhum modelo real executado |
| Prévia visual | **Bloqueada** por timeout da ferramenta; não há screenshot homologado |
| CMD/PowerShell/Tkinter Windows | **Não executados** neste ambiente |
| NexGrana Windows/Android: jornadas reais | **Não executadas**; inspeção de pacote não abre o app |
| Docker / PostgreSQL / hospedagem remota | **Não executados**; configuração/DDL são preparação |

Logs atuais: evidence/BACKEND_TESTS.txt, COLLECTOR_TESTS.txt, FRONTEND_BUILD.txt e HTTP_E2E.txt. Evidências antigas estão separadas em LEGADO_0_2.

A suíte teve dois warnings: depreciação de transporte no cliente de teste e criação intencional de entrada duplicada em ZIP para provar rejeição. A execução final não teve teste falho.

## O ciclo HTTP comprovou

Página compilada servida, login local privado, recusa de ator simulado na configuração normal, envio real do módulo do Collector com anexo, reenvio sem duplicação, triagem do worker, missão relacionada, upload e auditoria estática, download autenticado, consulta /resumo e recusa de aprovação sem homologação.

Todos os registros foram TEST DATA em banco temporário. Um teste positivo de gate usou fixtures para verificar transição de estado; não demonstra teste de EXE/APK real. Não foram incluídos dados de teste na base da entrega.

## Mudanças

- 12 tabelas novas e migração aditiva.
- Routers/serviços de integração, mantendo a fundação anterior.
- Login privado local; seletor de ator retirado; simulação só com flag explícita de teste.
- Worker com lease e fila persistida; inspeção, triagem e diário.
- Monitores antigos catalogados/desativados; comando livre retirado da central.
- IDs humanos com incremento atômico; idempotência por origem/ID e anexos por hash.
- Collector com transporte em thread, resultado real e preservação local em falha.
- Painel multiprojeto, organização por missões, canal, decisões e histórico.
- Evidência/cenário obrigatórios para encerrar missão e registrar regressão manual.
- Gate Windows+Android do NexGrana e release estável imutável para uploads.
- Adaptador IA local opcional, apenas texto, sem ferramentas.
- Inicialização, parada segura, backup e documentos/prompts.
- Código/banco financeiro do NexGrana não modificados.

## Limites conhecidos

- Gates ainda usam plataformas/cenários do NexGrana; precisam de parametrização para sites/APIs.
- Inspeção estática não avalia fluidez, pixels reais, regras financeiras ou segurança completa.
- Uploads/anexos usam memória com limites; streaming é evolução antes de exposição remota.
- Transação abortada pode deixar arquivo órfão privado; reconciliação é futura. Nenhuma exclusão automática de evidências foi ativada.
- Relatório diário mostra contadores acumulados no momento da primeira geração, não distribuição histórica por dia.
- Inspeção longa pode deixar heartbeat antigo até concluir; a etiqueta não prova morte do processo.
- Job interrompido aguarda expiração do lease para retomada e tem tentativas limitadas.
- Autorização herdada precisa de endurecimento por papel/projeto/ambiente antes de operação remota multiusuário.
- Login local é de Mafra. Nomes da equipe são papéis, sem passwords individuais reais criados.
- Identidade remota, notificações externas e rate limiting completo não estão ativos.
- Advisor local não tem memória conversacional longa; saída é proposta não verificada.
- Testes de fonte no QA desktop antigo do Collector continuam manuais e não são sandbox de SO.

## Próximo passo

Execute o roteiro do painel/docs/01 no Windows. Relate etapa, esperado, observado e evidência em caso de falha. Depois, priorize runner isolado e intake do NexGrana antes de animações avançadas e marketing.
