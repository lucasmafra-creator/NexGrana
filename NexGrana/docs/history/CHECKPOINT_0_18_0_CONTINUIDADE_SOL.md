# Continue aqui — checkpoint 0.18.0, 13/09/2026

Continue nesta mesma tarefa com GPT Sol. O usuário pediu concluir integralmente o prompt mestre, mas limitou o Astra a 60% do consumo da janela de 5 horas e pediu priorizar trabalhos complexos antes da troca. Este é um checkpoint INCOMPLETO, não um release pronto. Não reinicie o projeto nem substitua pelas versões antigas. Reserve Astra para grandes atualizações explicitamente solicitadas pelo usuário. Dê atualizações em português e estimativas honestas. Não é necessário criar outra tarefa.

## Fonte e caminhos

- Projeto atual: `C:\Users\lucas\Documents\Codex\2026-09-13\files-mentioned-by-the-user-prompt\outputs\NexGrana_0_18_0`.
- Workspace: diretório pai de `outputs`.
- Prompt autorizado: `REQUISITOS_AUTORIZADOS.md`, cópia integral de `C:\Users\lucas\Downloads\PROMPT_MESTRE_GPT6_ASTRA_NEXGRANA.md`.
- Original: `C:\Users\lucas\Downloads\NexGrana_0_17_0_Virada_Base.zip`; extraído e preservado em `work/source/NexGrana_0_17_0_Virada_Base`.
- `ALTERACOES_CHECKPOINT.json`: relação exata de arquivos novos/alterados/removidos em relação ao original, com SHA256. `MANIFEST_CHECKPOINT.json`: hashes dos arquivos empacotados.
- Scripts `work/upgrade.py`, `fix.py`, `split_modules.py` foram transformações pontuais já executadas. NÃO reexecutar sobre este código.
- Nenhuma migração ou mutação foi executada no Supabase real. Não use dados financeiros reais como fixtures. Não apagar o original.

## Implementado até aqui

