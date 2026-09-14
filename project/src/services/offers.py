"""Contratos mínimos para recomendações comerciais éticas.

Ranking de utilidade e monetização são camadas separadas. Esta versão não
consulta parceiros na rede nem faz scraping.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Recommendation:
    key: str
    title: str
    relevance: float
    reason: str


@dataclass(frozen=True)
class Offer:
    offer_id: str
    recommendation_key: str
    provider: str
    title: str
    price: float | None
    currency: str = "BRL"
    url: str = ""
    campaign: str | None = None
    platform: str | None = None
    sponsored: bool = False


@dataclass(frozen=True)
class OfferSource:
    key: str
    name: str
    allowed_domains: tuple[str, ...]
    platform_eligibility: tuple[str, ...] = ("all",)


@dataclass(frozen=True)
class AffiliateProvider:
    key: str
    name: str
    disclosure: str
    source_key: str
    enabled: bool = False


@dataclass(frozen=True)
class AffiliateLink:
    provider_key: str
    offer_id: str
    url: str
    campaign: str | None = None


@dataclass(frozen=True)
class SponsoredContent:
    content_id: str
    title: str
    sponsor: str
    disclosure: str
    url: str | None = None


@dataclass(frozen=True)
class ClickEvent:
    offer_id: str
    origin: str
    campaign: str | None = None


def rank_recommendations(rows: list[Recommendation]) -> list[Recommendation]:
    """Ordena somente por relevância/identidade da recomendação.

    Comissão não existe no contrato e, portanto, não consegue alterar ranking.
    """
    return sorted(rows, key=lambda r: (-float(r.relevance), r.title.lower(), r.key))


def validate_offer_url(url: str, allowed_domains: set[str]) -> bool:
    try:
        parsed = urlparse(str(url))
    except Exception:
        return False
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    host = parsed.hostname.lower().rstrip(".")
    allowed = {d.lower().rstrip(".") for d in allowed_domains}
    return host in allowed or any(host.endswith("." + d) for d in allowed)
