# PROMPT MESTRE — GPT-6 ASTRA — NEXGRANA “CÓDIGO DA VIRADA”

Você receberá um ZIP de um aplicativo chamado **NexGrana**, atualmente em Flet/Python com Supabase. Sua tarefa é agir como **engenheiro principal + arquiteto de software + product designer + especialista em segurança e privacidade + QA lead** e devolver um novo ZIP funcional, preservando os dados existentes e aproximando o app ao máximo de um produto público final.

## REGRA 0 — NÃO FAÇA UMA MAQUIAGEM SUPERFICIAL
Não quero apenas trocar cores, nomes ou espaçamentos. Quero uma transformação coerente de produto, arquitetura, UX, lógica financeira, mascote, responsividade e segurança.

Inspecione **todos os arquivos do ZIP** antes de alterar qualquer coisa. Leia o código inteiro, SQL, assets, README, Character Bible, scripts de build e histórico de patches. Faça um inventário do que existe, o que está duplicado, o que é inseguro, o que está obsoleto e o que pode quebrar.

Não peça confirmação para decisões óbvias. Se algo puder ser resolvido com análise do código e requisitos abaixo, resolva.

Ao final, entregue:
1. ZIP completo executável.
2. Changelog detalhado.
3. Migration SQL idempotente.
4. Relatório de segurança/LGPD.
5. Relatório de testes executados.
6. Comandos exatos para Windows e Android.
7. Lista curta de pendências reais que ainda dependam de serviço externo/chave/API.

---

# 1. IDENTIDADE DO PRODUTO

Nome oficial: **NexGrana**.
Slogan principal: **“Sua grana. Seu próximo nível.”**
Mascote oficial: **Nex**.

O NexGrana NÃO é “um dashboard financeiro com mascote”.
É **um aplicativo financeiro pessoal/familiar cujo mascote transforma dados em decisões e acompanha o usuário no dia a dia**.

A experiência deve ser:
- premium, jovem e confiável;
- simples o suficiente para quem nunca teve educação financeira;
- útil para adolescentes/adultos jovens e público até ~40 anos;
- viva, interativa e agradável de abrir todos os dias;
- sem tom infantil;
- sem promessas de enriquecimento;
- sem julgamentos sobre a situação financeira do usuário.

---

# 2. NEX — CHARACTER BIBLE É IMUTÁVEL

Leia `NEX_CHARACTER_BIBLE.md` e trate como contrato visual.

Nex:
- coruja cartoon 3D;
- penas roxas;
- rosto/peito claros;
- olhos grandes castanho/alaranjados;
- óculos grandes;
- bico e pés laranja;
- mesma anatomia, rosto, proporções e identidade em todas as telas.

Pode mudar:
- expressão;
- pose;
- roupa/skin;
- acessórios;
- contexto.

Não pode mudar:
- espécie;
- anatomia;
- rosto;
- assinatura de cores;
- silhueta reconhecível.

## 2.1 Assets e animações
Os assets antigos estão visualmente ruins/pixelados em alguns estados. Não amplie sprites de baixa resolução.

Crie uma camada de assets profissional:
- fundo verdadeiramente transparente;
- sem checkerboard embutido;
- sem halo serrilhado;
- enquadramento consistente;
- versões específicas para hero, card e avatar;
- assets em alta resolução reduzidos para o tamanho final;
- nunca aumentar asset pequeno.

Preferência técnica para personagem vivo: **Rive/state machine** ou solução equivalente suportada de forma estável por Flet/Flutter. Se Rive não puder ser integrado sem quebrar o build, use animações 2D/3D pré-renderizadas em alta qualidade, mas com interface de estado centralizada para futura migração.

Estados mínimos:
- idle/respiração;
- piscando;
- olhando para lados;
- pensando/calculando;
- atento;
- preocupado sem julgar;
- tranquilo;
- comemorando;
- jogando moedas;
- pulando/pousando no galho;
- dormindo/ocioso;
- escaneando nota;
- estudando/Trilha Nex.

O Nex deve parecer **solto dentro da UI**, não uma imagem quadrada colada no card.

No desktop, criar um **Nex Dock** discreto e vivo na lateral. No mobile, usar o Nex em pontos de alto valor, sem roubar espaço útil.

---

# 3. PERSONALIDADE DO NEX

