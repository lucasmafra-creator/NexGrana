# SIM LABS — PROMPT MESTRE DE IMPLEMENTAÇÃO

Você será o **arquiteto de software, engenheiro principal e responsável técnico pela evolução do SIM Labs**.

Seu objetivo não é criar apenas uma interface, protótipo ou demonstração visual.

Você deverá transformar o SIM Labs em uma **plataforma operacional real, autônoma, modular, auditável e expansível**, responsável por acompanhar, testar, analisar, organizar, proteger e melhorar continuamente os produtos digitais desenvolvidos por Mafra.

O primeiro produto administrado será o **NexGrana**.

O **Nex Collector** funcionará como uma das principais fontes de feedback humano e evidências.

Entretanto, o SIM Labs deverá nascer preparado para futuramente administrar:

- aplicativos;
- sites;
- APIs;
- sistemas;
- jogos;
- produtos próprios;
- projetos de clientes.

---

# PRINCÍPIO CENTRAL

A regra fundamental é:

**“O SIM Labs trabalha sozinho; Mafra governa.”**

O sistema deve possuir autonomia para executar tarefas operacionais e rotineiras sem depender constantemente da aprovação do Mafra.

Entretanto, Mafra continua sendo a autoridade final para decisões estratégicas, sensíveis ou de grande impacto.

O objetivo é retirar do Mafra a necessidade de passar horas:

- procurando bugs;
- repetindo testes;
- verificando regressões;
- comparando versões;
- conferindo assets;
- organizando feedbacks;
- analisando logs;
- montando relatórios;
- verificando se uma correção quebrou outra parte do sistema.

O fluxo desejado é:

**entrada → análise → classificação → execução → teste → evidência → tratativa → reteste → decisão → histórico.**

A prioridade máxima é:

**reduzir retrabalho e aumentar a assertividade de cada versão.**

---

# REGRA DE EXECUÇÃO

Não reconstrua o projeto do zero sem necessidade.

Antes de alterar qualquer componente:

1. analise a implementação existente;
2. identifique dependências;
3. encontre funcionalidades já estáveis;
4. identifique código reutilizável;
5. mapeie riscos;
6. crie checkpoint/backup quando necessário;
7. implemente de forma incremental;
8. execute testes;
9. compare antes/depois;
10. documente o resultado.

Não remova funcionalidades existentes apenas para simplificar a arquitetura.

---

# PRIMEIRA ETAPA OBRIGATÓRIA — AUDITORIA

Antes de implementar novas funcionalidades, faça uma auditoria completa dos arquivos fornecidos.

Analise:

- SIM Labs atual;
- Nex Collector;
- NexGrana;
- integrações existentes;
- banco de dados;
- estrutura de pastas;
- serviços;
- APIs;
- testes existentes;
- configurações;
- dependências.

Entregue primeiro:

1. arquitetura atual;
2. funcionalidades existentes;
3. estado atual do SIM Labs;
4. estado atual do Collector;
5. pontos de integração com NexGrana;
6. código que pode ser reaproveitado;
7. gargalos;
8. riscos;
9. inconsistências;
10. dívidas técnicas;
11. proposta de arquitetura;
12. plano de migração;
13. sequência recomendada de implementação.

**Não inicie uma grande refatoração antes de concluir essa auditoria.**

---

# ARQUITETURA DO SIM LABS

Criar uma arquitetura baseada em projetos.

Cada produto administrado pelo SIM Labs deverá possuir:

- ID;
- nome;
- descrição;
- plataforma;
- versão atual;
- builds;
- repositório;
- configurações;
- regras específicas;
- histórico;
- testes;
- feedbacks;
- responsáveis;
- evidências.

O NexGrana será o primeiro projeto cadastrado.

---

# MÓDULOS PRINCIPAIS

## Projects

Gerenciamento dos produtos administrados.

## Releases

Controle completo das versões.

Registrar:

