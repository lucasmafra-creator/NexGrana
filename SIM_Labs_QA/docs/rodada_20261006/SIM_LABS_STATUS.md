# SIM Labs — estado verificável
Fonte 0.4.0 preservada, Collector presente. Backend 88 testes após inclusões desta rodada; frontend compilado. Engine/Worker e integração HTTP exercitados em QA temporário Linux. A API Windows 127.0.0.1:8000, SQLite instalado, tarefas Runner/Bridge e últimas execuções não são acessíveis daqui.

Engine mantém processamento/triagem existentes. Novo runner exige execução manual de Mafra sobre fonte confiável; não há isolamento de rede/arquivos. Relatório vai ao Release & QA por evidência e hash, não dispara programa nem promove DONE. Registro de EXE/APK pronto no código; nenhum artefato nativo foi registrado na instalação ativa.

INSTALAR_NO_BOOT.bat é opt-in: Startup+Logon/S4U, privilégios mínimos e bateria permitida. Requer administrador para registrar tarefas; sem credenciais de rede/EFS via S4U. Máquina desligada/suspensa não opera. Não foi aplicado nem testado em reboot Windows.

Antes de aplicar, comparar com Observer/Bridge/Runner já instalados e preservar configurações, bancos, .runtime, feedbacks, missões, evidências e agendamentos. Pacote fonte disponível não prova equivalência com instalação ativa. Usar diff revisável e clone QA, nunca copiar toda a pasta sobre instalação operacional.

## RC7
verify_nex_assets.py executado aqui: 72 variantes PASS em checks técnicos/hashes. Não declara criatividade, melhoria automática ou aprovação visual nativa. CONCLUIR_RODADA_QA.cmd prepara testes, auditoria e build e aceita registro opcional, mantendo instalação/execução de binários separadas. O novo comando ainda requer validação Windows.


## RC8 — Ofertas & links
Painel local do CEO e conectores restritos foram adicionados. A fila coleta feeds autorizados; erros de token viram EXTERNAL_BLOCKER. Revisões e pausas persistem. `scripts/publish_offer_catalog.py` só faz preview por padrão; quando indicado, usa sessão administrativa e RPC comercial. A coleta real e o publish real ficam bloqueados até acesso AWIN/ML autorizado e projeto Supabase de staging. Validação real em HTTP com dados sintéticos confirmou painel atualizado servido, preview do catálogo e ausência de ofertas escritas sem credenciais. Nex Finance RLS continua separada; PGlite cobriu RLS de Achados, host, admin, expiração, replay e rollback.
