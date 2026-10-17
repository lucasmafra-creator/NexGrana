# PROMPT MESTRE — NEXGRANA: PRÓXIMA GRANDE ATUALIZAÇÃO

**Destinatário: GPT-5.6 Sol**

Você é responsável por implementar, validar e entregar a próxima atualização do NexGrana a partir do ZIP mais recente fornecido.

Trabalhe como engenheiro principal e responsável por produto, UX, performance e integridade financeira. **Edite o projeto e entregue os resultados; não se limite a produzir uma análise ou um plano.**

Faça uma evolução incremental. Preserve o que funciona, investigue as falhas e mantenha rastreabilidade entre requisitos, alterações e testes.

## 1. Missão e decisões de produto

Transformar o NexGrana em um aplicativo financeiro consumer com identidade própria, navegação fluida e utilidade diária.

A experiência deve transmitir clareza, confiança, proximidade e progresso. O Nex é o parceiro financeiro do usuário: ajuda a entender, decidir e acompanhar. Sua aparência e comportamento devem ser consistentes.

Regras obrigatórias:

- Todas as funcionalidades permanecem gratuitas.
- Não criar assinatura, Premium, paywall ou bloqueios para estimular pagamento.
- Limites técnicos contra abuso podem existir, mas devem ser proporcionais, explicados e acompanhados de alternativa local quando possível.
- Não vender dados nem compartilhar informações financeiras com anunciantes.
- Não usar comissão para determinar a recomendação financeira.
- Não usar falsa urgência, culpa, medo, perda de sequência ou pressão para comprar.
- Não transformar a Home em uma coleção de indicadores.
- Não reescrever o aplicativo inteiro sem demonstrar que a refatoração incremental é insuficiente.
- Não substituir cálculos financeiros determinísticos por respostas de IA.
- Não remover funcionalidades existentes silenciosamente.

**Prioridade de decisão:** integridade e segurança → funcionamento → clareza → velocidade → identidade visual → retenção → monetização.

Receita comercial nunca justifica prejudicar uma decisão financeira.

## 2. Inspeção inicial e contrato de execução

Antes de editar:

1. Identifique o ZIP mais recente, sua versão, data, estrutura e hash.
2. Extraia em diretório de trabalho separado. Preserve o ZIP original.
3. Leia os requisitos, checkpoint, changelogs, instruções locais e feedbacks fornecidos.
4. Identifique arquivos históricos para não tratar documentação antiga como estado atual.
5. Mapeie:
   - entry point e bootstrap;
   - telas, navegação e estado;
   - Cloud/repositórios;
   - motor financeiro;
   - pipeline do Nex;
   - autenticação e armazenamento;
   - schema, migrations, RLS e RPCs;
   - assets e controlador do mascote;
   - build Windows/Android;
   - testes existentes.
6. Confira versões efetivamente instaladas e declaradas. Verifique as assinaturas das APIs usadas na versão do Flet do projeto.
7. Rode a suíte existente antes das alterações e registre a linha de base.
8. Transforme os requisitos deste documento em IDs rastreáveis e apresente um plano curto por prioridade. Depois execute.

Use os nomes de arquivo citados neste prompt como **pontos de investigação**, não como garantia de que o ZIP mais recente mantém a mesma estrutura.

### Estado anterior conhecido — revalidar

Um checkpoint anterior, `0.18.0`, registrava:

- motor financeiro com Decimal e saldo contínuo;
- extração de telas para `screens/*`;
- Vault e cache por usuário/família;
- RPCs de despesas, rateios, aportes e conferência de Mercado;
- 40 testes Python aprovados;
- testes SQL em PGlite;
- mascote HD, mas com estados ainda reutilizando uma mesma imagem;
- funcionalidades incompletas de trilhas, consentimentos, sincronização e Nex;
- falha de builds por “Acesso negado” no Flutter.

Isso é histórico, **não comprovação da versão recebida**. Reexecute os testes relevantes. Testes de construção de componentes não equivalem a inspeção visual; PGlite não equivale a Supabase completo; build não equivale a teste em dispositivo.

Não use o banco financeiro real como ambiente de testes.

## 3. Prioridades e limites de escopo

| PrioridadeTrabalhoCondição para avançar |                                                                                                          |                                                                                    |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| P0                                      | Integridade financeira, migrations, autenticação, isolamento, crashes, chat Android e ações sem resposta | Testes críticos passando; nenhum defeito conhecido de perda de dados ou isolamento |
| P1                                      | Profiling, navegação, Nex Engine, design system, asset pipeline, Home, Análises e simulador              | Evidências comparáveis de funcionamento e performance                              |
| P2                                      | Aquisições, Mercado, diagnóstico de renda extra, Trilhas Nex e acessibilidade completa                   | Fluxos persistentes e utilizáveis, sem botões decorativos                          |
| P3                                      | Central de Oportunidades, abstrações comerciais, instrumentação mínima e polimento                       | Não introduzir regressões nem depender de monetização para funcionar               |

Problemas de integridade encontrados em qualquer tela são P0, independentemente da posição da funcionalidade na tabela.

Nesta atualização:

- implemente a infraestrutura mínima de afiliados e uma experiência útil sem parceiros;
- não construa marketplace transacional próprio, carteira de cashback, plataforma B2B ou rede de anúncios;
- não integre dezenas de provedores;
- não amplie o escopo para crédito, investimentos ou movimentação bancária;
- evite abstrações que não resolvam uma necessidade concreta.

