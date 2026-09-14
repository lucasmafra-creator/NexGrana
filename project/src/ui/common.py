import asyncio
import calendar
import uuid
import re
import unicodedata
from difflib import SequenceMatcher
from collections import defaultdict
from datetime import datetime, date
from urllib.parse import quote, quote_plus

import flet as ft
try:
    import flet_camera as fc
except Exception:
    fc = None

from cloud import Cloud, load_config, save_config, storage_dir
from affiliate_config import AFFILIATE_DISCLOSURE
from nex_controller import NexStateMachine
from services.transactions import expense_batch
from services.finance_engine import snapshot, split_amount, day, expense_status, goal_scenarios, affordable_acquisitions, analysis_summary, monthly_goal_commitments
from services.nex_engine import NexEngine, Context
from services.privacy import POLICY_TEXT, export_snapshot, write_backup
from services.affiliate import active_offers
from ui.responsive import bucket
import logging
logger = logging.getLogger(__name__)
__all__ = ['asyncio','calendar','uuid','re','unicodedata','SequenceMatcher','defaultdict','datetime','date','quote','quote_plus','ft','fc','Cloud','load_config','save_config','storage_dir','AFFILIATE_DISCLOSURE','NexStateMachine','expense_batch','snapshot','split_amount','day','expense_status','goal_scenarios','affordable_acquisitions','analysis_summary','monthly_goal_commitments','NexEngine','Context','POLICY_TEXT','export_snapshot','write_backup','active_offers','bucket','logger','PEOPLE_MODE','KINDS','CATEGORIES','PRIORITIES','COLORS','FINANCIAL_RESOURCES','EXTRA_INCOME_MANUALS','FINANCIAL_KNOWLEDGE','brl','money','month_key','add_months','month_label','parse_date','base_desc']

PEOPLE_MODE = ["Individual", "Família"]
KINDS = ["Fixa", "Variável", "Parcelamento/Financiamento"]
CATEGORIES = [
    "Contas da Casa", "Alimentação", "Saúde", "Transporte",
    "Educação", "Pet", "Lazer", "Reserva", "Outros"
]
PRIORITIES = ["Alta", "Média", "Baixa"]
COLORS = [
    ft.Colors.INDIGO, ft.Colors.BLUE, ft.Colors.PINK, ft.Colors.ORANGE,
    ft.Colors.GREEN, ft.Colors.PURPLE, ft.Colors.CYAN, ft.Colors.AMBER
]


FINANCIAL_RESOURCES = [
    {
        "title": "Banco Central — Cidadania Financeira",
        "subtitle": "Orçamento, crédito, dívidas, consumo, reserva, investimentos e prevenção de riscos.",
        "url": "https://www.bcb.gov.br/cidadaniafinanceira",
    },
    {
        "title": "Banco Central — Vídeos e materiais",
        "subtitle": "Biblioteca com vídeos e cadernos de educação financeira.",
        "url": "https://www.bcb.gov.br/cidadaniafinanceira/cidadania_biblioteca",
    },
    {
        "title": "CVM — Portal do Investidor",
        "subtitle": "Conteúdo educativo sobre risco, liquidez, renda fixa, renda variável e investimentos.",
        "url": "https://www.gov.br/investidor/pt-br",
    },
    {
        "title": "CVM — Educação",
        "subtitle": "Cursos, publicações e materiais gratuitos para investidores.",
        "url": "https://www.gov.br/cvm/pt-br/assuntos/educacao/",
    },
    {
        "title": "CVM — Antes de investir",
        "subtitle": "Objetivos, prazo, liquidez, risco e cuidados antes de escolher investimentos.",
        "url": "https://www.gov.br/investidor/pt-br/investir/antes-de-investir",
    },
]