Nex é:
- inteligente;
- atencioso;
- direto;
- curioso;
- levemente engraçado;
- nunca moralista;
- nunca humilha o usuário;
- sério em dívida, risco, crédito e decisões importantes.

Exemplos de tom:
- conversa casual: humor leve;
- meta concluída: comemorar;
- orçamento apertado: “eu seguraria essa compra” em vez de bronca;
- dado ausente: dizer que não encontrou, nunca inventar.

Se o usuário disser “bom dia”, “boa noite”, “tudo bem?”, o Nex conversa normalmente.
Se o usuário mudar de assunto, o Nex acompanha.
Se a pergunta financeira usar números, os números devem vir de ferramentas determinísticas/dados reais.

---

# 4. NEX CONVERSATION ENGINE — UM ÚNICO PIPELINE

Hoje existem múltiplas entradas de conversa e algumas quebram, especialmente no Android.

Crie **um único motor de conversa** usado por:
- texto digitado;
- Enter;
- seta Enviar;
- sugestões rápidas;
- “Perguntar ao Nex” em Aquisições;
- “Simular com Nex” em Planejamento;
- “Me ajude a escolher” em Renda Extra;
- “Conversar com Nex sobre esta trilha”;
- cards da Home;
- alertas/análises.

Contrato:
`UI action -> context payload -> Nex engine -> deterministic tools -> response -> conversation state -> UI update`

Nenhum botão pode apenas inserir texto no histórico.
A ação só é concluída quando existe resposta ou erro visível.

## 4.1 LLM
Para versão realmente conversacional, desenhe arquitetura de LLM com backend seguro.

Regras:
- chave do LLM NUNCA no APK/EXE;
- backend server-side/edge function;
- prompt do Nex server-side;
- dados financeiros acessados por ferramentas autorizadas;
- LLM não calcula saldo “na cabeça” quando existe função determinística;
- respostas com números devem ter fonte interna/resultado da tool;
- timeout/fallback;
- rate limiting;
- proteção contra prompt injection;
- não enviar mais dados do que o necessário;
- logs sem conteúdo financeiro sensível por padrão.

Se a chave/backend não estiver disponível, mantenha fallback local funcional e honesto; não finja que é LLM completo.

---

# 5. RESPONSIVIDADE REAL

O app deve ser mobile-first e funcionar também em notebook/desktop.

Testar no mínimo:
- 360 px;
- 390 px;
- 430 px;
- 768 px;
- 1366 px;
- 1920 px.

Nada pode sair da tela.
O seletor de mês/perfil deve sempre ficar acessível.

Regras:
- mobile: navegação inferior, toque com uma mão, cards empilhados;
- desktop: sidebar e uso inteligente de largura;
- tablet/compact: composição intermediária;
- não esticar layout mobile no desktop;
- não espremer desktop no mobile;
- evitar larguras fixas desnecessárias;
- preferir `ResponsiveRow`, `expand`, breakpoints e layout adaptativo.

---

# 6. HOME / INÍCIO — APP, NÃO EXCEL

A Home atual ainda parece dashboard/BI.

A nova Home deve responder em segundos:
1. Como estou hoje?
2. O que mudou?
3. O que merece atenção?
4. O que faço agora?

Estrutura sugerida:
- saudação da família/perfil ativo;
- saldo disponível da família;
- próxima conta;
- saldo projetado após compromissos;
- saldo por pessoa;
- “Nex diz” contextual;
- 1–3 insights prioritários;
- CTA claro para ação.

Gráficos detalhados ficam em Análises; Home só mostra visual quando houver decisão útil associada.

Separar claramente:
- saldo da família;
- saldo individual;
- receitas;
- despesas pagas;
- despesas futuras;
- saldo projetado.

Nunca somar/duplicar rateio do casal incorretamente.

---

# 7. FLUXO DE CAIXA E DATAS

Regra crítica:
- saldo não zera na virada do mês;
- saldo final de agosto vira saldo inicial de setembro;
- despesa futura não reduz saldo atual antes de pagamento/data efetiva;
- pagamento manual deve permitir confirmação;
- débito automático pode seguir regra configurada;
- status: agendada, paga, atrasada, cancelada;
- renda também precisa de data real de recebimento, não apenas mês.

Exemplo:
31/08 saldo R$100 -> 01/09 saldo R$100.
Conta R$714 em 07/09 -> em 03/09 aparece como compromisso futuro, não saldo -714.

