# Relatório de testes — candidata 0.24.0 QA RC1

Executado em Linux com Python 3.12, Flet 0.86.5 e dependências de
`requirements.txt`/`gateway/requirements.txt` em `.venv` local.

- `python -m unittest discover -s tests -q`: **156 testes OK** na rodada de
  validação; o empacotador repete a suíte antes de gerar o ZIP.
- `python -m compileall -q src gateway tests`: sintaxe Python verificada.
- `python -m pip check`: sem requisitos quebrados após resolver PyJWT.
- Arte canônica `src/assets/nex/nex_hd.png`: SHA-256
  `4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796`.
- UI: instancia telas do tutorial para cada uma das 13 atividades em 360 e
  900 px; testa Mercado/listas e Achados em 360 e 1200 px. Verifica saldos
  individual/familiar, diferença visual aquisição/meta e falha de itens da
  lista sem converter erro em lista vazia.
- Regressões: saldo pessoal, contas futuras, isolamento de perfis,
  investimentos, sessões/offline, Nex e filtros continuam na suíte.
- Segurança do gateway: teste isolado confirma consentimento, revogação,
  indisponibilidade fail-closed e rejeição de redirects; **não é teste com
  Supabase ou provedor reais**.
- Listas: payload carrega `household_id` para o filtro da cópia offline e a
  migração liga cada item ao mesmo espaço da lista. Restrição SQL/RLS ainda
  precisa ser exercitada em banco de QA com duas contas.
- `python security_scan.py`: varredura estática local OK; não substitui
  pentest, teste de RLS real nem auditoria de credenciais.

Não executados aqui: migração SQL em banco real, RLS A/B, retenção do histórico
após fechar APK/EXE real, autenticação contra Supabase de homologação, acesso
ao provedor LLM e consumo/custo, verificação visual com teclado Android,
build Windows/APK e assinatura iOS. Não tratar esta candidata como pronta
para publicar enquanto esses itens e as lacunas do README estiverem abertos.
