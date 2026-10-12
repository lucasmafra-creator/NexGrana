# NexGrana — estado atual da entrega de trabalho

Data da revisão: 01/10/2026  
Base: fonte NexGrana 0.24.0 QA RC6 para Windows e Android.  
Estado deste pacote: **código-fonte atualizado para revisão; não é um build compilado nem uma aprovação de release**.

## O que foi implementado nesta atualização

- **Virada do mês:** fechamento interativo com saldo carregado apenas após confirmação. A continuidade é separada por perfil e consolidado familiar; o saldo de meses abertos não é carregado. Inclusões atrasadas continuam na competência da data e recalculam o saldo dos meses seguintes. Requer `MIGRATION_0_25.sql` no Supabase.
- **Chat Android do Nex:** envio preserva a tela do composer e a resposta é gravada na conversa/perfil capturados no início do pedido. Trocar de conversa ou perfil não deve misturar respostas. A correção ainda precisa de homologação do teclado/IME em aparelho.
- **Primeiro acesso offline:** login e onboarding explicam que criar/validar a conta e carregar o espaço pela primeira vez exigem internet. Depois, só dados já sincronizados e protegidos no aparelho ficam disponíveis offline.
- **Skins Nex:** 36 artes adicionadas ao catálogo, escolha manual disponível em qualquer data e modo Automático com datas festivas e de conscientização. A arte canônica continua como master para avatar/dock; cards com texto são usados como prévia/slots grandes.
- **SIM Labs local:** console no Update Collector para receber pacote/build, calcular SHA-256, conferir estrutura, importar feedback por ID, registrar checklist manual e salvar relatórios. O feedback não é fechado automaticamente.
- **Update Collector 0.4.1:** exclusão de vários feedbacks selecionados e ação “Selecionar visíveis” após filtro/pesquisa.

## Limites que continuam ativos

- A continuidade mensal só funciona depois de aplicar a migração 0.25. O código detecta ausência da tabela, avisa na Home e mantém a sincronização das demais tabelas.
- A análise de APK/EXE é estrutural. Não instala nem executa o aplicativo. O teste de código do SIM Labs exige confirmação, mas não tem sandbox de sistema operacional nem bloqueio de rede.
- Não foi recebido servidor, endpoint, autenticação, storage privado, runner remoto ou hosting do SIM Labs. A tela atual roda localmente; não é um serviço 24/7.
- Nex Online/gateway hospedado e feeds externos de Achados não foram ativados por esta entrega.
- As 36 novas artes são cards RGB pequenos com legenda e algumas bordas/recortes laterais; não são cutouts transparentes prontos para todos os tamanhos. Não substituem a identidade master do Nex.
- A área de treino, o fluxo de Mercado/Listas e o reset QA já existem na base RC6/migrações anteriores; não foram validados em uma conta Supabase real nesta sessão.
- iOS permanece fora do escopo desta fase.

## Verificação local

- `compileall` da fonte e dos testes Python: passou.
- Testes Python determinísticos de finanças, fechamento mensal, chat e skins: 47 passaram.
- Testes do núcleo SIM Labs: 3 passaram.
- A descoberta completa foi tentada: 131 entradas de teste, com 5 erros de importação por dependências ausentes (`flet`, `fastapi`/`httpx` e `supabase`); não considero a suíte completa aprovada.
- Sintaxe de `MIGRATION_0_25.sql` validada em PGlite; não foi aplicada ao Supabase de QA.
- UI Flet, banco real, Windows e Android não puderam ser homologados neste ambiente.

## Próximo gate de Windows/Android

1. Aplicar migrations 0.24.x pendentes e `MIGRATION_0_25.sql` em staging.
2. Reproduzir o mês de setembro com saldo inicial registrado, fechar, abrir outubro e adicionar uma despesa retroativa; conferir os totais por perfil/família e a fila offline.
3. Testar o chat Android com teclado aberto, envio repetido, troca de conversa, troca de perfil e rotação.
4. Gerar builds Windows/APK em hosts com as ferramentas instaladas, instalar e executar smoke tests reais.
5. Revisar contraste e escala das skins; confirmar que cartões com texto não são exibidos como avatar pequeno.
6. Conectar o SIM Labs remoto somente após definir endpoint, autenticação, retenção, política de upload e runners isolados.

Somente depois desses gates a candidata deve ser considerada pronta para distribuição. A próxima fase de produto/iOS vem depois da homologação Windows/Android.
