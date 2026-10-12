# BUILD_STATUS — rodada NexGrana 0.24.0

Data de preparação: 2026-10-12  
Branch: codex/nexgrana-rc8-source-ci-2026-10-12

| Gate | Status inicial desta branch |
|---|---|
| Fonte 0.24.0 importada do pacote corrigido | PASS |
| Manifesto dos diretórios ativos (604 arquivos) | PASS — hashes gerados; CI fará a verificação
| Assets e identidade canônica | PASS — 149 PNGs ativos foram decodificados; o asset de foco foi restaurado e uma referência PNG truncada em documentação foi retirada |
| Fonte SIM Labs QA/Collector e dados locais fora do Git | PASS |
| Python embarcado do Flet | PENDING — ajustado para 3.12 após o primeiro runner Android detectar incompatibilidade de wheel no 3.14 |
| Testes NexGrana, SIM Labs, Collector e UI | PENDING |
| Build Windows | PENDING — só confirmar após EXE e artefato do Actions |
| Build Android APK | PENDING — só confirmar após APK e artefato do Actions |
| iOS | DEFERRED |

O histórico do repositório contém um build Windows aprovado e um Android falho da versão 0.19. Eles não contam como evidência da 0.24.0.

A branch configura GitHub Actions para rodar os testes, compilar Windows e Android e guardar os artefatos por 30 dias. Nenhum binário é declarado como pronto antes do término bem-sucedido do respectivo job.
