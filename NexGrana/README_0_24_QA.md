# NexGrana 0.24.0 — candidata de código-fonte para homologação

Este pacote **não é uma publicação pronta**. Os testes automatizados locais passam,
mas não há build Windows, APK, migração aplicada nem conversa online homologada.
O arquivo `NEXGRANA_ESTADO_OFICIAL_0_23_0.md` permanece intocado até o dono
aprovar a 0.24 após os testes.

## Mudanças desta candidata

- Tutorial de 13 etapas com superfícies de treino específicas; saldo hipotético
  recalcula ao digitar, entrada inválida apaga resultado velho e nunca vira renda
  real. A etapa visitada não conta como concluída automaticamente.
- Progresso do tutorial pertence a usuário/espaço/perfil, não à geração temporária
  de sessão. Promoção de renda/despesa/aquisição/meta exige marcar cada registro
  antes da confirmação; itens já salvos ou pendentes não voltam à promoção.
- Ajuda de conexão do Nex agora responde localmente sem alegar queda de rede
  quando o serviço nem foi configurado. O indicador distingue serviço configurado
  de resposta online efetiva e o consentimento fica acessível no chat.
- Gateway exige consentimento verificado por JWT/RLS no espaço exato, nega se
  o servidor de autorização falhar e não trata números enviados pelo cliente
  como extrato. Token não é encaminhado em redirects HTTP.
- Mercado tem aba própria para Achados e listas pessoais com orçamento,
  adição, marcação de comprados e remoção; a nova tabela exige aplicar e validar
  `MIGRATION_0_24.sql` primeiro na homologação. Item e lista pertencem
  obrigatoriamente ao mesmo espaço; erros de leitura não aparecem como zero.
- Home distingue saldo pessoal do saldo familiar com hierarquia legível;
  Aquisições deixam explícita a diferença entre intenção de compra e meta.
- Reset QA usa ID explícito do espaço atual e bloqueia a saída de proprietário
  quando há outros membros; migração SQL ainda não foi aplicada.
- Nex Vivo mantém o PNG aprovado; reações não são sobrescritas pelo loop
  artificial de 7/9 segundos. Controle de som sem implementação foi removido.
- Empacotador executa testes, confere arte canônica e verifica hashes de todos
  os arquivos dentro do ZIP antes de apresentar checksum.

## Para testar no Windows

Extraia o ZIP e abra o Prompt de Comando **dentro da pasta `project`**.
Digite apenas os comandos, sem copiar o texto `C:\Users\...>` do prompt:

```cmd
VALIDAR_0_24.cmd
```

Para gerar cada plataforma, depois da validação:

```cmd
COMPILAR_0_24_WINDOWS.cmd
COMPILAR_0_24_ANDROID.cmd
```

Os scripts usam por padrão `%USERPROFILE%\flutter\3.44.8`. Se o Flutter
estiver em outra pasta, faça `set "NEX_FLUTTER_ROOT=C:\caminho\do\flutter"`
antes do build. Logs e artefatos ficam em `project\dist\<data-hora>\`.
O instalador Windows é o diretório produzido, não somente um EXE isolado;
o APK será encontrado em `project\dist\<data-hora>\apk\`.

Para verificar o ZIP original no Windows antes de extrair, confira o SHA-256
com `certutil -hashfile "CAMINHO_DO_ZIP" SHA256` e compare ao arquivo
`SHA256SUMS_0_24_0_RC1.txt`. O hash é um resultado, **não é um comando**.

## Bloqueios reais antes de lançamento

- Hospedar gateway HTTPS e configurar secrets **no servidor**, não no APK/EXE;
  definir limites de custo e validar serviço, token, consentimento e respostas em
  dois dispositivos. Sem URL pública `build_config.NEX_GATEWAY_URL` preenchida
  **antes do build Android**, o Nex segue intencionalmente no modo local.
- Implantar e testar `MIGRATION_0_24.sql` somente após backup em projeto de QA;
  verificar RLS com contas A/B e reset com famílias de múltiplos membros.
- Validar telas Android com teclado, conexões fracas e rotação; gerar builds em
  Windows/Android. iOS exige macOS, Xcode, assinatura e conta Apple.
- Não anunciar conversa financeira LLM como pronta: a 0.24 candidata impede
  contexto financeiro fornecido pelo cliente de ser chamado de dado oficial;
  falta ferramenta financeira autorizada e testada no gateway.
- Completar testes de ponta a ponta com Supabase real (persistência, fila e
  sincronização), conversação do tutorial e refinamento visual em dispositivo.

O progresso e as lacunas estão em `TEST_REPORT_0_24.md` e
`NEXGRANA_ESTADO_CANDIDATO_0_24_0.md`.

Após o teste do proprietário foram confirmadas lacunas adicionais. A referência
mais atual é `NEXGRANA_ESTADO_ATUAL.md`; a auditoria completa está em
`AUDITORIA_LACUNAS_0_24_RC1.md` e o trabalho corretivo foi isolado em
`PROMPT_IMPLEMENTACOES_PENDENTES_0_24_RC2.md`. O reset da conta oficial QA,
personalização por usuário e Nex online não estão concluídos nesta RC1.
