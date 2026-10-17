# Auditoria da base — NexGrana 0.23.0 QA RC1

Data: 20/09/2026.

## Escopo inspecionado

- motor financeiro e isolamento pessoa/família;
- chat Nex local, gateway, preferências e escopo assíncrono;
- implementação e assets canônicos do mascote;
- onboarding/tutorial, navegação Windows/Android e teclado móvel;
- cache/fila offline, Achados/admin, migrations e validação de release.

## Achados tratados

1. Conversa ampla dependia demais do fallback local: mensagens gerais agora tentam o gateway autorizado antes do fallback.
2. Histórico online era curto: passou a até 24 mensagens sob orçamento de 12 mil caracteres.
3. Resposta atrasada poderia chegar após troca de conta/conversa: o escopo agora inclui usuário, família, perfil, mês, conversa, geração da sessão e request ID.
4. No Android, focar o composer escondia o cabeçalho/saída: o cabeçalho permanece visível e existe “Fechar teclado sem enviar”, preservando o rascunho.
5. Tutorial era modal estático: virou rota responsiva com central de 13 atividades e sandbox isolado.
6. O Nex tinha movimentos dispersos: recebeu motor central de eventos, estados, cooldown, antirrepetição, preferências e fallback Golden Nex.

## Limitações honestas

- conversa geral 100% online exige gateway HTTPS publicado, provedor configurado e consentimento do usuário;
- nenhum novo pack artístico foi aceito nesta candidata; microanimações usam o Golden Nex existente;
- build/instalação Windows e Android precisam ser executados no ambiente do proprietário;
- iOS continua dependendo de macOS, Xcode e assinatura Apple.

