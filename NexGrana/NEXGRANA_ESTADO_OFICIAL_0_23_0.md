# NEXGRANA — ESTADO OFICIAL

**Versão de trabalho:** 0.23.0  
**Data:** 20/09/2026  
**Base consolidada:** 0.23.0 QA RC1  
**Última validação automatizada:** 130/130 testes Python aprovados em 20/09/2026; cadeia SQL até `MIGRATION_0_23.sql` e varredura de segurança mantidas na validação de release  
**Status da 0.23.0:** código-fonte validado localmente; builds e testes físicos Windows/Android ainda pendentes

## Stack

- Python 3.11 ou superior; ambiente de homologação do Lucas em Python 3.14.
- Flet 0.86.5.
- Flutter 3.44.8.
- Supabase: Auth, PostgreSQL, RPC e Row Level Security.
- `supabase-py` 2.31.0.
- `cryptography` 48.0.0, escolhida pela compatibilidade com Android/Flet.
- Gateway opcional em FastAPI para conversa online do Nex.
- Node.js + PGlite somente para a suíte SQL local.

## Estrutura do projeto

| Caminho | Responsabilidade |
| --- | --- |
| `src/main.py` | inicialização, shell responsivo, navegação, sessão e ciclo de telas |
| `src/screens/` | telas de autenticação, início, transações, análises, planejamento, mercado, Nex e configurações |
| `src/services/` | regras financeiras, Nex, sincronização, investimentos, trilhas, ofertas, privacidade e analytics |
| `src/cloud.py` | Supabase, sessão, cache cifrado, fila offline, refresh e RPCs |
| `src/assets/` | ícone, Nex canônico, avatar, hero, dock, stickers, skins e elementos visuais |
| `admin/achados_admin.py` | painel web privado de administração dos Achados |
| `gateway/` | backend opcional e separado para IA externa |
| `tests/` | testes Python e suíte SQL de migrações/RLS |
| `MIGRATION_*.sql` | evolução aditiva e ordenada do banco Supabase |

## Arquitetura

- Interface Flet única e responsiva para Windows e Android; iOS é alvo futuro.
- Navegação móvel com cinco destinos: Início, Transações, Planejamento, Mercado e Nex.
- Desktop usa barra lateral, preservando os mesmos dados e regras.
- Camada de serviços separa UI, cálculos e acesso à nuvem.
- O motor financeiro local é determinístico e é a única fonte para saldo, futuro e margem.
- Supabase é a fonte remota, protegida por RLS e escopo de família/perfil.
- Cache local cifrado abre a experiência antes da rede; mutações offline entram em fila persistente.
- O Nex funciona localmente para ações financeiras conhecidas. O modo de conversa online depende de gateway HTTPS, JWT e consentimento.
- O painel de Achados é uma aplicação separada e não usa `service_role` no cliente.

## Banco de dados

- PostgreSQL no Supabase.
- Migrações devem ser aplicadas em ordem e nunca automaticamente pelo app.
- Segurança por RLS, funções RPC com validação de `auth.uid()` e isolamento de família.
- Inclusões financeiras críticas usam operações atômicas e identificadores estáveis para impedir duplicação.
- O cliente utiliza chave pública/anon; `service_role` é proibida no aplicativo e no painel.

## Tabelas Supabase

| Domínio | Tabelas |
| --- | --- |
| Conta e família | `profiles`, `households`, `household_members` |
| Finanças | `income`, `expenses`, `expense_shares`, `wallet_accounts`, `semester_summaries` |
| Planejamento | `acquisitions`, `financial_goals`, `goal_contributions` |
| Mercado | `market_trips`, `market_items` |
| Nex | `nex_conversations`, `nex_messages`, `nex_journeys` |
| Privacidade | `privacy_consents` |
| Achados | `affiliate_offers`, `affiliate_offer_audit` |
| Administração/QA | `app_admins`, `qa_testers` |

## Autenticação

