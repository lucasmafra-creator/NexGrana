"""Instrumentação privacy-first.

Nesta versão não há envio remoto. O adaptador valida um schema mínimo e mantém
um buffer local em memória apenas para testes/diagnóstico. Valores financeiros,
texto de chat, e-mail e identificadores familiares são proibidos por design.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

ALLOWED_EVENTS = {
    "onboarding_completed": {"version", "platform", "variant"},
    "useful_action_completed": {"action_type", "success"},
    "nex_request_completed": {"source", "result", "latency_bucket"},
    "goal_milestone_reached": {"milestone_type"},
    "journey_step_completed": {"step"},
    "offer_impression": {"offer_id", "position", "campaign"},
    "offer_clicked": {"offer_id", "origin", "campaign"},
    "offer_hidden": {"reason_category"},
    "reminder_preference_changed": {"state"},
    "app_error": {"code", "version", "platform"},
}

FORBIDDEN_KEYS = {
    "amount", "balance", "income", "expense", "description", "goal_name",
    "chat", "message", "email", "token", "household_id", "member_id", "url",
}


@dataclass(frozen=True)
class AnalyticsEvent:
    name: str
    payload: dict
    occurred_at: str


class AnalyticsAdapter:
    def __init__(self, enabled: bool = False, max_events: int = 200):
        self.enabled = bool(enabled)
        self.max_events = int(max_events)
        self.events: list[AnalyticsEvent] = []

    def track(self, name: str, **payload):
        if not self.enabled:
            return False
        allowed = ALLOWED_EVENTS.get(name)
        if allowed is None:
            raise ValueError("Evento não permitido")
        keys = set(payload)
        if keys & FORBIDDEN_KEYS:
            raise ValueError("Payload contém dado proibido")
        unknown = keys - allowed
        if unknown:
            raise ValueError(f"Campos não permitidos: {sorted(unknown)}")
        evt = AnalyticsEvent(name, dict(payload), datetime.now(timezone.utc).isoformat())
        self.events.append(evt)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        return True
