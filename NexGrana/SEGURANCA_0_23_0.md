# Segurança — NexGrana 0.23.0 QA

- Cliente usa somente chave pública/anon do Supabase; `service_role` é proibida.
- RLS e RPCs resolvem usuário/família no servidor.
- Gateway exige HTTPS público, JWT, limite de tamanho e rate limit.
- Intenção geral não inclui snapshot financeiro; intenção financeira exige consentimento.
- Preferências conversacionais não contêm IDs nem valores.
- Chat descarta resposta atrasada após troca de usuário, família, perfil, mês, conversa ou sessão.
- Sandbox do tutorial não é enviado ao gateway nem convertido silenciosamente em renda.
- Cache e preferências autenticadas usam o cofre local disponível.
- Nex Vivo é camada de UX: não possui acesso de escrita financeira.
- Testes cobrem injeção de prompt, URLs privadas, adulteração de cache, RLS local e segregação de perfil.

Pendências pré-produção: pentest externo, revisão LGPD, política de retenção/exclusão e rotação de segredos do gateway.

