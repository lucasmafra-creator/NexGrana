# Instruções de agentes — NexGrana

## Continuidade e segurança de produto
Leia `README.md`, `NEXGRANA_RULES.md`, `PROJECT_STATE.md`, `LEIA_PRIMEIRO_QA.md` e os documentos de release/testes pertinentes antes de alterar o app. Regras canônicas financeiras, privacidade, isolamento de perfis, segurança, identidade da coruja roxa Nex e release prevalecem sobre qualquer sugestão estética. Nunca mascarar erro de saldo, usar dados reais em teste, enfraquecer RLS ou substituir a identidade aprovada.

## Skills de interface
Consultar Impeccable (Apache-2.0: https://github.com/pbakaus/impeccable) em UI financeira de produto: clareza, hierarquia, acessibilidade, responsividade, estados de erro e confiança. Usar Taste-Skill (MIT: https://github.com/Leonxlnx/taste-skill) apenas em páginas públicas de marketing; para redesign de interface existente, consultar `redesign-existing-projects`. Não aplicar a skill Taste principal a dashboard, fluxo de lançamento ou telas financeiras.

Instalar no runtime da tarefa visual, sem presumir que este arquivo instala o pacote: `npx impeccable install`; Taste: `npx skills add https://github.com/Leonxlnx/taste-skill --skill design-taste-frontend` ou `--skill redesign-existing-projects`. Confirmar arquivos/runtime e revisar o diff de setup antes de declarar instalado. Taste requer Node 22+ e Chrome/Edge/Chromium para inspeção real; sem isso, marcar BLOCKED/NOT RUN. Todo asset precisa preservar a coruja Nex, conferir licença/crédito e não reduzir qualidade aprovada.

Esta regra não instala skills automaticamente nos runtimes locais. Registrar estado por runtime como `INSTALLED`, `NOT INSTALLED`, `BLOCKED` ou `NOT VERIFIED`, com versão e evidência.