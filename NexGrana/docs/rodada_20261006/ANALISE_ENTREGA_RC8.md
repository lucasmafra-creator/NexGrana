# Estado atual — NexGrana + SIM Labs RC8 (6 de outubro, horário de São Paulo)

Foi preparada uma atualização de código do NexGrana e do SIM Labs em cópias isoladas. O ganho mais concreto nesta rodada é o módulo **Ofertas & links** no SIM Labs: cadastro/importação de ofertas, aprovação, pausa/arquivo, fontes autorizadas, coletas agendadas pela fila persistente, histórico, exportação do catálogo e ponte CLI autenticada para o catálogo comercial do NexGrana. A ponte só envia ofertas e hosts autorizados. Ela não consulta nem altera receitas, despesas, saldos ou dados familiares.

O sistema aceita conectores estritos para o feed JSONL autorizado da AWIN e consulta autorizada a um item do Mercado Livre. Suporta fontes sem token para simular/validar o contrato; sem token real ou permissão documentada, grava EXTERNAL_BLOCKER e não afirma que encontrou promoções atuais. O importador de JSON local continua utilizável. Os preços e links permanecem em revisão por padrão; o operador declara explicitamente preço verificado e link afiliado. A aprovação automática é opcional, restrita ao catálogo privado do SIM. A publicação no app é uma ação separada de administrador. A ponte usa sessão de administrador de ofertas, nunca service role.

Há nova migração aditiva NexGrana `MIGRATION_0_25_6.sql` e migração operacional SIM `0006_promotions`. Aplicação real no staging, novos domínios e contas AWIN não foram disponibilizados nesta sessão. A migração Nex foi testada no simulador PostgreSQL PGlite, não em Supabase. **Não aplicar no Supabase de produção.** Faça backup e revisão em projeto de staging, confirme migrations 0.25.1–0.25.5 e depois aplique 0.25.6 em clone descartável.

As skins adicionais entregues anteriormente seguem no pacote, com 36 conjuntos de roupa e 72 imagens transparentes em tamanhos completos/compactos; as seis artes canônicas são preservadas. Isso não torna as PNGs animações. A checagem técnica confirma hash, canal alpha, dimensões e recorte. Não foi possível comparar a experiência nativa em Windows/Moto G22 nesta máquina; também não foi fornecida aqui uma cópia reaberta da imagem de referência visual original. Evite chamar o resultado de homologação estética no aparelho.

## Verificação executada neste host Linux

| Verificação | Resultado |
|---|---:|
| Testes NexGrana | 207 aprovados |
| Testes backend SIM Labs | 88 aprovados |
| Testes Collector | 3 aprovados |
| Contratos/segurança SQL Nex | 117 verificações aprovadas |
| Build TypeScript/Vite SIM Labs | aprovado |
| Verificação HTTP com API, Collector, fila/Engine real e CLI de preview | aprovada com dados TEST DATA em banco temporário; sem feed externo/publicação Supabase |
| Recuperação Linux do watchdog | worker próprio encerrado e reiniciado em cópia temporária; Engine permaneceu ativo |
| Auditor técnico de assets | aprovado; revisão estética/nativa é separada |
| Build Windows/Android | bloqueado: host Linux sem Flutter/ADB e sem aparelho |

São verificações de código/contrato da cópia candidata. Não equivalem à comparação da instalação SIM Labs ativa, a testes financeiros de duas contas no Supabase, nem a aplicativo instalado.

## Leitura analítica e próximos gates

**Pontos fortes:** fronteira SIM Labs–NexGrana clara; fila e coleta integradas; consentimento de afiliado explícito; feed incompleto/repetido, preço vencido, estoque esgotado, replay de catálogo e domínio não autorizado bloqueados; pausas e versões concorrentes respeitadas; nenhuma ação automática em finanças.

**Limites operacionais:** nenhum token/conta autorizada da rede de afiliados foi fornecido. Portanto, coleta de preço ao vivo, links com tracking, comissão, volume e receita são desconhecidos. Coletar links diretos de varejo não cria autorização de afiliado. O catálogo aceita até 500 ofertas e 30 domínios por manifesto, respostas de até 8 MiB e até 10.000 registros por feed. Oferta de preço requer conferência recente; até 24 horas, estoque e validade também expiram. Produtos pausados/arquivados exportam como inativos. Não há publicação nem sincronização periódica para uma Supabase real testada.

