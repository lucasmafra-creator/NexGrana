# SIM Labs QA 0.4.1-qa.2 · V7 one-click stability

Esta pasta é um **clone de validação** criado a partir do RC8. `SIM_Labs/` ao lado é o snapshot estável original do pacote, preservado sem as alterações desta rodada. O snapshot não foi comparado com a instalação ativa do Windows.

## O que foi corrigido neste hotfix

- O reparador mantém o serviço QA acompanhado em uma janela PowerShell própria e espera a API responder com a identidade desta pasta antes de abrir a central. Deixe essa janela aberta enquanto usar o SIM Labs.
- A inicialização tem mais tempo para concluir dependências e migrações e mostra progresso; portas de outros serviços continuam preservadas.
- Se uma execução QA encerrar sem relatório, a central marca a execução como `BLOCKED` e limpa somente o lock daquela execução. A página não deixa um `RUNNING` antigo aparentar estar ativo.
- Se a resposta se perder durante a execução, o botão fica protegido contra disparo duplicado e a tela tenta reconectar sozinha.
- O executor grava o primeiro marcador do log antes de iniciar, roda Python sem buffer e informa as etapas para que uma falha não produza um log vazio.
- Adicionados testes de regressão para conexão, confirmação perdida, execução encerrada e limpeza de lock.
- O manifesto e o preflight ignoram os arquivos temporários WAL/SHM do SQLite e validam os mesmos arquivos da raiz do pacote, evitando falha por dados locais em uso.
- A entrada CMD da raiz agora executa reparo, health, interface e login local; depois dispara ou acompanha o pipeline autenticado sem mostrar a senha.
- Se a central já tiver um pipeline ativo, a automação acompanha o mesmo `run_id`. Se a resposta do início se perder, ela consulta o estado e não reenvia o POST às cegas.
- O pipeline aceita o Python estável `>=3.11` declarado no `pyproject.toml`, instala dependências apenas nos ambientes do clone QA e tenta Windows antes de Android.
- Windows e Android aparecem com estados separados; iOS permanece para a fase posterior.

## Atualização preservando sua senha local

O ZIP contém uma pasta de pacote `NexGrana_SIM_Labs_QA_RC8_QA_2026-10-07_STARTUP_FIXED_V5`. Extraia-o para a pasta imediatamente acima do pacote ativo (no seu caminho atual, a pasta `...STABILITY_HOTFIX_V6`), para mesclar/substituir o `...STARTUP_FIXED_V5` existente; não selecione a própria subpasta `...STARTUP_FIXED_V5` como destino, pois isso criaria um nível duplicado. Confirme a substituição dos arquivos. Mantenha `.runtime`, `.env`, o banco e `SIM_Labs_QA/data`: eles preservam a credencial local, o SQLite e as evidências da cópia QA. Depois, abra **uma vez** `REPARAR_E_INICIAR_SIM_LABS_QA.cmd` na raiz `...STABILITY_HOTFIX_V6\...STARTUP_FIXED_V5`. Não execute scripts de dentro de `SIM_Labs_QA`.

## O que mudou

- A API recusa iniciar se detectar modo de produção, chave Supabase privilegiada ou endpoint que não corresponda a um projeto separado com referência `qa-*` ou `staging-*`.
- A central recebeu **Gestão de hoje**, um painel de decisão com dados registrados e mapa 2.5D clicável por setor.
- O mapa mostra tarefas verdadeiras do NexGrana e limitações operacionais. Red Team e Chaos Test aparecem separados e sem execução ofensiva/injeção de falhas.
- O SIM Labs tem endpoint CEO-only para iniciar/consultar o pipeline fixo deste clone. A preparação de dependências fica em `.venv`/`node_modules` do clone; os binários são produzidos somente se todos os testes locais passarem e o host Windows possuir SDKs.
- A tela e o pipeline não instalam, abrem, publicam ou promovem EXE/APK. Isso continua exigindo QA manual.

## Uso

O mesmo comando de um clique valida a instância, abre a central local e inicia/acompanha o pipeline QA. O pipeline autentica localmente usando a credencial salva. Se o navegador pedir login interativo para abrir o painel, use a mesma senha persistida no `.runtime\PRIMEIRO_ACESSO.txt`; o launcher não a imprime nem troca. Mantenha abertas as janelas do inicializador e do serviço enquanto ele trabalha. A primeira preparação pode precisar de internet. A central também mostra **Gestão de hoje**. O pipeline pode levar algum tempo, exibe seu andamento, grava log/relatório e termina com código de saída apropriado. Se a execução já estiver ativa, acompanha aquela execução sem criar outra.

Para iniciar o pipeline diretamente, use somente se estiver fazendo diagnóstico manual:

```cmd
py SIM_Labs_QA\scripts\run_release_pipeline.py --package-root . --prepare-deps
```

Antes, regenere os hashes após alterações:

```cmd
py SIM_Labs_QA\scripts\generate_release_manifest.py --package-root .
```

Não configure este clone com banco, URL ou credenciais do ambiente oficial. Para acesso remoto de QA, crie primeiro projeto Supabase separado com nome de referência `qa-*` ou `staging-*`, banco/dados fictícios e somente chaves limitadas. Ainda não existe staging conectado nesta entrega.

## Provas e limites

- O ZIP contém fontes e scripts, sem EXE NexGrana ou APK.
- Este host Linux não tem `pytest`, `tsc`, PGlite, Flutter ou ADB. A suíte completa e builds nativos ficam bloqueados por dependências/host.
- Nenhum Windows real, Moto G22, Supabase staging ou feed afiliado autorizado foi validado nesta sessão.
- SIM Labs continua operando localmente; não trabalha se o computador estiver desligado e não é um serviço hospedado 24/7.
- Esta rodada executa testes unitários da automação por HTTP local simulado, testes do manifesto, verificações de sintaxe e teste de estado da UI neste host Linux. O launcher Windows/PowerShell ainda precisa de uma execução real na máquina Windows.
- O one-click inicia testes/builds somente dentro do clone QA; nenhum binário é instalado/publicado e nenhum segredo sai do computador.
- iOS fica para a fase posterior. Nex Online continua adiado por decisão do Mafra.