---

# 8. PERFIS/FAMÍLIA

Conta pode ser familiar.
Criar experiência de perfil ativo:
- Mafra;
- Karol;
- outros membros.

O perfil ativo personaliza:
- saudação;
- novos registros;
- recomendações;
- conversa.

Mas os dados familiares continuam compartilhados conforme permissões.

Home deve explicar saldo por pessoa e saldo familiar sem dupla contagem.

---

# 9. AQUISIÇÕES — JORNADA DE COMPRA

Não usar cards de painel administrativo.

Cada aquisição deve ter:
- imagem/ícone coerente;
- nome;
- dono;
- prioridade;
- valor/meta;
- quanto já guardou;
- progresso;
- status;
- ações principais;
- menu para editar/excluir.

## 9.1 Imagens
Se houver imagem automática de internet:
- usar fonte/provedor confiável/licenciado;
- correspondência semântica mínima;
- se confiança baixa: ícone neutro;
- nunca mostrar imagem aleatória;
- bloquear conteúdo sexual explícito/adulto e categorias proibidas;
- melhor sem imagem que imagem errada.

## 9.2 Nex recomenda agora
Recomendação deve considerar:
- saldo real;
- despesas futuras;
- margem mensal;
- metas;
- prioridade;
- valor;
- reserva mínima;
- parcelas existentes.

Se nada couber, Nex deve dizer para esperar.

Perguntas como “qual aquisição de uns R$50 posso comprar?” devem filtrar por faixa de preço; não escolher PS5 só por prioridade.

---

# 10. PLANEJAMENTO 2.0

Metas precisam ser editáveis:
- nome;
- valor;
- prazo;
- estratégia;
- responsável;
- status/pausa.

Card deve mostrar jornada e progresso.

## Simular com Nex
Esse botão precisa produzir cenários numéricos reais:
- manter prazo;
- +1 mês;
- +2 meses;
- entrada/aporte agora;
- impacto de outras contas/metas;
- margem do mês;
- saldo projetado.

Mostrar recomendação explicada e deixar claro que é simulação.

Conectar:
`Aquisição -> Planejamento -> Aportes -> Compra -> Conquista`.

---

# 11. MERCADO

Mercado deve permitir CRUD completo:
- editar/excluir compra;
- editar/excluir produto;
- quantidade/preço/categoria;
- recálculo imediato.

## 11.1 Conferir nota
No Android:
- câmera real;
- galeria;
- múltiplas fotos;
- miniaturas;
- opção futura QR Code NFC-e;
- OCR/visão só pode sugerir leitura;
- usuário confirma antes de alterar dados;
- não inventar itens/valores.

Fluxo final:
`capturar -> extrair -> prévia -> comparar -> divergências -> confirmação`.

## 11.2 Cashback
Explicar claramente:
- cashback é valor recebido depois;
- não muda total fiscal da nota;
- registrar apenas valor efetivamente recebido.

---

# 12. ANÁLISES — DIRECIONAR O DINHEIRO

A tela atual está crua.
Transformar em diagnóstico mensal vivo.

Mostrar:
- saúde financeira com explicação;
- fluxo “entrou -> saiu -> ficou disponível”;
- mudanças vs mês anterior;
- principais riscos;
- oportunidades de economia;
- impacto de parcelas futuras;
- metas em risco;
- sugestão de alocação editável.

Exemplo:
“Nex faria isso com sua margem”: Reserva, Metas, Lazer, Manter livre.

Não mover dinheiro automaticamente.
Cada insight deve oferecer ação:
- resolver;
- simular;
- falar com Nex.

---

# 13. RENDA EXTRA E TRILHA NEX

Renda Extra não é lista de artigos.

## 13.1 Me ajude a escolher
Fluxo guiado, uma pergunta por vez:
- horas/semana;
- investimento inicial;
- online/presencial;
- habilidades;
- equipamentos;
- objetivo de renda;
- prazo.

Entregar 3 caminhos com justificativa, sem promessa de ganho.

## 13.2 Trilha Nex
Transformar em sistema transversal de jornada.

Trilha:
- diagnóstico;
- etapas;
- missões;
- checklist;
- progresso persistente;
- lembretes;
- reagendamento;
- histórico;
- métricas reais;
- conquistas;
- Nex contextual.

