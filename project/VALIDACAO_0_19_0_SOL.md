# Validação — NexGrana 0.19.0 SOL

## Executado aqui

### Sintaxe/compilação
- `python -m compileall -q src` → OK.
- `validate_release.py` confere versão 0.19.0, arquivos críticos, variantes do Nex e rejeita GIF como variante ativa.

### Testes de núcleo
`python validate_release.py` executou 44 testes e todos passaram:
- motor financeiro/rollover/status de pagamento/rateio/reservas/metas;
- backup local/Vault/criptografia;
- fila de sync em fundação, retry/conflito/idempotência;
- afiliados/ofertas;
- Nex Engine determinístico;
- analytics privacy-first;
- performance monitor;
- Trilha Nex de 10 etapas.

### Descoberta completa
`python -m unittest discover -s tests -v` encontrou 46 entradas. Duas não foram carregadas neste ambiente:
- `test_market_cloud`: `supabase` ausente;
- `test_ui`: `flet` ausente.

Isso é limitação do runtime desta sessão e **não comprova** que os testes pendentes passam.

## Não validado aqui
- Flet renderizado em Windows/Android.
- comportamento real do teclado/IME no Android;
- câmera/permissões Android;
- build `.exe` e `.apk`;
- Supabase/PostgREST/RLS em projeto real ou staging;
- `MIGRATION_0_19.sql` aplicada;
- concorrência real em duas conexões;
- performance p50/p95 em hardware do usuário;
- acessibilidade com leitor de tela/fonte ampliada em aparelho;
- pack final 3D/Rive do Nex (não existe nesta candidata).

## Teste obrigatório no PC do usuário

```bat
py -m pip install -r requirements.txt
py validate_release.py --full
py -m flet.cli run src
```

Depois, no Android, verificar no mínimo:
1. abrir Nex;
2. focar o campo e confirmar que o texto digitado e Enviar permanecem acessíveis;
3. enviar pela seta;
4. enviar por submit/Enter;
5. tocar nas quatro perguntas rápidas;
6. usar `Simular com Nex` em Planejamento;
7. usar `Conversar com Nex` em Trilha;
8. trocar perfil durante/antes de uma nova consulta;
9. fechar teclado/voltar;
10. testar rede instável.

Qualquer falha nesses itens impede classificar a candidata como release pública.
