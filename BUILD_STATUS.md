# BUILD_STATUS — NexGrana 0.24.0

Data: 2026-10-12  
Branch: codex/nexgrana-rc8-source-ci-2026-10-12  
Commit do código compilado: d8eef5ecf25eefadac91c9b2e51956aecc8cabd7  
Workflow: [Actions run #7](https://github.com/lucasmafra-creator/NexGrana/actions/runs/38204162992)

| Gate | Resultado |
|---|---|
| Fonte NexGrana 0.24.0 e SIM Labs QA/Collector | PASS |
| Manifesto de fontes | PASS — 604/604 arquivos |
| NexGrana Python | PASS — 211 testes, 1 skipped; 227 subtests |
| SQL e isolamento de perfis | PASS |
| SIM Labs backend/Collector | PASS — 129 testes; 2 warnings |
| Interface SIM Labs | PASS — teste de estado e build Vite |
| Build Windows | PASS — EXE encontrado e ZIP de homologação publicado |
| Build Android APK | PASS — APK publicado |
| iOS | DEFERRED |

O artefato Windows e o APK são de homologação. O Android usa cryptography 43.0.1 e Pillow 12.2.0 porque essas são as wheels disponíveis no catálogo Android do Flet; Windows/QA usa 48.0.0 e 12.3.0. Revisar e atualizar a dependência Android antes de distribuição pública.

Os artefatos ficam disponíveis na execução do Actions por 30 dias, até 2026-11-11. A compilação não substitui instalação e smoke test em dispositivos físicos, homologação do backend/Supabase, assinatura de loja ou validação de produção.

Hashes dos binários:
- Windows ZIP: `F23B1760EA06CE7E6A13F143F7F68B52D4D6CD696A92C54660E04D735853E020`
- Android APK: `739052A1E73BCC9030DA6F871AA8B7C8A5F1446F37FDD400CCAE75650A4E91E2`
