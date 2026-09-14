# NexGrana 0.17 — Auditoria técnica antes da virada

## Resumo
A base atual funciona, mas ainda é um protótipo avançado, não uma versão de produção. O foco da 0.17 é corrigir falhas funcionais críticas, reduzir superfícies de segurança e criar uma base explícita para a reconstrução visual/arquitetural da próxima grande versão.

## Achados principais no código
- `src/main.py` concentra milhares de linhas e responsabilidades de UI, regras financeiras, chat, navegação, Mercado e Planejamento. Isso aumenta risco de regressão e precisa ser dividido por módulos.
- O Nex tinha múltiplos caminhos de entrada (`send`, sugestões, Planejamento, Aquisições, Trilha Nex). Alguns apenas inseriam texto no histórico sem gerar resposta, especialmente perceptível no Android. A 0.17 centraliza o pipeline em `_process_nex_message()`.
- O motor do Nex é determinístico/local e baseado em regras. Não deve ser apresentado como LLM generativo completo. Para a versão final, a IA conversacional deve ficar atrás de backend seguro e chamar ferramentas determinísticas para números.
- Sessão e cache são gravados localmente. A 0.17 remove sessão/cache ao sair da conta, mas para produção deve-se migrar tokens para armazenamento seguro do SO e criptografar cache offline.
- A publishable key do Supabase pode permanecer no cliente; `service_role`, chaves de IA e outros segredos nunca podem entrar em APK/EXE.
- O schema original continha uma policy `members join self` que, combinada com conhecimento do UUID da família, ampliava a superfície de entrada direta. A migration `SUPABASE_SECURITY_0_17.sql` remove esse caminho e exige a RPC com invite code.
- Policies de Mercado com `FOR ALL ... created_by=auth.uid()` poderiam impedir edição familiar de registros criados por outro membro. A migration separa INSERT de UPDATE/DELETE.
- Novos códigos de convite passam de 8 para 16 caracteres hexadecimais.
- Existem vários `except Exception` amplos. Na versão final, substituir por exceções específicas e logging estruturado sem PII/valores sensíveis.

## LGPD / privacidade — requisitos de produção
- Privacy by design/default.
- Finalidade, adequação, necessidade/minimização e transparência por categoria de dado.
- Centro de privacidade: acesso/exportação, correção, exclusão de conta/dados quando aplicável, revogação de consentimentos opcionais e informações sobre compartilhamento.
- Registro/versionamento de política de privacidade e termos.
- Dados financeiros não devem ser vendidos nem usados para segmentação publicitária sem base legal clara e transparência.
- Analytics deve ser minimizado e, quando possível, agregado/pseudonimizado.
- Backup e logs não devem vazar tokens, e-mail, saldos ou descrições financeiras.
- Plano de incidente, rotação de chaves, backups e restauração testados.
- Revisão jurídica antes da publicação pública; este documento é orientação técnica, não parecer jurídico.

## Monetização adotada como princípio
O app gratuito não deve ser degradado para forçar pagamento.

1. **Afiliados transparentes**: uma área opcional `Achados Nex` pode abrir links de afiliado. A recomendação financeira nunca deve ser alterada por comissão.
2. **Oferta contextual futura**: apenas se combinar com aquisição/necessidade registrada, sem usar PII fora do NexGrana e com explicação clara de que é link de afiliado.
3. **Premium opcional futuro**: recursos de conveniência/automação avançada, nunca bloquear controle financeiro básico, exportação ou segurança.
4. **B2B/white-label futuramente**: versão para pequenas empresas/educação financeira, separada dos dados pessoais.
5. **Sem dark patterns**: nada de urgência falsa, preço inventado, "últimas unidades" falsa, anúncios que pareçam recomendação neutra ou venda de dados.

## O que a 0.17 já muda
- Pipeline único do Nex para texto, atalhos e chamadas contextuais.
- Diagnóstico guiado inicial de renda extra.
- Resposta estruturada para Trilha Nex.
- Simulação numérica mais explicativa de metas.
- `Vídeos para se aprofundar` em vez de links repetidos.
- Área inicial `Achados Nex` com disclosure explícito de afiliado.
- Limpeza de cache local pela interface e no logout.
- Convites novos mais longos.
- Migration SQL de hardening/RLS.
