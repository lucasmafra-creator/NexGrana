# Segurança e LGPD — NexGrana 0.18.1 SOL

Este documento é técnico e não substitui assessoria jurídica.

## Controles implementados
- Supabase no cliente usa apenas configuração pública/publishable; `service_role` não deve entrar no APK/EXE.
- RLS e funções de autorização limitam dados pelo espaço familiar.
- Operações críticas de despesas/metas usam RPCs transacionais/controle de concorrência.
- Sessão/cache/preferências pessoais são protegidos no dispositivo por Vault cifrado.
- DPAPI protege a chave local no Windows; secure storage é utilizado nas demais plataformas suportadas.
- Exportação de dados existe; operações destrutivas antigas estão bloqueadas nesta candidata.
- Consentimentos opcionais ficam separados do funcionamento financeiro básico.
- IA externa permanece desligada sem backend seguro; nenhuma chave LLM é embarcada.
- Ofertas afiliadas usam disclosure e não recebem parâmetros derivados de histórico financeiro.

## Princípios aplicados
- minimização: usar apenas contexto necessário para cada função;
- finalidade: finanças, sync, segurança, exportação e recursos opcionais consentidos;
- transparência: texto de privacidade e disclosure de afiliados;
- segurança: RLS, cifragem local, transações, idempotência e validações;
- não discriminação: recomendações não devem explorar vulnerabilidade financeira;
- livre acesso/correção: registros editáveis e exportação de dados.

## Antes de lançamento comercial
- definir/publicar controlador e canal de privacidade;
- documentar bases legais por finalidade;
- definir prazos de retenção e descarte;
- listar suboperadores e transferências internacionais aplicáveis;
- implementar exclusão de conta/espaço com confirmação forte e preservação correta de dados compartilhados;
- revisar portabilidade em formato apropriado;
- testar revogação de consentimento ponta a ponta;
- executar testes reais de RLS/PostgREST com duas famílias e papéis diferentes;
- revisar incident response, backup/restore e processo de notificação;
- revisão jurídica da política/termos antes da publicação.

## Dados que o app não deve solicitar/armazenar
- senha de internet banking;
- PIN;
- CVV;
- número completo de cartão quando não estritamente necessário;
- chaves privadas/tokens de instituições financeiras;
- `service_role` do Supabase;
- chave de provedor LLM no cliente.
