"""Motor financeiro determinístico do NexGrana.

Todos os cálculos monetários são feitos com ``Decimal`` em centavos. Telas,
Nex e planejamento devem consumir este módulo em vez de repetir fórmulas.
O saldo é mensal e verificável: soma as rendas da competência selecionada e
subtrai somente despesas dessa competência cuja data de vencimento já chegou.
Despesas posteriores ao dia de corte aparecem apenas como futuras.
"""
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
import calendar

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def amount(value):
    number = Decimal(str(value or 0))
    if not number.is_finite():
        raise ValueError("Valor financeiro inválido")
    return number.quantize(CENT, rounding=ROUND_HALF_UP)


def day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    raise ValueError("Data inválida; use dd/mm/aaaa ou aaaa-mm-dd")


def split_amount(value, members):
    ids = list(dict.fromkeys(str(m) for m in members))
    if not ids or amount(value) < 0:
        raise ValueError("Rateio inválido")
    cents = int(amount(value) * 100)
    base, remainder = divmod(cents, len(ids))
    return [(mid, Decimal(base + (i < remainder)) / 100) for i, mid in enumerate(ids)]


def effective_income(row):
    """Retorna apenas a data explicitamente registrada; nunca inventa uma data."""
    if row.get("received_at"):
        return day(row["received_at"]), False
    return None, False


def effective_expense(row):
    """A despesa torna-se efetiva na própria data de vencimento."""
    if row.get("payment_status") == "cancelled":
        return None
    return day(row["expense_date"])


def expense_status(row, today=None):
    today = today or date.today()
    if row.get("payment_status") == "cancelled":
        return "cancelled"
    return "paid" if day(row["expense_date"]) <= today else "scheduled"


def _months_until(target, today=None):
    today = today or date.today()
    target = day(target)
    return max(1, (target.year - today.year) * 12 + target.month - today.month + 1)


def monthly_goal_commitments(
    goals,
    today=None,
    *,
    exclude_goal_id=None,
    exclude_acquisition_id=None,
):
    """Soma o esforço mensal restante das metas ativas.

    ``saved_amount`` representa dinheiro já acumulado e não deve ser subtraído
    novamente do caixa como se fosse compromisso futuro.  O compromisso é o
    valor *restante* dividido pelo prazo remanescente.
    """
    today = today or date.today()
    total = ZERO
    for goal in goals or ():
        if str(goal.get("status") or "active") != "active":
            continue
        if exclude_goal_id is not None and str(goal.get("id")) == str(exclude_goal_id):
            continue
        if (
            exclude_acquisition_id is not None
            and goal.get("acquisition_id")
            and str(goal.get("acquisition_id")) == str(exclude_acquisition_id)
        ):
            continue
        try:
            remaining = max(amount(goal.get("target_amount")) - amount(goal.get("saved_amount")), ZERO)
            if remaining <= 0:
                continue
            months = _months_until(goal.get("target_date"), today)
            total += amount(remaining / months)
        except (ValueError, TypeError, KeyError):
            # Uma meta inválida não deve contaminar o saldo. A UI deve sinalizar
            # o registro para correção separadamente.
            continue
    return amount(total)