1. `services/finance_engine.py`: Decimal/centavos; saldo contínuo; data real de recebimento; dinheiro futuro/sem data excluído do caixa; agendado/atrasado não é pago; débito automático explícito; rateios sem duplicação e resto em não atribuído; mês de pagamento correto; cenários de metas e filtro conservador por preço TOTAL da aquisição.
2. `services/transactions.py`: lote parcelado com UUID estável e datas limitadas ao último dia do mês. `SQL_ATOMIC_0_18.sql`: RPC atômica despesas+rateios, retry idempotente, advisory lock por UUID, comparação de todos os campos relevantes e rateios, rejeição de valores negativos/não finitos/subcentavos e membro duplicado. Edição via RPC; inclusão legada `Cloud.add_expense` ainda existe e precisa revisão.
3. `MIGRATION_0_18.sql`: novas colunas sem inventar datas históricas, responsável/aquisição em metas, pausa, contribuições, trilhas, consentimentos e ofertas. RLS por família/leitor/escritor; validações de referências entre famílias; proteção contra promoção de membro e apropriação de placeholder; convite com lock; aporte idempotente e atômico. Políticas antigas permissivas substituídas nas tabelas tratadas.
4. Refatoração: 82 métodos extraídos de `main.py` para `screens/{home,movements,acquisitions,planning,market,nex,analysis,extra_income,settings,auth}.py` e `ui/theme.py`; utilitários em `ui/common.py`, que possui `__all__` explícito. Main mantém shell/navegação/lifecycle. Cloud ainda possui monkey patches.
5. `services/nex_engine.py`: contexto estruturado, resposta ou erro explícito, metas/aquisições determinísticas. Demais assuntos ainda usam motor legado em `screens/nex.py`. Não há LLM conectado; não fingir geração por IA externa.
6. `app.py` + `services/privacy.py`: Vault Fernet; chave protegida por DPAPI no Windows e secure storage nas demais plataformas; migração da sessão antiga; cache cifrado por usuário/família; exportação snapshot SQLite com fechamento de conexão. Política preliminar versionada. Configuração pública Supabase não é chave service_role.
7. Cloud: históricos paginados em 500; leituras mensais derivadas dos históricos; membros/metas/mercado também em cache; transporte pode usar cópia offline, ausência de cópia gera erro em vez de falso saldo zero; erros de autorização/schema não retornam cache antigo nem são repetidos. Limpar cache não apaga sessão/fila/preferências. Preferências pessoais agora cifradas por usuário/família; arquivo JSON retém só tema. Troca de perfil limpa conversa/fotos.
8. Home: caixa efetivo/individual contínuo, próxima conta, composição móvel. Movimentos: recebimento real de renda, confirmação/cancelamento de pagamento, auto explícito, rateio em centavos. Metas: responsável/status/pausa/edit, aporte via RPC e simulação de entrada. Análise: alocação editável baseada em margem conservadora. Chat: Enter/Shift+Enter, bolhas fluidas, resposta de falha sem valor inventado.
9. Mercado: câmera montada antes das chamadas nativas; galeria separada e seleção cumulativa; miniaturas; isolamento e limpeza de fotos por conferência; comparação manual antes de salvar; validação de quantidade/cashback; CRUD de produtos em compras encerradas. Banco serializa edições por compra e recalcula carrinho na mesma transação, preserva nota/cashback, RPC recusa confirmação desatualizada. Exclusão de compra usa FK cascade atômica. OCR não foi implementado.
10. `services/sync.py`: fundação da fila cifrada, UUID, retry e conflito testáveis; ainda NÃO conectada a mutações offline. `services/affiliate.py`: catálogo backend, whitelist HTTPS, expiração, parâmetros permitidos e disclosure; sem link fixo com dados financeiros.
11. Mascote: `assets/nex/nex_hd.png`, RGBA 1254×1254, alpha real validado; `nex_controller.py` centraliza estados e tamanhos, mas reutiliza a mesma imagem. Micro movimentos NÃO equivalem ao pacote de expressões/animações exigido. Asset veio de imagegen; primeira tentativa foi rejeitada por checkerboard, segunda aceita.
12. `build_multiplataforma.py`: CLI windows/apk/both, versão 0.18.0, Python atual, Flutter via argumento/FLUTTER_ROOT, saída nova por tentativa sem apagar anterior, logs/JSON, só declara build quando artefato existe. Python mínimo corrigido para 3.11 por StrEnum. Pins Flet 0.86.5/Supabase 2.31.0/cryptography 50.0.0 e overrides Windows preservados.

## Evidências de validação

- 40 testes Python passaram: finanças, segurança local, fila, afiliados, Mercado, comportamento de falha offline e componentes Flet.
- Componentes: 10 telas × 6 larguras (360/390/430/768/1366/1920), 9 diálogos. Isto NÃO é inspeção visual renderizada nem teste em aparelho.
- Ruff `--select F` passou; compileall passou. Não declarar lint integral.
- SQL executado duas vezes em PGlite efêmero: migrations idempotentes; fixtures A/B/C, anon, placeholder, membro, referências cruzadas, promoção recusada, RPC despesas/rateios/rollback/retry divergente, aporte idempotente, recibo desatualizado e entre famílias recusado, edição de compra encerrada, cascade. `tests/test_sql.mjs` reproduz com pacote npm fixado. Harness cria auth.uid/roles simulados e omite somente CREATE EXTENSION pgcrypto porque UUID nativo funciona no PGlite. NÃO equivale a autenticação Supabase/PostgREST/E2E nem teste real de concorrência de conexões.
- Builds reais Windows e APK tentados, ambos exit 1 sem artefatos. Logs em `dist/20260913-032841-140823`. Flutter não executou `ver`, CreateFile failed 5/Acesso negado. Antes disso doctor também falhou ao executar Git. Git direto funciona. Não atribuir o bloqueio a erro do aplicativo sem evidência.
- `VALIDACAO_CHECKPOINT.txt` contém saídas da última rodada.

## Próximo trabalho — prioridade técnica