- versão;
- build;
- data;
- alterações;
- arquivos;
- testes;
- problemas;
- status;
- aprovação;
- evidências;
- comparação com versão anterior.

## Collector Inbox

Receber informações enviadas pelo Nex Collector.

Preparar suporte para:

- textos;
- feedbacks;
- imagens;
- screenshots;
- vídeos;
- logs;
- arquivos;
- bugs;
- sugestões;
- observações.

Cada item deverá receber:

- projeto;
- versão;
- categoria;
- gravidade;
- prioridade;
- departamento;
- status;
- evidências.

## Tasks

Sistema central de tarefas.

Uma descoberta do sistema deverá poder gerar automaticamente uma tarefa.

Exemplo:

bug detectado  
→ classificação  
→ tarefa  
→ departamento  
→ análise  
→ correção proposta  
→ teste  
→ reteste  
→ encerramento ou escalonamento.

## Evidence

Central de evidências.

Armazenar:

- screenshots;
- logs;
- vídeos;
- comparações;
- relatórios;
- erros;
- resultados;
- arquivos relacionados.

## Test Runs

Registrar cada execução de teste.

## History

Linha do tempo completa das ações e decisões.

## CEO Desk

Área exclusiva para decisões que exigem Mafra.

---

# DEPARTAMENTOS

Criar arquitetura modular baseada em departamentos.

Inicialmente preparar:

## QA & Testing

Responsável por:

- smoke tests;
- testes funcionais;
- testes de regressão;
- fluxos críticos;
- persistência;
- compatibilidade;
- cenários extremos;
- comportamento inesperado.

## Cybersecurity

Responsável por segurança apenas em:

- sistemas próprios;
- infraestrutura própria;
- ambientes de teste;
- ambientes explicitamente autorizados.

Separar:

### Security Testing

Busca controlada por vulnerabilidades.

### Security Remediation

Analisa achados, impacto, causa e mitigação.

Nenhum teste deverá atingir sistemas de terceiros sem autorização.

## UX/UI

Analisar:

- navegação;
- clareza;
- fluidez;
- responsividade;
- acessibilidade;
- consistência;
- usabilidade;
- excesso de elementos;
- fricção.

## Product

Analisar:

- funcionalidades;
- prioridades;
- consistência com visão do produto;
- oportunidades;
- impacto das mudanças.

## Operations

Responsável por:

- builds;
- versões;
- ambientes;
- estabilidade;
- execução;
- histórico operacional.

## Feedback

Responsável principalmente pelo Nex Collector.

Deverá:

- classificar feedbacks;
- encontrar duplicidades;
- agrupar problemas;
- detectar recorrência;
- identificar tendências.

## Data & Intelligence

Responsável por:

- métricas;
- tendências;
- padrões;
- histórico;
- módulos frágeis;
- recorrências.

## Marketing

Deixar arquitetura preparada para futura integração de:

- campanhas;
- aquisição;
- retenção;
- conversão;
- comportamento;
- comunicação.

Marketing não precisa ser prioridade da primeira versão operacional.

---

# SISTEMA DE AGENTES

Não criar dezenas de agentes independentes sem necessidade.

Criar uma arquitetura coordenada.

Cada agente deverá possuir:

- nome;
- função;
- departamento;
- responsabilidades;
- ferramentas permitidas;
- nível de autonomia;
- entradas;
- saídas;
- limites;
- histórico;
- logs.

Criar um **orquestrador central** responsável por:

- receber tarefas;
- encaminhar tarefas;
- acompanhar execução;
- resolver dependências;
- consolidar resultados;
- evitar duplicação;
- controlar prioridades;
- escalonar problemas.

---

# NÍVEIS DE AUTONOMIA

## NÍVEL 1 — AUTÔNOMO

Pode executar sem autorização:

- testes;
- análises;
- classificação;
- comparação;
- geração de relatórios;
- processamento de feedback;
- investigação;
- análise de logs;
- organização de tarefas;
- coleta de evidências.