- Entrada e criação de conta por e-mail e senha via Supabase Auth.
- Alternância explícita entre “Entrar” e “Criar conta”.
- Senha com mínimo de seis caracteres e confirmação no cadastro.
- Redirecionamento `localhost` é rejeitado no cliente; confirmação de e-mail deve usar URL HTTPS pública configurada no Supabase.
- Refresh de JWT coordenado, com uma repetição segura e bloqueio de cache antigo em falhas de autorização.
- Falha de rede não remove uma sessão válida já persistida.
- Conta oficial de homologação conhecida: `[e-mail redigido]`; a senha não deve ser registrada neste documento.

## Sistema familiar

- O usuário escolhe criar espaço próprio ou entrar em uma família por código.
- Cada registro financeiro pertence a um `household_id` e, quando aplicável, a um `member_id`.
- Perfil individual nunca recebe texto ou saldo consolidado de família.
- O consolidado familiar é explícito e não substitui o saldo da pessoa selecionada.
- Integrante comum não pode promover a si próprio a proprietário.
- Na 0.23, o reset de homologação segue estas regras:
  - conta QA sozinha e proprietária: o espaço de teste é removido;
  - conta QA que entrou em outra família: somente sua participação é removida;
  - conta QA proprietária com outro integrante ativo: a propriedade é transferida e somente a conta QA sai;
  - outro integrante apenas inativo: reset bloqueado para revisão manual.

## Tela inicial

- Saldo atual do perfil selecionado.
- Compromissos futuros e saldo projetado.
- Panorama individual ou familiar adaptado ao modo do espaço.
- Alertas que merecem atenção e acesso contextual ao Nex.
- Acesso à Trilha Nex sem inserir valores de exemplo na conta real.

## Finanças

- Registros por competência mensal.
- Operações de inclusão, edição e exclusão com cache/fila offline.
- Rateio de despesa compartilhada sem duplicar o total familiar.
- Parcelas de outros meses não afetam a competência aberta.
- Repetição de uma inclusão com o mesmo ID não duplica o lançamento.

## Saúde financeira

- Resumos baseados somente nos registros reais disponíveis.
- Margem segura considera saldo após compromissos, reserva e esforço mensal de metas.
- Quando não existe margem, o app não recomenda compra.
- Nenhum dado ausente é substituído por estimativa silenciosa.

## Nex

- Mascote 3D canônico e identidade visual preservada.
- Ações financeiras locais usam regras determinísticas do app.
- Entende saudações e algumas gírias localmente; conversa ampla depende do gateway online.
- Se faltar dado, o Nex deve informar a limitação e nunca chutar valor.
- Dados de outro perfil/família, segredos e conteúdo não autorizado não entram no contexto.
- Modo online é opcional, exige consentimento e não está ativado automaticamente.
- Intenções gerais tentam o gateway autorizado antes do fallback local; consultas financeiras continuam determinísticas.
- Preferências explícitas permitem nome/apelido, tom e nível de detalhe, com opção de não memorizar.
- Nex Vivo centraliza eventos, estados, cooldown, antirrepetição, intensidade e redução de movimento sem escrever nas finanças.

## Chat Nex

- Um chat livre por pessoa.
- Até cinco conversas fixadas por pessoa.
- Fixação/substituição atômica, histórico preservado, renomear e excluir.
- Troca de perfil não pode misturar conversas ou valores.
- Mobile possui retorno explícito, composer fixo, estado local/online e botão para fechar o teclado preservando o rascunho sem enviar.
- Respostas tardias são descartadas se usuário, família, perfil, mês, conversa ou geração da sessão mudarem.
- Sem gateway configurado, respostas genéricas continuam limitadas; isso deve ser comunicado honestamente.

## Achados

- Área de afiliados dentro do Mercado, separada das finanças pessoais.
- Catálogo inicial com seis links reais fornecidos pelo proprietário.
- Pesquisa local, categorias e filtros sem depender de comissão para ranqueamento.
- Preço ausente permanece ausente; o app não inventa preço.
- Disclosure de link afiliado obrigatório.
- Painel privado permite criar rascunho, pré-visualizar, publicar, desativar e excluir.
- Administração protegida por `app_admins`, RLS, allowlist de URLs/imagens e auditoria.

## Investimentos