## 4. Integridade financeira: uma única fonte de cálculo

Centralize os cálculos usados por Home, Análises, Planejamento, Aquisições e Nex.

O motor deve retornar resultados estruturados, com:

- valor;
- período e instante de referência;
- origem dos dados;
- estado de atualização;
- premissas;
- classificação: **registrado, calculado, projetado ou sugerido**.

### Invariantes obrigatórios

1. Valores monetários em centavos inteiros ou Decimal com arredondamento definido. Nunca usar float como representação autoritativa.
2. Despesa agendada ou atrasada não reduz caixa como se estivesse paga.
3. Pagamento confirmado usa a data real de pagamento.
4. Débito automático só atua quando explicitamente configurado, sem duplicar confirmação posterior.
5. Renda futura ou com recebimento desconhecido não integra saldo recebido.
6. A mudança de mês não zera o caixa nem apaga histórico.
7. Rateio individual soma exatamente o total familiar. Transferências internas não viram receita familiar.
8. Parcelas possuem identidade própria; o agrupamento não duplica lançamentos.
9. Dinheiro reservado continua compondo patrimônio/caixa conforme o modelo existente, mas deixa de ser livre. Reservar para uma meta não é uma despesa por si só.
10. Compra vinculada a uma meta gera no máximo uma baixa financeira, mesmo após retry.
11. Cashback previsto não é recebido. Cashback recebido não altera o total fiscal da nota e só gera entrada financeira uma vez.
12. Datas financeiras usam a data local pertinente; timestamps técnicos usam convenção explícita, preferencialmente UTC.
13. Valores ausentes, inválidos ou desatualizados não se tornam zero silenciosamente.
14. Nenhum resultado deve somar totais de snapshots incompatíveis sem indicar a inconsistência.

Defina “disponível para gastar” de forma explicável: caixa confirmado menos compromissos e reservas protegidas, considerando um horizonte explícito. Não deduza a mesma reserva duas vezes.

Diferencie:

- caixa acumulado;
- resultado do mês;
- compromissos pendentes;
- reservas;
- margem estimada.

Não mude a matemática existente apenas para encaixar uma nova interface.

### Concorrência e sincronização

- Use transação para operações que afetam múltiplas tabelas.
- Persistir o identificador idempotente antes da primeira tentativa de envio.
- A mesma operação repetida deve produzir o mesmo efeito, uma única vez.
- Reutilizar um ID com conteúdo diferente deve gerar conflito explícito.
- Use versão esperada ou mecanismo equivalente em edições suscetíveis a sobrescrita concorrente.
- Defina ordem consistente de locks e teste deadlocks/retries.
- Teste duas conexões concorrentes; testes sequenciais não comprovam concorrência.
- Operações offline precisam de escopo usuário/família, estado visível, backoff persistido e resolução de conflitos.
- Não habilite escrita offline até esses fluxos estarem validados.

## 5. P0: reconstruir o fluxo do Nex e corrigir Android

Todos os pontos de entrada devem chamar uma única função pública:

```
send_to_nex(message, context)
```

Contexto mínimo:

```
request_id
conversation_id
source
authenticated_user_scope
household_id
active_member_id
period
entity_type / entity_id, quando aplicável
snapshot_reference
```

O backend deve derivar e validar a identidade autenticada. IDs enviados pelo cliente não concedem autorização.

Fontes atendidas pela mesma função:

- botão Enviar;
- Enter/submit;
- perguntas sugeridas;
- Perguntar ao Nex;
- Simular com Nex;
- conversa sobre aquisição/meta;
- conversa sobre Trilha;
- diagnóstico de renda extra.

### Ciclo de requisição

```
idle → submitting → responding → success
                              ↘ error → retry
                              ↘ cancelled
```

Requisitos:

- feedback visual imediato;
- prevenção de double submit por operação;
- timeout e erro recuperável;
- retry preservando identidade e contexto;
- nenhuma exceção silenciosa;
- resposta associada à mensagem correta;
- troca de perfil/conta cancela ou descarta respostas de escopo antigo;
- navegação não duplica requisições;
- cancelamento ou timeout não pode aplicar uma mutação financeira posteriormente sem controle.

O Nex é somente leitura por padrão. Alterações financeiras e aplicação de cenários exigem confirmação com resumo concreto.

### Arquitetura

```
UI
→ Nex Orchestrator
→ Intent + contexto conversacional
→ Context Builder autorizado
→ ferramentas determinísticas / Financial Engine
→ Response Composer
→ UI
```

O Composer não recalcula valores independentemente.

Conversas devem aceitar continuidade e mudança de assunto:

- “Como está meu mês?”
- “E se eu gastar R$ 100?”
- “Agora quero falar da minha meta de viagem.”

Resolva referências quando inequívocas; pergunte quando houver ambiguidade real. Não mantenha o usuário preso a um questionário após mudança clara de assunto.

Se houver LLM:

- chamada somente por backend;
- segredo fora do cliente;
- ferramentas permitidas explicitamente;
- argumentos validados;
- autorização em cada ferramenta;
- contexto mínimo necessário;
- orçamento de custo e timeout;
- nenhuma execução de SQL/código arbitrário;
- conteúdo de notas, OCR e ofertas tratado como dado não confiável;
- fallback determinístico útil e claramente identificado.

Sem provedor configurado, preserve os fluxos suportados e explique limites. Não finja conversa generativa ilimitada.

### Android e teclado

