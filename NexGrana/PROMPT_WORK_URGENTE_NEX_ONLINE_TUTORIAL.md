# PROMPT PARA WORK — CORREÇÃO URGENTE NEX ONLINE + TUTORIAL + NEX VIVO

Trate esta tarefa como correção crítica da release NexGrana 0.23.0. Use o código-fonte recebido como base e leia primeiro `NEXGRANA_ESTADO_OFICIAL_0_23_0.md`, `NEX_GATEWAY_0_23_0.md`, `ATUALIZACAO_0_23_0_RC2_LOCAL_FIXES.md` e os testes existentes.

## 1. Problema crítico: Nex NÃO está online de verdade

Nos testes em Android e Windows, perguntas gerais como “opa nex de boa?”, “como habilitar?”, “tranquilo nex?” e “tá conectado na rede?” recebem respostas prontas do fallback, por exemplo dizendo que “o modo de conversa ampla está indisponível”. Isso destrói a sensação de chat vivo.

O código já possui `gateway/app.py` e `src/services/nex_gateway.py`, mas `src/build_config.py` não possui um endpoint público configurado. Não mascarar o problema com mais respostas prontas. Não declarar “online” só porque existe uma classe de gateway.

### Objetivo obrigatório

Entregar o Nex como chat conversacional completo e natural quando houver internet e consentimento, mantendo as regras financeiras determinísticas existentes.

### Implementação obrigatória

1. Publicar/configurar um gateway HTTPS real e seguro usando o backend já existente em `gateway/` ou equivalente.
2. A chave do provedor deve existir SOMENTE no servidor/cofre, nunca no APK, EXE, repositório ou `build_config.py` público.
3. Configurar no app uma URL pública válida em `NEXGRANA_NEX_GATEWAY_URL`/configuração de build.
4. Validar JWT Supabase no gateway.
5. Manter histórico recente para continuidade real da conversa.
6. Entender português informal, erros, abreviações e gírias sem depender de frases rígidas.
7. Assuntos gerais devem receber respostas normais, não cair no fallback quando o gateway está saudável.
8. Assuntos financeiros devem combinar conversa natural com valores determinísticos do app; nunca inventar saldo, renda, despesas, datas ou parcelas.
9. Se o gateway realmente cair, mostrar aviso curto e útil, mas tentar reconexão de forma transparente. Não repetir quatro variações da mesma resposta pronta.
10. O indicador visual deve refletir o estado real: `online`, `reconectando` ou `offline/local`.
11. Testar Android e Windows em rede real.
12. Confirmar que consentimento “IA externa” persiste no Android e não volta ao estado anterior após fechar/reabrir.

## 2. Nex Vivo perdeu a sensação de vida

O usuário ativou Nex Vivo, microanimações e efeitos, porém não percebe GIFs, reações ou movimento relevante. O Golden Nex visual atual é de alta qualidade e NÃO pode sofrer regressão, serrilhado ou substituição por asset inferior.

### Objetivo

Nex deve parecer vivo sem degradar a imagem canônica.

### Requisitos

- Preservar `nex_hd.png` e derivados atuais como Golden Nex.
- Microanimações visíveis e suaves: respiração, leve balanço, olhar/reação, salto curto, celebração e estados de pensamento.
- Reações a eventos concluídos: renda adicionada, despesa, economia, meta, investimento, chat pensando/respondendo e toque no Nex.
- Não usar GIF pesado ou de baixa qualidade apenas para “ter animação”. Rive/WebP/sprites só se forem visualmente superiores e validados.
- As animações devem respeitar `reduzir movimento`.
- Evitar travamentos e consumo excessivo de CPU/bateria.
- Garantir interação tanto em Android quanto em desktop, não apenas na home.

## 3. Tutorial atual não atende ao conceito solicitado

O tutorial deve ser experiência de primeiro acesso e treinamento interativo, não uma central de textos com botão “Praticar na área real”.

### Fluxo esperado

- Ao iniciar o tutorial, usuário entra em um modo de treinamento completo.
- A tela só sai antecipadamente pelo botão explícito `Pular tutorial completo`.
- Sempre existir `Passo anterior` e `Próximo passo`.
- Ao concluir o último passo, botão `Concluir tutorial`.
- Se o usuário clicar `Pular tutorial completo`, abrir confirmação com duas opções:
  - manter informações digitadas no treinamento;
  - descartar informações digitadas no treinamento.
