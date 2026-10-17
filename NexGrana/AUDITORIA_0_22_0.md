# Auditoria da base — NexGrana 0.22.0 QA

Base confirmada: código 0.21.0 QA RC3, preservado no mesmo projeto e sem recriação da stack. A validação inicial passou 90 testes Python e toda a cadeia SQL até a migration 0.21.

## Achados confirmados

- `HomeScreen` usava “Consolidado da família” mesmo com `household.mode=individual`.
- O Nex resolvia intenções financeiras, mas o fallback era genérico para perguntas amplas; `nex_gateway.py` só preparava payload e não executava integração.
- O tutorial tinha altura fixa e pouco conteúdo útil, produzindo área vazia em telas pequenas.
- As dez etapas de Renda Extra eram iguais para qualquer atividade.
- O painel de Achados não possuía imagem, prévia, exclusão, filtros nem testes próprios.
- O app já possuía cache cifrado, fila offline, navegação sem remontar a página, correções de autenticação e formulário de Mercado responsivo. Esses pontos foram preservados.

## Limites externos

- Login real, reset QA real, painel conectado e gateway online dependem do projeto Supabase/homologação e de credenciais sob controle do proprietário.
- Não foi publicado servidor, comprado provedor, criado domínio ou gerado instalador.
- iOS continua bloqueado até existir Mac com Xcode, assinatura e conta Apple.
