# Validação — NexGrana 0.20.0

Data da evidência local: 15/09/2026.

## Resultado automatizado atual

Executado na raiz limpa de desenvolvimento:

```text
versão/manifesto Nex: OK
compileall: OK
Ran 74 tests
OK
Nex HD SHA256: 4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796
VALIDAÇÃO CONCLUÍDA
```

Também foi executado `npm run test:sql`, com aprovação das migrations 0.18, 0.18.1, 0.19 e 0.20, isolamento entre famílias, bloqueio anônimo, atomicidade financeira e troca da sexta conversa fixada.

## Cobertura relevante

- renda por competência, despesa futura/no vencimento, pagamento não inventado e outros meses;
- rateio por pessoa e soma familiar reconciliada;
- Mafra/Karol sem vazamento de valor ou conta;
- JWT expirado, refresh único, concorrência, refresh inválido e falha de rede;
- Nex assíncrono, falha sem valor inventado e ações determinísticas;
- chat livre, cinco fixados, sexta com arquivo/substituição e RLS;
- simulador de investimento com taxa zero/negativa/anual, prazo, aporte, custos e impostos;
- seis Achados com URLs exatas e sem preço fictício;
- interface em 360, 390, 430, 768, 1366 e 1920 px;
- rotas mobile/desktop, diálogos e reaproveitamento do shell.

## Estado por plataforma

| Plataforma | Código/suíte | Build 0.20 | Instalação 0.20 | Estado honesto |
|---|---:|---:|---:|---|
| Windows | aprovado localmente | não executado nesta revisão | não executada | aguardando build e teste real |
| Android APK/AAB | aprovado localmente | não executado nesta revisão | não executada | aguardando build e dispositivo |
| iOS IPA | núcleo/configuração preparados | não executado | não executada | bloqueado sem macOS/Xcode/assinatura |

## Checklist manual obrigatório por plataforma

1. Instalar sobre uma versão anterior e confirmar preservação de dados.
2. Entrar, fechar, reabrir e testar sessão expirada.
3. Trocar Mafra/Karol e conferir contas, saldo, metas e Nex exclusivos.
4. Registrar renda e uma despesa futura; conferir a virada no dia do vencimento.
5. Confirmar que vencimento não exibe pagamento confirmado sem ação do usuário.
6. Abrir Saúde Financeira e navegar por todas as áreas de Planejamento.
7. Enviar mensagens rápidas/repetidas, usar teclado, texto longo e voltar.
8. Fixar cinco assuntos, tentar o sexto e substituir um sem perder o histórico.
9. Simular investimento e confirmar que nenhuma transação/saldo mudou.
10. Pausar/retomar uma Trilha Nex e conferir o lembrete somente dentro do app.
11. Abrir Achado sem preço e conferir disclosure/navegador externo.
12. Desligar/religar rede e verificar pendências sem duplicação.
13. Sair e entrar com outra conta sem enxergar dados anteriores.

## Banco e rollback

- Fazer backup verificável antes de `MIGRATION_0_20.sql`.
- Aplicar primeiro em homologação e repetir a migration para provar idempotência.
- Conferir o `select` final de catálogo/RPC/tabelas.
- Não reaplicar migrations históricas já presentes em produção.
- Se o cliente precisar voltar à RC4, não apagar as tabelas novas; correção progressiva evita perda de conversas.

Uma suíte verde valida o código-fonte, não a loja nem o dispositivo. A plataforma só recebe status validado depois de build, instalação, abertura e checklist concluído.
