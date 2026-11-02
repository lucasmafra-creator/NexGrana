# Auditoria de estabilidade — 2026-11-02

## Resultado

**Parcial / BLOCKED para auditoria funcional e QA da V7.** A branch `main` foi identificada em `f4ae9704822173c2c39ab1b361257ccebbbbddd1`, mas a documentação do próprio repositório não comprova que essa árvore seja a fonte V7 instalada ou o checkout V7 usado anteriormente. Nenhum teste financeiro, build nativo ou smoke test foi executado nesta rodada.

## Escopo e evidências consultadas

Leitura somente de arquivos por GitHub; nenhuma alteração de banco, secret, ambiente de produção ou serviço hospedado.

- [AGENTS.md](https://github.com/lucasmafra-creator/NexGrana/blob/f4ae9704822173c2c39ab1b361257ccebbbbddd1/AGENTS.md): exige preservar regras financeiras, privacidade, isolamento e identidade do Nex.
- [README.md](https://github.com/lucasmafra-creator/NexGrana/blob/f4ae9704822173c2c39ab1b361257ccebbbbddd1/README.md): descreve “SIM Labs 0.4.0” e informa que não há EXE compilado.
- [PROJECT_STATE.md](https://github.com/lucasmafra-creator/NexGrana/blob/f4ae9704822173c2c39ab1b361257ccebbbbddd1/PROJECT_STATE.md): descreve árvore local derivada de V7 comparada ao ZIP V5, sem metadados Git verificáveis e sem equivalência confirmada com o repositório remoto ou instalação Windows.
- [NEXGRANA_RULES.md](https://github.com/lucasmafra-creator/NexGrana/blob/f4ae9704822173c2c39ab1b361257ccebbbbddd1/NEXGRANA_RULES.md): define invariantes para saldo, datas, idempotência, isolamento de perfis, RLS e dados sintéticos.
- [BUILD_STATUS.md](https://github.com/lucasmafra-creator/NexGrana/blob/f4ae9704822173c2c39ab1b361257ccebbbbddd1/BUILD_STATUS.md): registra build Windows bloqueado, nenhum EXE/APK e validações pendentes.
- [release_manifest.json](https://github.com/lucasmafra-creator/NexGrana/blob/f4ae9704822173c2c39ab1b361257ccebbbbddd1/release_manifest.json): status `SOURCE_BUNDLE_UNBUILT`; artefatos Windows e Android nulos.
- [LEIA_PRIMEIRO_QA.md](https://github.com/lucasmafra-creator/NexGrana/blob/f4ae9704822173c2c39ab1b361257ccebbbbddd1/LEIA_PRIMEIRO_QA.md): descreve clone de validação, informa ausência de staging conectado e limitações de validação Windows/dispositivo.

O SHA atual foi obtido pela busca de commits do repositório em 2026-11-02. Os arquivos `NOW.md` e `SKILL.md` não existiam na raiz (respostas 404 da API do GitHub); a skill nova foi colocada em `.agents/skills/nexgrana-review/SKILL.md`.

## Achados

| Prioridade | Estado | Achado e impacto |
| --- | --- | --- |
| Bloqueador | BLOCKED | A identidade da fonte V7 não está provada. README, PROJECT_STATE e manifesto descrevem componentes/estados que não estabelecem equivalência entre main, clone local e app instalado. Testes nesta árvore não fechariam o aceite da V7. |
| Alta | NOT RUN | Continuidade de mês não tem resultado reproduzível nesta rodada. Não foi possível mapear uma fonte V7 confirmada nem executar casos sintéticos; nenhuma correção foi feita. |
| Alta | BLOCKED | Builds nativos não estão disponíveis no manifesto e BUILD_STATUS marca Windows/Android bloqueados. Não há artefato a hashear ou executar. |
| Média | NOT RUN | Revisão estática completa de arquitetura, cálculos, autenticação/RLS, sincronização, dependências, acessibilidade, assets e workflows não foi executada. Esta rodada foi limitada à leitura documental indicada acima. |

## Testes e mudanças

- Skill reutilizável criada nesta branch: `.agents/skills/nexgrana-review/SKILL.md`.
- Testes automatizados: **NOT RUN**; checkout executável não estava disponível neste workspace.
- Testes de continuidade de mês: **BLOCKED**; fonte V7 e comandos de teste não confirmados.
- Windows/Android builds e smoke: **NOT RUN/BLOCKED**; nenhum build foi iniciado.
- Produção: **sem alterações**.
- Nenhum EXE/APK foi criado nem declarado validado.

## Próximo passo necessário

No Windows, localizar o checkout/ZIP V7 exato que Mafra pretende testar e registrar caminho, versão e SHA-256. Comparar sua árvore/manifesto com o repositório e obter confirmação explícita da fonte canônica antes de integrar mudanças ao produto. Com a fonte confirmada, rodar primeiro os testes sintéticos existentes de virada de mês; corrigir apenas a regressão já autorizada e só então avaliar build QA.
