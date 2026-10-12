"""Missões e recompensas determinísticas das Trilhas Nex."""
from __future__ import annotations


BASE_STEPS = (
    ("Validar a atividade", "Converse com 3 possíveis clientes e anote o problema real que eles querem resolver."),
    ("Mapear seus recursos", "Liste horas livres, habilidades, ferramentas e o valor máximo que pode testar sem apertar o orçamento."),
    ("Aprender o essencial", "Escolha uma fonte confiável e pratique uma entrega pequena antes de cobrar."),
    ("Calcular todos os custos", "Inclua material, deslocamento, taxas, perdas e o valor do seu tempo."),
    ("Montar oferta e preço", "Crie uma oferta simples com escopo, prazo, custo e margem visíveis."),
    ("Fazer a primeira divulgação", "Mostre sua oferta a 5 pessoas do público certo e registre as respostas."),
    ("Concluir a primeira venda", "Registre o combinado, entregue o escopo e peça uma avaliação honesta."),
    ("Medir o lucro real", "Subtraia todos os custos da receita e calcule também quanto sobrou por hora."),
    ("Revisar o resultado", "Compare procura, margem, esforço, recorrência e feedback sem se prender à ideia inicial."),
    ("Decidir o próximo ciclo", "Escolha conscientemente entre continuar, ajustar, pausar ou ampliar o teste."),
)


SPECIALIZED = {
    "marmita": (
        (0, "Validar cardápio e demanda", "Mostre 2 opções de cardápio a 5 pessoas e anote preço, restrições e dias preferidos."),
        (3, "Calcular custo por porção", "Pese ingredientes, embalagem, gás, perdas e entrega de uma porção real."),
        (5, "Abrir uma pré-encomenda", "Ofereça um lote pequeno com data limite; produza apenas o que foi confirmado."),
    ),
    "doce": (
        (0, "Escolher o produto de teste", "Valide até 3 sabores com compradores reais antes de ampliar o cardápio."),
        (3, "Calcular custo por unidade", "Some ingredientes, embalagem, gás/energia, perdas e tempo por unidade."),
        (5, "Vender um lote pequeno", "Abra encomendas para um lote curto e registre conversão e sobras."),
    ),
    "lavagem": (
        (0, "Validar o serviço local", "Converse com 3 donos de veículo no seu raio e descubra o pacote mais útil."),
        (3, "Medir custo por lavagem", "Registre produto, água, energia, deslocamento, desgaste e tempo."),
        (5, "Fazer um antes e depois", "Realize um teste autorizado, fotografe o resultado e peça indicação."),
    ),
    "aulas": (
        (0, "Definir aluno e resultado", "Escolha matéria, nível e uma transformação mensurável para a primeira aula."),
        (3, "Calcular preparo e aula", "Inclua tempo de preparação, material, plataforma e deslocamento."),
        (5, "Oferecer uma aula piloto", "Convide 3 alunos potenciais para uma aula curta com feedback estruturado."),
    ),
    "vídeo": (
        (0, "Escolher um nicho", "Selecione um tipo de cliente e reúna 3 exemplos do formato que ele já publica."),
        (2, "Criar uma amostra", "Edite um vídeo curto de portfólio e defina claramente o número de revisões."),
        (5, "Enviar propostas objetivas", "Mostre a amostra a 5 clientes compatíveis e registre respostas e objeções."),
    ),
}


def journey_steps(title: str) -> list[tuple[str, str]]:
    steps = list(BASE_STEPS)
    normalized = str(title or "").casefold()
    for keyword, replacements in SPECIALIZED.items():
        if keyword in normalized:
            for index, name, detail in replacements:
                steps[index] = (name, detail)
            break
    return steps


def journey_xp(progress: int, metrics: dict | None = None) -> int:
    progress = max(0, min(int(progress or 0), len(BASE_STEPS)))
    metrics = metrics or {}
    evidence = sum(bool(metrics.get(key)) for key in ("notes", "expected_cost", "actual_cost", "revenue_note", "hours"))
    return progress * 100 + evidence * 20


def journey_level(progress: int) -> tuple[str, int]:
    progress = max(0, min(int(progress or 0), len(BASE_STEPS)))
    if progress >= 10:
        return "Ciclo concluído", 4
    if progress >= 7:
        return "Primeira venda", 3
    if progress >= 4:
        return "Oferta pronta", 2
    return "Explorador", 1


def journey_badges(progress: int, metrics: dict | None = None) -> list[str]:
    progress = max(0, min(int(progress or 0), len(BASE_STEPS)))
    metrics = metrics or {}
    badges = []
    if progress >= 1:
        badges.append("🔎 Ideia validada")
    if progress >= 5:
        badges.append("🧮 Preço consciente")
    if progress >= 7:
        badges.append("🤝 Primeira entrega")
    if metrics.get("actual_cost") is not None and metrics.get("revenue_note") is not None:
        badges.append("📊 Lucro medido")
    if progress >= 10:
        badges.append("🏆 Ciclo concluído")
    return badges
