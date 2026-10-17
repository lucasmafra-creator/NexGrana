# NexGrana 0.18.1 SOL — changelog

## Integridade financeira
- Centralização de cálculos monetários em `services/finance_engine.py` usando `Decimal`/centavos.
- Saldo contínuo entre competências; virada de mês não zera dinheiro.
- Despesa futura não reduz caixa atual antes da efetivação; estados agendada/paga/atrasada/cancelada.
- Data real de recebimento de renda participa do caixa; renda futura/sem confirmação não é tratada como disponível.
- Rateio evita duplicação e mantém divergência explicitamente como não atribuída.
- Compromisso mensal de metas considera apenas valor restante e não baixa novamente o que já foi guardado.
- Simulação de metas calcula manter prazo, +1 mês, +2 meses, entrada e outras metas ativas.
- Aquisições usam preço total e orçamento conservador (caixa, compromissos, reserva e metas).

## Concorrência e banco
- RPC atômica/idempotente para despesas + rateios.
- Edição de meta exige `version` esperado para evitar sobrescrita silenciosa.
- Aporte em meta usa UUID idempotente; a migration 0.18.1 rejeita reuso divergente do UUID, meta encerrada e aporte acima do restante.
- Políticas/RPCs continuam limitadas por família e papel de escrita.
- Exclusão destrutiva de meses e substituição por banco legado foram bloqueadas no cliente nesta candidata.

## Nex
- `services/nex_engine.py` é a fronteira de ações financeiras estruturadas.
- Contexto valida família e perfil ativo.
- `Simular com Nex` e avaliação de aquisição recebem `entity_id`/ação explícita.
- Números críticos vêm do motor determinístico; em falha o Nex retorna erro explícito e não inventa valores.
- Não há LLM externo conectado nesta versão e nenhuma chave de IA é embarcada no cliente.

## Trilha Nex / renda extra
- Diagnóstico ampliado para orientar renda extra com contexto do usuário.
- Continuação de trilha contextual por etapa.
- Base de progresso, pausa, lembrete opt-in e soneca.
- Conteúdo externo fica concentrado em materiais para aprofundamento; não há promessa de ganho.

## Segurança e privacidade
- Vault local com Fernet.
- Chave protegida por DPAPI no Windows e secure storage nas demais plataformas.
- Migração de sessão plaintext antiga e remoção do arquivo antigo.
- Cache cifrado escopado por usuário/família.
- Consentimentos opcionais para lembretes, IA externa futura e personalização de afiliados.
- Exportação de snapshot SQLite sem apagar a nuvem.
- Fluxos destrutivos legados permanecem desativados.

## UX
- Home orientada a “como estamos / o que merece atenção / o que fazer agora”.
- Análises usam margem conservadora e recomendações rastreáveis.
- Perfis ativos da família continuam separados da identidade autenticada.
- Nex usa master HD com alpha real nas telas principais; estados visuais 3D/Rive completos continuam como evolução de arte, não são falsamente declarados.

## Mercado
- Câmera/galeria e miniaturas para conferência manual.
- Limites de memória/fotos temporárias na experiência de nota.
- Edição/exclusão de produtos e compras respeitando operações de banco.
- OCR automático ainda não é declarado; o app não inventa itens de nota.

## Monetização
- Infraestrutura de ofertas afiliadas com URLs HTTPS permitidas, validade e disclosure.
- Recomendação financeira não pode ser alterada por comissão.
- Dados de saldo/despesas/metas não são adicionados ao link de afiliado.
