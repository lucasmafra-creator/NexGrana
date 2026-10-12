# Candidata QA RC4 — tutorial e diagnóstico do Nex

- Tela fotografada: etapa Privacidade do tutorial ocupava a área com um bloco cinza. Substituídos os switches em linhas flexíveis por três caixas de seleção em cartões compactos, cada uma com explicação e gravação restrita ao treino. Verificação automatizada: suíte Python local e migrações SQL locais.
- Nex online: `src/build_config.py` continua com `NEX_GATEWAY_URL` vazio; não há evidência de gateway público ativo nem chaves do provedor no servidor. O diagnóstico `diagnosticar_nex_online.py` verifica configuração e `/health` sem imprimir credenciais.
- Para Windows: na pasta `project`, execute `..\.venv\Scripts\python diagnosticar_nex_online.py` (ajuste o caminho do Python se necessário). Para Android: publique o gateway seguro e preencha **apenas a URL HTTPS pública** em `src/build_config.py` antes de compilar novo APK. Siga `README_NEX_ONLINE_0_24_RC2.md` para configurar ambiente e testar consentimento e resposta real.
- **Não validado:** renderização em Windows/Android e conversa online real. `/health` isolado não prova autenticação, Supabase, consentimento ou resposta do provedor.