- Conteúdo educativo e simulador baseado em premissas declaradas pelo usuário.
- Cálculo de equivalência entre taxa anual e mensal, aportes e períodos.
- Custos, impostos e taxa negativa precisam ser explícitos.
- Não usa cotação em tempo real e não altera o saldo financeiro.
- Não promete rentabilidade nem recomenda produto específico como garantia.

## Renda

- Renda válida da competência selecionada soma ao saldo.
- Renda de outro mês é ignorada no mês aberto.
- Registro precisa informar competência ou data válida.
- “Renda extra” é uma área de orientação do usuário e não se confunde com a monetização dos Achados.

## Despesas

- Despesa pertence à competência registrada.
- A data de pagamento não desloca silenciosamente a despesa para outro mês.
- Despesa cancelada não entra no cálculo.
- Débito automático não antecipa o desconto.
- O campo “pago” não pode reduzir o saldo antes do vencimento.

## Saldo

- **Saldo atual da pessoa = rendas da competência − despesas da competência cuja data já chegou.**
- **Saldo projetado = saldo atual − compromissos futuros da competência.**
- Despesa futura aparece como futura e só reduz o saldo no vencimento.
- O vencimento não inventa confirmação de pagamento.
- Saldo familiar é calculado separadamente e nunca substitui saldo individual.

## Regras financeiras

1. Nunca inventar renda, despesa, preço, saldo, pagamento ou cotação.
2. Nunca usar valores de outro perfil para responder sobre a pessoa selecionada.
3. Renda soma somente na competência correta.
4. Despesa reduz somente quando a data de vencimento chega.
5. Futuro reduz apenas o saldo projetado.
6. Uma despesa compartilhada reduz o total familiar uma única vez.
7. Metas pausadas não consomem margem.
8. Valor já guardado em meta não é reservado duas vezes.
9. Comissão de afiliado nunca participa de decisão financeira do usuário.
10. Investimentos simulados não alteram contas reais.

## Administração

- Painel de Achados separado do app principal.
- Acesso somente para UUID habilitado em `app_admins`.
- `qa_testers` autoriza exclusivamente ferramentas de homologação; não concede administração.
- Toda alteração de oferta é auditada.
- URLs de parceiro e imagens obedecem allowlists HTTPS.
- Conta administrativa nunca deve ser definida somente por texto de e-mail no cliente.

## Assets

- `icon.png`: ícone oficial em alta resolução, 1254 × 1254 na base 0.22.
- `nex_hd.png`: master HD canônico; SHA-256 `4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796`.
- Avatar, hero, card e dock separados por contexto de uso.
- Stickers e skins não podem alterar rosto, anatomia, espécie ou identidade central do Nex.
- Animações futuras devem ser leves, opcionais e medidas em Android antes da liberação.
- O master HD anterior é o **Golden Nex**. Nenhum novo pack artístico entrou na 0.23; microanimações preservam o mesmo asset aprovado.

## UX/UI

- Tema escuro com roxo como cor principal e verde apenas para estados financeiros positivos.
- Sem excesso de gradientes, sombras ou espaços vazios.
- Layout denso, organizado e responsivo, inspirado em ferramentas de produtividade.
- Mobile deve respeitar teclado, área segura, rolagem e ações acessíveis.
- Tutorial Nex 2.0 implementado como rota “Aprender fazendo”, com convite pós-entrada, 13 atividades, progresso por perfil e layout mobile/desktop.
- Sandbox financeiro usa o motor oficial: no exemplo R$ 200/R$ 10, dia 19 mantém R$ 200 atuais e R$ 190 projetados; no dia 20 o atual passa a R$ 190.
- Saldo hipotético nunca oferece gravação silenciosa como renda; áreas reais são abertas separadamente para confirmação explícita.
- Textos mudam entre espaço individual e familiar.
- Navegação usa shell reutilizável para reduzir reconstruções e atraso.

## Funcionalidades atuais

