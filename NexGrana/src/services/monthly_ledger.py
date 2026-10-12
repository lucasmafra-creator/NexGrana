"""Confirmed month-to-month cash continuity without double counting.

Closures are explicit user confirmations. Opening balances are recomputed from
the closed history, so a late transaction entered into a closed month updates
the following balances instead of being silently stranded in the past.
"""
from __future__ import annotations

import calendar
from datetime import date

from services.finance_engine import amount, day, member_snapshot, snapshot


def canonical_month(value: str | date) -> str:
    if isinstance(value, date):
        return value.strftime("%m/%Y")
    raw = str(value or "").strip()
    if "/" in raw:
        month, year = raw.split("/", 1)
        validated = date(int(year), int(month), 1)
        return validated.strftime("%m/%Y")
    parsed = day(raw)
    return parsed.strftime("%m/%Y")


def month_start(value: str | date) -> date:
    month, year = map(int, canonical_month(value).split("/"))
    return date(year, month, 1)


def previous_month(value: str | date) -> str:
    start = month_start(value)
    if start.month == 1:
        return f"12/{start.year - 1:04d}"
    return f"{start.month - 1:02d}/{start.year:04d}"


def _record_month(row: dict) -> str | None:
    value = row.get("month") or row.get("month_start")
    if value:
        try:
            return canonical_month(value)
        except (TypeError, ValueError):
            pass
    value = row.get("expense_date") or row.get("received_at")
    if value:
        try:
            return day(value).strftime("%m/%Y")
        except (TypeError, ValueError):
            return None
    return None


def month_has_activity(incomes, expenses, month: str | date, member_id=None) -> bool:
    target = canonical_month(month)
    for row in incomes or ():
        if row.get("receipt_status") == "cancelled" or str(row.get("_sync_state") or "").startswith(("rejected", "conflict")):
            continue
        if _record_month(row) == target and (
            member_id is None or str(row.get("member_id") or "") == str(member_id)
        ):
            return True
    for row in expenses or ():
        if row.get("payment_status") == "cancelled" or str(row.get("_sync_state") or "").startswith(("rejected", "conflict")):
            continue
        if _record_month(row) != target:
            continue
        if member_id is None:
            return True
        shares = row.get("expense_shares") or []
        if shares and any(str(item.get("member_id") or "") == str(member_id) for item in shares):
            return True
        if not shares and str(row.get("payer_member_id") or "") == str(member_id):
            return True
    return False


def month_is_closed(closures, month: str | date, member_id=None) -> bool:
    target = canonical_month(month)
    scope = str(member_id or "")
    return any(
        _record_month(row) == target
        and str(row.get("member_id") or "") == scope
        and str(row.get("status") or "closed") == "closed"
        and not str(row.get("_sync_state") or "").startswith(("rejected", "conflict"))
        for row in (closures or ())
    )


def opening_balance_for_month(
    incomes,
    expenses,
    closures,
    month: str | date,
    members=(),
    member_id=None,
):
    """Return carry-in only when every immediately preceding month is closed.

    The amount is calculated from the ledger instead of trusted as a frozen
    number from the closure record. This includes correctly dated late entries.
    Family and member closures use separate scopes.
    """
    target = canonical_month(month)
    current = previous_month(target)
    chain = []
    while month_is_closed(closures, current, member_id):
        chain.append(current)
        current = previous_month(current)
        if len(chain) >= 1200:
            raise ValueError("Histórico de fechamentos excede o limite de cálculo")

    carried = amount(0)
    for period in reversed(chain):
        start = month_start(period)
        month_end = date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])
        if member_id is None:
            result = snapshot(
                incomes,
                expenses,
                period,
                members=members,
                today=month_end,
                opening_balance=carried,
            )
        else:
            result = member_snapshot(
                incomes,
                expenses,
                period,
                member_id,
                members=members,
                today=month_end,
                opening_balance=carried,
            )
        carried = amount(result.get("balance"))
    return carried