**Prontidão iOS:** pronto para planejar e inspecionar compatibilidade; não para abrir a homologação de distribuição como concluída. A fonte Flet já declara `com.nexgrana.app` e permissões de câmera, mas isso não valida os plugins nativos/dependências binárias para iOS. Primeiro fechar staging + Windows + Android, corrigir o chat/teclado com Moto G22 e capturas reais, aceitar regressões financeiras e preparar macOS com Xcode/CocoaPods, wheels de dependências binárias, perfil/certificado Apple e teste TestFlight. Flet requer macOS para `flet build ios-simulator` e `flet build ipa`; o IPA exige assinatura configurada. Fonte: [requisitos iOS do Flet](https://flet.dev/docs/publish/ios/) e [TestFlight](https://developer.apple.com/testflight/).

AWIN exige conta/permissão, bearer token e limite documentado de até cinco downloads por minuto; o feed é JSONL e pode encerrar com uma linha de erro mesmo após HTTP 200. Seus links de produto são diretos, sem tracking: a automação não os converte em afiliados. Fonte: [API oficial do feed de varejo AWIN](https://help.awin.com/apidocs/retail-publisher-productapidocumentation-1).

**Comparação analítica com RC7:** SIM Labs tinha Releases/QA, Collector e Engine, mas não painel/setor de promoções. RC8 adiciona triagem comercial e ponte. NexGrana preserva os guardas anteriores de finanças, privacidade e UX; a nova loja continua secundária e não altera ranking ou decisões financeiras. A diferença testada é de capacidade e controle, não de vendas, estabilidade no usuário, fidelização ou receita. Concorrentes e experiência comercial só podem ser comparados com versão, preço, coorte e evidências atuais; não deduza vantagem de negócio pelos testes sintéticos.

## Próxima execução

1. Descompacte em `C:\NEX_QA_20261007` e `C:\SIM_QA_20261007`; não sobreponha instalação, `.env`, SQLite, runtime ou tarefas existentes. Compare também Observer/Bridge/Runner locais com `CHANGED_FILES.json` e `SOURCE_CHANGES.diff`.
2. Em cópia isolada, use `py -m venv .venv`, instale dependências fixadas e rode `CONCLUIR_RODADA_QA.cmd "C:\NEX_QA_20261007\NexGrana"`. Confirme que a ferramenta nativa está instalada antes de esperar EXE/APK. O comando não instala nem executa o binário.
3. Faça backup do NexGrana staging. Revise e aplique migrações 0.25.1–0.25.6 em projeto descartável. Teste dois usuários/famílias, offline, idempotência, edição concorrente e links/domínios permitidos.
4. Instale o APK apenas no Moto G22 de QA. Reteste chat/teclado, histórico, rotação, voltar, offline, Mercado/OCR/câmera, dimensões 360/390/412 px e 25 feedbacks. Registre capturas reais, esperado/observado e hashes no SIM Labs. Somente Mafra fecha IDs após a evidência.
5. Acesse Ofertas & links localmente. Só cadastre feed/token depois de comprovar permissão do anunciante. Comece com autoaprovação desativada, 1 palavra-chave, 1 fonte e intervalo mínimo de 900 s. Revise 5 ofertas, valide redirect/domínio, preço/estoque/validade e catálogo gerado. No Supabase staging, cadastre Mafra em `app_admins`, aplique 0.25.6 e teste publicação idempotente, pausa, expiração, duas contas não-admin e rollback. Depois avalie `--watch --interval 900` na conta local; ele persiste apenas enquanto o computador/sessões estiverem operando.
6. Recompare pacote com instalação SIM Labs real e abra as conversas por voz antes de começar o estudo de build iOS no Mac.

**Decisão:** não há “OK” para distribuição nem início de homologação final iOS. Há código integrado e testado para revisão controlada; os gates externos acima precisam fechar. Nex Online continua fora desta rodada.