- Nenhum dado de treino pode virar dado financeiro real sem confirmação específica.

### Tutorial deve ser interativo

Criar sandbox isolado em que o usuário pratica, no mínimo:

1. Boas-vindas e regras essenciais.
2. Saldo atual x projetado.
3. Registrar renda de exemplo.
4. Registrar despesa de exemplo com vencimento e visualizar impacto.
5. Criar aquisição de exemplo.
6. Criar meta e simular esforço.
7. Simular investimento.
8. Criar experimento de renda extra.
9. Montar item/lista de mercado.
10. Entender Achados/afiliados.
11. Conversar com Nex e entender online/local.
12. Entender perfis/família.
13. Configurar privacidade/consentimentos.

Cada passo deve explicar rapidamente, permitir ação real dentro do sandbox e avançar de forma clara.

## 4. Responsividade do tutorial no notebook

Na versão observada, o tutorial fica espremido pela sidebar e o conteúdo principal não aproveita a tela, tornando a experiência confusa.

### Obrigatório

- Tutorial em desktop/notebook deve ocupar a área útil inteira da janela.
- Não exibir sidebar principal durante o tutorial.
- Pode existir uma coluna interna de passos dentro do próprio tutorial.
- Conteúdo principal deve usar espaço restante de forma fluida.
- No Android, manter layout vertical, legível e sem elementos saindo da tela.

## 5. Privacidade no Android não está persistindo

A tela de “Privacidade e seus dados” permite alterar IA externa e outros consentimentos, mas no Android a escolha não está sendo salva de forma confiável.

### Obrigatório

- Persistência local segura imediatamente após o toque em Salvar.
- Sincronização Supabase em segundo plano quando disponível.
- Reabrir o app deve restaurar os switches corretamente.
- Falha de rede não pode apagar a escolha local.
- A política remota deve reconciliar quando a conexão voltar.
- Criar testes de regressão.

## 6. Não regredir regras existentes

Preservar obrigatoriamente:

- saldo nunca inventado;
- renda real soma corretamente;
- despesa futura não debita antes do vencimento;
- aquisição não debita saldo;
- isolamento entre perfis/famílias;
- máximo de cinco chats fixados por perfil;
- qualidade visual atual do Nex;
- Supabase e offline-first;
- segurança do gateway e ausência de chave do provedor no cliente.

## 7. Testes obrigatórios

Adicionar/ajustar testes para:

- tutorial navegação anterior/próximo;
- tutorial sandbox de renda, despesa e aquisição;
- pular tutorial mantendo sandbox;
- pular tutorial descartando sandbox;
- tutorial desktop sem sidebar principal;
- consentimentos persistindo offline/Android;
- gateway configurado realmente responde online;
- indicador online não aparece falsamente;
- histórico conversacional mantém contexto;
- falha do gateway não entra em loop de respostas repetidas;
- Nex Vivo reage e respeita reduzir movimento.

## 8. Definition of Done

Não entregar ZIP até:

1. toda suíte Python passar;
2. testes SQL passarem;
3. `python -m flet.cli run src` abrir sem traceback crítico;
4. login e Supabase serem testados;
5. chat Nex online ser testado com perguntas gerais reais;
6. persistência de consentimentos ser testada em Android;
7. tutorial completo ser percorrido no Android;
8. tutorial completo ser percorrido no Windows/notebook;
9. `python -m flet.cli build windows --build-version 0.23.0 --output "dist\\Windows" --yes` concluir;
10. `python -m flet.cli build apk --build-version 0.23.0 --output "dist\\Android" --yes` concluir;
11. EXE e APK serem localizados e conferidos;
12. `TEST_REPORT.md`, `BUILD_REPORT.md`, `CHANGELOG.md` e `NEXGRANA_ESTADO_ATUAL.md` serem atualizados.

Se o gateway não puder ser publicado/testado no ambiente do Work, não declarar o Nex online como concluído. Entregar o restante corrigido e documentar exatamente o que falta para ativar o backend.
