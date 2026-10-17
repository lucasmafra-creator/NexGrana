# NexGrana 0.24 — recorte visual P2 (candidata de código)

Esta rodada aplica um primeiro recorte implementado a partir das referências mobile e desktop de 30/09/2026. Não é a implantação integral do prompt do Astra, nem uma release Windows/Android aprovada.

## Alterações implementadas

- Tokens centrais com navy, violeta e ciano; três temas com superfícies e bordas distintas.
- Prévia clicável dos três temas em Mais → Aparência, com persistência já existente por conta e espaço.
- Home com card do Nex reorganizado, ação de conversa, saldo/projeção e resumo explícito de entradas e saídas; navegação desktop com seleção mais evidente.
- Painéis de Análises, Aquisições, Tutorial, Renda Extra, Investimentos e Planejamento agora usam a paleta ativa em vez de manter um fundo violeta fixo no tema claro.
- O registro de despesa agora distingue pagamento único de parcelamento e apresenta a soma das parcelas antes da confirmação; a operação financeira subjacente permaneceu igual.
- Três novas poses transparentes do Nex: acolhendo, pensativo e comemorando. O master `nex_hd.png` foi mantido sem alterações (SHA-256 `4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796`). As novas poses são usadas somente na Home, evitando trocar os outros estados sem inspeção visual.
- Novo teste de integração estrutural da Home/asset e atualização do teste de paleta alterada legitimamente.

## Verificação neste ambiente

- Python: 170 testes aprovados com dependências locais reaproveitadas.
- SQL: `node tests/test_sql.mjs` aprovado.
- `compileall` aprovado.
- Três PNGs verificados como RGBA com transparência real.
- Não houve execução visual em Windows ou Android, instalação, EXE ou APK nesta rodada. A aparência final e o impacto de desempenho continuam pendentes de inspeção nos aparelhos.

## Estado dos 11 feedbacks do Collector

1. Skins Nex: três novas poses da Home implementadas; galeria sazonal e preferências de skins pendentes.
2. Reset de homologação: pendente de reprodução no backend real e inspeção do erro da evidência.
3. Aparência: tema central e prévia implementados parcialmente; falta revisar todas as telas e contraste.
4. Exportação/exclusão: pendente.
5. Valor de parcela: rótulo e prévia do total implementados; validar a interação em Android e Windows.
6. Mercado/Achados visível: pendente.
7. Lista integrada à compra: pendente.
8. Administração de Achados: pendente de painel e fontes de ofertas aprovadas.
9. Chat Android: pendente de reprodução e teste no aparelho.
10. Idiomas: pendente.
11. Seleção de perfis: pendente de avaliação e implementação.

Os rótulos P0/P1/P2 foram preservados no feedback original; esta entrega aborda especificamente o recorte visual P2, sem reclassificar ou dar baixa aos demais.

## Regras de aceite para a próxima integração

Abrir o app nas resoluções 360×800, 390×844, 412×915, 1366×768 e 1920×1080; verificar espaços, quebras de linha, teclado, contraste, hit areas, tema claro, fundo transparente e tamanho do pacote. Comparar tela real com as artes de referência. Corrigir regressões antes de expandir o sistema visual a todas as telas. Manter Nex Online congelado por custo conforme o prompt vigente e isolado do fluxo financeiro.

A imagem desktop contém valores e classificação de saúde ilustrativos. O código desta rodada usa apenas o resumo determinístico do perfil ativo. Não se deve reproduzir os valores da arte em produção.
