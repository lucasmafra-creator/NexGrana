"""Curated offline help. No network, personal ledger inference or live rates."""
import re
import unicodedata

VERSION = "2026.10.06.1"
REVIEWED_AT = "2026-10-06"
SOURCE = "https://www.bcb.gov.br/content/cidadaniafinanceira/documentos_cidadania/Cuidando_do_seu_dinheiro_Gestao_de_Financas_Pessoais/caderno_cidadania_financeira.pdf"

TOPICS = (
    (("como usar o nexgrana", "por onde comecar", "primeiros passos"),
     "Comece registrando a renda que recebeu e as despesas, com as datas corretas. Na Home, confira o mês e o perfil selecionado. Depois use Mercado para acompanhar compras e Metas para planejar. Quer começar pela renda ou pelas despesas?"),
    (("como fechar o mes", "fechamento mensal", "virada do mes", "fechar mes"),
     "Abra o mês que quer revisar na Home e toque em Revisar mês. Confira entradas, despesas, pendências e saldo antes de confirmar. O saldo só passa para o mês seguinte após o fechamento. Se aparecer migration 0.25 pendente, o administrador precisa atualizar o ambiente de teste; esconder o aviso não resolve."),
    (("como usar achados", "o que e achados", "afiliados"),
     "Achados reúne links de ofertas e fica separado das suas despesas. Confira preço, frete e vendedor no parceiro antes de comprar; um preço indisponível não é estimativa. Links de afiliado são identificados. Abrir uma oferta não cria uma despesa nem garante desconto."),
    (("como usar mercado", "lista de compras", "orcamento da compra"),
     "Em Mercado, crie uma lista ou compra e informe um limite. Adicione produtos, quantidades e preços; o resumo mostra o gasto e o restante. Esse limite é um planejamento da compra, separado do saldo real. Confira a nota antes de finalizar."),
    (("como trocar perfil", "onde trocar perfil", "consolidado familiar"),
     "Use a seleção de perfil para consultar os registros daquele integrante. O consolidado da família é uma visão diferente do saldo individual. Confira o nome do perfil e o mês na tela antes de interpretar qualquer valor."),
    (("como sincronizar", "usar offline", "modo offline"),
     "No primeiro acesso, você precisa de internet para validar a conta e carregar o espaço. Depois, os dados já sincronizados podem ficar disponíveis no aparelho. Sem rede, confira o indicador de pendências; uma alteração local ainda não prova que chegou à nuvem. Reconecte e revise conflitos antes de decidir uma compra."),
    (("como apagar mensagens", "limpar chat", "excluir mensagens"),
     "No chat, abra Limpar mensagens, escolha o período e confira o intervalo e a quantidade antes de confirmar. A ação vale para a conversa e o perfil selecionados. Ela não apaga rendas, despesas ou outras conversas. Mensagens antigas sem data confiável ficam preservadas."),
    (("como mudar skin", "visual do nex", "trocar skin"),
     "Abra Aparência → Visual do Nex, ou use Visual do Nex no chat. Você pode escolher manualmente ou usar Automático por data. O visual muda o personagem, sem alterar seus registros ou liberar benefícios financeiros."),
    (("como criar meta", "o que e uma meta", "metas de economia"),
     "Uma meta registra objetivo, valor e prazo. Cadastre o que já foi guardado e revise a projeção quando a renda ou as despesas mudarem. Criar uma meta não movimenta dinheiro da sua conta. Quer entender a diferença entre meta e aquisição?"),
    (("o que e aquisicao", "meta e aquisicao", "aquisicao e meta"),
     "Aquisição é uma intenção de compra; meta é um objetivo de acumulação. Nenhuma das duas debita seu saldo automaticamente. O Nex só consegue avaliar a margem com registros confirmados do perfil ativo; compromisso futuro não é dinheiro livre."),
    (("o que e orcamento", "como montar um orcamento", "comecar um orcamento"),
     "Orçamento é comparar entradas e saídas previstas e acompanhar o realizado. Liste despesas essenciais e compromissos, confira datas e revise o plano quando houver mudanças. Evite decidir pelo saldo de um único dia. Qual parte você quer organizar primeiro?"),
    (("o que e reserva de emergencia", "como criar uma reserva", "montar reserva de emergencia"),
     "Uma reserva serve para imprevistos. O valor adequado depende das despesas essenciais e da estabilidade da renda; não há uma quantia universal. Defina uma meta compatível com seu orçamento e reveja o prazo. Isso é orientação geral, sem indicação de um produto financeiro específico."),
    (("o que sao juros", "como funcionam juros", "juros compostos"),
     "Juros são o custo de usar dinheiro ou a remuneração por emprestá-lo. Nos compostos, os juros se incorporam à base dos próximos períodos. Compare prazo, custo total e taxas efetivas. Eu não consulto taxas atuais no modo local."),
    (("organizar dividas", "por onde comecar com dividas", "como negociar uma divida"),
     "Liste credor, saldo confirmado, vencimentos e custo total. Compare propostas de renegociação e o que cabe no orçamento antes de aceitar. Não assuma uma nova parcela sem conferir as condições. Eu não conheço o valor das suas dívidas sem registros confirmados."),
)

def normalize(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())

def local_answer(message):
    text = normalize(message)
    # Personal totals and live information always stay with verified tools.
    if re.search(r"\b(meu|minha|meus|minhas|hoje|agora|atual|atualmente)\b", text):
        return None
    matches = [(len(alias), answer) for aliases, answer in TOPICS for alias in aliases if alias in text]
    return max(matches, default=(0, None), key=lambda row: row[0])[1]
