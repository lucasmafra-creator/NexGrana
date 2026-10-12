# Evidências e limites

## Execução registrada em 09/10/2026
Pipeline: 8 grupos PASS, 0 falhos/bloqueados entre testes. O resultado global é BLOCKED porque este host é Linux.
- NexGrana Python: 210 testes OK.
- SIM Labs backend: 99 testes PASS.
- Collector: 3 testes PASS.
- Scripts: 16 testes OK na execução do pipeline.
- Guard QA, SQL/PGlite, estado da interface e compilação frontend: PASS.
- Navegador Chromium: login real, menu Gestão de hoje, botão Executar QA, dados autenticados do iframe e upload Collector visível: PASS; nenhum erro JavaScript.
- NexGrana: screenshot da abertura real em web local, armazenamento isolado, sem login em produção. Flet precisou de renderizador local (FLET_WEB_NO_CDN) e locale pt-BR no navegador de teste. Isso não equivale a smoke do EXE.

## Revisão final em 10/10/2026
Incluídos doctor e registro condicionado do build no fluxo do iniciador. A evidência complementar dos scripts finais fica em reports/final-script-tests.txt. O pipeline anterior permanece datado, sem alteração retroativa do seu resultado. Não houve mudanças no código financeiro após aquela execução.

## Não validado
PowerShell/CMD executados em Windows; compilação Windows; executável instalado; Android em dispositivo; chat/teclado Android; Supabase staging e isolamento ponta a ponta com contas reais; inspeção subjetiva de todas as skins; registro real de binário compilado. Sem essas evidências, não declarar GREEN.

## Artefatos
Screenshots em reports/simlabs-*.png e reports/nexgrana-web-abertura.png. Relatórios herdados estão separados em reports/historico e não provam o estado desta entrega. Nenhuma imagem de referência ausente foi recriada ou presumida como analisada.


## Regressão de senha da interface — 11/10/2026
A correção valida health/service/phase/instance_id antes de enviar a senha e abre a interface com a sessão concedida pelo login local. O token viaja apenas no fragmento da URL, que não é enviado ao servidor; o frontend o guarda na aba e apaga o fragmento do endereço. Testes automatizados cobrem instância errada, login rejeitado e sessão concedida. Testes unitários específicos: 3 PASS.

## Diagnóstico do run Windows 4a786e1a — 11/10/2026

Resultado informado pelo usuário: **BLOCKED**, 6 dos 8 grupos passaram, 0 builds e 0 releases.
- `manifest_consistency`: dois testes de parada falhavam porque a fixture montava o caminho do executável com `/` literal em vez de usar o separador nativo do Windows. Ajustada para compor o caminho com `Path`.
- `nex_python`: dois erros de importação em `gateway.app`, pois o venv NexGrana não instalava as dependências de `gateway/requirements.txt`; o detector também não verificava FastAPI/Uvicorn. A inclusão recursiva e a verificação de módulos foram corrigidas.
- O hash do venv agora cobre os arquivos de requirements incluídos; alteração no arquivo do gateway força nova preparação, mesmo que a biblioteca já esteja parcialmente instalada.
- A suíte de scripts que importa o bootstrap local agora usa o Python do venv QA do backend, cujas dependências são verificadas antes da execução.

## Verificação do hotfix — 11/10/2026

- Sintaxe Python dos arquivos alterados: PASS.
- 24 testes direcionados de sessão, manifesto, pipeline único, registro, gates, dependências e parada de processos: PASS.
- O teste de bootstrap de credenciais não foi executado no host Linux desta revisão porque ele não possui as dependências `python-dotenv` e FastAPI; o pipeline corrigido o executa com o venv QA preparado.
- O run Windows bloqueado continua registrado como histórico e não foi alterado retroativamente. A execução Windows corrigida, a geração do EXE e o smoke do EXE ainda precisam ocorrer no computador do usuário.

## Recuperação de atualização sobreposta — 11/10/2026

- Causa provável do novo bloqueio: a pasta recebeu o ZIP sobre uma árvore anterior e reteve arquivos de código removidos do pacote novo. A mensagem anterior não expôs a divergência específica; a causa exata da pasta Windows não foi observada diretamente.
- A inicialização atualizada guarda em quarentena somente arquivos extras não listados no manifesto, preservando seu conteúdo em `SIM_Labs_QA/.runtime/source-quarantine`.
- Conteúdo versionado com hash alterado, fonte faltante ou manifesto divergente continua bloqueado sem movimentar arquivos. O manifesto não é regenerado automaticamente.
- Testes: arquivo antigo extra = reparado e manifesto PASS; fonte versionada alterada = BLOCKED e preservada; fixtures SQLite com WAL/SHM = PASS. Sintaxe Python = PASS.
- Suíte completa dos scripts neste host: 26 PASS e 1 BLOQUEADO, porque o Python global Linux não tem `python-dotenv`. Não foi mascarado com mock; o teste de bootstrap deve rodar no venv de backend preparado pelo iniciador Windows.
- É necessária uma execução no Windows com o ZIP atualizado. O EXE ainda não foi gerado.

## Falha `nex_python` do run 96c0a5da — 11/10/2026

- A saída enviada pelo usuário localizou a única falha: `test_every_outfit_has_padded_transparent_full_and_compact_assets`, skin `foco`, papel `hero`; Pillow reportou PNG truncado.
- O arquivo tinha 171.520 bytes; o manifesto da skin esperava 499.761 bytes e SHA-256 `9b946fbe4bde1163a0d07687d048678db54e90b6181c1e635c59c45ee35a57cc`.
- Restaurada a versão V5 preservada em `candidate_tree`, que confere byte a byte com o manifesto da skin. Os outros 146 PNGs também foram decodificados por completo.
- `test_privacy_and_skins.py`: 8/8 PASS após correção. O run Windows anterior fica BLOCKED historicamente; o pipeline final requer uma única repetição para aprovar o conjunto dos 210 testes e tentar o build.
