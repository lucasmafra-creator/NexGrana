# Segurança — NexGrana 0.22.0 QA

## Controles implementados

- Supabase anon/publishable no cliente; `service_role` proibida;
- RLS e UUID administrativo para Achados, com auditoria de insert/update/delete;
- URL afiliada e imagem em allowlist HTTPS, sem usuário/senha, fragmento ou porta alternativa;
- gateway sem chave no cliente, JWT verificado por JWKS, limite por usuário, timeout e histórico limitado;
- contexto financeiro reduzido por allowlist e somente com consentimento;
- logs do gateway sem mensagem/chat/saldo e identidade pseudonimizada com salt;
- cache local com criptografia autenticada e teste de adulteração;
- proteção contra contexto de outra família, prompt injection, SSRF local, replay/duplicação e mutações rejeitadas.

## Limites

- não é criptografia ponta a ponta quando o gateway/modelo processa conversa;
- política LGPD, retenção, exclusão completa e termos comerciais exigem revisão jurídica antes da publicação;
- testes defensivos foram locais/simulados. Nenhum serviço externo foi atacado ou varrido;
- integração real do JWT/gateway e rotação de chaves dependem da hospedagem autorizada.
