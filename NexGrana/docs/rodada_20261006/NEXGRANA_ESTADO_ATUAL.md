# NexGrana + SIM Labs — RC8, 2026-10-06 (horário local)
Estado: candidata de QA com código e assets atualizados; homologação nativa BLOCKED.

As fontes foram recuperadas dos ZIPs RC6 do NexGrana e SIM Labs 0.4.0 e editadas em cópias isoladas. Os caminhos Windows informados pelo Mafra não estão acessíveis neste host Linux. A instalação ativa, tarefas agendadas, credenciais de staging e aparelho não puderam ser consultados. A fonte SIM disponível não contém necessariamente todos os módulos Observer/Bridge/Runner adicionados à instalação ativa.

Implementado nesta rodada: fechamento mensal remoto em lote atômico, proteção contra saldo de mutações rejeitadas, avisos acionáveis para schema ausente; base offline curada; histórico capturado por requisição do Nex; exclusão por período e tombstones sincronizáveis; orçamento de compras com restante, confirmação e histórico de alterações; OCR local opcional com confirmação; diagnóstico de homologação; 36 skins transparentes com variantes compactas. Achados agora possui painel integrado ao SIM Labs para ofertas, fontes autorizadas, coleta revisável e catálogo comercial com ponte explícita. Leia ANALISE_ENTREGA_RC8.md para os limites e passos.

Nex Online permanece congelado. Nenhuma migration de produção, publicação, instalação ou envio externo foi realizado. Não existe nesta entrega EXE/APK gerado. Os seis feedbacks continuam OPEN aguardando evidência em dispositivo.

Faltam antes da homologação: validar Supabase staging, compilação Windows/Android, instalação real, teclado/voltar/rotação/offline no Moto G22 e comparação visual nas dimensões pedidas. Mercado agora oferece compra→despesa atômica/idempotente e desfazer edição, exclusão e limite, validados em testes de código/SQL. Homologação física permanece pendente. A integração automática de ofertas depende de feed autorizado. iOS fica depois dos gates Windows/Android.
