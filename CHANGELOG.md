# Recuperação 2026-10-10

- INICIAR.cmd com menu único de diagnóstico, execução, testes, build e acesso.
- Inicialização confirma health, service, phase, instance_id e POST de login antes de abrir navegador.
- Reparo mantém senha, hash e chave de sessão; leitura suporta UTF-8 com BOM.
- Parada revalida a propriedade de cada processo e tolera filhos encerrados pelo supervisor.
- Liveness Windows usa APIs de processo; não usa os.kill(pid, 0).
- Gestão de hoje incluída no frontend fonte e estáticos reconstruídos.
- Collector instala pytest. Flet CLI e desktop Windows constam em requirements-qa.txt.
- Preparação acompanha hash dos requirements; não reinstala a cada execução quando inalterados.
- Manifesto ignora bancos/WAL/SHM, backups, runtime, .data, caches e artefatos gerados; não é refeito automaticamente na inicialização.
- Builds só aceitam artefatos novos da execução; Android exige etapa explícita após Windows.
- Opção 4 registra o pacote Windows completo com verificação de hashes; não executa/publica o binário.
- Doctor coleta ferramentas, imports, sintaxe, banco QA somente leitura, permissão de runtime e inspeção técnica de imagens. Não aprova estética/serrilhado automaticamente.
- Regras financeiras, dados reais, identidade canônica e skins existentes preservados.

## Hotfix QA Windows — 2026-10-11

- Corrigida fixture dos testes de parada para caminhos nativos Windows.
- Dependências FastAPI/Uvicorn do gateway adicionadas ao ambiente de QA do Nex; detector e doctor agora também as verificam.
- Hash do ambiente inclui requirements aninhados, evitando venv desatualizado quando muda `gateway/requirements.txt`.
- Suíte de regressão do SIM Labs executada no venv QA backend já preparado, em vez de depender do Python global.
- Nenhuma regra financeira, dado de usuário ou identidade visual do Nex foi alterada. O EXE ainda depende do build Windows passar.

## Hotfix de pasta sobreposta — 2026-10-11

- O erro genérico de integridade agora exibe as divergências concretas.
- Arquivos de código antigos extras deixados por extração sobre uma pasta anterior são movidos, com conteúdo preservado, para `SIM_Labs_QA/.runtime/source-quarantine`; senha, banco QA e dados locais permanecem intactos.
- Arquivos versionados com hash divergente, fontes ausentes e inconsistências do manifesto continuam bloqueando a execução sem alteração automática.
- A reparação é reversível e coberta por testes. O manifesto não é regenerado para mascarar diferenças.

## Correção do asset Nex foco — 2026-10-11

- Restaurado `NexGrana/src/assets/nex/skins/cutouts/foco_v3.png` da fonte V5 íntegra: RGBA 768×768, 499.761 bytes; hash confere com o manifesto canônico de skins.
- O arquivo entregue anteriormente tinha 171.520 bytes e estava truncado. Os outros 146 PNGs do app foram lidos integralmente sem erro.
- Suíte `test_privacy_and_skins.py`: 8/8 PASS após a restauração.


# Correção do acesso pela tela — 2026-10-11

- A central era validada pelo iniciador, mas depois a senha era digitada outra vez numa página que podia pertencer a outra cópia ou receber erro de digitação.
- O fluxo normal agora valida a identidade e a senha da instalação e abre a tela já autenticada. O token de 12h é carregado de um fragmento local, transferido para sessionStorage e removido imediatamente da barra de endereço.
- O serviço continua limitado a loopback. Senha e token não são impressos nem salvos em novo arquivo. O formulário manual continua como fallback.
- Cobertura: pasta/instância incorreta é bloqueada antes de enviar a credencial; login inválido não abre sessão; a URL carrega o token como fragmento.
