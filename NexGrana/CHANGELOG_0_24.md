# NexGrana 0.24.0 QA RC1 — código para teste

## Checkpoint documental após teste do proprietário

- Confirmado que Nex online ainda não foi implantado, a personalização com três
  identidades não existe e o reset da conta oficial QA é recusado em uso real.
- Auditoria ampliada identificou também matching de listas, Nex Vivo/Android,
  rota independente de Achados, RLS real, automação de build, performance,
  segurança externa e builds/smokes como parciais ou pendentes.
- Adicionados memória atual, auditoria de lacunas e prompt corretivo RC2. Nenhum
  desses documentos transforma funcionalidade pendente em concluída.

- Tutorial: 13 estações com simuladores e sandboxes; números inválidos e
  progresso de sessão corrigidos; promoção seletiva e explícita.
- Nex: respostas locais de ajuda para ativação, diagnóstico honesto de
  conexão, atalho de privacidade no chat, instruções do gateway revisadas.
- Segurança: consentimento verificado no servidor por JWT/RLS, recusa segura
  em falha de autorização, sem redirecionar Bearer token e sem confiar em
  extrato informado pelo cliente.
- Mercado: listas independentes com orçamento e confirmação de itens;
  Achados em subaba separada. Itens isolados por espaço tanto na consulta
  offline quanto no banco; erro de leitura não finge lista vazia.
  Requer migração 0.24 em QA.
- Home: consolidado familiar legível e separado do saldo pessoal; linguagem
  de aquisição explicita que ela não equivale a uma meta nem reserva dinheiro.
- Reset QA direcionado ao espaço explícito e sem transferência automática
  de propriedade; depende da mesma migração de homologação.
- Nex Vivo: eventos não sobrescritos por animação ociosa; som inexistente
  removido da interface, asset canônico intocado.
- Engenharia: pacote e manifesto verificáveis, comandos Windows locais e
  relatórios de QA sem alegar build/implantação inexistentes.

Pendências e limitação de escopo: `README_0_24_QA.md` e `TEST_REPORT_0_24.md`.
