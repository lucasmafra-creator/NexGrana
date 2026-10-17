# Testes — 0.24 QA RC3 UX FIX

- 168/168 testes Python aprovados em Linux com Flet 0.86.5.
- PGlite: migrations até 0.24.2, isolamento e reset QA testados localmente.
- Scan de segredos e integridade da arte Nex aprovados; Golden Nex SHA-256
  `4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796`.
- Testes UI: lista em 360 px, limite útil no desktop 1920 px, chat com histórico
  e composer, consentimentos em 360×800, 390×844, 412×915, 1366×768 e
  1920×1080, ausência de `Container` explicitamente branco em rotas escuras,
  ordem do tutorial e continuidade de conversa de treino.

Não houve execução de renderizador Flutter/Windows ou Android nesta máquina;
testes de árvore de controles não comprovam clipping ou cores renderizadas.
O vídeo do proprietário não foi reproduzível, portanto falta inspeção visual
comparada e screenshots. Não chamar este relatório de aprovação UX.