Exemplo renda extra:
1. Entender negócio.
2. Aprender básico.
3. Calcular custos.
4. Definir preço/margem.
5. Conseguir primeiros clientes.
6. Registrar primeiro lucro.

Adicionar lembretes opt-in:
- horário/dias escolhidos;
- snooze/reagendar;
- pausar trilha;
- notificações sem spam.

Depois integrar com dados reais:
- receita;
- custos;
- lucro;
- horas;
- retorno/hora.

## 13.3 Vídeos
Título: **“Vídeos para se aprofundar”**.
Não repetir links em cada tópico.
Usar catálogo curado/whitelist de fontes confiáveis (ex.: Sebrae/Senac/canais oficiais) ou backend de busca com filtro. Não abrir busca genérica como solução final.

Expandir Trilhas no futuro para:
- reserva de emergência;
- sair das dívidas;
- reduzir gastos;
- realizar meta;
- organização do casal.

---

# 14. MONETIZAÇÃO — RENTÁVEL SEM PREJUDICAR O GRATUITO

Objetivo do criador: tornar o app sustentável e financiar o desenvolvimento de novos produtos, sem degradar a experiência gratuita.

## 14.1 Afiliados
Implementar uma arquitetura de afiliados transparente.

Nome sugerido da área: **Achados Nex**.

Regras:
- identificar “Link de afiliado”;
- explicar que o app pode receber comissão;
- comissão nunca altera recomendação financeira;
- se compra não cabe, Nex recomenda não comprar;
- não enviar renda/saldo/despesas/e-mail ao parceiro;
- não rastrear além do necessário;
- links configuráveis por backend/admin, não hardcoded no app final;
- ofertas expiradas devem sumir automaticamente;
- não usar urgência falsa/dark patterns.

Começar com Mercado Livre e permitir outros parceiros depois.

## 14.2 Ofertas baseadas em intenção
Ex.: usuário já tem PS5 em Aquisições. Pode aparecer “Comparar ofertas” depois da análise financeira.

Não usar dado financeiro para publicidade externa sem base legal/transparência.

## 14.3 Premium futuro sem destruir o free
Free deve manter:
- registro financeiro básico;
- saldo;
- metas básicas;
- privacidade;
- exportação básica.

Premium possível:
- IA avançada/cota maior;
- OCR avançado em volume;
- relatórios longos;
- automações;
- múltiplos espaços avançados;
- recursos profissionais.

Também considerar futuramente B2B/white-label/produtos separados em vez de poluir o NexGrana com anúncios.

---

# 15. LGPD / PRIVACIDADE / SEGURANÇA

Não declare “LGPD compliant” automaticamente. Implemente os controles técnicos e gere checklist para revisão jurídica.

Princípios:
- finalidade;
- adequação;
- necessidade/minimização;
- livre acesso;
- qualidade;
- transparência;
- segurança;
- prevenção;
- não discriminação;
- responsabilização.

Implementar/planejar:
- privacy by design/default;
- política de privacidade versionada;
- base legal por finalidade;
- consentimentos opcionais separados;
- exportação de dados;
- correção;
- exclusão/anonimização quando aplicável;
- exclusão de conta com confirmação forte;
- revogação de consentimentos;
- informação sobre compartilhamentos;
- revisão de decisões automatizadas/recomendações;
- retenção mínima;
- inventário de dados;
- plano de incidente;
- logs minimizados;
- backup/restore testados.

## 15.1 Secrets
Nunca no cliente:
- service_role Supabase;
- chave LLM;
- segredo de afiliado;
- chaves privadas.

Publishable key pode estar no cliente.

## 15.2 Local storage
Produção:
- tokens em secure storage do SO;
- cache offline criptografado;
- cache separado por usuário/família;
- limpar cache/session no logout;
- bloquear exposição por backup indevido quando aplicável.

## 15.3 Supabase / RLS
Testar RLS com pelo menos:
- família A não acessa família B;
- membro normal não vira owner;
- convite só funciona por RPC/código;
- anon não acessa dados;
- UPDATE/DELETE respeitam household;
- placeholders de família não permitem escalada.

Use `SUPABASE_SECURITY_0_17.sql` como base e melhore se necessário.

---

# 16. OFFLINE-FIRST

