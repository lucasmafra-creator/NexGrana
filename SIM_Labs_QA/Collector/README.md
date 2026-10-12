# NexGrana Update Collector + SIM Labs QA local — 0.4.1

Este pacote acrescenta ao Collector um console local para registrar builds, executar verificações estruturais, importar feedbacks e acompanhar validações manuais de Windows e Android.

## O que já funciona localmente

- importar `.zip`, `.apk`, `.aab`, `.exe`, `.msi`, `.msix` e `.appx`;
- calcular SHA-256, identificar versão quando o pacote fornece manifesto e conferir estrutura de ZIP;
- conferir manifesto/DEX/assinatura de APK quando as ferramentas Android correspondentes estão instaladas;
- executar testes da base em ZIP somente após confirmação explícita;
- importar partes do Update Collector e mesclar repetições pelo ID original;
- filtrar feedbacks e remover vários itens selecionados de uma só vez, incluindo todos os itens visíveis após aplicar um filtro;
- registrar checklist manual por build e salvar relatórios JSON/Markdown;
- manter os dados em `data/sim_labs/` no computador.

## Windows

Execute `RUN_WINDOWS.bat`. Para gerar um executável local, use `BUILD_EXE_WINDOWS.bat` em Windows com os requisitos instalados.

## Limites desta entrega

- O console é local e não envia builds nem feedbacks para um servidor.
- Não há backend SIM Labs, URL de API, autenticação de equipe, banco remoto ou serviço de execução contínua incluídos nos arquivos recebidos.
- A análise estrutural não abre o aplicativo. Instalação, navegação e inspeção visual ainda dependem de homologação em dispositivo/build real.
- Testes de código executam o ZIP com as permissões do usuário. A confirmação e o timeout não são uma sandbox de sistema operacional nem bloqueiam rede; execute apenas código confiável.
- APK/AAB podem ser inspecionados, mas não são instalados automaticamente. A validação Android continua manual.
- Esta entrega cobre o código Windows/Android existente. iOS fica para a próxima fase; nenhum IPA é produzido.

O plano para tornar o SIM Labs um control plane persistente, com runners isolados e rotina diária, está em `docs/SIM_LABS_BLUEPRINT.md`.
