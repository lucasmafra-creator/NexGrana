# Análise e entrega — NexGrana / SIM Labs

## Arquivos e evidências revisados

Consegui abrir a fonte NexGrana 0.24 QA, o Update Collector, o ZIP das 36 skins, os pacotes de feedback de 29/09 e 01/10, as referências visuais e as gravações presentes nos pacotes. As duas partes de 01/10 repetem os mesmos três IDs de feedback; o Collector agora mescla repetições por ID e mantém o status SIM Labs já registrado.

As referências mostram três objetivos visuais: painel desktop escuro com acentos violeta/ciano (`image(10)`), telas mobile (`image(9)`) e catálogo de poses do Nex (`image(8)`). A janela de notas sobreposta nas gravações de desktop é uma transcrição externa, não um controle do app. O vídeo vertical mostra o chat Android e o histórico existente; os vídeos horizontais mostram navegação e telas desktop.

Os arquivos não incluem servidor/endpoint do SIM Labs, projeto Supabase acessível, credenciais de teste, APK/EXE atual ou toolchain de build Android/Windows. Os arquivos de build anteriores registram Windows bloqueado por host e tentativa Android sem artefato; não usei isso como validação do código atualizado.

## Resultado por pedido

| Pedido | Estado no código entregue | Gate que falta |
|---|---|---|
| P0 — continuidade do saldo na virada | Fechamento confirmado por família e perfil; carry-in só passa por mês fechado; mês aberto não carrega; lançamento retroativo recalcula a cadeia | Aplicar `MIGRATION_0_25.sql` em staging e testar com o saldo/lançamentos reais de setembro, incluindo offline e lançamento atrasado |
| P0 — mensagem de primeiro acesso offline | Login e onboarding explicam que primeiro acesso e criação do espaço exigem internet; offline fica limitado a sessão/dados já sincronizados | Verificar texto e comportamento em Windows/Android após login real |
| P0/P1 — chat Android | Atualização da conversa é incremental; resposta usa o escopo capturado no envio e não re-renderiza a página durante o teclado | Aparelho Android: teclado aberto, resposta longa, envio rápido, troca de conversa/perfil e rotação |
| P0 — reset de homologação | Fonte inclui fluxo protegido e migrations de reset QA; sem backend real não confirmei permissão/execução | Aplicar migrations necessárias e testar em sandbox descartável sem dados de terceiros |
| Mercado/Listas e Achados | Fluxos e organização da base RC6 mantidos; a transição lista→compra usa gravação atômica | Aplicar migrations 0.24.x necessárias e testar compra, reabertura offline e telas em dispositivo |
| P2 — skins festivas e sociais | 36 artes no catálogo; seleção manual e agenda automática; master do Nex preservado em avatar/dock | Rever contraste/recorte em telas pequenas; artes novas são cards RGB com texto, não recortes transparentes |
| SIM Labs | Collector local recebe build/pacote, calcula hash, verifica estrutura, importa feedback, guarda checklist e relatórios | Ainda faltam API autenticada, storage privado, fila, runners isolados, rotina diária e hosting 24/7 |
| Collector — apagar vários itens filtrados | Multisseleção e botão para selecionar os resultados visíveis antes de excluir | Teste manual da interface Windows |

## Agenda automática das skins

O modo Automático cobre Ano Novo, Carnaval, Páscoa, Dia da Mulher, Dia dos Povos Indígenas, Dia do Trabalho, Meio Ambiente, Halloween, Consciência Negra e Natal; dezembro fora de 24–25 usa a arte sazonal existente. A escolha manual pode ser usada em qualquer data; retornar para Automático restaura o calendário.

As novas imagens têm legenda integrada, baixa resolução e pequenas sobras laterais em algumas peças. O catálogo as mantém como cards/prévias e slots grandes; avatares e dock continuam usando a arte master aprovada para evitar texto ilegível e recortes ruins.

## SIM Labs: estado e próxima implementação

A entrega é a etapa **local 0.4.1** do Update Collector. A análise estrutural não executa o APK/EXE. A execução de testes de fonte exige confirmação e prazo máximo, mas ainda executa código com as permissões do usuário; não é sandbox. Nenhum dado ou build é enviado para fora do computador.

Antes de habilitar upload, definir API, autenticação por pessoa/produto, URL temporária de upload, limites, retenção, redaction, trilha de auditoria, política de consentimento e ambiente isolado por build. Depois, implementar fila idempotente, runners Windows/Android, comparação visual e relatório diário. O desenho detalhado está em `SIM_LABS_BLUEPRINT.md`.

## Roteiro do iOS

O iOS fica para a próxima fase, depois do gate Windows/Android. A base ainda não produz IPA e este pacote não inclui configuração Apple, certificado ou host macOS. A fase deverá validar build Flet/Flutter iOS, autenticação/deep links, armazenamento seguro, permissões de câmera, teclado e layout, assinatura, TestFlight e revisão de privacidade. Compartilhar a mesma regra financeira e os mesmos contratos de chat/fechamento; não criar uma implementação financeira divergente.

### Prompt para a próxima fase

> Use `NEXGRANA_ESTADO_ATUAL.md` e este relatório como estado canônico. Primeiro feche os gates Windows/Android: aplique migrations em staging, teste fechamento/virada/lançamento atrasado, chat Android com IME e build instalado nos dois sistemas. Não declare release sem artefato e evidência real. Depois, em uma fase separada, avalie a viabilidade iOS na base existente; confirme versões atuais das ferramentas no host macOS, faça build assinado de teste, valide login/deep links, armazenamento seguro, câmera, teclado e telas, e documente TestFlight. Preserve o master do Nex, os limites de privacidade e as regras de saldo. Não invente backend, teste, build ou aprovação. SIM Labs remoto só deve receber builds depois de contrato, autenticação, retenção e runner isolado aprovados.

## Verificação executada nesta sessão

- Sintaxe Python (`compileall`): passou.
- Núcleo financeiro, fechamento mensal, escopo do chat e skins: 47 testes passaram.
- Núcleo SIM Labs: 3 testes passaram.
- A descoberta completa foi executada, mas não aprovada: 131 entradas de teste e 5 erros de importação por dependências ausentes (`flet`, `fastapi`/`httpx` e `supabase`).
- `MIGRATION_0_25.sql` foi analisada pelo parser PGlite; não foi aplicada ao Supabase de QA.
- Não foi possível executar a suíte de UI nem instalar/testar builds: Flet, Flutter, Android SDK/ADB, `psql` e host Windows não estão disponíveis neste ambiente.
