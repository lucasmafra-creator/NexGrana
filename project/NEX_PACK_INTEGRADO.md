# NEX PACK — estado integrado na 0.19.0

## Fonte canônica
O runtime usa `src/assets/nex/nex_hd.png` como master RGBA transparente e gera/usa derivados por tamanho:

- `nex_hero.png`
- `nex_card.png`
- `nex_dock.png`
- `nex_avatar.png`

A seleção fica centralizada em `src/nex_controller.py` e declarada em `src/assets/nex/manifest.json`.

## O que foi descontinuado
Os antigos GIFs/frames de `clean`, `clean2`, `display`, `animations`, `actions` e `expressions` não eram adequados à qualidade pública e não são mais usados/empacotados como fonte ativa do personagem.

Não reintroduza esses caminhos no código.

## Estados atuais
O controlador mantém estados semânticos (`idle`, `thinking`, `alert`, `worry`, `celebrate`, `coins`, `jump`, `sleep`, etc.) e aplica micro-movimentos sobre a arte canônica.

Isso é um **fallback visual de alta nitidez**, não um rig 3D final.

## Próxima etapa de arte
Antes de adotar Rive/Lottie/WebP/sprites:
1. produzir um pequeno pack de estados realmente distintos a partir da Character Bible;
2. padronizar canvas, pivô, escala e alpha;
3. testar Windows e Android;
4. medir memória/decode/FPS;
5. somente então escolher o formato definitivo.

GIF tradicional deve permanecer apenas como legado excepcional, não como formato principal do Nex.
