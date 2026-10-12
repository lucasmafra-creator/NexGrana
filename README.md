# NexGrana

Repositório do NexGrana com os pacotes históricos preservados e o código atual da candidata 0.24.0 em NexGrana/.

## Rodada atual

A branch codex/nexgrana-rc8-source-ci-2026-10-12 traz o código do pacote corrigido, preserva as regras financeiras e a identidade canônica do Nex, e configura uma validação automática antes dos builds de Windows e Android. O SIM Labs QA e o Collector também ficam versionados em SIM_Labs_QA/. O pipeline valida backend/UI do SIM Labs, testa o NexGrana e só então libera os builds de Windows e Android. Não publica em produção.

### Testes locais

```powershell
cd NexGrana
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-qa.txt pytest==9.1.1
npm ci
.venv/Scripts/python.exe -m pytest -q
npm run test:sql
```

### Builds locais

Windows e Android usam Flutter 3.44.8. O projeto fixa o Python embarcado do Flet em 3.12. O Android usa cryptography 43.0.1 e Pillow 12.2.0, wheels encontradas no catálogo Android do Flet; Windows/QA usa cryptography 48.0.0 e Pillow 12.3.0. JNI também fica fixado em 1.1.0 para atender ao binding Android gerado pelo plugin. Estes artefatos são de homologação, não publicação de loja. Android também precisa de Java 17 e Android SDK. Depois de preparar esses pré-requisitos:

```powershell
.venv/Scripts/python.exe build_multiplataforma.py windows --timeout 3600
.venv/Scripts/python.exe build_multiplataforma.py apk --timeout 3600
```

O release_manifest.json valida os hashes dos arquivos ativos de NexGrana/ e SIM_Labs_QA/. A automação no GitHub Actions executa os testes e confere esse manifesto antes dos dois builds, depois disponibiliza os arquivos em Actions → execução do workflow → Artifacts por 30 dias. Os builds são artefatos de homologação; não são publicação assinada para lojas.

## Builds de homologação gerados

O workflow do GitHub Actions concluiu os testes e gerou Windows + APK Android para o commit de código `d8eef5ecf25eefadac91c9b2e51956aecc8cabd7`.

Abra [a execução do Actions](https://github.com/lucasmafra-creator/NexGrana/actions/runs/38204162992) e baixe:

- `NexGrana-Windows-0.24.0`: extraia o artefato, extraia `NexGrana_0.24.0_Windows.zip` e execute o EXE mantendo os arquivos da pasta juntos.
- `NexGrana-Android-0.24.0`: extraia o artefato e instale o APK em um dispositivo Android de teste.

Artefatos expiram em 11/11/2026. São builds de homologação; o CI confirmou compilação e arquivos gerados, mas não instalou em dispositivo físico nem publicou em loja. O APK Android usa cryptography 43.0.1 e Pillow 12.2.0 por disponibilidade das wheels do Flet; revisar/atualizar essas versões antes de distribuição pública.

## Regras e limites

- NEXGRANA_RULES.md é a referência financeira e de privacidade.
- Nenhuma credencial, banco local, virtualenv, node_modules ou build gerado é versionado.
- Nenhuma migração de produção ou chamada a Supabase de produção é executada pelo pipeline.
- iOS fica para a próxima fase.
- A integração online depende de backend e segredos de homologação próprios; não os coloque no APK/EXE.
