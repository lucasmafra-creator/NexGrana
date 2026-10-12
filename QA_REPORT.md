# QA_REPORT — sincronização 0.24.0

## Escopo
Fonte do NexGrana 0.24.0 e do SIM Labs QA/Collector adicionada em branch isolada. Inclui testes Python, migrations SQL, assets, gateway e configurações de build. Dependências instaladas e resultados de CI são executados em máquina limpa pelo GitHub Actions.

## Evidências de execução
- A branch principal anterior continha documentação, scripts e pacotes antigos; o app atual não estava versionado como fonte.
- O teste de skins confirmou a restauração do asset de foco. A varredura de PNGs encontrou 149 imagens decodificadas e um PNG truncado sem referência no app em docs/references/identidade_visual.png; esse arquivo de documentação foi excluído da fonte publicada. Nenhum asset canônico foi substituído. A verificação do manifesto inclui os dois diretórios ativos e exclui caches e dados locais.
- Os testes locais de regressão do SIM Labs passam 8 de 9 casos; o único erro no container é a ausência local de python-dotenv, declarado em backend/requirements.txt. A automação instala as dependências antes dos testes.
- Os arquivos locais SQLite WAL/SHM que causaram deriva de manifesto foram excluídos do Git, e os .gitignore agora bloqueiam esses sidecars, bancos locais, credenciais, virtualenvs e builds.
- O teste novo de proveniência e a compilação sintática passaram localmente. A suíte completa e os builds nativos continuam aguardando o workflow desta branch.

## Critério para fechar
1. Testes Python e SQL passam.
2. Windows publica ZIP contendo EXE e arquivos de runtime necessários.
3. Android publica APK.
4. O hash SHA-256 de cada artefato fica no log do workflow.
5. Nenhum segredo de produção, banco ou dado local é adicionado.

Não considerar Windows/Android prontos antes de baixar e instalar os artefatos gerados. Testes de dispositivo, Supabase de QA e iOS continuam independentes.
