# Matriz de requisitos — NexGrana 0.21.0 QA

| Requisito | Estado | Evidência/limite |
| --- | --- | --- |
| Integridade de saldo e vencimento | Implementado | suíte de finanças preservada |
| Cache isolado por usuário/família | Implementado | cofre cifrado e sessão confiável obrigatória |
| Leitura local rápida | Implementado | `fetch_all` prioriza cache validado |
| Fila offline idempotente | Implementado para operações principais | inclusão, edição e exclusão ordenadas; UUID estável, fila cifrada, backoff e recuperação após interrupção |
| Cadastro claro | Implementado | modos separados, confirmação e ajuda de senha |
| Remover localhost | Código e documentação implementados | exige URL HTTPS/allowlist externa |
| Troca criar/entrar em família | Implementado | formulários independentes, atualização local |
| Tutorial opcional | Implementado | oferta por abertura, pular, dispensar, replay |
| Chat Android utilizável | Implementado em código | exige teste visual no Android real |
| Mercado com teclado | Implementado em código | painel rolável e ações em blocos; exige teste real |
| Privacidade responsiva | Implementado em código | blocos roláveis e ações internas |
| Achados com busca/filtros | Implementado | busca acento-insensível e categoria |
| Administração exclusiva | Implementado em código/SQL | RLS por UUID, auditoria; exige deploy separado |
| Reset da conta QA | Implementado em código/SQL | só projeto de homologação, UUID autorizado e família unitária |
| Nex seguro e conversação local | Implementado | gírias e intenções cobertas localmente; números determinísticos; testes de prompt injection |
| Nex amplo e multilíngue | Fronteira preparada, não ativada | depende de gateway LLM seguro, consentimento e avaliação real de custo/qualidade |
| iOS | Preparado | build exige macOS/Xcode; teste é a próxima fase |
| “Viral garantido” | Não é promessa válida | produto inclui base para uso recorrente e compartilhamento voluntário |
