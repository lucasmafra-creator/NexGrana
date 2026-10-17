# Estado candidato 0.24.0 (não substituir estado oficial 0.23)

> Checkpoint histórico. Após os testes do proprietário, a referência atual
> passou a ser `NEXGRANA_ESTADO_ATUAL.md`, acompanhada de
> `AUDITORIA_LACUNAS_0_24_RC1.md`. Este arquivo não registra sozinho as lacunas
> de Nex online, personalização e sandbox QA confirmadas depois.

O estado oficial anterior em `NEXGRANA_ESTADO_OFICIAL_0_23_0.md` continua
congelado até Mafra aprovar testes em Windows e Android e declarar
“aguarde testes”/aprovar a atualização da memória canônica.

## Stack e empacotamento

Python com Flet 0.86.5, Flutter 3.44.8 para builds na máquina do proprietário,
Supabase e gateway FastAPI opcional. `pyproject.toml` e título da UI indicam
0.24.0 QA. `package_release.py` aceita a pasta extraída `project`, executa
a suíte, gera um único ZIP com raiz `NexGrana_0_24_0_QA_RC1/project`, confere
o manifesto com SHA-256 em `verificar_pacote.py`, grava SHA256SUMS; não inclui
`.venv`, caches, dist ou segredos. Scripts CMD dentro de `project`.

## Domínio e produto preservados

Renda efetivamente recebida soma na competência; despesa futura não debita
antes do vencimento; saldo pessoal nunca incorpora outro perfil; consolidado
não conta compartilhada duas vezes; falha de dados nunca inventa valores.
Aquisição é intenção, meta é compromisso, investimento é projeção e renda
extra é oportunidade para o usuário. Achados exibe afiliados externos para
o negócio, sem contaminar recomendação financeira. Seis URLs iniciais
permanecem configuradas e o painel externo administrador segue protegido.

## Alterações e limites desta candidata

Tutorial e cálculos em `src/services/tutorial.py`, `tutorial_activities.py` e
`src/screens/tutorial.py`: 13 módulos, dados sintéticos isolados, progresso
por usuário/espaço/perfil sem depender de refresh do JWT; não marcar módulo
como praticado só ao avançar. Simulador de saldo usa Decimal, prévia atualiza
com edição válida e limpa resultado com valor inválido. Promoção exige marcar
o que será realmente lançado; itens salvos/pendentes não reaparecem. Investimento
e compras têm simulação própria. Não alegar chat de treinamento LLM: ele é
local e não envia extrato real. Sandbox não substitui revisão final no app real.

Nex `src/services/nex_engine.py`: perguntas sobre conexão recebem resposta
local baseada no estado, não na suposição de internet; gateway ausente fica
“local”. `src/services/nex_gateway.py` aceita somente HTTPS `/v1/chat`,
não segue redirects portando Bearer token. `gateway/app.py` consulta
`privacy_consents` por JWT do usuário e RLS antes de chamar provedor;
nega se autorização revogada/não verificável; não trata dicionário financeiro
do cliente como extrato real. **Online ainda não homologado**, e a integração
financeira LLM baseada em ferramentas server-side ainda não existe.

Mercado `src/screens/market.py` separa Compras/listas e Achados. Listas
(`src/cloud.py`, `MIGRATION_0_24.sql`) são pessoais por padrão, criadas
com perfil ativo, têm itens, preço, quantidade, marcar comprado e orçamento.
Itens carregam `household_id` e a migração exige que item e lista pertençam
ao mesmo espaço, para que leitura/cache offline não falhem nem cruzem espaços.
Erros de leitura dos itens são exibidos, não convertidos em lista vazia.
SQL ainda **não aplicado**; sem migração, UI informa indisponibilidade.
Correspondência automática lista/carrinho e edição de itens ainda pendentes.
Migração atualiza RPC QA para receber household_id explícito; bloqueia
remoção de espaço com outros integrantes sem transferência prévia.

Nex Vivo: arte HD intacta SHA-256
`4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796`.
Loop ocioso não sobrescreve evento real; som não implementado removido dos
controles. Ainda precisa QA visual e acessibilidade no aparelho.

## Conclusão e continuação

Home familiar exibe saldo do membro e consolidado familiar em blocos separados;
em espaço individual não exibe consolidado de família. Aquisição é marcada
como intenção de compra, sem se passar por meta ou reserva de caixa.

156 testes automatizados locais passaram na última checagem, mas não provam
RLS/Supabase real, gateway hospedado, Windows/APK ou iOS. Não aplicar
`MIGRATION_0_24.sql` diretamente em produção: backup, QA e validação
de permissões primeiro. Não colocar OPENAI_API_KEY no app. A memória oficial
0.23 só deve ser substituída depois do retorno do proprietário dos testes.
