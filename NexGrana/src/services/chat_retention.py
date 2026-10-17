"""Explicit, scoped chat removal intervals; unknown legacy dates are retained."""
import calendar
from datetime import datetime, timedelta, timezone

PERIODS = {"hour": "Última hora", "day": "Último dia", "week": "Última semana", "month": "Último mês", "year": "Último ano"}

def interval(period, now=None):
    now = now or datetime.now().astimezone()
    if now.tzinfo is None:
        raise ValueError("O horário precisa incluir fuso")
    if period in {"hour", "day", "week"}:
        start = now - {"hour": timedelta(hours=1), "day": timedelta(days=1), "week": timedelta(days=7)}[period]
    elif period in {"month", "year"}:
        year, month = now.year, now.month
        if period == "month":
            year, month = (year-1, 12) if month == 1 else (year, month-1)
        else:
            year -= 1
        start = now.replace(year=year, month=month, day=min(now.day, calendar.monthrange(year,month)[1]))
    else:
        raise ValueError("Período inválido")
    return start.astimezone(timezone.utc).isoformat(), now.astimezone(timezone.utc).isoformat()

def timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None

def in_interval(message, start, end):
    stamp = timestamp(message.get("created_at"))
    left, right = timestamp(start), timestamp(end)
    return bool(stamp and left and right and left <= stamp <= right)

def retain_messages(messages, tombstones, conversation_id):
    applicable = [t for t in tombstones if str(t.get("conversation_id")) == str(conversation_id)]
    return [dict(m) for m in messages if m.get("state") != "deleted" and not any(in_interval(m,t["start"],t["end"]) for t in applicable)]
