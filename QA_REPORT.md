# QA_REPORT — NexGrana 0.24.0

## Execução final

Workflow: [NexGrana 0.24 — validação e builds Windows + Android, run #7](https://github.com/lucasmafra-creator/NexGrana/actions/runs/38204162992)  
Commit de código: `d8eef5ecf25eefadac91c9b2e51956aecc8cabd7`  
Resultado geral: **SUCCESS**

- NexGrana Python: 211 testes aprovados, 1 skipped, 227 subtests aprovados.
- SQL e isolamento de perfis: PASS.
- SIM Labs/Collector: 129 testes aprovados, 2 warnings.
- Manifesto: 604/604 fontes conferidas.
- UI do SIM Labs: teste de estado e build Vite PASS.
- Windows: build passou, EXE encontrado, ZIP de homologação publicado.
- Android: build passou, APK publicado.

## Binários e integridade

Baixe em [Actions → run #7 → Artifacts](https://github.com/lucasmafra-creator/NexGrana/actions/runs/38204162992). Disponíveis até 2026-11-11.

- Windows ZIP de execução: SHA-256 `F23B1760EA06CE7E6A13F143F7F68B52D4D6CD696A92C54660E04D735853E020`.
- APK Android: SHA-256 `739052A1E73BCC9030DA6F871AA8B7C8A5F1446F37FDD400CCAE75650A4E91E2`.
- Artefatos do Actions: Windows `sha256:768b8038d0a626d70b960d6e7e0cd45bc1bc919691edc6ec6747fb3eab570f38`; Android `sha256:d53bf50092779046548e3376489d330b274bb67adc6a4bfb7f2131018cfea638`.

## Correções verificadas

- Asset truncado do skin Foco restaurado; PNG 768×768 RGBA.
- Cache Flet, sidecars SQLite, banco de QA, credenciais e ambientes virtuais excluídos do bundle fonte.
- Python embarcado do Flet fixado em 3.12.
- Dependências separadas por plataforma: Android cryptography 43.0.1/Pillow 12.2.0; Windows/QA cryptography 48.0.0/Pillow 12.3.0.
- JNI Android fixado em 1.1.0 para corresponder aos bindings gerados pelo plugin.

## Limites do resultado

Os builds foram compilados e publicados para homologação; não foram instalados em dispositivo físico. Login real, sincronização Supabase de staging, câmera, notificações e uso prolongado precisam de smoke test manual. O APK usa versões Android específicas por disponibilidade das wheels; revisar/atualizar cryptography antes de distribuição pública. Nenhuma migração de produção ou publicação em loja foi feita. iOS continua para a próxima fase.
