# NexGrana 0.19.0 SOL — Virada (candidata de teste)

Esta pasta continua a linha 0.18.1/RC2 e implementa a especificação refinada pelo Astra sem recomeçar o projeto. É uma **candidata de teste**, não uma release pública: neste ambiente não foi possível executar Flet/Supabase nem gerar Windows/APK.

## O que mudou nesta rodada

- **Nex Android / pipeline único:** botão Enviar, submit, sugestões rápidas, Planejamento, Aquisições e Trilha convergem para o mesmo dispatcher assíncrono, com `request_id`, escopo de família/perfil/mês, estado ocupado, erro explícito e descarte de resposta tardia de outro contexto.
- **Composer mobile:** no Android a navegação inferior e conteúdo não essencial podem ser ocultados durante foco para preservar a área de digitação; o campo é multilinha e o histórico não é remontado a cada mensagem.
- **Performance de navegação:** `main.py` mantém um host principal persistente e troca apenas seu conteúdo, em vez de `page.clean()` a cada rota. O polling de sincronização foi reduzido para 15 s e o Nex não troca mais `src` da imagem a cada microanimação.
- **Nex visual:** o runtime não usa mais os GIFs degradados. Há um master RGBA 1254×1254 e derivados `hero/card/dock/avatar` para reduzir custo de decode. Estados realmente distintos ainda dependem de um pack de animação aprovado; esta versão não finge que micro-movimento é rig 3D.
- **Design system:** tokens de espaçamento, radius, movimento, touch target, breakpoints e identidade roxo/azul em `src/ui/design.py`; diálogos críticos passaram a respeitar dimensões do viewport.
- **Renda Extra:** diagnóstico guiado em 8 dimensões e recomendação de até 3 rotas sem promessa de renda.
- **Trilha Nex:** 10 etapas, progresso persistente, pausa/retomada, notas e métricas de acompanhamento, lembrete opt-in dentro do app, e conversa contextual com o Nex. Anotações de receita/custo da trilha não criam lançamento financeiro automaticamente.
- **Análises:** comparação do mês atual usa o mesmo recorte de dias do mês anterior, evitando comparar mês parcial com mês completo sem aviso.
- **Monetização gratuita:** nenhuma função paga, Premium ou paywall. Arquitetura mínima para recomendações/ofertas/afiliados separa utilidade financeira de monetização. Analytics remoto permanece desativado.
- **LGPD/segurança:** preserva Vault, isolamento por família/RLS, consentimentos opcionais, bloqueio de importação destrutiva e princípios de minimização. Nenhuma migration é aplicada automaticamente ao Supabase real.

## Validação disponível neste ambiente

```text
python validate_release.py
→ versão/manifesto Nex: OK
→ compileall: OK
→ 44 testes de núcleo: OK
```

A descoberta completa encontra 46 entradas, mas `test_ui` e `test_market_cloud` não carregam aqui porque os pacotes `flet` e `supabase` não estão instalados neste runtime. Isso **não** conta como aprovação desses testes.

Consulte `VALIDACAO_0_19_0_SOL.md` para a lista honesta do que foi e não foi validado.

## Antes de usar com seu banco

1. Faça backup.
2. Leia `MIGRATION_0_19.sql`.
3. Aplique migrations apenas em homologação primeiro.
4. Rode `py validate_release.py --full` no seu PC após instalar `requirements.txt`.
5. Teste login, perfil, lançamentos, Nex com teclado Android, Mercado/câmera e logout/login antes de considerar publicação.

## Comandos principais

Veja `COMANDOS_0_19_0_WINDOWS_ANDROID.txt`.

## Estado de recursos deliberadamente não concluídos

- Nex não possui ainda um rig 3D/Rive final com expressões realmente diferentes.
- Não há LLM externo conectado; cálculos financeiros continuam determinísticos.
- OCR de nota não é declarado como pronto.
- Escrita offline continua desabilitada até a fila/conflitos serem validados end-to-end.
- Analytics remoto não é enviado.
- Rede de afiliados precisa de aprovação/termos de cada parceiro e elegibilidade por plataforma antes de ativação comercial ampla.
