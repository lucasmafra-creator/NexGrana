"""Deterministic practice calculations; none of these can write real records."""
from __future__ import annotations

from decimal import Decimal

from .finance_engine import day
from .investment_engine import investment_projection
from .tutorial import training_money


def practice_income(origin, value, received_at):
    if not str(origin or "").strip():
        raise ValueError("Diga de onde veio a renda")
    when=day(received_at)
    amount=training_money(value)
    if amount <= 0:
        raise ValueError("A renda precisa ser maior que zero")
    return {"origin":str(origin).strip(),"amount":amount,"competence":when.strftime("%m/%Y")}


def practice_goal(target, saved, months):
    target=training_money(target)
    saved=training_money(saved)
    try:
        count=int(months)
    except (TypeError, ValueError) as exc:
        raise ValueError("Informe o prazo em meses") from exc
    if count < 1 or count > 600 or target <= 0 or saved > target:
        raise ValueError("Confira meta, valor guardado e prazo")
    return {"progress":(saved / target * 100).quantize(Decimal("0.1")),
            "remaining":target-saved,"monthly":((target-saved)/count).quantize(Decimal("0.01"))}


def practice_basket(items, budget):
    maximum=training_money(budget)
    total=Decimal("0")
    for row in items:
        qty=row.get("quantity")
        if not isinstance(qty,int) or qty < 1 or qty > 1000 or not str(row.get("name") or "").strip():
            raise ValueError("Confira item e quantidade")
        total+=training_money(row.get("price"))*qty
    return {"total":total,"remaining":maximum-total,"over_budget":total > maximum}


def practice_investment(initial, monthly, months, annual_rate):
    return investment_projection(training_money(initial),training_money(monthly),months,
                                 training_money(annual_rate),rate_period="annual")
