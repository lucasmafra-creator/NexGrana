# Checkpoint — NexGrana 0.19.0 SOL Virada

## Base
Continuação incremental da 0.18.1 SOL RC2, orientada pelo prompt refinado pelo Astra. Não voltar a versões anteriores para novas correções.

## Implementado nesta rodada
- versão 0.19.0;
- pipeline único do Nex com request/contexto e atualização parcial do chat;
- foco Android/composer e bottom navigation adaptativa;
- host persistente de navegação para reduzir flicker;
- poll de sincronização em 15 s;
- Nex canônico RGBA e derivados por tamanho; GIFs degradados desativados/removidos do runtime;
- design tokens e tamanho seguro de diálogos críticos;
- Renda Extra em 8 dimensões;
- Trilha Nex em 10 etapas + métricas/notas/lembrete in-app;
- comparação parcial de mês em Análises;
- arquitetura mínima de ofertas/afiliados independente da recomendação;
- analytics privacy-first desligado por padrão;
- migration 0.19 aditiva;
- 44 testes de núcleo passando neste ambiente.

## Pendências que não devem ser escondidas
- Android real: validar teclado, quick actions, envio e câmera;
- Flet/Supabase: suíte completa não roda neste runtime por dependências ausentes;
- Windows/APK: não gerados aqui;
- RLS/PostgREST/migration 0.19: validar em staging;
- pack final do Nex com expressões/rig 3D realmente distintos ainda não existe;
- OCR não está pronto;
- escrita offline permanece desativada até E2E de fila/conflitos;
- analytics remoto continua desativado;
- parceiros afiliados precisam de termos/aprovação por plataforma.

## Próximo ciclo
1. instalar requirements em ambiente normal;
2. `py validate_release.py --full`;
3. smoke Windows;
4. APK em Android real;
5. corrigir qualquer P0/P1 observado;
6. staging Supabase e migration 0.19;
7. só então classificar como release pública.
