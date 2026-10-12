# Relatório final — NexGrana 0.23.0 QA RC1

Data: 20/09/2026.

## Arquivos centrais adicionados

- `src/services/nex_conversation.py`: intenções, preferências e escopo assíncrono.
- `src/services/tutorial.py`: catálogo, estados, sandbox e prévia pelo motor financeiro.
- `src/screens/tutorial.py`: rota responsiva “Aprender fazendo”.
- `tests/test_nex_conversation.py`, `tests/test_nex_vivo.py`, `tests/test_tutorial.py`.

## Arquivos centrais alterados

- `src/nex_controller.py`, `src/main.py`, `src/screens/nex.py`, `src/screens/settings.py`.
- `src/services/nex_engine.py`, `src/services/nex_gateway.py`, `gateway/app.py`.
- `src/screens/movements.py`, `src/screens/planning.py`, validação, build, versão e documentação.

## Nex Vivo implementado

- motor central de eventos/estados;
- eventos de abertura, renda, despesa, economia, metas, conta, gasto, investimento, conquista, idle, clique, chat e erro;
- estados idle, olhar, piscar, pensar, alerta, preocupação, calma, comemoração, moedas, pulo, sono, estudo, trabalho, investimento, orgulho e confusão;
- cooldown e antirrepetição de estados/falas;
- configuração desligado/discreto/normal/animado, microanimações, efeitos, som e reduzir movimento;
- reação progressiva a múltiplos cliques;
- fallback de asset otimizado → Golden Nex HD.

Não foram adicionados frames 3D, Rive, Lottie, WebP ou GIF nesta candidata. Sem um pack artisticamente consistente, o Golden Nex perfeito foi preservado.

## Tutorial Nex 2.0

- convite com Começar agora / Explorar sozinho / Lembrar depois;
- rota completa mobile/desktop;
- 13 módulos iniciáveis isoladamente;
- progresso sem valores financeiros;
- sandbox por usuário/família/perfil/sessão;
- fixture R$ 200/R$ 10 validada nos dias 19/20 pelo motor oficial;
- saldo hipotético não pode ser salvo como renda;
- acesso explícito à área real para praticar, mantendo confirmação no formulário oficial.

## Chat

- histórico online até 24 mensagens/12 mil caracteres;
- conversa geral tenta gateway autorizado antes do fallback;
- fallback offline alterna respostas honestas e não repete a frase fixa;
- apelido, tom e detalhe configuráveis;
- Android mantém Voltar visível e oferece fechar teclado sem enviar;
- rascunho preservado;
- resposta atrasada descartada após mudança de escopo.

## Evidências

- 130/130 testes Python: OK;
- SQL até `MIGRATION_0_23.sql`: OK;
- compileall e security scan: OK;
- Golden Nex byte-idêntico: SHA-256 `4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796`;
- processo Flet web permaneceu ativo no smoke test sem traceback após instalar as dependências de execução do ambiente.

## Pendências honestas

- gerar/instalar build 0.23 em Windows e Android físicos;
- medir performance real e testar o teclado em diferentes Androids;
- publicar o gateway HTTPS antes de considerar a conversa ampla online completa;
- iOS exige macOS/Xcode/assinatura;
- novos assets animados dependem de produção artística e comparação visual formal.

