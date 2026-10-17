"""Contratos mínimos para recomendações comerciais éticas.

Ranking de utilidade e monetização são camadas separadas. Esta versão não
consulta parceiros na rede nem faz scraping.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


DEMO_OFFERS = [
    {
        "id": "demo-cafeteira-lov",
        "product_key": "cafeteira-lov-preta",
        "title": "Cafeteira Espresso LOV preta — TRES 3 Corações",
        "subtitle": "Confira voltagem, vendedor, preço e condições no parceiro.",
        "category": "Casa e cozinha",
        "provider": "Mercado Livre",
        "url": "https://meli.la/1PQ6Tsq",
    },
    {
        "id": "demo-carregador-iphone",
        "product_key": "carregador-iphone-tipo-c",
        "title": "Carregador compatível com iPhone — fonte tipo C",
        "subtitle": "Confirme potência, certificação e compatibilidade do modelo.",
        "category": "Tecnologia",
        "provider": "Mercado Livre",
        "url": "https://meli.la/1eo2BxR",
    },
    {
        "id": "demo-lavadora-portatil",
        "product_key": "lavadora-portatil-maleta",
        "title": "Lavadora portátil com duas baterias e maleta",
        "subtitle": "Confira pressão declarada e todos os itens incluídos.",
        "category": "Casa e ferramentas",
        "provider": "Mercado Livre",
        "url": "https://meli.la/1UHNRHW",
    },
    {
        "id": "demo-travesseiros-oaktex",
        "product_key": "kit-travesseiros-oaktex",
        "title": "Kit com 2 travesseiros Oaktex 70 × 50 cm",
        "subtitle": "Confirme composição, medidas, quantidade e condições.",
        "category": "Casa",
        "provider": "Mercado Livre",
        "url": "https://meli.la/1hC8mC7",
    },
    {
        "id": "demo-soquetes-216",
        "product_key": "kit-soquetes-216",
        "title": "Kit de soquetes e catraca, 216 peças, Cr-V",
        "subtitle": "Confira a composição real do kit antes da compra.",
        "category": "Ferramentas",
        "provider": "Mercado Livre",
        "url": "https://meli.la/1D1t21D",
    },
    {
        "id": "demo-fone-capacete",
        "product_key": "fone-capacete-bluetooth",
        "title": "Fone para capacete Bluetooth RGB",
        "subtitle": "Confira funções, potência e compatibilidade; não presumimos intercomunicação.",
        "category": "Acessórios",
        "provider": "Mercado Livre",
        "url": "https://meli.la/1YRwdMx",
    },
]

for _offer in DEMO_OFFERS:
    _offer.update(
        enabled=True,
        expires_at="2099-12-31T23:59:59Z",
        platform="all",
        price=None,
        currency="BRL",
        campaign="catalogo-inicial-020",
        sponsored=False,
    )


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


def validate_partner_url(url: str, allowed_domains: set[str]) -> bool:
    """Exact approved host; subdomains require their own approval."""
    try:
        parsed = urlparse(str(url))
        return (len(str(url)) <= 2000 and parsed.scheme == 'https'
                and parsed.hostname in allowed_domains and not parsed.username
                and not parsed.password and parsed.port in (None,443) and not parsed.fragment)
    except (ValueError, TypeError):
        return False
