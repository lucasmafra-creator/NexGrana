# NexGrana 0.23.0 RC2 — correções locais preparadas

Esta revisão corrige problemas que podem ser resolvidos no cliente sem inventar infraestrutura externa.

## Corrigido no código

- Tutorial passa a ocupar a janela inteira em desktop/notebook, sem a sidebar principal competindo com a experiência.
- Tutorial virou fluxo guiado com `Passo anterior`, `Próximo passo` e `Pular tutorial completo`.
- Saída antecipada do tutorial exige decisão explícita entre manter ou descartar os dados de treino.
- Renda, despesa, aquisição, metas, investimentos, renda extra, mercado e demais módulos ganharam campos de simulação isolados.
- Dados do treinamento continuam separados dos registros reais e não são promovidos automaticamente.
- Consentimentos de privacidade passam a ter cache local protegido; em rede instável/Android, a escolha não some apenas porque o Supabase falhou naquele instante.
- O Nex recebe microanimação também na área de conversa/desktop, reaproveitando o Golden Nex sem introduzir GIF de baixa qualidade.
- O selo `online` agora só indica uma resposta realmente online; quando o gateway está apenas configurado, mostra `online pronto`.

## Limitação que NÃO pode ser fingida como corrigida

O chat geral online depende de um gateway HTTPS real. O projeto contém o servidor em `gateway/`, mas `src/build_config.py` não possui URL pública configurada. Sem publicar esse serviço e fornecer `NEXGRANA_NEX_GATEWAY_URL`, perguntas gerais continuarão entrando no fallback local. Não é seguro embutir a chave OpenAI no APK/EXE.

Use `PROMPT_WORK_URGENTE_NEX_ONLINE_TUTORIAL.md` para a etapa que exige publicação/configuração do gateway e QA ponta a ponta.

## Validação executada neste ambiente

- `py_compile`: arquivos alterados OK.
- 81 testes unitários independentes de Flet/Supabase: OK.
- A suíte completa não pôde ser executada neste ambiente porque Flet/Supabase não estão instalados no runtime do container. No PC do projeto, rode `validate_release.py --full` e toda a suíte antes de chamar de release.
