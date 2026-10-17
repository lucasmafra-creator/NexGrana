# Auditoria inicial — NexGrana 0.21.0

Data da auditoria: 18/09/2026  
Base preservada: árvore de trabalho `codex/nexgrana-020`, derivada do commit `8cbcefc`, com as alterações da candidata 0.20.0 RC1 ainda não consolidadas no Git.  
Cópia de evolução: `NexGrana_0_21_work`, branch local `codex/nexgrana-021`.

## Evidência disponível

- A validação estrutural local reconheceu versão, manifesto, ícone e compilação Python.
- A suíte completa não pôde ser executada no primeiro minuto porque o pacote Flet não estava instalado. Um ambiente virtual isolado foi criado e a rodada final da 0.21 aprovou 88 testes Python; as migrations/RLS passaram também em PostgreSQL local (PGlite). A evidência externa apresentada por Lucas continua sendo a prova dos builds Windows e APK 0.20.0.
- A migration 0.20 existe na base, mas sua aplicação no Supabase de produção não é presumida.

## Achados P0

1. **A navegação ainda pode bloquear na rede.** A construção de várias telas chama `fetch_all()`, que consulta a nuvem antes de devolver o cache. O loop de sincronização também consulta todas as coleções em sequência. Isso explica parte da lentidão percebida em conexão mediana.
2. **A fila offline está isolada do produto.** `SyncQueue` possui idempotência local, conflito e backoff, mas nenhuma mutação financeira passa por ela. O próprio módulo documenta essa limitação.
3. **Cadastro e onboarding executam rede na thread do evento.** Login, cadastro, criação e entrada em família usam chamadas síncronas. Enquanto aguardam o Supabase, a interface pode aparentar travamento.
4. **O retorno de confirmação depende da configuração externa do Supabase.** O cliente não informa um `email_redirect_to` confiável nem trata retorno móvel. Com Site URL em `localhost:3000`, o Android abre uma página impossível de alcançar.
5. **A troca de modo do espaço usa o mesmo controle de nome em dois painéis e depende de atualização completa da página.** Isso permite estado visual incoerente no Android e amplia o custo da troca.
6. **A separação de cache por usuário e família está presente**, e erros de autorização não usam cache antigo. Essa proteção deve ser preservada.
7. **O motor financeiro aprovado está determinístico.** Ele separa saldo atual e compromissos futuros pela data de vencimento, deduplica IDs e reconcilia rateios. Não será substituído.

## Achados P1

1. O chat já tem conversa livre e até cinco assuntos fixados por pessoa, mas o cabeçalho, o herói e os atalhos competem com as mensagens no celular.
2. O modo de foco oculta elementos quando o teclado abre, porém não oferece uma entrada explícita para conversa em tela cheia nem uma seta de retorno persistente.
3. O formulário de produto usa `AlertDialog.actions` com três ações longas; em tela pequena e com teclado elas se sobrepõem.
4. Privacidade usa um único diálogo longo. Apesar da rolagem, o conteúdo e as ações não se adaptam bem à altura efetiva do Android.
5. Achados já preserva os seis links enviados e não inventa preço. Falta busca/filtros completos e uma administração remota exclusiva, auditável e independente de rebuild.
6. O Nex atual é um motor local determinístico. Ele protege números financeiros, mas respostas abertas caem em texto genérico. Uma IA ampla real exigirá gateway de servidor, consentimento e credenciais que não devem existir no APK.
7. Não há oferta de tutorial por abertura, replay completo em Ajuda nem reset seguro de homologação com escopo explícito.

## Decisões da atualização

- Abrir dados locais primeiro e atualizar em segundo plano, mantendo indicação honesta de cache, pendências, conflito e erro.
- Integrar uma fila cifrada às mutações autorizadas somente quando servidor e cliente tiverem idempotência verificável; não declarar escrita offline pronta antes disso.
- Mover operações de autenticação/onboarding para tarefas assíncronas e impedir envios duplicados.
- Corrigir o fluxo visual no Android sem reduzir fonte nem esconder informação financeira.
- Adicionar migration aditiva para catálogo administrativo, operação idempotente e controles de homologação, sem apagar dados existentes.
- Tratar o ambiente de teste como separado do uso real. O e-mail de teste não concede administração de Achados.
- Executar testes ofensivos somente contra código local, mocks e ambiente de homologação autorizado.

## Dependências externas que continuam necessárias

- Definir uma URL HTTPS real para confirmação/recuperação ou configurar e validar deep links para Android e, depois, iOS.
- Informar o UUID da conta administrativa de Lucas no Supabase por configuração segura de servidor.
- Aplicar e validar a migration 0.21 em homologação antes de liberar o novo cliente.
- Para conversa ampla por modelo de linguagem, publicar um gateway autenticado e adicionar a chave do provedor somente no servidor.
