# NexGrana 0.21.0 QA — atualização

Esta candidata fecha os problemas observados no Android e prepara a próxima fase de homologação. A 0.20.0 RC1 foi preservada em outra árvore de trabalho.

## Mudanças implementadas

- cache cifrado é lido antes da rede somente após uma sessão validada;
- sincronização passou para segundo plano com espera progressiva quando a conexão falha;
- inclusões, edições e exclusões financeiras suportadas entram em fila cifrada ordenada antes da atualização otimista; UUIDs são estáveis e o estado é reconstruído após interrupção;
- erros permanentes de permissão/validação param de repetir; operações transitórias usam backoff;
- alteração recusada ou em conflito é retirada do cálculo otimista e pode ser repetida ou descartada em Mais > Sincronização;
- login, cadastro, criação de espaço e entrada em família não bloqueiam mais a thread da interface;
- Entrar e Criar conta são ações separadas, com confirmação e requisitos reais de senha configuráveis;
- RC2 corrige o seletor de autenticação no Flet 0.86.5: modo, campos e texto do botão agora mudam juntos e indicam claramente se é login ou cadastro;
- RC3 corrige a execução de login/cadastro (`asyncio`) e inclui teste que envia os dois formulários, além de verificar apenas sua aparência;
- callback de autenticação rejeita explicitamente localhost; confirmação e recuperação exigem URL HTTPS configurada;
- escolha Criar meu espaço/Entrar em uma família atualiza localmente e usa campos independentes;
- tutorial curto é oferecido por abertura até o usuário dispensá-lo, com replay em Mais;
- chat móvel ganhou cabeçalho compacto, Voltar visível e mais espaço para mensagens;
- formulário de produto ficou rolável, com ações separadas e salvamento assíncrono;
- tela de privacidade usa blocos responsivos e fechamento acessível;
- Achados ganhou pesquisa e filtro local, preservando os seis links fornecidos e sem inventar preços;
- painel web separado permite administrar Achados sob RLS, com auditoria e domínios permitidos;
- Nex bloqueia extração de segredos/dados de outra família e pedidos operacionais nocivos, preservando perguntas defensivas;
- build QA inclui reset de homologação protegido no servidor e restrito a espaço de um único integrante;
- script de build agora transmite o progresso para o terminal e interrompe cedo em caminho Windows longo.

## Regras preservadas

- renda recebida soma no saldo;
- despesa futura só reduz o saldo no vencimento;
- rateio familiar é reconciliado sem descontar a mesma despesa duas vezes;
- Nex nunca calcula saldos por modelo de linguagem nem inventa valores;
- investimentos continuam como estudo/simulação;
- Achados não altera a análise financeira e não vende dados.

## Dependências de infraestrutura

Antes do APK de homologação conectado à nuvem, aplique `MIGRATION_0_21.sql` em homologação e configure os UUIDs de `qa_testers` e `app_admins`. O retorno de e-mail exige uma URL HTTPS real em `src/build_config.py` (para o APK), opcionalmente em `NEXGRANA_AUTH_REDIRECT_URL` no desktop, e na allowlist do Supabase. O painel administrativo precisa ser publicado separadamente em HTTPS.

O Nex continua com motor local determinístico nesta candidata. `NEX_GATEWAY_0_21_0.md` documenta a fronteira minimizada já preparada; conversa ampla por LLM só pode ser ativada depois de existir um gateway autenticado no servidor. Nenhuma chave de provedor entra no APK.
