# Usar o SIM Labs local

1. Abra o Update Collector e clique em **Abrir SIM Labs QA**.
2. Em **Builds e verificações**, escolha o alvo e importe o ZIP, APK/AAB ou pacote Windows.
3. Leia os checks e o SHA-256. O console não inicia o aplicativo recebido.
4. Para um ZIP confiável de código-fonte, clique em **Executar testes do ZIP** e aceite o aviso. Dependências não são baixadas.
5. Importe todas as partes do Collector em **Feedbacks**. IDs iguais são mesclados e o status de QA existente é preservado.
6. Em **Checklist de dispositivo**, marque somente o que você verificou no build selecionado.
7. Salve o relatório JSON/Markdown e revise cada feedback. Build verde ou teste verde não altera o status automaticamente.

Os registros ficam em `data/sim_labs/`. Faça backup da pasta ao trocar de computador. O compartilhamento para um serviço remoto ainda não está habilitado.