Objetivo:
- app continua funcional em internet ruim;
- leitura do último estado;
- criação/edição offline futuramente;
- fila de sync;
- UUID idempotente;
- retry/backoff;
- conflito detectável;
- deduplicação;
- status Online / Offline / Sincronizando;
- não perder formulário por timeout/WinError 10054.

Não implemente sync offline de escrita de forma improvisada. Se não ficar seguro nesta versão, implemente arquitetura e fila testável antes de ativar.

---

# 17. ARQUITETURA DO CÓDIGO

O `main.py` atual está grande demais.
Refatorar sem quebrar compatibilidade.

Estrutura sugerida:
- `app.py` / bootstrap;
- `ui/theme.py`;
- `ui/responsive.py`;
- `screens/home.py`;
- `screens/movements.py`;
- `screens/acquisitions.py`;
- `screens/market.py`;
- `screens/planning.py`;
- `screens/analysis.py`;
- `screens/nex.py`;
- `screens/extra_income.py`;
- `services/cloud.py`;
- `services/finance_engine.py`;
- `services/nex_engine.py`;
- `services/sync.py`;
- `services/privacy.py`;
- `services/affiliate.py`;
- `models/...`;

Centralizar lógica financeira em `finance_engine` para Home, Chat, Análises e Planejamento nunca divergirem.

Eliminar duplicações do mascote: um único controller/state machine.

Substituir `except Exception` silenciosos por logging e exceções específicas onde possível.

---

# 18. TESTES OBRIGATÓRIOS

Criar testes automatizados para:
- saldo contínuo mês a mês;
- despesa futura vs paga;
- renda com data de recebimento;
- rateio do casal;
- cálculo individual vs familiar;
- parcelas;
- metas e simulações;
- filtro de aquisições por faixa;
- chat/tool outputs sem inventar valor;
- RLS/smoke tests;
- affiliate disclosure;
- logout limpa cache/session;
- responsividade/breakpoints (ao menos smoke/component tests).

Executar:
- `py_compile`/lint;
- testes unitários;
- build Windows;
- build APK quando ambiente permitir.

Não informe “testado” se não foi realmente executado.

---

# 19. BUILD WINDOWS / ANDROID

Preservar/solucionar a incompatibilidade `screen_brightness_windows` que já ocorreu.
Não atualizar dependências cegamente.

Verifique Flet/Flutter/pubspec antes do build.

Gerar script confiável que produza:
- Windows;
- APK Android;
- ambos.

Se houver plugin não suportado em Windows, aplicar fallback por plataforma.

---

# 20. DESIGN — CRITÉRIO DE ACEITAÇÃO

A referência visual aprovada é dark premium, azul/roxo, cards compactos, Nex integrado e aparência de app consumidor.

Regra: **nenhuma tela deve parecer planilha Excel, ERP ou dashboard administrativo**.

Aplicar em TODAS as abas:
- Home;
- Transações;
- Aquisições;
- Mercado;
- Planejamento;
- Análises;
- Nex;
- Renda Extra;
- Mais/Configurações.

Usar:
- hierarquia visual;
- espaço respirável;
- microinterações;
- feedback de toque;
- progressos;
- estados;
- CTAs claros;
- menos informação crua simultânea.

---

# 21. COMPATIBILIDADE / MIGRAÇÃO

Não apagar dados existentes.
Preservar IDs e tabelas atuais quando possível.
Migration SQL deve ser idempotente.

Se alterar schema, incluir migração e rollback/documentação.

Não exigir que usuário final digite Supabase URL/key.
Login deve permanecer automático após sessão válida, com opção de sair/trocar conta.

---

# 22. ENTREGA FINAL

Antes de entregar:
1. Revise o projeto inteiro novamente.
2. Rode testes.
3. Procure segredos.
4. Procure dados pessoais em logs.
5. Procure TODOs críticos.
6. Verifique Android e Windows.
7. Verifique todos os botões do Nex.
8. Verifique mês/perfil em telas pequenas.
9. Verifique editar/excluir em todas as entidades relevantes.
10. Verifique que imagens automáticas nunca exibem conteúdo adulto/inadequado.

Entregue um ZIP que seja a melhor base possível para um beta público real, deixando explicitamente separado o que ainda exige infraestrutura externa (LLM backend, OCR provider, catálogo de afiliados, notificações push etc.).

**Prioridade máxima: confiabilidade financeira + segurança + experiência do usuário + identidade Nex.**
