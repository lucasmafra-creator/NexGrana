# PROJECT_STATE — NexGrana

- Versão-fonte atual desta rodada: 0.24.0, candidata para homologação.
- Fonte: pacote corrigido preparado a partir do ZIP de estabilidade V6; código em NexGrana/.
- SIM Labs QA, frontend e Collector: código-fonte também sincronizado em SIM_Labs_QA/; banco local, credenciais e virtualenvs excluídos.
- Base principal do repositório: mantém os pacotes históricos de 0.19 e scripts SIM Labs existentes.
- Branch de integração: codex/nexgrana-rc8-source-ci-2026-10-12.
- Manifesto de release cobre os 604 arquivos de NexGrana/ e SIM_Labs_QA/; caches e dados locais ficam fora.
- Próximo gate: GitHub Actions, testes de regressão e builds Windows + Android.
- Financeiro e privacidade: preservar NEXGRANA_RULES.md; não aplicar migrações em produção nem fabricar saldos.
- Nex: preservar a coruja, rosto e assinatura visual canônica; assets atuais mantidos.
- Online: homologação requer backend de QA e credenciais próprias. O pipeline não contém segredos.
- iOS: fora deste escopo, próxima fase.

Status real dos testes e dos builds deve ser atualizado após a execução do workflow, nunca antes.
