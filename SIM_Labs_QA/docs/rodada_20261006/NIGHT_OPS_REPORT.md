# Operação contínua
Não houve observação noturna/24 horas, reboot Windows ou medição de uptime/downtime do computador do Mafra.

Evidência disponível: watchdog_final.log — terminação restrita do próprio Worker QA Linux e recuperação por supervisor com Engine vivo. http_final.log — API temporária e persistência após restart. Timestamps reais constam dos relatórios de probes quando emitidos; não foram inventados períodos de disponibilidade.

MANUAL_REQUIRED: aplicar boot no clone QA Windows, reiniciar, consultar tarefas/status/heartbeat/logs; registrar HEALTHY/DEGRADED/OFFLINE/RECOVERING a partir de resposta e timestamps reais, confirmar bateria/logoff e retorno. Somente então observar uma noite e calcular disponibilidade. Não fechar missões por restart isolado.