- Cadastro/login, espaço individual e família.
- Renda, despesas, parcelas, rateio e saldo por competência.
- Metas, aquisições, investimentos educativos e Renda Extra.
- Mercado, carrinho, conferência de nota e Achados.
- Nex local, chat livre e até cinco conversas fixadas.
- Central de tutoriais, sandbox didático, privacidade, consentimentos, exportação/backup e reset QA.
- Nex Vivo configurável e preferências de conversa.
- Cache cifrado, fila offline, reconexão e sincronização em segundo plano.
- Painel privado de Achados.
- Gateway online executável, mas não publicado/configurado nesta candidata.

## Funcionalidades removidas ou desativadas

- Dados fictícios na conta real.
- Preços inventados em Achados.
- Uso de `service_role` no app ou painel.
- Redirecionamento de autenticação para `localhost` em produção.
- IA externa ativada sem consentimento.
- Pesquisa web anunciada sem integração real.
- Recursos premium/pagos ao usuário nesta fase.
- Cotação de investimentos em tempo real sem fonte confiável.

## Bugs já corrigidos

- Nunca voltar a inventar saldo ou valor financeiro.
- Despesas futuras só debitam no vencimento.
- Campo “pago” não antecipa débito.
- Isolamento de perfis e famílias.
- Despesa compartilhada descontada uma única vez.
- Retry idempotente sem duplicar lançamentos.
- Falha de autenticação por `NameError` no envio de login/cadastro.
- Troca visual entre “Entrar” e “Criar conta”.
- Redirecionamento de confirmação para `localhost` rejeitado.
- Cache antigo não aparece após erro de autorização.
- Sessão persistida não é apagada por falha comum de rede.
- Formulários principais testados em larguras móveis.
- Reset QA da 0.23 permite sair de família sem apagar dados alheios e transfere propriedade quando necessário.
- Chat Android não prende mais o usuário no modo de digitação nem exige envio para voltar.
- Respostas assíncronas do Nex não vazam para outro escopo após troca de conta/perfil/conversa.
- Tutorial estático foi substituído por uma rota responsiva com sandbox isolado.

## Testes existentes

- Motor financeiro e datas de vencimento.
- Competência, parcelas, rateio, duplicação e arredondamento.
- Metas, aquisições e margem segura.
- Simulador de investimentos.
- Cache cifrado, adulteração, backup e fila offline.
- Refresh JWT, falhas de rede, 401 e reconexão.
- Isolamento de família, perfil, chat e RLS.
- Nex local, consentimento, minimização de contexto e gateway.
- UI em múltiplas larguras, autenticação, diálogos e rotas.
- Achados, painel administrativo, allowlists e auditoria.
- Migrações completas em PostgreSQL local/PGlite.
- Reset QA: espaço individual, integrante de família e proprietário com sucessor.
- Tutorial: catálogo, estados, sandbox, descarte, idempotência e regra de vencimento dias 19/20.
- Nex Vivo: eventos, cooldown, antirrepetição, fallback Golden, desativação e redução de movimento.
- Chat Android: fechar teclado sem enviar e preservar rascunho.

## Último resultado dos testes

- Python: **130/130 OK**.
- SQL: cadeia completa até `MIGRATION_0_23.sql` **OK**.
- `compileall`: **OK**.
- Varredura de segredos/artefatos: **OK**.
- Observação: “74/74” pertence à 0.20.0 e não representa a base atual.

## Build Windows

- 0.20.0: build gerado com sucesso e localizado em `dist\Windows`.
- 0.22.0: execução de desenvolvimento no Windows realizada; build instalável desta candidata não foi formalmente registrado como validado.
- 0.23.0: **pendente** geração/instalação da candidata QA RC1.

## Build Android

- 0.20.0: APK gerado com sucesso em `dist\Android\nexgrana.apk`.
- 0.22.0/0.23.0: **pendente** build, instalação e checklist no aparelho físico.

## Build iOS

- Código preparado conceitualmente.
- Build exige macOS, Xcode, CocoaPods, assinatura e conta Apple.
- Ainda não validado em simulador, TestFlight ou aparelho.

## Comandos oficiais

No CMD, dentro da raiz curta do projeto, por exemplo `C:\NG23`:

```bat
cd /d C:\NG23
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python validate_release.py --full
npm ci
npm run test:sql
.venv\Scripts\python -m flet.cli run src
```

