# NexGrana 0.24.0 — RC3 UX FIX (candidata de código)

Continue os testes a partir desta RC3; o ZIP inclui a fonte, migrations,
testes, auditoria visual de código e relatórios. Consulte primeiro
`AUDITORIA_VISUAL_RC.md` e `CHANGELOG_0_24_RC3_UX_FIX.md`.

**Não é APK/Windows final.** O vídeo `https://youtu.be/FWE3qUOfI-8` não pôde
ser reproduzido neste ambiente e não houve inspeção manual em dispositivo.
O gate de UX solicitado pelo proprietário está aberto. Migrações não foram
aplicadas ao Supabase FinanceHub e não houve atualização do GitHub nesta etapa.

Para validar no Windows dentro da pasta `project`:

```cmd
VALIDAR_0_24.cmd
VALIDAR_SQL_0_24.cmd
```

O segundo comando executa um Postgres local em memória. Antes de homologar,
instale/rode o app e percorra Mercado, Listas, Nex, Tutorial e Privacidade nas
resoluções do relatório, compare com o vídeo e registre screenshots. Só então
decida se deve compilar as plataformas e atualizar a release GitHub. Não
substitua esse teste visual pelos testes de árvore de controles.