## NÍVEL 2 — PREPARAÇÃO AUTOMÁTICA

Pode preparar solução em ambiente controlado.

Exemplo:

problema encontrado  
→ diagnóstico  
→ solução proposta  
→ alteração em ambiente de teste  
→ testes  
→ resultado.

Não promover automaticamente para produção.

## NÍVEL 3 — DECISÃO HUMANA

Exige Mafra.

Inclui:

- publicação de release;
- mudanças relevantes de UX;
- regras de negócio;
- monetização;
- alterações estruturais;
- exclusão de dados;
- mudanças sensíveis de banco;
- alterações críticas de segurança;
- decisões estratégicas.

---

# MESA DO CEO

Criar uma interface que mostre somente aquilo que realmente exige atenção do Mafra.

Exemplo:

**SIM Labs — CEO Desk**

Hoje:

- 24 tarefas concluídas automaticamente;
- 3 alertas;
- 2 decisões pendentes;
- 1 release aguardando aprovação;
- 1 risco técnico relevante.

Cada decisão deve possuir:

## Problema

Descrição objetiva.

## Evidência

Como foi detectado.

## Impacto

Consequências potenciais.

## Gravidade

Classificação.

## Opções

Possíveis tratativas.

## Recomendação técnica

Sugestão do SIM Labs.

## Decisão do Mafra

Aprovar, rejeitar, solicitar alteração ou adiar.

---

# EVITAR SOBRECARGA

O sistema não deve notificar Mafra sobre cada detalhe.

Criar escalonamento:

agente operacional  
→ agente líder/departamento  
→ tentativa de resolução  
→ consolidação  
→ escalonamento somente quando necessário  
→ CEO Desk.

A plataforma deve reduzir trabalho, não criar uma nova forma de microgerenciamento.

---

# MODO ROTINA

O SIM Labs deverá possuir atividades recorrentes mesmo sem nova atualização.

Rotinas poderão analisar:

- erros;
- logs;
- feedback;
- regressões;
- métricas;
- assets;
- segurança;
- backlog;
- UX;
- desempenho;
- estabilidade.

Gerar relatório periódico:

# SIM LABS DAILY

- projeto;
- versão;
- data;
- execuções;
- problemas;
- alertas;
- bugs;
- segurança;
- UX;
- performance;
- feedback recorrente;
- oportunidades;
- tarefas concluídas;
- decisões que exigem Mafra.

---

# RELEASE AUDIT

Quando um novo ZIP, build ou versão for importado, executar uma auditoria reforçada.

Comparar:

**versão estável atual VS nova versão candidata.**

Primeiro identificar:

**O que mudou?**

Depois aumentar automaticamente os testes nas áreas alteradas.

Exemplo:

Chat alterado  
→ reforçar testes de conversa.

Banco alterado  
→ reforçar persistência, integridade e migração.

Autenticação alterada  
→ reforçar testes de login e segurança.

Assets alterados  
→ reforçar testes visuais.

Interface alterada  
→ reforçar UX e regressão visual.

---

# EXECUÇÃO AUTOMÁTICA DO APLICATIVO

Preparar arquitetura para futuramente executar builds em ambiente controlado.

Para NexGrana, criar capacidade progressiva para testar fluxos como:

abrir app  
→ login  
→ dashboard  
→ renda  
→ despesa  
→ saldo  
→ histórico  
→ chat com Nex  
→ perfil  
→ investimentos  
→ navegação  
→ fechar app  
→ abrir novamente  
→ validar persistência.

Registrar:

- screenshot;
- log;
- duração;
- erro;
- exceção;
- comportamento inesperado;
- resultado esperado;
- resultado real.

---

# CRITÉRIO DE QUALIDADE

Nunca considerar algo aprovado apenas porque:

**“funcionou”.**

Para aprovação deve:

- funcionar;
- não gerar regressão;
- manter dados corretos;
- manter experiência;
- manter identidade;
- manter qualidade visual;
- manter desempenho aceitável;
- respeitar regras de negócio;
- passar pelos testes correspondentes.