EXTRA_INCOME_MANUALS = [
    ("Lavagem automotiva em domicílio", "Presencial • baixo investimento", "Comece com um kit enxuto, calcule produto + deslocamento + tempo, monte 2 ou 3 pacotes e divulgue com fotos do antes/depois. Registre cada serviço e custo para medir o lucro real."),
    ("Doces, bolos e sobremesas", "Casa • baixo investimento", "Escolha poucos produtos, calcule custo por unidade, teste por encomenda para evitar desperdício e reinvista parte do lucro em embalagem e divulgação."),
    ("Marmitas e refeições", "Casa • investimento baixo/médio", "Defina cardápio curto, custo por porção, margem e dias de produção. Comece por encomenda e controle ingredientes, embalagem e entrega separadamente."),
    ("Revenda de usados", "Online/presencial • capital variável", "Comece por itens que você conhece. Pesquise preço vendido, não só anunciado; some taxas, frete e eventuais reparos antes de definir a margem."),
    ("Brechó e roupas usadas", "Online • baixo investimento", "Separe peças em bom estado, fotografe bem, informe medidas e defeitos, monte lotes e acompanhe taxa de venda por categoria."),
    ("Cuidados com pets", "Presencial • quase sem investimento", "Ofereça passeio, visita e alimentação. Defina raio de atendimento, duração, preço por visita e regras claras para chaves, medicamentos e emergências."),
    ("Limpeza residencial", "Presencial • baixo investimento", "Defina o que está incluso, duração média, deslocamento e material. Trabalhe com agenda e peça indicação após serviços bem avaliados."),
    ("Jardinagem e pequenos cuidados externos", "Presencial • baixo/médio investimento", "Comece por corte, limpeza e manutenção simples. Precifique por tempo, tamanho do local e descarte de resíduos."),
    ("Montagem e pequenos serviços domésticos", "Presencial • ferramentas necessárias", "Liste somente serviços que domina, cobre deslocamento e tempo e não aceite instalações elétricas/gás sem qualificação adequada."),
    ("Entregas e fretes leves", "Com veículo", "Calcule combustível, manutenção, seguro e depreciação. Defina valor mínimo por corrida para evitar trabalhar com margem negativa."),
    ("Fotografia de produtos com celular", "Online/local • baixo investimento", "Monte um fundo simples, iluminação consistente e pacotes por quantidade de fotos. Mostre portfólio antes/depois e entregue arquivos organizados."),
    ("Edição de vídeos curtos", "Online • baixo investimento", "Crie pacotes por quantidade/duração, defina número de revisões e use modelos para reduzir tempo sem sacrificar qualidade."),
    ("Aulas particulares", "Online/presencial • quase sem investimento", "Escolha um tema que domina, defina nível e duração, prepare material básico e ofereça aula avulsa ou pacote mensal."),
    ("Artesanato e personalizados", "Casa • investimento variável", "Produza sob encomenda no início, calcule matéria-prima + tempo + embalagem e evite estoque grande antes de validar a demanda."),
    ("Serviços em eventos", "Fim de semana", "Busque apoio em montagem, recepção, fotografia, garçom ou organização conforme experiência. Confirme horário, transporte e pagamento antes."),
]

