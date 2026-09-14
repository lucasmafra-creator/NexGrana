# FinanceHub Cloud V1.3 Beta

Esta versão transforma o FinanceHub local em uma base de produto com:

- Login por e-mail e senha
- Conta Individual
- Conta Família com até 7 membros
- Cada membro usa seu próprio login
- Código de convite para entrar em uma família
- Dados armazenados no Supabase/PostgreSQL
- Sincronização automática entre Windows e Android
- Renda por pessoa
- Despesas individuais e compartilhadas
- Divisão igual entre todos os membros (beta)
- Parcelamentos mensais
- Aquisições permanentes até conclusão
- Assistente financeiro baseado no histórico real
- Migração do banco SQLite antigo

## IMPORTANTE

O app usa apenas a chave pública `anon` / publishable do Supabase.
NUNCA coloque a `service_role` dentro do aplicativo.

## 1. Criar projeto Supabase

1. Acesse o Supabase e crie um projeto.
2. No SQL Editor, abra `supabase_schema.sql`.
3. Execute todo o arquivo.
4. Em Authentication > Providers > Email:
   - mantenha Email habilitado.
   - para testes rápidos, você pode desativar "Confirm email".
   - para produto real, é melhor manter confirmação por e-mail.
5. Copie:
   - Project URL
   - anon/public key (ou publishable key)

## 2. Executar no Windows

Na pasta do projeto:

    pip install -r requirements.txt
    flet run src

Na primeira tela, informe URL e chave pública do Supabase.

## 3. Conta Individual ou Família

Após criar/login:

- Individual: cria um espaço para apenas um membro.
- Família: cria um espaço compartilhado para até 7 pessoas.
- O administrador recebe um código de convite.
- Cada novo membro cria sua própria conta e entra usando o código.

## 4. Sincronização

A V1 Beta atualiza automaticamente os dados a cada ~5 segundos.
Isso já permite:
- lançar no Android;
- abrir no Windows;
- ver a atualização sem copiar banco.

O banco na nuvem é a fonte principal.

## 5. Migração

Depois de entrar na sua conta:
Mais > Importar banco antigo (.db)

Selecione o `financehub.db`.

Para o banco antigo Mafra/Karol:
- se os membros "Mafra" e "Karol" existirem na família, o importador associa por nome;
- caso ainda não existam, usa o primeiro membro disponível.

Recomendação: crie as contas/membros da família primeiro e só depois migre o banco antigo.

## 6. Builds

Windows:

    flet build windows

Android:

    flet build apk

## Próxima evolução

- Supabase Realtime por push (em vez do polling de 5 s)
- edição completa de lançamentos
- divisão manual/percentual/por renda
- permissões por membro
- recuperação de senha
- notificações
- gráficos comparativos entre meses
- backup/exportação
- assistente com metas de reserva e planejamento de dívidas


## Correção V1.1
- Corrigida a tela Entrar/Criar conta para compatibilidade com Flet 0.86.x.


## Correção V1.2
- Campo Nome corrigido na criação de conta.
- Tela de autenticação simplificada e validada.

## V1.3 - Família/Casal
- Campo de nome sempre disponível ao criar conta.
- Depois do login, escolha Individual ou Família/Casal.
- Família/Casal permite pré-cadastrar de 2 a 7 nomes.
- Cada pessoa passa a existir separadamente para renda, gastos e metas.
- Membros com login próprio podem ocupar seu nome pré-cadastrado usando o código da família.
- Execute `supabase_patch_v1_3.sql` uma vez no SQL Editor antes de criar a primeira família.

## V1.4 - Diagnóstico e correção de login
- Login válido não é mais revalidado imediatamente por uma segunda consulta.
- Erros de autenticação aparecem dentro da própria tela.
- Erros após autenticação mostram uma tela de diagnóstico em vez de voltar silenciosamente ao login.
- Mensagens amigáveis para e-mail não confirmado e credenciais inválidas.

## V1.6.1 - Hotfix da tela branca
- Corrigidos métodos inexistentes usados pela V1.6.
- `user_name()` substituído pelo perfil autenticado.
- `create_household()` corrigido para `create_workspace()`.
- `join_household()` corrigido para `join_family()`.
- Dropdown de ação usa `on_change`.
- Mantido Família/Casal com 2 a 7 integrantes.

## V1.6.2 - Importação temporária do banco antigo
- Corrigido FilePicker para a API assíncrona atual do Flet.
- Importação do financehub.db funciona no Windows e foi preparada para Android.
- No Android, o app lê os bytes do .db e cria apenas uma cópia temporária.
- O .db é usado somente para migração; depois, o Supabase Cloud é a fonte principal.

## V1.7 - Cloud-first e distribuição multiplataforma
- Nenhum banco SQLite antigo é incluído na distribuição.
- Importação do .db é exclusivamente manual.
- Supabase é a fonte principal dos dados.
- Mesmo código gera Windows e Android.
- Incluído `build_multiplataforma.py`.
- Builds finais são organizados em `dist/windows` e `dist/android`.
- Bundle ID mantido para permitir futuras atualizações do APK.

## V1.7.1 - Importação por substituição
- A importação do financehub.db não soma mais com os dados atuais.
- Antes de importar, remove renda, despesas, divisões e aquisições do espaço atual.
- Mantém conta, login, família e membros.
- Depois importa o histórico do .db antigo.

## V1.8 - Gestão completa e assistente financeiro
- Aba própria "Renda" com registro, edição e exclusão.
- Edição de despesas mantendo a parcela selecionada.
- Edição de aquisições.
- Pesquisa de preços por Mercado Livre, Shopee, Magalu e Amazon; AliExpress usa busca web limitada ao domínio para evitar links quebrados.
- Assistente com sugestão dinâmica de divisão da renda.
- Chat financeiro contextual usando os dados da própria conta.
- Sincronização deixou de redesenhar a tela a cada ciclo; só atualiza a interface quando os dados mudam.
- Importação do .db continua por substituição, preservando conta, família e membros.

## V1.9 - Testes do chat e backup
- Chat não chama mais render() ao responder, evitando voltar para o topo.
- Conversa usa ListView com auto-scroll e barra sempre visível.
- Base educacional ampliada para orçamento, dívidas, crédito, renda fixa, renda variável, inflação, reserva, aposentadoria, cripto, golpes e tributação.
- Adicionada seção com materiais oficiais do Banco Central e CVM.
- Adicionado "Gerar backup .db" em Mais.
- Backup inclui tabelas compatíveis com o FinanceHub antigo e um snapshot JSON completo para preservar os dados da família.
- No Windows o usuário escolhe onde salvar; no Android abre a folha de compartilhamento.