1. Segurança/lifecycle: validar DPAPI/secure storage em dispositivo; sessão inválida no Vault, corrida refresh/logout; bootstrap atualmente pode rotular falha de carregamento como falha de armazenamento; melhorar erro de schema ausente. Preferências cifradas precisam testes de troca real de conta. Revisar todas as exceções amplas, escrita autenticada/RLS e exclusão de conta fortemente confirmada com preservação do espaço familiar. Consentimentos/revogação ainda sem UI completa. Política precisa controlador/contato/retenção e revisão jurídica antes de publicação.
2. Finanças: eliminar cálculos divergentes no chat legado/análise/semestral. Revisar dupla reserva em aquisições, orçamento futuro e compromissos das outras metas. Concluir vínculo aquisição→meta→aporte→compra→conquista, sem dupla baixa. Saved_amount editável pode conflitar com aporte concorrente; precisa controle de versão. p_replace também merece teste de edição concorrente. RPC de despesas tem testes sequenciais, falta estresse concorrente.
3. Renda extra: diagnóstico legado só 4 perguntas; implementar as 7 do prompt. Trilhas ainda usam membro autenticado, não perfil ativo. Faltam métricas, missões, histórico visível, pausa, lembretes opt-in/soneca/reagendamento. Backend possui parte das colunas e trigger histórico, não declarar fluxo completo.
4. Sincronização: fila não ativada; implementar agendamento persistente/backoff/conflitos e integração segura antes de habilitar escrita offline. Tratar dado stale sem chamar sincronizado por sucesso isolado de uma consulta.
5. Nex: arquitetura backend autenticada/autorizações/tools/limites/timeouts/logs mínimos; nenhuma chave LLM no cliente. Fallback local honesto. Pipeline ainda precisa todos os botões com entity_id; motor legado tem respostas informais e promessas a revisar.
6. Mercado: validar permissão/lifecycle/desmontagem da câmera Android (API instalada não possui Camera.dispose); limitar memória de fotos, fechar por gesto também limpar; revisão multiusuário completa; caso editor de item mude ao mesmo tempo que recibo (há locks SQL, falta teste concorrente real). OCR fica dependência explícita somente se fluxo manual completo. Registros de mercado ainda não geram despesa financeira vinculada.
7. UX/arte: Home comparativo mês anterior e insights; análise diagnóstica completa; metas pausadas visualmente claras; diálogo despesas não deve reutilizar payload antigo silenciosamente se campos mudarem após falha; melhorias visuais nos breakpoints; mascote estados realmente distintos (hoje PNG único). Evitar prometer piscada quando só muda src para mesma arte.
8. Importação legada segura: UI destrutiva bloqueada provisoriamente. Existem métodos legados e textos de exclusão semestral que devem ser removidos/revisados. Não ativar importação que apaga dados antes de validar backup.
9. Validar visualmente, resolver SDK/permissões e gerar Windows/APK, executar smoke/login/câmera/offline/teclado em dispositivos. Depois finalizar README, changelog, guia migração/rollback, segurança, matriz requisitos→evidência→pendência e ZIP RELEASE. Docs antigas preservadas são histórico, não evidência da versão 0.18.

## Ambiente e reprodução

Python global `py` 3.14.6 tem Flet/CLI/Desktop/Camera/Charts/Supabase/cryptography. flet-secure-storage wheel extraído em `work/vendor`, não instalado globalmente; pip/venv falharam com permissão de metadata temporária. Instalar requirements em ambiente normal antes de testes em aparelho.

```powershell
py -m unittest discover -s tests -v
py -m compileall -q src
py -m pip install -r requirements.txt
py build_multiplataforma.py both --flutter C:\Users\lucas\flutter\3.44.8
```

No workspace: Ruff em `work/vendor/ruff-0.16.7.data/scripts/ruff.exe`. Node em `C:\Users\lucas\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`; Git em `...\dependencies\native\git\cmd\git.exe`. PGlite 0.5.8 extraído em `work/pglite/package`; harness original `work/test_sql.mjs`. Para ZIP em outro computador: `npm install` na raiz e `npm run test:sql`; não há npm neste ambiente, apenas Node. SQL tests são isolados, nunca usam URL/chave real.

Leia o prompt mestre inteiro e cruze com o código antes de continuar. A lista acima registra limites conhecidos, não dispensa revisão nem autoriza dizer que pendências internas são apenas configuração externa. Continue de onde parou, priorizando integridade dos dados.
