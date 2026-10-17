# Execução no Windows — clone QA
Estes comandos não foram executados neste host. Substitua somente os caminhos após conferir os diretórios reais. Nunca extraia por cima da instalação ativa. Preserve .env, bancos, .runtime, feedbacks, missões, evidências e agendamentos; faça backup controlado com os scripts atuais antes de migrar.

1. Extraia em C:\NEX_QA_20261006. Compare reports\CHANGED_FILES.json e SOURCE_CHANGES.diff com a fonte ativa, incluindo personalizações do Observer/Bridge/Runner. Aplique apenas mudanças compatíveis ao clone. Abra CMD no clone NexGrana.

```bat
cd /d C:\NEX_QA_20261006\NexGrana
py -0p
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -r gateway\requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
npm ci
npm run test:sql
flutter doctor -v
adb devices
COMPILAR_QA.cmd both
```

Use o Python compatível confirmado no host; o histórico cita 3.14, mas aqui os testes foram em 3.12.14. Não troque silenciosamente a versão do ambiente ativo. Visual Studio build tools e Flutter/SDK Android precisam estar saudáveis. OCR desktop requer Tesseract; Android ainda não homologado.

2. Em Supabase STAGING descartável, backup e revisão SQL: confirmar migrations anteriores 0.24 e 0.25; aplicar em ordem 0.25.1 a 0.25.6, revisando primeiro `NexGrana\MIGRATION_0_25_6.sql`. Sem aplicação automática em produção. Testar duas contas, família, reset QA e retomada offline.

3. No clone SIM Labs configure somente credenciais QA locais conforme README existente. Revise DATABASE_URL e porta para não apontar ao operacional. Prepare o ambiente e faça migration incremental do clone:

```bat
cd /d C:\NEX_QA_20261006\SIM_Labs
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.venv\Scripts\python.exe -m pytest backend\tests -q
cd backend
..\.venv\Scripts\python.exe -m alembic upgrade head
cd ..
VALIDAR_NEXGRANA.cmd "C:\NEX_QA_20261006\NexGrana"
```

4. Inicie a API QA conforme README/START_SIM_LABS.bat, verificando a porta e credencial CEO. Depois de build realmente BUILT, selecione o relatório novo e registre:

```bat
.venv\Scripts\python.exe scripts\register_latest_build.py "C:\NEX_QA_20261006\NexGrana\dist\PASTA_REAL\build-report.json" --version 0.24.0-qa-20261006 --target windows --runner-report nexgrana-run-report.json
```

O script solicita token sem exibi-lo e usa por padrão http://127.0.0.1:8000/api/v1. Para API QA em outra porta use register_release.py --endpoint com o endereço loopback correto, arquivo explícito, --version e --platform. Não registrar build-report bloqueado desta entrega. Registro não abre o EXE. Confira SHA no painel, instale/abra somente no Windows QA; registre evidência e envie para REVIEW.

5. Após verificar que os scripts apontam exclusivamente ao clone, INSTALAR_NO_BOOT.bat permite cadastrar boot. Não o execute no operacional antes de comparar as tarefas já presentes. Reboot real, bateria/logoff, heartbeat e recuperação ficam a validar. Nada promove DONE, stable ou publicação automaticamente.

6. Android: compilar, instalar APK no aparelho QA autorizado, testar teclado/rotação/voltar/offline e tamanhos 360×800, 390×844 e 412×915. Windows 1366×768 e 1920×1080. Anexar evidências redigidas por ID; fechar somente após esperado=observado.

## Comando da rodada RC8
Depois de preparar os ambientes no clone QA, executar de dentro do SIM_Labs:

```bat
CONCLUIR_RODADA_QA.cmd "C:\NEX_QA_20261006\NexGrana"
```

Para também registrar os binários efetivamente gerados na API QA correta:

```bat
CONCLUIR_RODADA_QA.cmd "C:\NEX_QA_20261006\NexGrana" registrar "http://127.0.0.1:8000/api/v1"
```

Use a porta QA real. Não iniciar outra API sobre a instalação ativa. Registro exige credencial CEO, é candidata 0.24.0-qa-rc8 e nunca instala/abre/publica. Se tool/build/check falhar, o comando para; não importa um arquivo antigo. latest-successful-build.txt só é escrito quando todos os targets solicitados concluem. Android ainda requer instalação e testes no aparelho autorizado. Migrações não são aplicadas por esse comando.


## SIM Labs: fontes de ofertas
A venv da raiz usada por `CONCLUIR_RODADA_QA.cmd` executa backend e testes; `START_SIM_LABS.bat` provisiona `backend/.venv` na primeira inicialização. Em cópia QA, configure `.env` local e adicione apenas o nome da variável ao painel; configure o valor do token do parceiro no `.env` privado do clone. `.env.example` contém nomes vazios, sem token real. A chave jamais vai no formulário/pacote. A AWIN requer feed criado/permissão da conta; um URL plausível não comprova acesso. Mercado exige um ID de item/autorização.

Comece sem feeds; configure manualmente 1 rascunho HTTPS com preço/validade conferidos. Depois importe no máximo 500 ofertas/8MB e aprove cada item. Para testar coleta, registre uma fonte autorizada, autoaprovação desligada e intervalo ≥900s, ative o Engine e clique “Coletar agora”. A parada/pausa na tela não apaga dados. Sem credencial a execução registra EXTERNAL_BLOCKER.

Preview do catálogo pede senha da API SIM Labs. `PREPARAR_CATALOGO_OFERTAS.cmd` salva JSON privado e relatório local; nenhuma publicação ocorre nesse modo. Nunca salve o JSON fora do computador sem política própria: contém links comerciais. Publicação real só depois de backup, `MIGRATION_0_25_6.sql` revisada/aplicada em Supabase staging, admin Mafra em `app_admins` e teste em duas contas. A ponte pede URL + project-ref exato; recusa endpoints fora do localhost/Supabase confirmado e chave `service_role`. Use somente login de admin de Achados. Para manter polling explícito depois do piloto: `backend\.venv\Scripts\python.exe scripts\publish_offer_catalog.py --publish --supabase-url https://SEU_REF.supabase.co --allow-project-ref SEU_REF --watch --interval 900`. Não execute em produção. Limite de segurança: relatório/artefato local contém dados de catálogo, sem senha ou token persistido. Ctrl+C encerra a ponte.

O conector AWIN respeita máximo de 5 requisições/min e impede feed concorrente; o scheduler local espaça no mínimo 30 s. Resposta incompleta não altera nenhuma oferta. Checkout e desconto precisam ser confirmados na loja: preço reportado não é promessa nem recomendação financeira.
