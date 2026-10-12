# Validação real
Host Linux, Python 3.12.14. Flet 0.86.5; Supabase 2.31.0; Pillow 12.3.0. Dependências de frontend registradas nos lockfiles. Comandos e logs completos: results.json e arquivos .log.

| Check | Resultado | Quantidade | Segundos de comando |
|---|---|---:|---:|
| nex_python | PASS | 207 | 1.729 |
| sim_backend | PASS | 88 | 10.119 |
| collector | PASS | 3 | 0.257 |
| sql | PASS | 117 | 3.161 |
| sim_frontend | PASS | build | 0.794 |

As 85 linhas SQL são verificações/scenarios no PGlite, não 85 testes de dispositivo ou Supabase remoto. UI Python usa controles fake, sem teclado Android real. A regressão do Nex também passou no runner manual com source oficial inalterada; nexgrana-run-report.json.

Probes reais Linux: watchdog_final.log registra Worker de QA terminado pelo próprio PID e recuperado com Engine vivo; http_final.log registra integração HTTP em ambiente temporário, Collector, deduplicação, evidência, gate CEO e persistência de pausa após restart. Não equivalem a reboot Windows ou 24 horas.

Falhas preservadas: runner-before-fix.json registra dependências ausentes após resolução incorreta do symlink da venv. Corrigido e coberto por regressão; execução posterior PASS. Tentativa HTTP inicial sem permissão para serviço local não iniciou API; probe posterior permitido passou. Não houve falha final nas suítes acima.

BLOCKED: host Windows, Flutter/SDK/ADB, Moto G22, Supabase staging autenticado e validação de assinatura/instalação dos binários. Scripts CMD/PowerShell são entregues para validação no host, não declarados executados aqui.

## Novas regressões RC7
Nota→despesa: isolamento familiar, membro inválido, rollback, total bruto, rateios, reenvio idempotente, retry divergente e despesa removida não ressuscitada. Mercado: desfazer offline em ordem, isolamento de perfil, bloqueio por edição posterior, soft delete, normalização UTC e precisão da quantidade. UI: escolha explícita e clique duplo não criam duas despesas. Transporte reconsulta dados autoritativos. OCR: Tesseract real em foto sintética Arroz 12,90.
As primeiras regressões desta extensão falharam por referência do teste a um helper não anexado à classe e por duas instruções SQL na chamada preparada da fixture. Fixtures corrigidas; versões finais PASS. Falhas de infraestrutura/comandos anteriores não foram convertidas em evidência de produto.
