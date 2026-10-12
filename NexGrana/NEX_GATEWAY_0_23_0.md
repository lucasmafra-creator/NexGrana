# Gateway do Nex — contrato 0.23.0

O app não contém chave do provedor. O cliente envia ao gateway próprio:

- request ID;
- mensagem do usuário;
- até 24 mensagens recentes, limitadas a 12 mil caracteres;
- intenção classificada;
- nome preferido, tom e detalhe autorizados;
- contexto financeiro mínimo somente para intenção financeira e com consentimento.

O gateway deve autenticar o JWT Supabase, aplicar rate limit, não registrar texto/valores e devolver apenas `reply`. Sem URL HTTPS configurada ou sem consentimento, o Nex mantém as funções determinísticas locais e informa a limitação. Não declarar “chat online completo” até o serviço ser publicado e testado.

