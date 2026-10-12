# NexGrana 0.24.0 — RC6 Windows/Android

Este ZIP contém **código-fonte e assets**, não um instalador EXE/APK. O iOS é a próxima plataforma. Esta RC ainda não pode ser chamada de release final Windows/Android: faltam build nativo, migrações no Supabase de QA e inspeção em aparelho. Não publique como versão comercial apenas com o resultado dos testes locais.

## O que mudou

- Identidade visual: três paletas com prévia, Home e painéis revisados, três poses novas do Nex e uma edição sazonal de dezembro. Em **Mais → Aparência → Escolher visual do Nex** ou no chat é possível escolher manualmente; automático troca em dezembro. O master original tem SHA-256 fixo no manifesto.
- Famílias com mais de um perfil recebem seleção visual ao entrar. A escolha altera o recorte financeiro, nunca a identidade autenticada. Espaços individuais entram diretamente.
- Achados ganhou acesso direto no desktop e na Home. Painel administrativo privado em `admin/achados_admin.py`; `admin/import_offers_csv.py` valida uma planilha autorizada e cria apenas rascunhos. Nenhuma promoção é gerada artificialmente. Links e imagens aceitos continuam restritos aos domínios Mercado Livre presentes nas regras SQL.
- Listas podem iniciar uma compra. Os produtos da lista são copiados, marcados conforme entram no carrinho, com preço editável e produtos extras. A conferência da nota conta somente itens confirmados e itens avulsos. Migração 0.24.3.
- Reset de QA: vínculo explícito de um espaço individual próprio da conta autorizada, seguido de `RESETAR_TESTE`. Migração 0.24.4. A autorização por UID em `qa_testers` ainda precisa existir no banco.
- Exportação agora explica o arquivo sem senha e inclui listas e conversas da própria conta. Exclusão atômica da própria conta/espaço individual mediante frase exata e servidor online; espaço familiar exige tratamento separado. Migração 0.24.5.
- Despesa única e parcelada têm rótulos e soma de parcelas claros. Chat mantém o composer habilitado enquanto Nex responde, evitando a perda de foco causada por desabilitar o campo no Android.

## Instalação e validação

1. Faça backup do Supabase de **homologação**. Aplique em ordem `MIGRATION_0_24.sql`, `MIGRATION_0_24_1.sql` até `MIGRATION_0_24_5.sql`, revisando cada SQL antes de executar. Esta entrega não alterou o backend remoto.
2. No Windows com Python 3.11+ e Flutter/Android SDK instalados: `py -m pip install -r requirements.txt`, `py validate_release.py --full`, `node tests/test_sql.mjs`, `py build_multiplataforma.py both --flutter C:\\caminho\\flutter`. Use `COMPILAR_0_24_ANDROID.cmd` se o Flutter já estiver no PATH.
3. Instale o APK em Android real e abra o EXE no Windows. Teste login, seleção de perfil, teclado e conversa Nex com várias mensagens, compra vinda de lista, nota, câmera, exportação, exclusão em conta de teste, reset QA, logout, modo offline e três aparências; compare 360×800, 390×844, 412×915, 1366×768 e 1920×1080 com `docs/references/`.
4. Para administrar Achados, execute `py -m flet.cli run --web admin/achados_admin.py` no ambiente autorizado. Para importar CSV, confira `py admin/import_offers_csv.py --help`; faça `--dry-run` antes de `--commit`, usando credenciais administrativas via ambiente. Revise e publique manualmente no painel.

## Evidência e limites

Os 173 testes Python, testes SQL com PGlite, análise estática, `security_scan.py` e integridade do ZIP passaram localmente. Build Windows foi bloqueado pelo host Linux. A tentativa de APK não gerou artefato porque a inicialização do Flutter excedeu o tempo disponível, sem evidência de erro do app. Não houve teste em Android/Windows reais ou aplicação das migrações ao Supabase remoto.

O idioma integral ainda é português; inglês/espanhol não foram liberados. A alimentação automática diária de Achados depende de fonte/API de parceiro autorizada e verificação de preço; o importador revisável e o painel já estão no pacote. Nex Online permanece congelado por custo, com respostas locais; não há custo externo disparado pela interface. Essas pendências impedem afirmar que só resta iOS para publicação.
