# PROTOCOLO DE CONTINUIDADE — NEXGRANA

## Fonte central

O arquivo `NEXGRANA_ESTADO_OFICIAL_0_23_0.md` é a memória canônica do projeto. Conversas, prompts antigos e intenções só entram no próximo ciclo quando forem reconciliados com o código, o banco e os testes.

## Ciclo obrigatório de atualização

1. Receber ZIP mais recente, estado oficial e novas evidências do usuário.
2. Auditar código, migrations, assets, documentação e testes.
3. Registrar divergências entre documento e base.
4. Definir escopo com prioridades P0/P1/P2 e backlog.
5. Refinar o plano no Astra quando solicitado.
6. Enviar ao Sol o prompt autocontido, ZIP e estado oficial.
7. Implementar incrementalmente, preservando regras imutáveis.
8. Executar testes Python, SQL, segurança e UI.
9. Executar builds e checklist por plataforma; nunca inferir validação.
10. Atualizar o estado oficial somente com fatos comprovados.
11. Gerar ZIP limpo, manifesto e SHA-256.
12. Gerar o prompt de continuidade da próxima atualização a partir do novo estado oficial.

## Conteúdo mínimo do estado oficial após cada release

- versão, data e base;
- stack e arquitetura;
- banco, tabelas, migrations e RLS;
- autenticação e sistema familiar;
- telas e funcionalidades reais;
- regras financeiras;
- segurança e privacidade;
- UX/UI e assets;
- bugs corrigidos;
- funcionalidades removidas/desativadas;
- testes executados e resultado exato;
- builds por plataforma;
- comandos oficiais;
- pendências e bloqueios externos;
- decisões de produto;
- regras que não podem ser alteradas;
- próxima atualização.

## Regra de evidência

- “Implementado” exige código e teste.
- “Validado” exige teste executado.
- “Build validado” exige build, instalação, abertura e checklist.
- “Pronto para produção” exige também infraestrutura, segurança, política/termos e validação em ambiente real.
- Intenção, mockup ou prompt deve ser marcado como planejado.

## Regras permanentes

1. Nunca inventar valores financeiros.
2. Nunca antecipar despesa futura.
3. Nunca misturar perfis/famílias.
4. Nunca esconder efeito real de uma operação.
5. Nunca gravar demonstração sem confirmação.
6. Nunca colocar segredo no cliente.
7. Nunca usar afiliado para distorcer recomendação.
8. Nunca declarar teste/build que não ocorreu.
9. Nunca aplicar migration automaticamente em produção.
10. Nunca apagar histórico técnico relevante do estado oficial.