def snapshot(incomes, expenses, month, members=(), today=None):
    """Calcula exclusivamente a competência selecionada, sem carregar históricos.

    Regra de caixa:
    - toda renda cadastrada na competência entra no saldo;
    - uma despesa da competência só reduz o saldo quando o vencimento chega;
    - antes do vencimento, ela aparece em pending_month e reduz apenas a
      projeção;
    - meses anteriores e posteriores nunca são carregados para o saldo atual.
    """
    today = today or date.today()
    m, y = map(int, month.split("/"))
    start = date(y, m, 1)
    end = date(y, m, calendar.monthrange(y, m)[1])
    cutoff = min(today, end)

    totals = defaultdict(Decimal)
    mi, me, mp, mb = (defaultdict(Decimal) for _ in range(4))
    categories = defaultdict(Decimal)
    pending_rows, issues = [], []
    seen = set()

    for row in incomes:
        rid = row.get("id")
        if rid and ("i", rid) in seen:
            continue
        if rid:
            seen.add(("i", rid))
        if row.get("receipt_status") == "cancelled":
            continue

        competence = str(row.get("month") or "").strip()
        if competence:
            try:
                cm, cy = map(int, competence.split("/"))
                date(cy, cm, 1)
                competence = f"{cm:02d}/{cy:04d}"
            except (TypeError, ValueError):
                competence = ""
        if not competence and row.get("received_at"):
            competence = day(row["received_at"]).strftime("%m/%Y")
        if not competence:
            issues.append("Renda sem competência ou data registrada: confirme em Transações.")
            continue
        if competence != month:
            continue

        value = amount(row["amount"])
        mid = str(row.get("member_id") or "unassigned")
        totals["income"] += value
        totals["balance"] += value
        mi[mid] += value
        mb[mid] += value

    for row in expenses:
        rid = row.get("id")
        if rid and ("e", rid) in seen:
            continue
        if rid:
            seen.add(("e", rid))
        if row.get("payment_status") == "cancelled":
            continue

        due = day(row["expense_date"])
        if not (start <= due <= end):
            continue

        value = amount(row["amount"])
        totals["registered_expense"] += value
        shares = [(str(item["member_id"]), amount(item["amount"])) for item in row.get("expense_shares", [])]
        if not shares:
            shares = [(str(row.get("payer_member_id") or "unassigned"), value)]
        else:
            shared = sum((share for _, share in shares), ZERO)
            if shared != value:
                issues.append("Rateio inconsistente: diferença mantida em Não atribuído.")
                shares.append(("unassigned", value - shared))

        if due <= cutoff:
            totals["expense"] += value
            totals["balance"] -= value
            categories[row.get("category") or "Outros"] += value
            for mid, share in shares:
                me[mid] += share
                mb[mid] -= share
        else:
            totals["pending_month"] += value
            pending_rows.append(row)
            for mid, share in shares:
                mp[mid] += share

    for key in (
        "balance",
        "opening_balance",
        "income",
        "expense",
        "registered_expense",
        "pending_month",
        "overdue",
        "prior_overdue",
        "expected_income",
    ):
        totals[key] += ZERO

    totals["projected_balance"] = totals["balance"] - totals["pending_month"]
    totals["monthly_result"] = totals["balance"]
    totals["projected_monthly_result"] = totals["projected_balance"]

    result = {key: float(value) for key, value in totals.items()}
    for key, data in (
        ("member_income", mi),
        ("member_expense", me),
        ("member_pending", mp),
        ("member_balance", mb),
    ):
        result[key] = {member_id: float(value) for member_id, value in data.items()}
    result.update(
        member_names={str(member["id"]): member["display_name"] for member in members},
        categories=sorted(
            ((category, float(value)) for category, value in categories.items()),
            key=lambda item: -item[1],
        ),
        pending_rows=sorted(pending_rows, key=lambda row: day(row["expense_date"])),
        prior_overdue_rows=[],
        issues=sorted(set(issues)),
        as_of=cutoff.isoformat(),
    )
    return result


