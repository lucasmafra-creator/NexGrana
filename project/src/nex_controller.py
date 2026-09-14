"""Controlador visual do Nex.

A 0.19 elimina GIFs legados e usa derivados do master RGBA em tamanhos adequados
para evitar decodificar a textura 1254x1254 em avatares pequenos. Estados ainda
são diferenciados principalmente por movimento enquanto o pack final de
expressões 3D/Rive não existe; o código não finge que a mesma arte é uma
expressão diferente.
"""
from enum import StrEnum


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


class NexStateMachine:
    sizes = {"hero": 220, "card": 104, "avatar": 48, "dock": 92}
    assets = {
        "hero": "nex/nex_hero.png",
        "card": "nex/nex_card.png",
        "avatar": "nex/nex_avatar.png",
        "dock": "nex/nex_dock.png",
        "master": "nex/nex_hd.png",
    }

    def __init__(self):
        self.state = State.IDLE

    def set_state(self, state):
        aliases = {
            "curioso": "look",
            "preocupado": "worry",
            "atento": "alert",
            "comemorando": "celebrate",
            "tranquilo": "calm",
            "happy": "celebrate",
            "warning": "alert",
            "supportive": "worry",
            "saving": "coins",
            "planning": "thinking",
            "shopping": "look",
            "goal": "thinking",
            "learning": "study",
            "money": "coins",
            "success": "celebrate",
        }
        state = aliases.get(str(state), state)
        try:
            self.state = State(state)
        except ValueError:
            self.state = State.IDLE

    def asset(self, role="hero"):
        """Retorna um asset otimizado para o tamanho de uso.

        O estado visual não troca para GIF degradado. Quando existir um pack de
        expressões aprovado, esta é a única fronteira que precisará mapear as
        artes distintas.
        """
        return self.assets.get(role, self.assets["hero"])

    def motion(self, phase):
        odd = phase % 2
        state = self.state
        if state == State.SLEEP:
            return {"scale": .985 if odd else .97, "rotate": -.035, "opacity": .82, "dy": .012}
        if state == State.JUMP:
            return {"scale": 1.05 if odd else .99, "rotate": .015 if odd else -.015, "opacity": 1, "dy": -.10 if odd else 0}
        if state in (State.CELEBRATE, State.COINS):
            return {"scale": 1.055 if odd else 1.01, "rotate": .03 if odd else -.03, "opacity": 1, "dy": -.035 if odd else 0}
        if state in (State.THINK, State.STUDY, State.SCAN):
            return {"scale": 1.012 if odd else 1, "rotate": .018 if odd else -.008, "opacity": 1, "dy": -.012 if odd else 0}
        if state in (State.ALERT, State.WORRY):
            return {"scale": 1.018 if odd else .995, "rotate": -.018 if odd else .012, "opacity": 1, "dy": 0}
        if state in (State.WAVE, State.LOOK, State.BLINK):
            return {"scale": 1.025 if odd else 1, "rotate": .035 if odd else -.025, "opacity": 1, "dy": -.016 if odd else 0}
        return {"scale": 1.018 if odd else 1, "rotate": .006 if odd else -.006, "opacity": 1, "dy": -.014 if odd else 0}
