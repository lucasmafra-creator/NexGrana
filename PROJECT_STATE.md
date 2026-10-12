# Estado atual — 2026-10-11

Fonte de trabalho: árvore NexGrana_SIMLabs, derivada do V7 local comparado ao ZIP V5 anexado. V7 preserva correções de runner/manifesto ausentes no V5. O anexo foi preservado. Não há Git/branch/commit verificável nesta árvore; não foi confirmada equivalência ao repositório remoto ou à cópia instalada no Windows de Mafra.

- NexGrana: fonte 0.24.0; sem mudanças no motor financeiro nesta recuperação.
- SIM Labs QA: protocolo 0.4.1-qa.2, patch de recuperação identificado no manifesto.
- Collector: 0.5.0-integrado; pytest incluído na preparação.
- Entrada única: INICIAR.cmd. Sem regeneração automática do manifesto para esconder divergências.
- SIM_Labs é baseline herdado, não outra fonte de desenvolvimento ativa.

## Hotfix do pipeline após execução Windows bloqueada
O run 4a786e1a apresentou falhas reproduzíveis na fixture de caminho de processos e dependências ausentes para os testes do gateway Nex. Corrigidos: fixture multiplataforma com `Path`; `requirements-qa.txt` inclui `gateway/requirements.txt`; o QA exige FastAPI/Uvicorn e calcula hash dos requirements transitivos; suíte de scripts roda com o Python do venv backend verificado. Ver `QA_REPORT.md`.

## Concluído
Inicialização com identidade/porta/login real; reparo preservando senha; parada tolerante a filhos já encerrados; consulta de PID Windows sem os.kill; aba QA no frontend e estáticos reconstruídos; dependências QA explícitas; manifesto exclui estado volátil; registro condicionado do ZIP Windows completo; abertura da central por sessão local autenticada, sem redigitar senha; logs e relatórios.

O iniciador autentica na API da cópia esperada e passa a sessão de 12 horas ao frontend via fragmento local de URL. O frontend guarda a sessão na aba e limpa o fragmento do endereço. O token não entra no pedido HTTP do fragmento e não é escrito em log.

## Limites
Não há EXE/APK novo nesta entrega. Importações do Collector/artefatos são inspeção, não implantação arbitrária de código. A automação de promoções existente não recebeu nova validação com provedores reais. Skins e identidade Nex foram preservadas, sem novo redesenho. iOS segue adiado. Operação 24/7 exige computador/servidor ligado; este ZIP não configura um serviço remoto.

## Próxima ação
Baixar a revisão atualizada, extrair sobre a mesma pasta substituindo os arquivos e executar `INICIAR.cmd build-windows` uma vez. O iniciador guarda sozinho arquivos extras antigos e preserva `.runtime`, senha e banco. O PNG truncado da skin foco foi restaurado e a suíte visual de skins passou 8/8. O pacote ainda não contém EXE; Windows build e smoke continuam sem validação até essa execução. Android e iOS permanecem em etapas posteriores.
