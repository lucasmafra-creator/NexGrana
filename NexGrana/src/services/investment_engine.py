"""Simulações educacionais determinísticas, sem cotação nem efeito contábil."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


CENT = Decimal("0.01")
MAX_MONEY = Decimal("1000000000000")


def _decimal(value, label):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{label} inválido") from exc
    if not result.is_finite():
        raise ValueError(f"{label} inválido")
    return result


def investment_projection(
    initial,
    contribution,
    periods,
    rate_percent,
    *,
    rate_period="monthly",
    contribution_timing="end",
    costs=0,
    taxes=0,
):
    """Retorna um cenário matemático explícito e auditável.

    Taxa anual é tratada como taxa efetiva e convertida para a taxa mensal
    equivalente: (1 + taxa_anual) ** (1/12) - 1. Custos e impostos só entram
    quando fornecidos pelo usuário e são abatidos ao final da simulação.
    """
    start = _decimal(initial, "Valor inicial")
    payment = _decimal(contribution, "Aporte")
    rate = _decimal(rate_percent, "Taxa")
    total_costs = _decimal(costs, "Custos")
    total_taxes = _decimal(taxes, "Impostos")
    try:
        count = int(periods)
    except (TypeError, ValueError) as exc:
        raise ValueError("Prazo inválido") from exc

    if any(value < 0 or value > MAX_MONEY for value in (start, payment, total_costs, total_taxes)):
        raise ValueError("Valores devem ficar entre zero e o limite da simulação")
    if count < 1 or count > 600:
        raise ValueError("Prazo deve ficar entre 1 e 600 meses")
    if rate < Decimal("-100") or rate > Decimal("1000"):
        raise ValueError("Taxa deve ficar entre -100% e 1.000%")
    if rate_period not in {"monthly", "annual"}:
        raise ValueError("Periodicidade da taxa inválida")
    if contribution_timing not in {"begin", "end"}:
        raise ValueError("Momento do aporte inválido")

    stated_rate = rate / Decimal("100")
    if rate_period == "annual":
        # Decimal não oferece raiz fracionária portátil nas versões usadas pelo
        # app. A conversão passa por float e volta imediatamente a Decimal.
        monthly_rate = Decimal(str((1.0 + float(stated_rate)) ** (1.0 / 12.0) - 1.0))
        convention = "taxa anual efetiva convertida para equivalente mensal composto"
    else:
        monthly_rate = stated_rate
        convention = "taxa mensal informada diretamente"

    balance = start
    invested = start
    for _ in range(count):
        if contribution_timing == "begin":
            balance += payment
            invested += payment
        balance *= Decimal("1") + monthly_rate
        if contribution_timing == "end":
            balance += payment
            invested += payment
        if not balance.is_finite() or abs(balance) > MAX_MONEY * Decimal("1000000"):
            raise ValueError("O cenário ultrapassou o limite numérico")

    gross = balance.quantize(CENT, rounding=ROUND_HALF_UP)
    invested = invested.quantize(CENT, rounding=ROUND_HALF_UP)
    gain = (gross - invested).quantize(CENT, rounding=ROUND_HALF_UP)
    net = (gross - total_costs - total_taxes).quantize(CENT, rounding=ROUND_HALF_UP)
    return {
        "periods": count,
        "monthly_rate": monthly_rate,
        "rate_period": rate_period,
        "contribution_timing": contribution_timing,
        "convention": convention,
        "total_invested": invested,
        "gross_result": gross,
        "hypothetical_gain": gain,
        "costs": total_costs.quantize(CENT, rounding=ROUND_HALF_UP),
        "taxes": total_taxes.quantize(CENT, rounding=ROUND_HALF_UP),
        "net_result": net,
    }
