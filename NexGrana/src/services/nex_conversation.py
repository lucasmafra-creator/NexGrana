"""Contratos locais da conversa do Nex.

Este módulo não calcula finanças e não chama provedores. Ele classifica apenas
o suficiente para escolher entre ferramentas determinísticas e conversa geral,
mantém preferências explícitas e cria uma identidade de escopo para descartar
respostas assíncronas atrasadas.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import re
import unicodedata


class ChatIntent(StrEnum):
    GENERAL = "general"
    FINANCIAL = "financial"
    APP_HELP = "app_help"
    WRITE_PROPOSAL = "write_proposal"


@dataclass(frozen=True)
class AssistantPreferences:
    preferred_name: str = ""
    tone: str = "friendly"
    detail: str = "balanced"
    remember: bool = False

    @classmethod
    def from_mapping(cls, value):
        value = value if isinstance(value, dict) else {}
        return cls(
            preferred_name=sanitize_preferred_name(value.get("preferred_name")),
            tone=value.get("tone") if value.get("tone") in {"neutral", "friendly"} else "friendly",
            detail=value.get("detail") if value.get("detail") in {"short", "balanced", "detailed"} else "balanced",
            remember=bool(value.get("remember")),
        )

    def public_payload(self):
        """Preferências de estilo; nunca contém IDs ou dados financeiros."""
        return asdict(self)


@dataclass(frozen=True)
class ChatScope:
    user_id: str
    household_id: str
    member_id: str
    month: str
    conversation_id: str
    session_generation: int
    request_id: str


def chat_scope_context(scope: ChatScope) -> tuple:
    """Return the profile/conversation identity, excluding per-message ID."""
    return (
        scope.user_id,
        scope.household_id,
        scope.member_id,
        scope.month,
        scope.conversation_id,
        scope.session_generation,
    )


def same_chat_context(left: ChatScope, right: ChatScope) -> bool:
    """Prevent delayed chat work from crossing profile or conversation scope."""
    return isinstance(left, ChatScope) and isinstance(right, ChatScope) and chat_scope_context(left) == chat_scope_context(right)


def same_chat_data_scope(left: ChatScope, right: ChatScope) -> bool:
    """Compare data/session scope when a reply should remain in its old chat."""
    if not isinstance(left, ChatScope) or not isinstance(right, ChatScope):
        return False
    return (
        left.user_id,
        left.household_id,
        left.member_id,
        left.month,
        left.session_generation,
    ) == (
        right.user_id,
        right.household_id,
        right.member_id,
        right.month,
        right.session_generation,
    )


def _norm(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text.casefold()).strip()


def sanitize_preferred_name(value):
    text = " ".join(str(value or "").split()).strip()
    text = "".join(ch for ch in text if ch.isalnum() or ch in " -_'À-ÿ")
    return text[:32]


_FINANCIAL_MARKERS = (
    "saldo", "renda", "gasto", "gastei", "despesa", "conta", "parcela",
    "comprar", "compra", "aquisicao", "meta", "guardar", "economizar",
    "invest", "cartao", "divida", "orcamento", "vence", "vencimento",
    "pix", "reais", "r$", "quanto tenho", "quanto falta", "meu mes",
    "este mes", "esse mes", "to lascado", "ta suave", "tá suave",
)
_APP_MARKERS = (
    "como usar", "onde fica", "abrir tela", "nexgrana", "fixar conversa",
    "trocar perfil", "sincronizar", "modo offline", "tutorial",
)
_WRITE_MARKERS = (
    "adicione uma despesa", "adicionar despesa", "registre uma despesa",
    "cadastrar despesa", "adicione uma renda", "adicionar renda",
    "registrar renda", "criar meta", "excluir lancamento", "apagar lancamento",
)


def classify_intent(message, action=None):
    if action and action != "message":
        return ChatIntent.FINANCIAL
    text = _norm(message)
    if any(marker in text for marker in _WRITE_MARKERS):
        return ChatIntent.WRITE_PROPOSAL
    if any(marker in text for marker in _APP_MARKERS):
        return ChatIntent.APP_HELP
    if any(marker in text for marker in _FINANCIAL_MARKERS):
        return ChatIntent.FINANCIAL
    return ChatIntent.GENERAL


def classify_intent_with_history(message, history=None, action=None):
    current=classify_intent(message,action)
    if current != ChatIntent.GENERAL:
        return current
    text=_norm(message)
    if not any(text.startswith(marker) for marker in (
        "e se", "e o que", "e quanto", "nesse caso", "neste caso",
        "e agora", "e depois", "mas e", "entao", "então",
    )):
        return current
    for row in reversed(list(history or [])[-8:]):
        if str((row or {}).get("role") or "") != "user":
            continue
        previous=classify_intent((row or {}).get("text") or (row or {}).get("content") or "")
        if previous in {ChatIntent.FINANCIAL,ChatIntent.APP_HELP}:
            return previous
    return current


def preferred_name_command(message):
    """Extrai apenas comandos explícitos de tratamento.

    Retorna (ação, nome): set, clear ou None. A função não grava nada.
    """
    text = " ".join(str(message or "").split()).strip()
    normalized = _norm(text)
    if any(term in normalized for term in (
        "nao me chama de", "nao me chame de", "sem apelido", "nao use apelido",
    )):
        replacement = re.search(r"(?:so|apenas)\s+([\wÀ-ÿ][\wÀ-ÿ _'-]{0,31})$", text, re.IGNORECASE)
        return ("set", sanitize_preferred_name(replacement.group(1))) if replacement else ("clear", "")
    match = re.search(
        r"(?:pode me chamar de|me chama de|me chame de|prefiro ser chamad[oa] de)\s+([\wÀ-ÿ][\wÀ-ÿ _'-]{0,31})",
        text,
        re.IGNORECASE,
    )
    if match:
        name=re.sub(
            r"\s+(?:sempre|daqui pra frente|nas pr[oó]ximas conversas|em todas as conversas)\s*$",
            "",match.group(1),flags=re.IGNORECASE,
        )
        return "set", sanitize_preferred_name(name)
    return None
