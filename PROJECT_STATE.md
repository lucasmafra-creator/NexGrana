# PROJECT_STATE — NexGrana

- Versão-fonte desta rodada: NexGrana 0.24.0 candidata para homologação.
- Fonte atual em `NexGrana/`; SIM Labs QA, frontend e Collector em `SIM_Labs_QA/`.
- Branch de integração: `codex/nexgrana-rc8-source-ci-2026-10-12`; PR #1 aberto contra `main`.
- Código compilado no commit `d8eef5ecf25eefadac91c9b2e51956aecc8cabd7`.
- GitHub Actions: testes Nex, regras financeiras, SQL/perfis, SIM Labs, Collector e UI PASS; Windows EXE e Android APK PASS.
- Manifesto de release: 604 arquivos verificados; caches, dados locais e credenciais fora do Git.
- Financeiro e privacidade: preservar `NEXGRANA_RULES.md); sem migração de produção nem saldos fictícios.
- Nex: preservar a coruja, rosto e assinatura visual canônica.
- Online: usar backend e credenciais de QA separados; nenhum segredo foi incluído nos builds.
- Próxima ação: baixar e instalar os artefatos, fazer smoke test físico e homologar o backend de QA.
- iOS: próxima fase, após a validação manual de Windows/Android.

Os binários atuais são para homologação. A compilação no CI não comprova login real, staging Supabase, execução em dispositivos físicos ou publicação de loja.