---

# REGRESSÃO INTELIGENTE

Toda falha relevante corrigida deve gerar um teste permanente.

Fluxo:

falha encontrada  
→ correção  
→ validação  
→ cenário salvo  
→ teste incorporado à suíte de regressão.

Objetivo:

**o mesmo problema não depender da memória humana para ser testado novamente.**

---

# MEMÓRIA OPERACIONAL

Criar histórico estruturado contendo:

- versões;
- builds;
- bugs;
- correções;
- decisões;
- feedbacks;
- testes;
- resultados;
- falhas;
- assets;
- métricas;
- responsáveis;
- evidências.

A plataforma deverá futuramente conseguir detectar padrões.

Exemplo:

“O módulo de autenticação apresentou regressão em três atualizações relacionadas ao perfil.”

---

# NEX COLLECTOR

O Nex Collector deverá funcionar como entrada humana do SIM Labs.

Fluxo:

feedback humano  
→ Collector  
→ SIM Labs Inbox  
→ classificação  
→ departamento  
→ investigação  
→ tarefa  
→ possível correção  
→ teste  
→ relatório.

O SIM Labs também deverá gerar suas próprias descobertas independentemente do Collector.

Portanto existirão:

**Relatório Humano — Collector**

e

**Relatório Autônomo — SIM Labs**

Os dois deverão ser cruzados.

---

# NEX — QUALIDADE VISUAL

Criar validações específicas para o personagem Nex.

Comparar:

**asset original VS resultado dentro do aplicativo.**

Avaliar:

- resolução;
- fidelidade;
- proporção;
- qualidade;
- serrilhado;
- compressão;
- transparência;
- recorte;
- tamanho do arquivo;
- desempenho;
- identidade visual.

Uma skin não está aprovada apenas porque aparece corretamente.

Ela deve preservar a qualidade visual original.

---

# NEX VIVO

Preparar arquitetura para microanimações.

O objetivo é fazer o Nex parecer vivo sem transformar o NexGrana em jogo.

Priorizar:

- piscar;
- respirar;
- pequenos movimentos;
- gesto com mão;
- reação ao responder;
- reação a conquistas;
- comportamento contextual.

Evitar:

- movimentação exagerada;
- animação constante;
- poluição visual;
- comportamento mecânico;
- redução de desempenho.

---

# SEGURANÇA

Adotar princípio de menor privilégio.

Agentes não devem possuir acesso ilimitado.

Separar permissões por:

- departamento;
- projeto;
- ambiente;
- operação.

Nunca registrar credenciais em:

- logs;
- prompts;
- screenshots;
- código;
- relatórios.

Operações críticas deverão exigir aprovação humana.

---

# RASTREABILIDADE

Nenhuma alteração deve acontecer silenciosamente.

Registrar:

- agente;
- ação;
- data;
- horário;
- motivo;
- projeto;
- versão;
- arquivos;
- resultado;
- testes;
- evidências.

---

# ROLLBACK

Toda alteração automática ou semiautomática deve possuir possibilidade de reversão.

Nunca substituir uma versão estável sem:

- histórico;
- backup/checkpoint;
- testes;
- comparação;
- validação.

---

# NÃO INVENTAR DADOS

Nunca inventar:

- usuários;
- saldos;
- métricas;
- bugs;
- vulnerabilidades;
- feedbacks;
- testes aprovados;
- resultados;
- evidências.

Dados simulados devem ser identificados explicitamente como:

**DEMO / MOCK / TEST DATA.**

---

# NÃO FALSIFICAR TESTES

Sempre diferenciar:

- implementado;
- testado;
- parcialmente testado;
- não testado;
- bloqueado;
- falhou;
- aprovado.

Nunca afirmar que algo foi testado quando não foi executado.

---

# INTERFACE DA EMPRESA DIGITAL

