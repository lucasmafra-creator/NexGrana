# Builds e registro
| Artefato | Estado | Arquivo/hash |
|---|---|---|
| NexGrana Windows EXE | BLOCKED: host Linux | inexistente; sem hash |
| NexGrana Android APK | BLOCKED: Flutter/SDK ausentes | inexistente; sem hash |
| Collector EXE | BLOCKED: Windows indisponível | inexistente; sem hash |
| SIM Labs frontend | BUILT: TypeScript/Vite | backend/static; hashes no manifesto |
| Fonte + assets + relatórios | PACKAGED | manifesto e SHA256 externos |

Tentativa real de build: native-build-attempt/build-report.json e logs. Registrar arquivo não significa executar, instalar ou publicar. register_latest_build.py recusa build bloqueado, arquivo fora da pasta e hash/tamanho divergente. O relatório do runner testa a fonte, sem comprovar execução do EXE que vier a ser compilado.
