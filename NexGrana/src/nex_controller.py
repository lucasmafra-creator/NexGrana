"""Motor visual e comportamental do Nex.

O motor nunca calcula nem altera finanças. Ele recebe eventos já concluídos e
devolve somente estado visual/fala opcional. O PNG HD aprovado permanece como
``Golden Nex`` e é o fallback final de qualquer animação futura.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from enum import StrEnum
import time


class State(StrEnum):
    IDLE = "idle"
    BLINK = "wink"
    LOOK = "look"
    THINK = "thinking"
    ALERT = "alert"
    WORRY = "worry"
    CALM = "calm"
    CELEBRATE = "celebrate"
    COINS = "coins"
    JUMP = "jump"
    LAND = "land"
    SLEEP = "sleep"
    SCAN = "scan"
    STUDY = "study"
    WAVE = "wave"
    WORKING = "working"
    INVESTING = "investing"
    PROUD = "proud"
    CONFUSED = "confused"


class NexEvent(StrEnum):
    APP_OPEN = "app_open"
    INCOME_ADDED = "income_added"
    EXPENSE_ADDED = "expense_added"
    SAVING_REGISTERED = "saving_registered"
    GOAL_CREATED = "goal_created"
    GOAL_PROGRESS = "goal_progress"
    GOAL_COMPLETED = "goal_completed"
    BILL_DUE = "bill_due"
    HIGH_SPENDING = "high_spending"
    INVESTMENT_ADDED = "investment_added"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    USER_IDLE = "user_idle"
    NEX_CLICK = "nex_click"
    NEX_MULTI_CLICK = "nex_multi_click"
    CHAT_THINKING = "chat_thinking"
    CHAT_REPLY = "chat_reply"
    GOOD_FINANCIAL_RESULT = "good_financial_result"
    BAD_FINANCIAL_RESULT = "bad_financial_result"
    UNEXPECTED_ERROR = "unexpected_error"


class NexIntensity(StrEnum):
    DISCREET = "discreet"
    NORMAL = "normal"
    ANIMATED = "animated"


@dataclass(frozen=True)
class NexSettings:
    enabled: bool = True
    intensity: str = NexIntensity.NORMAL.value
    sound: bool = False
    animations: bool = True
    effects: bool = True
    reduced_motion: bool = False

    @classmethod
    def from_mapping(cls, value):
        value = value if isinstance(value, dict) else {}
        intensity = str(value.get("intensity") or NexIntensity.NORMAL.value)
        if intensity not in {item.value for item in NexIntensity}:
            intensity = NexIntensity.NORMAL.value
        return cls(
            enabled=bool(value.get("enabled", True)),
            intensity=intensity,
            sound=bool(value.get("sound", False)),
            animations=bool(value.get("animations", True)),
            effects=bool(value.get("effects", True)),
            reduced_motion=bool(value.get("reduced_motion", False)),
        )

    def public_payload(self):
        return asdict(self)


@dataclass(frozen=True)
class NexReaction:
    event: str
    state: str
    speech: str = ""
    duration_seconds: float = 2.0
    accepted: bool = True


class NexAssetManager:
    """Resolve assets por papel com fallback imutável para o Golden Nex."""

    GOLDEN_ASSET = "nex/nex_hd.png"
    ASSETS = {
        "hero": "nex/nex_hero.png",
        "card": "nex/nex_card.png",
        "avatar": "nex/nex_avatar.png",
        "dock": "nex/nex_dock.png",
        "master": GOLDEN_ASSET,
    }

    def resolve(self, role="hero", candidate=None, candidate_approved=False):
        # Um pack novo nunca entra implicitamente. Precisa ter sido aprovado em
        # comparação visual antes/depois; sem aprovação, usa derivados do master.
        if candidate and candidate_approved:
            return str(candidate)
        return self.ASSETS.get(role, self.GOLDEN_ASSET)

    def fallback_chain(self, role="hero"):
        primary = self.ASSETS.get(role, self.GOLDEN_ASSET)
        return tuple(dict.fromkeys((primary, self.GOLDEN_ASSET)))


class NexStateMachine:
    """Estado central do Nex Vivo com cooldown e antirrepetição.

    Compatível com a API antiga ``set_state/asset/motion``. Eventos nunca
    disparam escrita financeira e podem ser ignorados sem afetar o app.
    """

    sizes = {"hero": 220, "card": 104, "avatar": 48, "dock": 92}
    assets = NexAssetManager.ASSETS

    _ALIASES = {
        "curioso": "look", "preocupado": "worry", "atento": "alert",
        "comemorando": "celebrate", "tranquilo": "calm", "happy": "celebrate",
        "warning": "alert", "supportive": "worry", "saving": "coins",
        "planning": "thinking", "shopping": "look", "goal": "thinking",
        "learning": "study", "money": "coins", "success": "celebrate",
    }

    _EVENT_STATES = {
        NexEvent.APP_OPEN: (State.WAVE, State.LOOK),
        NexEvent.INCOME_ADDED: (State.CELEBRATE, State.JUMP, State.COINS),
        NexEvent.EXPENSE_ADDED: (State.THINK, State.LOOK),
        NexEvent.SAVING_REGISTERED: (State.COINS, State.PROUD),
        NexEvent.GOAL_CREATED: (State.THINK, State.WORKING),
        NexEvent.GOAL_PROGRESS: (State.PROUD, State.CELEBRATE),
        NexEvent.GOAL_COMPLETED: (State.CELEBRATE, State.JUMP, State.PROUD),
        NexEvent.BILL_DUE: (State.ALERT, State.THINK),
        NexEvent.HIGH_SPENDING: (State.THINK, State.WORRY),
        NexEvent.INVESTMENT_ADDED: (State.INVESTING, State.PROUD),
        NexEvent.ACHIEVEMENT_UNLOCKED: (State.PROUD, State.CELEBRATE),
        NexEvent.USER_IDLE: (State.SLEEP, State.CALM, State.STUDY),
        NexEvent.NEX_CLICK: (State.LOOK, State.BLINK, State.WAVE),
        NexEvent.NEX_MULTI_CLICK: (State.CONFUSED, State.JUMP, State.CELEBRATE),
        NexEvent.CHAT_THINKING: (State.THINK, State.WORKING, State.STUDY),
        NexEvent.CHAT_REPLY: (State.LOOK, State.WAVE),
        NexEvent.GOOD_FINANCIAL_RESULT: (State.CELEBRATE, State.PROUD),
        NexEvent.BAD_FINANCIAL_RESULT: (State.THINK, State.WORRY),
        NexEvent.UNEXPECTED_ERROR: (State.CONFUSED, State.THINK),
    }

    _SPEECH = {
        NexEvent.INCOME_ADDED: ("Renda registrada. Boa! 🦉", "Entrou grana — registro confirmado."),
        NexEvent.SAVING_REGISTERED: ("Mais uma moeda protegida.", "Pequena escolha, grande conquista."),
        NexEvent.GOAL_CREATED: ("Meta criada. Agora vamos por etapas.", "Plano registrado; nada foi debitado."),
        NexEvent.GOAL_COMPLETED: ("Meta concluída! Essa merece comemoração. 🥳",),
        NexEvent.HIGH_SPENDING: ("Notei um gasto maior. Quer analisar sem julgamento?",),
        NexEvent.INVESTMENT_ADDED: ("Investimento registrado. Crescimento pede tempo e constância.",),
        NexEvent.UNEXPECTED_ERROR: ("Algo não saiu como esperado, mas seus dados financeiros continuam intactos.",),
    }

    def __init__(self, settings=None, clock=None):
        self.state = State.IDLE
        self.settings = NexSettings.from_mapping(settings)
        self.asset_manager = NexAssetManager()
        self._clock = clock or time.monotonic
        self._recent_states = deque(maxlen=5)
        self._recent_speech = deque(maxlen=5)
        self._event_at = {}
        self._clicks = deque(maxlen=12)
        self._active_until = 0.0

    def configure(self, value):
        self.settings = NexSettings.from_mapping(value)
        if not self.settings.enabled:
            self.state = State.IDLE
        return self.settings

    def set_state(self, state):
        state = self._ALIASES.get(str(state), state)
        try:
            self.state = State(state)
        except (TypeError, ValueError):
            self.state = State.IDLE
        return self.state

    def asset(self, role="hero"):
        return self.asset_manager.resolve(role)

    def _allowed(self, event):
        if not self.settings.enabled:
            return False
        if self.settings.intensity == NexIntensity.DISCREET.value:
            return event in {
                NexEvent.GOAL_COMPLETED, NexEvent.BILL_DUE,
                NexEvent.BAD_FINANCIAL_RESULT, NexEvent.UNEXPECTED_ERROR,
            }
        return True

    def _choose_state(self, event):
        options = self._EVENT_STATES.get(event, (State.IDLE,))
        chosen = next((state for state in options if state not in self._recent_states), options[0])
        self._recent_states.append(chosen)
        return chosen

    def _choose_speech(self, event):
        options = self._SPEECH.get(event, ())
        chosen = next((line for line in options if line not in self._recent_speech), options[0] if options else "")
        if chosen:
            self._recent_speech.append(chosen)
        return chosen

    def handle(self, event, context=None, *, now=None, cooldown_seconds=1.5):
        try:
            event = NexEvent(event)
        except (TypeError, ValueError):
            event = NexEvent.UNEXPECTED_ERROR
        now = self._clock() if now is None else float(now)
        if not self._allowed(event):
            return NexReaction(event.value, State.IDLE.value, accepted=False)
        previous = self._event_at.get(event.value)
        if previous is not None and now - previous < max(0.0, float(cooldown_seconds)):
            return NexReaction(event.value, self.state.value, accepted=False)
        self._event_at[event.value] = now
        state = self._choose_state(event)
        self.state = state
        duration = 1.2 if event in {NexEvent.NEX_CLICK, NexEvent.CHAT_REPLY} else 2.4
        self._active_until = now + duration
        return NexReaction(event.value, state.value, self._choose_speech(event), duration, True)

    def click(self, *, now=None):
        now = self._clock() if now is None else float(now)
        self._clicks.append(now)
        while self._clicks and now - self._clicks[0] > 2.2:
            self._clicks.popleft()
        count = len(self._clicks)
        event = NexEvent.NEX_MULTI_CLICK if count >= 4 else NexEvent.NEX_CLICK
        reaction = self.handle(event, now=now, cooldown_seconds=0)
        if count == 2:
            self.set_state(State.BLINK)
        elif count == 3:
            self.set_state(State.WAVE)
        elif count >= 10:
            self.set_state(State.CELEBRATE)
        return NexReaction(reaction.event, self.state.value, reaction.speech, reaction.duration_seconds, reaction.accepted)

    def settle(self, *, now=None):
        now = self._clock() if now is None else float(now)
        if now >= self._active_until:
            self.state = State.IDLE
        return self.state

    def motion(self, phase):
        if not self.settings.enabled or not self.settings.animations or self.settings.reduced_motion:
            return {"scale": 1, "rotate": 0, "opacity": 1, "dx": 0, "dy": 0}
        if self.settings.intensity == NexIntensity.DISCREET.value:
            return {"scale": 1, "rotate": 0, "opacity": 1, "dx": 0, "dy": 0}
        odd = phase % 2
        state = self.state
        if state == State.SLEEP:
            return {"scale": .985 if odd else .97, "rotate": -.035, "opacity": .82, "dx": 0, "dy": .012}
        if state == State.JUMP:
            return {"scale": 1.05 if odd else .99, "rotate": .015 if odd else -.015, "opacity": 1, "dx": 0, "dy": -.10 if odd else 0}
        if state in (State.CELEBRATE, State.COINS, State.PROUD):
            return {"scale": 1.055 if odd else 1.01, "rotate": .03 if odd else -.03, "opacity": 1, "dx": .012 if odd else -.012, "dy": -.035 if odd else 0}
        if state in (State.THINK, State.STUDY, State.SCAN, State.WORKING, State.INVESTING):
            return {"scale": 1.012 if odd else 1, "rotate": .018 if odd else -.008, "opacity": 1, "dx": 0, "dy": -.012 if odd else 0}
        if state in (State.ALERT, State.WORRY, State.CONFUSED):
            return {"scale": 1.018 if odd else .995, "rotate": -.018 if odd else .012, "opacity": 1, "dx": .008 if odd else -.008, "dy": 0}
        if state in (State.WAVE, State.LOOK, State.BLINK):
            return {"scale": 1.025 if odd else 1, "rotate": .035 if odd else -.025, "opacity": 1, "dx": .01 if odd else -.01, "dy": -.016 if odd else 0}
        return {"scale": 1.018 if odd else 1, "rotate": .006 if odd else -.006, "opacity": 1, "dx": 0, "dy": -.014 if odd else 0}