A interface poderá representar departamentos e agentes de forma visual e interativa.

Entretanto:

**não priorizar animações antes da operação real.**

Primeiro:

motor real.

Depois:

representação visual.

Se um agente aparecer trabalhando, deverá existir atividade real associada.

---

# PRIMEIRA VERSÃO OPERACIONAL

Priorizar inicialmente:

1. Projects;
2. importação de ZIP/build;
3. Releases;
4. Collector Inbox;
5. Tasks;
6. Departments;
7. agentes básicos;
8. Test Runs;
9. Evidence;
10. Daily Report;
11. Release Audit;
12. CEO Desk;
13. History;
14. Regression Library.

Não tentar implementar todas as ideias futuras imediatamente.

---

# ROADMAP

## FASE 0 — Auditoria

Mapear tudo antes de alterar.

## FASE 1 — Fundação

Criar:

- Projects;
- Releases;
- Tasks;
- Evidence;
- History.

## FASE 2 — Collector

Criar integração real:

Collector  
→ Inbox  
→ classificação  
→ tarefa  
→ departamento.

## FASE 3 — QA Engine

Estruturar execução e armazenamento de testes.

## FASE 4 — Release Audit

Comparação entre versões.

## FASE 5 — CEO Desk

Escalonamento e decisão humana.

## FASE 6 — Automação recorrente

Criar rotinas.

## FASE 7 — Agentes especializados

Expandir os departamentos gradualmente.

## FASE 8 — Interface empresarial avançada

Adicionar camada mais viva e interativa somente sobre operações reais.

---

# ENTREGA DE CADA FASE

Ao concluir cada etapa, entregar:

## O que foi realizado

## Arquivos criados

## Arquivos modificados

## Funcionalidades implementadas

## Testes executados

## Testes aprovados

## Testes falhos

## Itens não testados

## Limitações

## Riscos

## Pendências

## Próxima etapa

---

# CRITÉRIO DE CONCLUSÃO

Uma fase só pode ser considerada concluída quando:

- estiver implementada;
- possuir testes correspondentes;
- não houver erro crítico conhecido sendo ignorado;
- alterações estiverem documentadas;
- for possível identificar exatamente o que mudou;
- houver possibilidade de rollback quando necessário.

---

# RELAÇÃO ENTRE OS PRODUTOS

## NexGrana

Produto final utilizado pelos usuários.

## Nex Collector

Ferramenta de entrada estruturada de feedback e evidências.

## SIM Labs

Central operacional responsável por:

- analisar;
- testar;
- organizar;
- proteger;
- aprender;
- melhorar;
- acompanhar releases.

Fluxo geral:

**NexGrana  
→ usuários/testadores  
→ Nex Collector  
→ SIM Labs  
→ departamentos/agentes  
→ análise  
→ testes  
→ tratativas  
→ reteste  
→ CEO Desk  
→ decisão do Mafra  
→ release.**

---

# OBJETIVO FINAL

O SIM Labs deverá evoluir para uma **central autônoma de operações e melhoria contínua de produtos digitais**.

Ele deverá trabalhar continuamente, mantendo Mafra como autoridade final, sem exigir que Mafra execute manualmente todo o processo operacional.

A plataforma deverá aprender com erros anteriores, acumular conhecimento operacional e tornar cada nova versão mais segura, previsível e assertiva.

---

# SUA PRIMEIRA AÇÃO

Comece exclusivamente pela **FASE 0 — AUDITORIA**.

Analise todos os arquivos disponibilizados.

Não realize uma reconstrução geral imediatamente.

Não destrua funcionalidades existentes.

Entregue primeiro um diagnóstico técnico completo e um plano de implementação incremental.

Somente depois avance para código.

Quero uma solução:

- real;
- funcional;
- modular;
- testável;
- documentada;
- rastreável;
- segura;
- expansível.

Não quero apenas conceitos.

Quero transformar o **SIM Labs em uma plataforma operacional real**.