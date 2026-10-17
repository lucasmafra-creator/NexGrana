# Segurança — NexGrana 0.21.0 QA

## Controles

- sessão, preferências financeiras, cache e fila usam o cofre Fernet com chave protegida por DPAPI no Windows ou Secure Storage no dispositivo;
- cache é particionado por usuário e família e só abre em sessão autenticada ou previamente validada que ficou offline;
- erro de autenticação/autorização não cai silenciosamente para cache antigo;
- IDs das inclusões são gerados antes do envio; inclusões, edições e exclusões suportadas mantêm ordem na fila, e a repetição usa `upsert`/RPC idempotente;
- painel Achados usa chave pública, RLS, lista `app_admins`, validação de domínio e trilha de auditoria;
- `service_role` não entra no cliente nem no painel;
- reset QA exige conta presente em `qa_testers`, frase explícita, propriedade do espaço e exatamente um integrante;
- logs registram tipos de erro e tempos, sem valores financeiros, tokens ou senhas;
- payload preparado para futuro gateway Nex usa HTTPS público, consentimento e lista mínima de campos; contexto de outra família e segredos são recusados.

## Testes locais autorizados

A suíte cobre isolamento do cache, sessão expirada, retry de transporte, rejeição sem loop, ordem de edição/exclusão offline, recuperação após interrupção, adulteração do cofre, URLs de afiliado, callback localhost, escopo de perfil, prompt injection, duplicidade e integridade financeira. A suíte SQL local exerce RLS com duas famílias e contas sem privilégio. `security_scan.py` procura padrões conhecidos de segredo antes do empacotamento. Os testes não atacam Supabase de produção nem terceiros.

## Pendências antes da publicação

- executar scanner de dependências no CI com acesso à rede e manter a varredura local de segredos;
- validar todas as policies/RPCs em um Supabase de homologação usando duas famílias e contas sem privilégio;
- publicar Política de Privacidade/LGPD revisada, contato e retenção;
- configurar HTTPS/deep links e testar links expirados, reutilizados e outro aparelho;
- realizar revisão independente do gateway LLM quando ele existir;
- trocar `BUILD_CHANNEL` para `production` e remover ferramentas de homologação do build público.

Nenhuma revisão torna o produto “100% seguro”. Vulnerabilidades devem ter canal de reporte e correção versionada.