FINANCIAL_KNOWLEDGE = [
    {
        "keywords": ["onde investir", "aonde investir", "investir", "investimento", "aplicar dinheiro", "aplicação"],
        "title": "Como pensar antes de investir",
        "text": (
            "Não existe um único investimento melhor para todo mundo. Comece pelo objetivo: quando o dinheiro será usado, "
            "quanta liquidez você precisa e quanto risco aceita. Para dinheiro de emergência, priorize baixo risco e alta liquidez. "
            "Para objetivos mais longos, compare risco, prazo, liquidez, custos, impostos e diversificação antes de escolher."
        ),
    },
    {
        "keywords": ["reserva", "emergência", "emergencia", "imprevisto"],
        "title": "Reserva de emergência",
        "text": (
            "A reserva existe para absorver imprevistos sem depender de dívida. O foco principal é segurança e acesso rápido ao dinheiro, "
            "não buscar o maior retorno possível. Construa aos poucos e ajuste o tamanho à estabilidade da renda e às despesas essenciais."
        ),
    },
    {
        "keywords": ["renda fixa", "cdb", "lci", "lca", "tesouro", "selic", "ipca", "prefixado", "pós-fixado", "pos-fixado"],
        "title": "Renda fixa",
        "text": (
            "Renda fixa significa que a regra de remuneração é conhecida no momento da aplicação, mas isso não elimina riscos. "
            "Compare emissor, risco de crédito, prazo, liquidez, tributação e como a rentabilidade é calculada. "
            "Títulos prefixados e indexados à inflação podem oscilar antes do vencimento."
        ),
    },
    {
        "keywords": ["ações", "acoes", "bolsa", "renda variável", "renda variavel", "fii", "fundo imobiliário", "fundo imobiliario", "etf", "bdr"],
        "title": "Renda variável",
        "text": (
            "Renda variável pode oscilar bastante e gerar perdas. Antes de investir, avalie objetivo, horizonte de tempo, diversificação, "
            "custos, liquidez e sua capacidade de suportar quedas sem precisar vender em um momento ruim."
        ),
    },
    {
        "keywords": ["diversificar", "diversificação", "diversificacao", "carteira"],
        "title": "Diversificação",
        "text": (
            "Diversificar reduz a dependência de um único ativo, emissor ou classe, mas não elimina riscos. "
            "A diversificação deve respeitar objetivos, prazo, liquidez e tolerância a oscilações."
        ),
    },
    {
        "keywords": ["cartão", "cartao", "rotativo", "dívida", "divida", "endividado", "juros"],
        "title": "Dívidas e juros",
        "text": (
            "Dívidas de custo alto merecem prioridade. Organize saldo devedor, taxa, parcela, prazo e custo total; "
            "evite transformar o pagamento mínimo do cartão em rotina. Antes de investir com mais risco, compare o retorno esperado "
            "com o custo certo da dívida."
        ),
    },
    {
        "keywords": ["financiamento", "empréstimo", "emprestimo", "sac", "price", "cet"],
        "title": "Crédito e financiamento",
        "text": (
            "Compare o Custo Efetivo Total (CET), não apenas o valor da parcela. Prazo maior pode aliviar a prestação, mas aumentar muito "
            "o total pago. Simule cenários e verifique quanto da renda mensal ficará comprometido."
        ),
    },
    {
        "keywords": ["orçamento", "orcamento", "gastos", "despesas", "organizar dinheiro", "controle financeiro"],
        "title": "Orçamento",
        "text": (
            "Um orçamento mostra quanto entra, quanto sai e para onde o dinheiro está indo. Separe despesas essenciais, variáveis, dívidas, "
            "reserva e objetivos. O acompanhamento frequente é mais útil do que tentar acertar um orçamento perfeito de primeira."
        ),
    },
    {
        "keywords": ["inflação", "inflacao", "poder de compra"],
        "title": "Inflação",
        "text": (
            "Inflação reduz o poder de compra ao longo do tempo. Em objetivos longos, avalie o retorno real — isto é, o retorno depois da inflação, "
            "custos e impostos — em vez de olhar somente a taxa nominal."
        ),
    },
    {
        "keywords": ["juros compostos", "juros composto", "composto"],
        "title": "Juros compostos",
        "text": (
            "Nos juros compostos, os rendimentos passam a gerar novos rendimentos. Tempo, taxa e aportes recorrentes têm grande efeito no resultado, "
            "mas custos, impostos e inflação precisam entrar na comparação."
        ),
    },
    {
        "keywords": ["aposentadoria", "longo prazo", "previdência", "previdencia"],
        "title": "Planejamento de longo prazo",
        "text": (
            "Para objetivos longos, defina valor-alvo, prazo e contribuição periódica. Revise o plano com o tempo e diversifique conforme o horizonte "
            "e sua tolerância a risco. Produtos de previdência também exigem comparação de taxas, tributação e regras de resgate."
        ),
    },
    {
        "keywords": ["cripto", "bitcoin", "ethereum", "criptomoeda"],
        "title": "Criptoativos",
        "text": (
            "Criptoativos podem ter alta volatilidade e riscos operacionais, tecnológicos e de custódia. "
            "Evite usar dinheiro de emergência ou assumir uma exposição que comprometa objetivos essenciais."
        ),
    },
    {
        "keywords": ["golpe", "fraude", "pirâmide", "piramide", "retorno garantido"],
        "title": "Golpes e promessas de retorno",
        "text": (
            "Desconfie de promessa de ganho alto, rápido e garantido. Verifique quem oferece o produto, como o dinheiro é custodiado, "
            "quais riscos existem e se a atividade é regulada. Pressa e promessa de 'oportunidade única' são sinais de alerta."
        ),
    },
    {
        "keywords": ["imposto", "ir", "tributação", "tributacao", "declaração", "declaracao"],
        "title": "Tributação",
        "text": (
            "Impostos variam conforme produto, prazo e operação. Use o chat para organizar os conceitos, mas confirme regras, alíquotas e obrigações "
            "na fonte oficial ou com profissional habilitado antes de declarar ou tomar uma decisão tributária."
        ),
    },
]


def brl(value):
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def money(text):
    text = str(text or "").replace("R$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return float(text or 0)


def month_key(dt=None):
    return (dt or datetime.now()).strftime("%m/%Y")


def add_months(mm_yyyy, offset):
    m, y = map(int, mm_yyyy.split("/"))
    idx = y * 12 + m - 1 + offset
    ny, nm = divmod(idx, 12)
    return f"{nm + 1:02d}/{ny}"


def month_label(mm_yyyy):
    names = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    m, y = map(int, mm_yyyy.split("/"))
    return f"{names[m - 1]} de {y}"


def parse_date(text):
    return datetime.combine(day(text), datetime.min.time())


def base_desc(text):
    text = (text or "").lower().strip()
    text = re.sub(r"\s*\(parcela\s+\d+/\d+\)\s*$", "", text, flags=re.I)
    return " ".join(text.split())


