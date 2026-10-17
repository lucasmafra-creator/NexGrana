# Evidências de teste — QA RC2

Ambiente local Linux, Python do venv Flet 0.86.5, PGlite 0.5.8.

- `python validate_release.py --full`: **159 testes Python OK**, compileall
  e `security_scan.py` OK; asset Nex SHA-256
  `4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796`.
- `node tests/test_sql.mjs`: migrações 0.18 a 0.24.2 aprovadas localmente;
  isolamento entre famílias, escrita de renda/despesa entre integrantes,
  reset de QA marcado/não marcado/repetido e saída de membro QA aprovados.
- Testes específicos novos: UPDATE/DELETE com zero linhas não viram sucesso;
  Nex não repete requisição com resultado ambíguo; alternância de três temas e
  isolamento entre UID/espaços.

**Não testados neste ambiente:** migrations no FinanceHub, JWT/consentimento
com Supabase real, gateway com provedor real, instalação Windows e Android,
teclado/safe area no dispositivo, migração de usuário já existente. O SQL em
PGlite não substitui RLS exercida contra Supabase hospedado.
