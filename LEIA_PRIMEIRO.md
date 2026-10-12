# NexGrana + SIM Labs — entrega de recuperação

## Hotfix do bloqueio Windows — 11/10/2026

Este pacote corrige o run `4a786e1a` que terminou bloqueado: fixtures dos testes de parada agora funcionam com caminhos Windows; FastAPI/Uvicorn do gateway são preparados e verificados no venv Nex QA; mudanças em requirements incluídos invalidam corretamente o carimbo do ambiente. O pacote não contém executável ainda.

Se você já extraiu a recuperação anterior, extraia este ZIP **sobre a pasta pai existente** `C:\Users\lucas\Downloads\NEXGRANA_SIMLABS_RECUPERACAO (1)` e confirme substituir os arquivos da pasta `NexGrana_SIMLabs`. Não apague a pasta. O ZIP não carrega `.runtime`, senha local, `.env` ou banco de QA, então eles permanecem no computador.

Depois de substituir, use uma única vez `INICIAR.cmd build-windows` dentro de `NexGrana_SIMLabs`. O fluxo executa os gates corrigidos e tenta o EXE; não abra outra execução em paralelo.

1. Clique em **Extrair tudo**. Use uma pasta curta, por exemplo `C:\NexGrana_QA`. Não execute dentro do ZIP nem misture com V5/V6/V7.
2. Abra **INICIAR.cmd** e escolha **1 — Abrir central**. A primeira preparação usa internet e pode demorar; aguarde na mesma janela.
3. O iniciador valida a senha salva e abre a central já autenticada na porta e pasta corretas. Não precisa digitar a senha na tela. Se precisar consultá-la, escolha **7**.
4. Escolha **4 — Testar, gerar e registrar Windows**. O fluxo valida o login, acompanha uma execução, testa, tenta compilar Windows e registra o pacote completo em **Releases & QA** somente se o build passar.

**Esta entrega contém fonte e automação; não contém EXE ou APK já compilado.** Os testes e o navegador foram validados em Linux. Build Windows, ferramentas C++ e smoke do executável ainda exigem seu Windows. Python estável 3.11+ e Node/npm são necessários; Flutter pode ser preparado pela CLI Flet. A compilação Windows requer Visual Studio Build Tools com C++ e Windows SDK. Falhas são registradas, não ignoradas.

## Menu
- 1: abrir a central da pasta correta com validação de login.
- 2: diagnóstico, sem reinstalar nem alterar o banco.
- 3: testes, sem build.
- 4: testes + build Windows + registro local do pacote, sem instalação/publicação.
- 5: mesmo pipeline Windows completo; Android permanece separado.
- 6: preview offline do NexGrana com armazenamento isolado. Mostra a abertura; login financeiro precisa de staging configurado. Não é uma demonstração de finanças com dados fictícios.
- 7: consultar a credencial local desta instalação (uso de recuperação).
- 8: reparar acesso, encerrando apenas processos desta pasta e preservando a senha.

A aba **Gestão de hoje / Executar QA** está no menu lateral. Seu botão executa o pipeline local; a opção 4 do iniciador também realiza o registro final em Releases & QA. “Atualizar” apenas consulta o estado; não dispara um novo build.

## Dados e versões
Não apague as pastas antigas: elas podem conter seus dados. Este pacote inicia uma instalação QA independente e não migra automaticamente senhas/bancos de outra cópia. A senha antiga de V6 não é a senha desta nova instalação. Após o primeiro acesso, mantenha esta pasta como instalação única de trabalho.

Collector Inbox recebe pacotes de feedback. Releases & QA recebe artefatos para inspeção. Um ZIP enviado não é executado automaticamente: o pipeline usa exclusivamente a fonte revisada incluída neste pacote. O baseline SIM_Labs foi preservado para comparação; o iniciador usa SIM_Labs_QA.

## Se uma etapa bloquear
O relatório mostra a causa em `SIM_Labs_QA/data/qa_pipeline/runs/`. O diagnóstico fica em `SIM_Labs_QA/.runtime/doctor.json`. Não é necessário copiar comandos ou reinstalar tudo. Não envie `.env` ou PRIMEIRO_ACESSO.txt. Consulte o relatório antes de repetir.

Leia `QA_REPORT.md` e `BUILD_STATUS.md` para os limites reais. Relatórios antigos estão em `reports/historico` e não são aprovações desta entrega.