Inspecione o comportamento real de layout, IME e foco na versão instalada. `SafeArea` não deve ser tratado como solução automática para qualquer sobreposição de teclado; confira seu comportamento e APIs compatíveis na [documentação do Flet](https://flet.dev/docs/controls/safearea/).

Implemente:

- composer sempre visível acima do teclado;
- uma única responsabilidade pelo ajuste de inset, evitando padding duplicado;
- bottom navigation sem competir com a área de digitação;
- campo multilinha com altura máxima;
- botão enviar com área de toque adequada;
- scroll até a nova mensagem quando o usuário estiver próximo do fim;
- indicador de mensagem nova quando estiver lendo conteúdo anterior;
- preservação do rascunho durante resize e navegação pertinente;
- retorno do Android fechando primeiro o teclado quando apropriado;
- comportamento coerente para teclado físico, submit e Shift+Enter.

Teste em Android real, teclado aberto/fechado, gestos e navegação por três botões, rotação, fontes ampliadas e rede instável.

**Aceite:** nenhuma mensagem disparada por qualquer entrada fica sem resposta, erro explícito ou cancelamento identificável; o usuário consegue ler o que digita e tocar em Enviar em todas as larguras-alvo.

## 6. Performance: medir antes e depois

Antes de otimizar, registre:

- hardware, sistema e build;
- modo debug/profile/release;
- dataset e número de registros;
- rede;
- cenário;
- número de repetições;
- p50/p95;
- memória e sinais de trabalho bloqueando a interface.

Investigue:

- `page.clean()` e reconstruções globais;
- consultas por componente;
- repetição de snapshots;
- I/O síncrono;
- decodificação de imagens;
- listeners/tasks sem descarte;
- polling;
- atualizações excessivas;
- listas sem paginação ou virtualização;
- gráficos fora de tela.

Não faça chamadas de rede por card. Compartilhe snapshots coerentes e invalide cache por alterações relevantes. Evite crescimento ilimitado de cache de telas e imagens.

### Orçamento inicial de engenharia

Estes números são **metas de aceitação propostas**, não medições do aplicativo:

| IndicadorWindowsAndroid intermediário                                  |         |         |
| ---------------------------------------------------------------------- | ------- | ------- |
| Feedback após toque, p95                                               | ≤100 ms | ≤100 ms |
| Navegação quente com dados em cache, p95                               | ≤200 ms | ≤300 ms |
| Primeiro conteúdo útil local, p95                                      | ≤2 s    | ≤3 s    |
| Resposta determinística local do Nex, p95                              | ≤500 ms | ≤700 ms |
| Frames dentro do orçamento de 60 Hz em navegação/scroll                | ≥95%    | ≥95%    |
| Crescimento sustentado após 30 ciclos de navegação, após estabilização | ≤10%    | ≤10%    |

Para rede/LLM, separe tempo de feedback, consulta e resposta. Meta inicial de timeout total: 20 segundos, configurável, com recuperação visível.

Para memória do mascote, use orçamento inicial de até 32 MiB de conteúdo decodificado ativo no Android, com cache limitado. Meça o custo real do renderer.

Se uma meta não for viável no hardware definido, documente o gargalo e proponha um ajuste fundamentado. Não flexibilize critérios silenciosamente.

Entregue comparação antes/depois com cenários idênticos. Não apresente redução estimada como medição.

## 7. Asset pipeline e comportamento do Nex

### Master canônico

Inventarie os assets: dimensões, alpha, bordas, enquadramento, licenças, tamanho e identidade.

Escolha ou produza um master que preserve a Character Bible:

- coruja roxa;
- rosto e peito claros;
- olhos grandes;
- óculos quando presentes no canônico;
- bico e pés consistentes;
- anatomia, proporções e paleta reconhecíveis.

Não aceite halos, checkerboard incorporado, recorte danificado ou simples ampliação de uma imagem pequena.

Mantenha:

- origem e versão do master;
- referências visuais;
- licença/direitos;
- canvas, pivô e escala padronizados;
- variantes hero/card/avatar;
- manifesto dos assets e hashes.

### Escolha do formato

Faça uma prova curta em Windows e Android antes de escolher:

| FormatoUso possívelRisco a verificar |                                         |                                                       |
| ------------------------------------ | --------------------------------------- | ----------------------------------------------------- |
| PNG/WebP estático com transformações | Base consistente e fallback             | Não representa expressões distintas sozinho           |
| Rive                                 | Estados e interação com rig apropriado  | Compatibilidade, autoria e custo de raster/texturas   |
| Lottie                               | Movimento vetorial e efeitos auxiliares | Não presumir que reproduz a aparência 3D canônica     |
| WebP animado                         | Sequências raster compactadas           | Controle de playback e suporte real do decoder        |
| Spritesheet/PNG sequence             | Poses renderizadas consistentes         | Memória decodificada, atlas e carregamento            |
| GIF                                  | Somente legado excepcional              | Qualidade, alpha e eficiência inadequados ao objetivo |

Não escolha Rive apenas por reputação, nem incorpore PNGs enormes em uma animação vetorial e chame isso de otimização.

Implemente estados coerentes: idle, happy, celebrate, thinking, warning, supportive, saving, planning, shopping, goal, learning, money, success e sleep. Estados semanticamente distintos precisam de comportamento perceptível; renomear a mesma imagem não conclui o requisito.

Centralize em um `NexController` ou equivalente:

- prioridade de estados;
- transição e duração;
- retorno ao idle;
- preempção;
- pausa fora de tela;
- descarte;
- redução de movimento;
- reutilização de recursos.

Animações decorativas podem usar 24–30 fps se visualmente adequadas; a interface continua perseguindo fluidez própria. Salto, pouso e moedas devem ser pontuais, sem bloquear ações.

Carregue recursos compartilhados uma vez por sessão quando viável; não compartilhe indevidamente a mesma instância de controle entre múltiplos pais.

**Aceite visual:** avaliar sobre fundos claro, escuro e contrastante, nas escalas reais, sem clipping, halos ou mudança de identidade.

## 8. Design system e revisão das telas

Crie tokens e componentes reutilizáveis:

- spacing em escala coerente, por exemplo 4/8/12/16/24/32;
- radius e elevação com poucos níveis;
- tipografia e hierarquia;
- superfícies;
- cores semânticas;
- ícones;
- botões e estados;
- inputs e validação;
- dialogs/sheets;
- navegação;
- estados vazio/loading/erro/sucesso.

Use roxo/azul como identidade. Verde indica sucesso, não domina a interface.

Microinterações de 150–250 ms, sem atrasar o início da operação. Respeite redução de movimento, contraste, foco visível, leitura por tecnologia assistiva e áreas de toque de aproximadamente 48 unidades lógicas.

Teste 360, 390, 412, 768, 1366 e 1920 px. Preserve também 430 px caso já exista na suíte. Inclua altura pequena e fonte ampliada.

### Home

A hierarquia deve mostrar:

1. situação financeira agora;
2. uma próxima ação;
3. compromissos próximos;
4. progresso;
5. poucos insights;
6. presença contextual do Nex.

Diferencie saldo familiar e responsabilidade individual. Exponha o significado e a origem dos valores por detalhes progressivos.

Não preencha espaços com gráficos sem finalidade.

### Análises

Estruture “o que aconteceu → por quê → o que fazer”.

- comparação com período equivalente;
- categorias que explicam mudanças;
- eventos excepcionais;
- previsão com premissas;
- alertas acionáveis;
- alocação editável;
- acesso ao Nex com contexto correto.

Não compare mês incompleto com mês completo sem avisar. Não use variação percentual quando a base é zero ou inadequada.

### Aquisições

Cada item mostra nome, prioridade, preço, reservado, restante, progresso, impacto e CTA contextual.

Identifique modelo/variante antes de associar imagem ou oferta. Sem correspondência confiável, use placeholder por categoria. Não faça busca automática de imagens inadequadas para conteúdo sensível.

A recomendação de compra usa o orçamento, os compromissos e as reservas. A presença de afiliado não muda o resultado.

### Planejamento

Completar criar, editar, excluir, pausar, retomar, aportar e simular.

Cenários:

- manter prazo: calcular aporte necessário;
- reduzir aporte: calcular novo prazo;
- alongar prazo: calcular novo aporte;
- renda extra: mostrar contribuição hipotética, sem contar como renda recebida.

Mostrar impacto sobre outras metas e fluxo futuro. Datas vencidas, aporte zero e renda desconhecida precisam de tratamento explícito.

Aplicar cenário somente após confirmação, validando novamente a versão dos dados.

### Mercado

Fluxo:

```
captura/galeria → preview → extração disponível → conferência
→ correções → comparação → confirmação → persistência
```

- câmera com lifecycle e permissão corretos;
- múltiplas imagens, remover/refazer e limite de memória;
- limpeza de arquivos temporários;
- CRUD de itens e compras encerradas;
- total calculado em centavos;
- cashback separado;
- vínculo financeiro explícito para evitar duplicidade.

Sem OCR validado, ofereça conferência manual e informe que não houve extração. Não use “escaneado” para um fluxo que apenas anexou a foto.

### Renda extra e Trilhas Nex

O diagnóstico deve cobrir **oito dimensões**: tempo, capital, habilidades, online/presencial, equipamentos, prazo, objetivo mensal e tolerância a risco. Esta versão substitui referências antigas a sete perguntas.

Não obrigue o usuário a responder tudo de uma vez. Permita pular, editar e retomar.

Sugira até três rotas com justificativa, investimento hipotético, riscos, primeiro experimento e critérios para continuar. Não prometer renda.

Trilha de dez etapas:

1. escolher atividade;
2. avaliar situação;
3. aprender;
4. calcular custos;
5. definir preço;
6. buscar primeiros clientes;
7. registrar venda;
8. registrar lucro;
9. revisar resultado;
10. decidir se amplia.

Persistir tarefas, notas, prazo, status, custos previstos/reais, receita, lucro e próxima ação. Permitir corrigir e desmarcar conclusão.

Receita/lucro devem derivar de registros vinculados ou ser identificados como anotações não contabilizadas. Não lançar tudo novamente ao concluir uma etapa.

Lembretes opt-in, com pausa, soneca e horário. Diferenciar lembrete local com aplicativo aberto de notificação realmente agendada pelo sistema.

Concentrar materiais externos em “Vídeos para se aprofundar”, com fonte, assunto e link verificado.

### Matriz de experiência por tela

| TelaDesktopMobileNexVazioLoadingErro |                                   |                             |                              |                             |                                |                               |
| ------------------------------------ | --------------------------------- | --------------------------- | ---------------------------- | --------------------------- | ------------------------------ | ----------------------------- |
| Onboarding/acesso                    | Fluxo curto e legível             | Teclado e campos visíveis   | Apresenta valor sem bloquear | Convite a primeiro registro | Estado da autenticação         | Recuperação sem perder campos |
| Home                                 | Hierarquia com densidade moderada | Resumo vertical             | Uma orientação relevante     | Primeiro passo útil         | Snapshot anterior identificado | Sem falso saldo zero          |
| Transações                           | Filtros e edição eficientes       | Cards/lista e sheets        | Explica impacto              | Criar lançamento            | Paginação/estado local         | Preservar formulário          |
| Nex                                  | Histórico e composer estáveis     | IME, foco e scroll corretos | Conversa central             | Sugestões funcionais        | Pedido identificado            | Retry/cancelamento            |
| Análises                             | Comparações legíveis              | Uma pergunta por seção      | Explica mudanças             | Dados insuficientes         | Conteúdo progressivo           | Indicar consulta afetada      |
| Aquisições                           | Lista visual comparável           | Cards verticais             | Avalia orçamento             | Criar desejo/meta           | Placeholder correto            | Sem oferta inventada          |
| Planejamento                         | Cenários comparáveis              | Cenários empilhados         | Simulação numérica           | Criar meta                  | Dados-base visíveis            | Não aplicar cenário inválido  |
| Mercado                              | Edição rápida                     | Câmera e toque              | Ajuda na conferência         | Iniciar compra              | Progresso da extração          | Correção manual               |
| Renda extra/Trilhas                  | Etapas e resultados               | Próxima tarefa em destaque  | Orienta e acompanha          | Diagnóstico opcional        | Retomar estado salvo           | Não perder notas              |
| Oportunidades                        | Comparação transparente           | Ofertas secundárias         | Independente de comissão     | Recomendação sem afiliado   | Sem bloquear finanças          | Remover oferta inválida       |
| Configurações/privacidade            | Controles agrupados               | Ações acessíveis            | Explicações opcionais        | Estado explícito            | Exportação/exclusão rastreável | Resultado verificável         |

## 9. Monetização gratuita: decisão e arquitetura

### Base pesquisada para esta especificação

Afiliados podem remunerar compras ou ações qualificadas; a ocorrência de um clique não comprova comissão. A Amazon também exige aprovação específica para aplicativos móveis e impõe restrições a software instalado. Portanto, não presuma que um link permitido em um site possa ser usado no aplicativo Windows. Verifique elegibilidade por plataforma. [Amazon: compras qualificadas](https://associados.amazon.com.br/help/node/topic/GWJ4AHCH7U5LCL86), [aplicativos móveis](https://associados.amazon.com.br/help/node/topic/GQZMCDD9PB7CXV7N), [políticas](https://associados.amazon.com.br/help/operating/policies).

CPA/CPL são formas de remuneração, não necessariamente canais independentes. Compare-as sem somar a mesma receita duas vezes. A Awin descreve comissão por transação e por lead qualificado. [Awin](https://www.awin.com/br/faq).

Cashback envolve regras de elegibilidade e confirmação; o Méliuz descreve um modelo em que divide com o usuário valores recebidos das lojas. Isso demonstra o mecanismo, não a disponibilidade de uma integração para o NexGrana. [Méliuz](https://www.meliuz.com.br/como-funciona).

Publicidade depende de impressões e eCPM, entre outros fatores, e estimativas não são receita garantida. Anúncios e SDKs continuam sujeitos às políticas do aplicativo e da loja. [AdMob](https://support.google.com/admob/answer/6168758?hl=en), [Google Play: anúncios](https://support.google.com/googleplay/android-developer/answer/9857753?hl=en-GB).

Parcerias corporativas com aplicativos de bem-estar existem, mas isso não comprova demanda ou contratação do NexGrana. [Wellhub: parceiros](https://wellhub.com/en-us/partners/).

### Avaliação estratégica

Classificações abaixo são julgamentos relativos para este produto, não previsões de faturamento.

| ModeloPotencialFacilidadeEscala necessáriaRisco UXConfiançaComplexidade de dados/LGPDDecisão |                                             |                   |                               |                     |                                   |                           |                                                    |
| -------------------------------------------------------------------------------------------- | ------------------------------------------- | ----------------- | ----------------------------- | ------------------- | --------------------------------- | ------------------------- | -------------------------------------------------- |
| Afiliados por venda                                                                          | Médio, depende de intenção                  | Média             | Média                         | Baixo se contextual | Médio                             | Média                     | Implementar camada mínima; ativar só com aprovação |
| Publicidade tradicional                                                                      | Incerto em pequena base                     | Média             | Alta                          | Alto                | Alto                              | Alta com SDK/rastreamento | Testar futuramente; sem SDK nesta release          |
| Comparador                                                                                   | Médio; monetiza indiretamente               | Baixa             | Média                         | Baixo               | Médio por preços incorretos       | Média                     | Preparar arquitetura                               |
| Cashback próprio                                                                             | Incerto                                     | Baixa             | Média/alta                    | Médio               | Alto por expectativa de pagamento | Alta                      | Adiar operação; manter modelo de estados           |
| CPA de ação não financeira                                                                   | Médio e contratual                          | Média             | Média                         | Médio               | Médio                             | Média                     | Preparar arquitetura                               |
| CPL                                                                                          | Potencial maior por ação, incerto           | Baixa/média       | Média                         | Médio               | Alto                              | Alta                      | Testar depois, só por solicitação consciente       |
| Marketplace próprio                                                                          | Potencial de longo prazo                    | Baixa             | Alta                          | Médio/alto          | Alto                              | Alta                      | Fora desta atualização                             |
| Parcerias diretas                                                                            | Médio e contratual                          | Média             | Nicho engajado                | Baixo/médio         | Médio                             | Média                     | Preparar catálogo e identificação                  |
| Conteúdo patrocinado                                                                         | Médio e contratual                          | Alta tecnicamente | Nicho engajado                | Baixo se útil       | Médio                             | Baixa/média sem tracking  | Piloto futuro                                      |
| B2B                                                                                          | Potencial contratual; ciclo comercial longo | Baixa             | Poucos contratos podem bastar | Baixo no consumer   | Alto se expuser funcionário       | Alta                      | Validar comercialmente antes de construir          |

Descartar: venda de dados, publicidade coercitiva, ofertas disfarçadas de orientação, rewarded ads para liberar função essencial e leads de crédito baseados em vulnerabilidade financeira.

### Central de Oportunidades

Implementar uma camada secundária, sem ocupar a Home por padrão:

```
necessidade solicitada
→ recomendação independente
→ ofertas elegíveis
→ comparação
→ resolução de afiliado
→ identificação comercial
→ saída para parceiro
```

Criar contratos pequenos para `Recommendation`, `Offer`, `OfferSource`, `AffiliateProvider`, `AffiliateLink`, `SponsoredContent` e `ClickEvent`.

A camada de ranking não recebe comissão como atributo decisório. Teste que alterar comissão mantendo os demais dados não muda a recomendação.

Cada oferta deve ter:

- identificação correta do produto/variante;
- fonte;
- preço e moeda;
- frete conhecido ou “não informado”;
- disponibilidade;
- instante de consulta e validade;
- plataforma elegível;
- URL validada;
- identificação comercial;
- origem/posição/campanha, quando aplicável.

Não afirmar “menor preço” sem cobertura demonstrável. Não inventar preço nem usar scraping sem verificar permissões e termos.

URLs externas: HTTPS, domínio permitido, sem credenciais, sem parâmetros financeiros, sem open redirect. Verificar também redirecionamentos relevantes.

Não pesquisar parceiros automaticamente com texto financeiro ou título sensível de uma meta. Consulta externa deve partir de intenção consciente e transmitir somente o necessário.

Use “O NexGrana pode receber comissão por este link”. Acrescente “sem aumentar o preço” apenas quando essa condição puder ser sustentada.

Ofertas devem ser ocultáveis. A falta de afiliado nunca remove uma recomendação útil.

## 10. Instrumentação, retenção e sustentabilidade

Implemente um adaptador de analytics desacoplado, com payload permitido por schema. Sem provedor/base legal definidos, mantenha envio remoto desativado e valide os eventos localmente.

Nunca incluir valores, saldos, descrições, títulos de metas, texto do chat, fotos, e-mail, tokens ou IDs internos familiares nos eventos comerciais.

Eventos mínimos:

| EventoFinalidadeDados permitidos |                |                                       |
| -------------------------------- | -------------- | ------------------------------------- |
| onboarding\_completed            | Ativação       | Versão, plataforma, variante          |
| useful\_action\_completed        | Valor entregue | Tipo categórico da ação, sucesso      |
| nex\_request\_completed          | Confiabilidade | Origem, resultado, faixa de latência  |
| goal\_milestone\_reached         | Progresso      | Tipo de marco, sem valor/nome         |
| journey\_step\_completed         | Continuidade   | Etapa padronizada                     |
| offer\_impression                | Exposição real | Oferta pública, posição, campanha     |
| offer\_clicked                   | Interesse      | Oferta pública, origem, campanha      |
| offer\_hidden                    | Rejeição       | Categoria genérica do motivo          |
| reminder\_preference\_changed    | Controle       | Habilitado/pausado                    |
| app\_error                       | Qualidade      | Código sanitizado, versão, plataforma |

Não envie nomes de arquivo, URLs livres ou exceções brutas.

Defina impressão como visibilidade efetiva por tempo mínimo, com deduplicação; não conte rebuild como nova impressão.

Retenção exige identificação longitudinal: não a chame de anônima se usar pseudônimo persistente. Defina consentimento/base aplicável, expiração e exclusão. Não rastreie quem recusou analytics opcional.

Métricas:

- ativação: primeiro registro válido seguido de visualização de resultado útil;
- D1/D7/D30: retorno com ação útil em coorte e calendário definidos;
- DAU/MAU e ações úteis por sessão;
- conclusão de metas/trilhas;
- sucesso e utilidade percebida do Nex;
- ocultação de ofertas;
- CTR por impressão válida;
- conversão somente quando confirmada pelo parceiro;
- receita confirmada por usuário ativo.

Modelo econômico, sem inventar números:

```
receita afiliada = conversões aprovadas × comissão líquida média
receita publicitária = impressões monetizadas / 1.000 × eCPM realizado
ARPA mensal = receita confirmada do mês / usuários ativos definidos
receita por 1.000 ativos = ARPA × 1.000
```

Calcule LTV por coorte usando margem de contribuição e retenção observada. Inclua custos de IA, infraestrutura, suporte, estornos e aquisição. Não extrapole LTV confiável de poucos dias.

Não otimize CTR isoladamente. Adote guardrails de sucesso das tarefas, retenção, reclamações, latência e ocultação. Experimentos comerciais devem ser reversíveis, consentidos quando necessário e ter limiar de parada definido antes do início.

## 11. Segurança, privacidade e threat model

Trate dados financeiros como informação pessoal de alto risco. Não confunda essa classificação de engenharia com a definição legal específica de “dado pessoal sensível”. Use a [LGPD](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm) e orientações aplicáveis da [ANPD](https://www.gov.br/anpd/pt-br/assuntos/noticias-periodo-eleitoral/anpd-lanca-guia-orientativo-201ccookies-e-protecao-de-dados-pessoais201d); consentimento não substitui a identificação correta de finalidade e base legal.

| AmeaçaControleEvidência exigida    |                                                |                                                         |
| ---------------------------------- | ---------------------------------------------- | ------------------------------------------------------- |
| Acesso de família A aos dados de B | RLS e autorização em RPC/API                   | SELECT/INSERT/UPDATE/DELETE/RPC negativos               |
| Escalada por membro/placeholder    | Regras de vínculo e papel no servidor          | Testes de promoção e apropriação                        |
| Vazamento por cache/troca de conta | Cofre e escopo; limpeza/cancelamento           | Teste A→logout→B e resposta tardia                      |
| Duplicação ou sobrescrita          | Idempotência, transação e versão               | Retry, duas conexões e conflito                         |
| Segredo no cliente/log             | Segredos no backend e sanitização              | Varredura do fonte, build e logs                        |
| Prompt injection via OCR/oferta    | Dados separados de instruções; tools restritas | Conteúdo adversarial sem efeito                         |
| URL/arquivo malicioso              | Validação, limites e parser seguro             | Casos de redirect, arquivo excessivo e formato inválido |
| Backup/migration destrutiva        | Pré-validação, backup e recuperação            | Restore ensaiado e integridade                          |
| SDK comercial excessivo            | Minimização e controle de envio                | Inspeção de tráfego e payloads                          |

Checklist obrigatório:

- inventário de dados e destinos;
- armazenamento seguro de sessão;
- renovação/logout sem corrida;
- expiração e revogação;
- política versionada com controlador e contato;
- finalidades e retenção por categoria;
- exportação com escopo autorizado;
- correção de dados;
- exclusão de conta com reautenticação e confirmação;
- tratamento explícito de dados compartilhados ao excluir um integrante;
- consentimentos opcionais separados e revogáveis;
- fotos e arquivos temporários eliminados;
- backups protegidos;
- logs e crash reports sanitizados;
- declaração de dados da loja coerente com o comportamento;
- nenhuma alegação genérica de “100% conforme à LGPD”.

Privacidade é funcionalidade implementada, não apenas texto de política.

## 12. Migrations e rollback

Use migrations versionadas e registre versão aplicada. Não reescreva migrations já publicadas sem entender o estado instalado.

Plano obrigatório:

1. inventário de versões existentes;
2. backup e ensaio de restauração;
3. migração aditiva;
4. backfill determinístico, quando seguro;
5. validação de contagens, somas, vínculos e permissões;
6. compatibilidade entre cliente antigo e novo durante transição;
7. ativação gradual do novo comportamento;
8. remoção de estruturas antigas somente em versão futura justificada.

Datas desconhecidas continuam desconhecidas. Não criar datas financeiras históricas por conveniência.

Teste banco vazio, upgrade do ZIP anterior, reexecução pertinente, interrupção, falha parcial, registros legados inconsistentes e volume representativo.

Rollback:

- aplicativo: artefato anterior identificado e flags reversíveis;
- schema aditivo: desativar novo caminho sem apagar dados;
- migração destrutiva inevitável: procedimento específico e aprovação;
- restaurar backup pode descartar gravações posteriores; documentar reconciliação e janela de manutenção;
- preferir correção progressiva quando downgrade perder informação.

Nunca usar “recriar banco” como procedimento padrão.

## 13. Matrizes obrigatórias de execução

### A. Diagnóstico e aceite

As causas abaixo são hipóteses até haver reprodução.

| ProblemaCausa provávelArquivo/componente candidatoCorreção esperadaTesteCritério de aceite |                                                       |                            |                                          |                                |                                   |
| ------------------------------------------------------------------------------------------ | ----------------------------------------------------- | -------------------------- | ---------------------------------------- | ------------------------------ | --------------------------------- |
| Chat Android sem envio                                                                     | Handlers divergentes, foco/IME, callback incompatível | `screens/nex.py`, shell    | Pipeline único e composer adaptativo     | Dispositivo, todas as entradas | Uma resposta/erro por solicitação |
| Tela vazia ao navegar                                                                      | Desmontagem global e I/O acoplado                     | `main.py`, render          | Preservação de estado e carga assíncrona | Perfil de navegação            | Sem tela vazia intermediária      |
| Lentidão                                                                                   | Consultas repetidas, decode, polling                  | Cloud, Home, NexController | Snapshot/cache e lifecycle               | Antes/depois                   | Orçamento de performance          |
| Saldo contraditório                                                                        | Cálculos ou períodos diferentes                       | Financial Engine/telas     | Fonte única com semântica                | Fixtures mensais e familiares  | Reconciliação exata               |
| Retry altera/duplica dados                                                                 | IDs efêmeros ou operação parcial                      | RPC/fila                   | Idempotência e transação                 | Concorrência/falha de rede     | Efeito financeiro único           |
| Meta sobrescreve aporte                                                                    | Read-modify-write sem versão                          | Planejamento/RPC           | Controle concorrente                     | Duas conexões                  | Sem lost update                   |
| Nex degradado                                                                              | Master insuficiente/escala/alpha                      | Assets/controlador         | Pipeline canônico                        | Visual e memória               | Identidade consistente            |
| Nota salva errada                                                                          | Falta de revisão/versão do carrinho                   | Mercado/RPC                | Preview e confirmação atômica            | Carrinho muda durante revisão  | Conflito explícito                |
| Trilha perde estado                                                                        | Persistência incompleta/escopo errado                 | Trilhas/Cloud              | Modelo persistente correto               | Reinício e troca de perfil     | Retomada exata                    |
| Oferta enviesada                                                                           | Comissão misturada ao ranking                         | Recommendation/Affiliate   | Separação arquitetural                   | Alterar comissão               | Ranking financeiro invariável     |

Preencha a causa confirmada e caminhos/linhas reais durante a implementação.

### B. Rastreabilidade de requisitos

Mantenha esta matriz atualizada para **todos os IDs**, sem marcar “testado” por inspeção de código:

| RequisitoImplementadoTestadoEvidênciaPendência |                 |                       |                        |                       |
| ---------------------------------------------- | --------------- | --------------------- | ---------------------- | --------------------- |
| FIN-01 — caixa e rateio                        | Sim/parcial/não | Tipo e resultado      | Arquivo do teste/log   | Limitação concreta    |
| NEX-01 — envio único Android                   | Sim/parcial/não | Dispositivo e cenário | Vídeo/log sanitizado   | Caso não coberto      |
| PERF-01 — navegação                            | Sim/parcial/não | Hardware e p95        | Relatório antes/depois | Meta não atingida     |
| ASSET-01 — master/estados                      | Sim/parcial/não | Visual/runtime        | Manifesto/capturas     | Asset ausente         |
| PRIV-01 — isolamento/exclusão                  | Sim/parcial/não | RLS/E2E               | Testes e resultados    | Dependência           |
| MIG-01 — upgrade/restore                       | Sim/parcial/não | Versões de origem     | Logs de migração       | Restrição             |
| MON-01 — afiliado independente                 | Sim/parcial/não | Ranking e URL         | Testes                 | Aprovação do parceiro |

Expanda para as demais telas e fluxos. Cada requisito precisa de evidência ou pendência explícita.

## 14. Testes, aprovação e entrega

Execute:

- compileall;
- análise estática pertinente;
- unitários financeiros;
- integração entre UI, orquestrador e serviços;
- RLS/RPC sob identidades distintas;
- testes concorrentes;
- migrations e restauração;
- offline/reconexão;
- permissões negadas;
- formulários e ações;
- responsividade e acessibilidade;
- Android com teclado/câmera;
- Windows smoke;
- performance;
- integridade do pacote.

Fixtures mínimas: individual, casal, família, leitor, membro, owner, placeholder, duas famílias, ausência de dados, 24 meses de histórico, parcelas, datas desconhecidas, atraso pago em mês posterior, reserva, metas simultâneas e duplicação de resposta de rede.

Não apresente relatório agregado que esconda testes pulados.

### Checklist de release

- Nenhum P0/P1 conhecido sem resolução.
- Nenhum botão morto ou sucesso sem persistência confirmada.
- Cálculos reconciliados entre telas e Nex.
- Chat Android utilizável com teclado aberto.
- Estado preservado em navegação, erro e retry.
- Nenhuma imagem quebrada ou degradada aceita silenciosamente.
- Sem vazamento, clipping ou conteúdo atrás da navegação.
- Perfil ativo não altera identidade autenticada.
- Upgrade e recuperação ensaiados.
- Segredos, sessões, dados reais e caches excluídos do ZIP.
- Dependências e licenças inventariadas.
- Windows/APK construídos quando possível e testados separadamente.
- Logs, matriz de requisitos e limitações entregues.
- ZIP extraído e conferido, com manifesto e SHA256.

### Aprovação humana

Continue autonomamente em refatorações, correções, testes isolados e decisões reversíveis.

Prepare resultados concretos antes de solicitar aprovação para:

- aplicar migration no banco de produção;
- executar alteração destrutiva inevitável;
- publicar em loja ou distribuir release pública;
- contratar serviços ou gerar custos externos;
- ativar coleta comercial/analytics remoto;
- aceitar termos ou ativar provedores afiliados;
- finalizar mudanças substanciais na identidade canônica;
- aprovar política jurídica e modelo de retenção.

Não peça aprovação novamente para algo já autorizado claramente na sessão.

### Entregáveis

Entregue:

1. ZIP completo do código atualizado.
2. Binários Windows/APK quando o ambiente permitir, identificando assinatura e finalidade de teste.
3. README de instalação, execução, build e atualização.
4. Changelog de comportamento, sem inflar o resultado.
5. Migrations e roteiro de rollback/restauração.
6. Relatório financeiro e de segurança.
7. Relatório de performance antes/depois.
8. Manifesto de assets e dependências.
9. Matrizes de diagnóstico, telas e rastreabilidade.
10. Lista explícita do que não pôde ser validado, por quê e como validar.
11. Checkpoint de continuidade caso exista bloqueio externo.

Se o build falhar, registre comando, ambiente, erro e investigação. Entregue o fonte utilizável e os logs, mas não chame o pacote de release pronta.

Se faltar Android real, declare a validação móvel pendente e trate a entrega como candidata a testes. Não atribua ao ambiente pendências que ainda são implementação incompleta.

**Execute até concluir o escopo autorizado ou encontrar um bloqueio externo comprovado. A medida de sucesso é um NexGrana mais confiável, rápido, claro e útil, com identidade própria e monetização subordinada ao interesse do usuário.**

14:49