def analysis_summary(data, goals=(), allocation=(40, 30, 10, 20), minimum_reserve=0, today=None):
    """Resumo único usado por Análises, Nex e Planejamento.

    Retorna métricas de compromisso sem mover dinheiro. ``safe_margin`` é uma
    referência conservadora: caixa após contas/reserva, resultado mensal
    projetado e esforço mensal das metas.
    """
    today = today or date.today()
    income = amount(data.get("income"))
    paid = amount(data.get("expense"))
    pending = amount(data.get("pending_month"))
    committed = paid + pending
    balance = amount(data.get("balance"))
    projected = amount(data.get("projected_balance"))
    monthly_projected = amount(data.get("projected_monthly_result"))
    reserve = max(amount(minimum_reserve), ZERO)
    goal_commitment = monthly_goal_commitments(goals, today=today)

    cash_after_reserve = max(projected - reserve, ZERO)
    monthly_after_goals = max(monthly_projected - goal_commitment, ZERO)
    safe_margin = min(cash_after_reserve, monthly_after_goals)
    free_margin = income - committed
    ratio = (committed / income) if income > 0 else ZERO

    if income <= 0:
        health = "Sem dados"
        detail = "Cadastre a renda recebida para calibrar o diagnóstico."
        level = "unknown"
    elif free_margin < 0:
        health = "Crítica"
        detail = "As despesas pagas e pendentes do mês superam a renda recebida."
        level = "critical"
    elif ratio <= Decimal("0.70"):
        health = "Boa"
        detail = "Há margem registrada para reserva e objetivos, respeitando os próximos compromissos."
        level = "good"
    elif ratio <= Decimal("0.90"):
        health = "Atenção"
        detail = "A maior parte da renda do mês já está comprometida."
        level = "attention"
    else:
        health = "Apertada"
        detail = "Mais de 90% da renda recebida está comprometida com gastos pagos ou pendentes."
        level = "tight"

    percentages = list(allocation or (40, 30, 10, 20))
    if len(percentages) != 4 or any(Decimal(str(x)) < 0 for x in percentages):
        percentages = [40, 30, 10, 20]
    total_pct = sum(Decimal(str(x)) for x in percentages)
    if total_pct <= 0:
        percentages = [40, 30, 10, 20]
        total_pct = Decimal(100)
    normalized = [Decimal(str(x)) * Decimal(100) / total_pct for x in percentages]
    alloc_amounts = [amount(safe_margin * pct / 100) for pct in normalized]

    return {
        "health": health,
        "health_detail": detail,
        "health_level": level,
        "income": float(income),
        "paid_expense": float(paid),
        "pending_expense": float(pending),
        "committed_expense": float(committed),
        "free_margin": float(free_margin),
        "balance": float(balance),
        "projected_balance": float(projected),
        "goal_monthly_commitment": float(goal_commitment),
        "minimum_reserve": float(reserve),
        "safe_margin": float(safe_margin),
        "allocation_percentages": [float(x.quantize(CENT)) for x in normalized],
        "allocation_amounts": [float(x) for x in alloc_amounts],
    }


def goal_scenarios(goal, margin, projected, other_goals=(), entry=0, today=None, reserve=0):
    today = today or date.today()
    months = _months_until(goal["target_date"], today)
    remaining = max(amount(goal["target_amount"]) - amount(goal.get("saved_amount")), ZERO)
    other = monthly_goal_commitments(other_goals, today=today, exclude_goal_id=goal.get("id"))
    entry = amount(entry)
    if entry < 0 or entry > remaining or entry > max(amount(projected), ZERO):
        raise ValueError("Aporte excede o caixa ou o valor restante")
    free = min(amount(margin), max(amount(projected) - max(amount(reserve), ZERO), ZERO)) - other
    free = amount(max(free, ZERO))
    keep = amount(remaining / months)
    return {
        "months": months,
        "remaining": float(remaining),
        "keep": float(keep),
        "plus_one": float(amount(remaining / (months + 1))),
        "plus_two": float(amount(remaining / (months + 2))),
        "entry": float(entry),
        "after_entry": float(amount((remaining - entry) / months)),
        "other_goals": float(other),
        "free": float(free),
        "projected_after_entry": float(amount(projected) - entry),
        "fits": keep <= free,
    }


def affordable_acquisitions(items, data, goals=(), reserve=0, price_limit=None, today=None):
    """Retorna compras que cabem em uma margem conservadora.

    O filtro ``price_limit`` compara o preço TOTAL do item.  Metas já
    acumuladas não são descontadas de novo; apenas o esforço mensal restante
    das outras metas reduz a margem.
    """
    today = today or date.today()
    reserve = max(amount(reserve), ZERO)
    cash_capacity = max(
        ZERO,
        min(amount(data.get("balance")), amount(data.get("projected_balance"))) - reserve,
    )
    goal_commitment = monthly_goal_commitments(goals, today=today)
    monthly_capacity = max(ZERO, amount(data.get("projected_monthly_result")) - goal_commitment)
    budget = amount(min(cash_capacity, monthly_capacity))

    candidates = []
    for item in items or ():
        if str(item.get("status") or "active") != "active":
            continue
        price = amount(item.get("estimated"))
        if price <= 0:
            continue
        if price_limit is not None and price > amount(price_limit):
            continue
        if price <= budget:
            candidates.append(item)
    candidates.sort(
        key=lambda x: (
            {"Alta": 0, "Média": 1, "Baixa": 2}.get(x.get("priority"), 3),
            amount(x.get("estimated")),
        )
    )
    return candidates, float(budget)
