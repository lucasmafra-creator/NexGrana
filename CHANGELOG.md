# CHANGELOG

## 2026-10-12 — NexGrana 0.24.0 RC para homologação
- Restaurada a fonte atual de 0.24.0 e sincronizados SIM Labs QA/Collector na branch de estabilização; arquivos históricos permanecem preservados.
- Asset de foco da skin restaurado conforme o manifesto canônico; cache Flet e sidecars SQLite excluídos da proveniência do build.
- Adicionado pipeline de testes Python/SQL e builds de homologação Windows/Android no GitHub Actions.
- Flet fixado para empacotar Python 3.12 depois que o primeiro runner Android identificou falta de wheel Pillow para Python 3.14.
- Builds ainda são pendentes até a execução terminar com artefatos verificáveis.
- iOS permanece para a próxima fase.