Builds da futura candidata 0.23.0:

```bat
.venv\Scripts\python -m flet.cli build windows --build-version 0.23.0 --output "dist\Windows" --yes
.venv\Scripts\python -m flet.cli build apk --build-version 0.23.0 --output "dist\Android" --yes
.venv\Scripts\python -m flet.cli build aab --build-version 0.23.0 --output "dist\AndroidAAB" --yes
```

## Pendências conhecidas

- Confirmar que `MIGRATION_0_23.sql` aplicada na homologação corresponde ao arquivo empacotado e retestar a conta oficial.
- Gateway do Nex ainda não hospedado/configurado; sem isso, conversa ampla permanece limitada.
- Pesquisa web com fontes não conectada.
- Medir latência p50/p95, memória e quedas de frame em Android real.
- Validar 0.23 em Windows e Android com rede boa, mediana, offline e reconexão.
- Configurar URL pública de confirmação de e-mail.
- Revisar LGPD, retenção, exclusão e termos antes da publicação comercial.
- Preparar ambiente macOS e validar iOS.
- Caso o reset encontre outro integrante somente inativo, fazer revisão manual no banco.
- Definir, sem ambiguidade contábil, se “saldo inicial” será apenas simulação ou um tipo real de lançamento; nunca gravá-lo silenciosamente como renda.
- Evoluir cada tutorial de abertura contextual para commit guiado direto somente quando houver prévia, revalidação de escopo e idempotência completas.
- Produzir/validar um pack artístico Nex Vivo apenas se a comparação provar qualidade igual ou superior ao Golden Nex.

## Decisões de produto

- O app permanece gratuito nesta fase.
- Monetização principal estudada: links de afiliados em Achados, com transparência.
- Renda Extra pertence ao usuário e não é receita do aplicativo.
- Nex é parceiro educativo e financeiro, não substitui profissional qualificado.
- Visual deve ser marcante e próprio, sem sacrificar desempenho móvel.
- Recursos virais devem nascer de utilidade, progresso e compartilhamento voluntário; nunca de spam ou exposição de dados.
- Dados reais e confiança têm prioridade sobre aparência, velocidade de entrega ou respostas “completas”.

## Regras que NÃO devem ser alteradas

1. Nunca inventar números financeiros.
2. Nunca debitar despesa futura antes do vencimento.
3. Nunca misturar dados de pessoas ou famílias.
4. Nunca colocar `service_role` ou segredo de provedor no cliente.
5. Nunca ativar IA externa sem consentimento.
6. Nunca fazer Achados interferir na recomendação financeira.
7. Nunca preencher preço ausente como se fosse real.
8. Nunca usar dados fictícios no saldo real do usuário.
9. Nunca declarar plataforma validada sem build, instalação e checklist.
10. Nunca aplicar migration automaticamente em produção.

## Próxima atualização

1. Gerar Windows e APK 0.23.0, instalar e testar o checklist físico.
2. Validar no Android o teclado do chat, tutorial, rolagem, botão Voltar e desempenho do Nex Vivo.
3. Publicar/configurar o gateway HTTPS em homologação e testar consentimento, latência, rate limit e indisponibilidade.
4. Refinar os módulos do Tutorial para commits diretos idempotentes, sem permitir salvar saldo hipotético como renda.
5. Medir desempenho e somente depois avaliar pack Rive/WebP/sprites do Nex Vivo.
6. Preparar e testar o fluxo iOS em macOS/Xcode.
7. Consolidar os números de versão da candidata 0.23.0 em código, documentos e manifesto.
8. Gerar Windows/APK, instalar e executar o checklist completo, incluindo tutorial, teclado, offline e rede mediana.
9. Hospedar o gateway seguro do Nex somente após definir provedor, custo, consentimento e limites.
10. Medir desempenho no Android e corrigir qualquer regressão antes de iniciar a fase iOS.

---

Este arquivo é a referência de continuidade do projeto. Toda nova versão deve atualizar data, status de validação, migrations, testes, builds, pendências e decisões sem apagar o histórico técnico relevante.
