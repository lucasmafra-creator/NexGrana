# CHANGELOG

## 2026-10-12 — NexGrana 0.24.0 RC para homologação
- Restaurada a fonte atual de 0.24.0 e sincronizados SIM Labs QA/Collector na branch de estabilização; arquivos históricos permanecem preservados.
- Asset de foco da skin restaurado conforme o manifesto canônico; cache Flet e sidecars SQLite excluídos da proveniência do build.
- Adicionado pipeline de testes Python/SQL e builds de homologação Windows/Android no GitHub Actions.
- Flet fixado para empacotar Python 3.12 depois que o primeiro runner Android identificou falta de wheel Pillow para Python 3.14.
- Dependências nativas separadas por alvo: Android cryptography 43.0.1/Pillow 12.2.0 e Windows cryptography 48.0.0/Pillow 12.3.0, conforme as wheels disponíveis.
- Builds ainda são pendentes até a execução terminar com artefatos verificáveis.
- iOS permanece para a próxima fase.
