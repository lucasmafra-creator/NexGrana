# Estado de execução e builds — 2026-10-09

## Ambiente desta auditoria

| Item | Estado observado |
|---|---|
| Sistema do executor | Linux; não é o Windows do Mafra |
| Python disponível | Runtime 3.12.14 e `/usr/bin/python3` 3.12.3 |
| Flet do candidato | `0.86.5`, instalado em venv temporário |
| Node.js | `v24.19.0` |
| Java | OpenJDK 17 |
| Flutter | Ausente |
| Android SDK / `adb` | Ausentes |
| Git na cópia | Sem diretório/metadados `.git`; branch e commit indisponíveis |
| Banco remoto | Não acessado; nenhuma migration aplicada |

## Estado por etapa

| Etapa | Estado | Evidência / limite |
|---|---|---|
| Doctor | PARCIAL | Inventário manual do runtime; ainda não existe um comando único de doctor no candidato. |
| Run | PARCIAL | `flet run --web --host 127.0.0.1 --port 8550 src/main.py`; servidor respondeu HTTP 200 em verificação loopback. Não houve navegação de tela. |
| Unit/regressão Python | PASS COM RESSALVA | 210 testes; ver `QA_REPORT.md` para a adaptação temporária do encerramento asyncio. |
| Financeiro/perfil | PASS LOCAL | Coberto pelos testes Python e SQL/PGlite; sem confirmação em serviço Supabase real. |
| SQL/PGlite | PASS LOCAL | 117 verificações no banco efêmero de QA. |
| Assets | PASS ESTÁTICO | 147 imagens decodificáveis; testes validam os conjuntos de skins. Aprovação visual nativa continua pendente. |
| SIM Labs backend | PARCIAL | 36 testes sem `TestClient` aprovados; servidor QA temporário respondeu HTTP 200 em health, OpenAPI e UI. 95 casos foram coletados; os casos que usam `TestClient` ficam bloqueados pela falha de wakeup entre threads deste executor, também reproduzida num app mínimo. |
| SIM Labs senha local | PASS EM CLONE DESCARTÁVEL | Bootstrap executado duas vezes: created-once e depois preserved, sem mudar o arquivo da senha. Persistência na instalação Windows do Mafra ainda precisa ser confirmada. |
| Launcher QA na raiz | UM CLIQUE IMPLEMENTADO / WINDOWS PENDENTE | O comando valida health/interface/login, abre a central e dispara ou acompanha o pipeline sem repetir POST. Simulação local automatizada PASS; execução Windows real ainda pendente. |
| Manifesto/pipeline | PASS LOCAL | Gerador e preflight concordam no escopo e ignoram WAL/SHM/journal temporários; teste reproduz arquivos SQLite voláteis. |
| Python do pipeline | AJUSTADO | Seleciona Python estável `>=3.11` conforme `pyproject.toml`; compatibilidade das dependências ainda precisa ser confirmada no Windows. |
| Windows EXE | BLOCKED | Host atual é Linux; nenhum `.exe` foi gerado. |
| Android APK | BLOCKED | Flutter, SDK e `adb` não estão instalados neste host; nenhum `.apk` foi gerado. |
| iOS | ADIADO | Fase posterior; requer macOS, Xcode e assinatura. |

## Comandos já existentes no projeto

- `VALIDAR_0_24.cmd` — instala dependências, roda `pip check` e `validate_release.py --full`.
- `VALIDAR_SQL_0_24.cmd` — prepara PGlite e executa testes SQL locais.
- `COMPILAR_0_24_WINDOWS.cmd` — valida e tenta build Windows no host Windows preparado.
- `COMPILAR_0_24_ANDROID.cmd` — valida e tenta build Android no host com Flutter/SDK.
- Execução web usada nesta auditoria: `python -m flet.cli run --web --host 127.0.0.1 --port 8550 src/main.py`.

O comando `REPARAR_E_INICIAR_SIM_LABS_QA.cmd` agora cobre a inicialização e execução integrada do pipeline QA. O diagnóstico completo de todas as dependências nativas, execução Windows e builds ainda depende do PC Windows do usuário. Nenhum artefato nativo foi gerado nesta sessão.
