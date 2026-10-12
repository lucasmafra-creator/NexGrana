# NexGrana 0.24.0 QA RC2 — código para testes

Esta candidata implementa mudanças sobre a RC1 auditada. **Não contém APK,
EXE ou IA online implantada.** Não aplique migrations diretamente em produção.

## No Windows, depois de extrair o ZIP

Abra o CMD na pasta `project` (onde existem `requirements.txt` e
`VALIDAR_0_24.cmd`); digite somente os comandos abaixo, sem copiar
`C:\Users\...>` do prompt:

```cmd
VALIDAR_0_24.cmd
VALIDAR_SQL_0_24.cmd
```

O segundo comando precisa de Node.js e instala as dependências do teste SQL
na primeira execução. Executa as migrations em um Postgres de teste em memória,
sem alterar FinanceHub. Se algum comando falhar, não construa o app ainda.

Antes de reconstruir, obtenha backup do ambiente de QA e aplique na ordem
`MIGRATION_0_24.sql`, `MIGRATION_0_24_1.sql`, `MIGRATION_0_24_2.sql` somente
se ainda não aplicadas. Teste RLS com duas contas, reset com workspace marcado
e persistência em sessão nova. Espaço QA anterior à 0.24.1 requer aprovação e
registro em `qa_workspace_registry` pelo administrador após conferir a ID;
não marque automaticamente um espaço usado como sandbox.

Para gerar builds no seu Windows, após a validação e Flutter disponível em
`%USERPROFILE%\flutter\3.44.8`:

```cmd
COMPILAR_0_24_WINDOWS.cmd
COMPILAR_0_24_ANDROID.cmd
```

Os scripts mostram caminho dos logs e artefatos em `project\dist`. Confira
hash do APK e teste instalação, login e reabertura. Leia
`README_NEX_ONLINE_0_24_RC2.md` antes de anunciar Nex online: sem gateway
HTTPS hospedado e URL pública embutida no build Android, o chat geral é local.

## O que foi implementado na RC2

- Reset QA protegido por registro específico e teste SQL de recusa/replay;
- confirmação de escrita na sincronização e recarga de listas;
- isolamento de escrita de renda/despesa por autor;
- três visuais por conta e espaço armazenados no cofre local;
- cliente Nex evita replay de POST, guia de configuração e Dockerfile do gateway;
- validador Windows usa a mesma suíte completa do empacotamento.

## Bloqueadores para publicação

- Migrações e RLS não confirmadas em Supabase real;
- leitura de linhas financeiras segue acessível a outros integrantes da mesma
  família via API; requer redefinir contrato do consolidado e restringir RLS;
- gateway e ferramentas financeiras de IA server-side não implantados;
- custo/rate limit de IA ainda em memória do processo;
- Windows, APK e UX em Android real ainda não testados nesta candidata.

Os itens de SIM Labs permanecem em documentos de planejamento; esta candidata
não afirma ter implementado o Control Center. iOS continua na fase seguinte.
