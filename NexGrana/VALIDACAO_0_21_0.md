# Validação — NexGrana 0.21.0 QA

## Automatizada

Execute:

```cmd
py validate_release.py --full
```

Critérios: compilação Python, dependências fixadas, versão consistente, assets canônicos, contratos SQL, varredura de segredos e toda a suíte. A rodada RC3 registrou 90 testes Python aprovados no ambiente Linux de desenvolvimento.

As migrations e regras RLS também foram executadas em PostgreSQL local (PGlite):

```cmd
npm install
npm run test:sql
```

Foram validados isolamento entre famílias, negação anônima, rateios, idempotência, limite de chats fixados, administração de Achados e bloqueio do reset QA para conta não autorizada.

## Manual obrigatória

1. Aplicar `MIGRATION_0_21.sql` em homologação e cadastrar UUIDs separados em `qa_testers` e `app_admins`.
2. Criar conta, confirmar e recuperar senha usando URL HTTPS real; não aceitar localhost.
3. Alternar criar/entrar em família rapidamente em Android pequeno.
4. Usar `[e-mail redigido]`, criar espaço individual e reiniciar homologação.
5. Abrir/trocar abas em rede mediana, modo avião e após reconectar.
6. Criar, editar e excluir renda, despesa, meta, aquisição e produto offline; conferir ordem, pendência e efeito único no servidor.
7. Verificar despesa de R$ 10 no dia 20: futura no dia 19 e efetiva uma vez no dia 20.
8. Abrir Nex, teclado, atalhos, chat fixado, tela cheia/Voltar e troca de perfil.
9. Abrir Privacidade e Adicionar produto com teclado/fonte ampliada.
10. Pesquisar e filtrar Achados; conferir os seis links e a divulgação de comissão.
11. Entrar no painel com conta comum (deve negar) e com UUID admin (deve permitir e auditar).
12. Compilar Windows/APK em `C:\NG21` e instalar em aparelho limpo.

Build e teste manual não são declarados concluídos até Lucas executar no Windows/Android e fornecer a evidência.
