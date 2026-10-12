# Entrega integrada RC8 — NexGrana + SIM Labs

Abra primeiro `ANALISE_ENTREGA_RC8.md` para o estado analítico e `PASSO_A_PASSO_CMD.md` para a execução Windows/staging. O SIM Labs inclui o painel **Ofertas & links**, coleta agendada de fontes autorizadas, fila/relatórios e ponte separada do catálogo NexGrana. Migrações novas exigem clone+backup+revisão staging.

Linux CI local: NexGrana 207 testes; backend SIM 88; Collector 3; SQL PGlite 117; Vite build PASS. HTTP: API, Collector, frontend e Engine reais em banco temporário; coleta sem credenciais produz EXTERNAL_BLOCKER; ponte confirmou apenas preview. Watchdog Linux recuperou filho isolado. Veja `reports/http_final.log` e `reports/watchdog_final.log`.

**Ainda não compilado/homologado:** EXE/APK, Windows ativo, Android físico, SIM ativo, Supabase staging/produção e feed de parceiro autorizado. Não publique nem inicie a fase de lançamento. O próximo passo técnico é clone Windows + staging + Moto G22. iOS é só plano de compatibilidade após esse gate; Nex Online segue congelado.

`PROMPT_REUNIAO_VOZ.md` contém o contexto/prompt para abrir a nova conversa “Reunião” por voz. Hashes e diff em `MANIFEST_SHA256.json`, `CHANGED_FILES.json` e `SOURCE_CHANGES.diff`.
