"""Validação e transformação de dados do painel privado de Achados.

Este módulo não conhece Flet nem Supabase. Manter as regras em funções puras
permite testar o painel sem rede e impede que a interface envie dados parciais
ou URLs inseguras ao banco.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from uuid import uuid4

from .offers import validate_offer_url


OFFER_HOSTS = {"meli.la", "mercadolivre.com.br", "www.mercadolivre.com.br"}
IMAGE_HOSTS = {"http2.mlstatic.com"}
CATEGORIES = (
    "Casa",
    "Casa e cozinha",
    "Casa e ferramentas",
    "Tecnologia",
    "Eletrônicos",
    "Ferramentas",
    "Carro e moto",
    "Beleza e cabelo",
    "Acessórios",
    "Outros",
)


class OfferValidationError(ValueError):
    """Erro de formulário seguro para exibição ao administrador."""


def normalize_tags(value) -> list[str]:
    if isinstance(value, str):
        parts = value.split(",")
    else:
        parts = value or []
    result: list[str] = []
    seen: set[str] = set()
    for part in parts:
        tag = " ".join(str(part).strip().split())[:50]
        key = tag.casefold()
        if tag and key not in seen:
            seen.add(key)
            result.append(tag)
    return result[:20]


def parse_optional_money(value) -> float | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        amount = Decimal(raw)
    except InvalidOperation as exc:
        raise OfferValidationError("Preço inválido. Use, por exemplo, 129,90.") from exc
    if not amount.is_finite() or amount < 0:
        raise OfferValidationError("O preço não pode ser negativo.")
    return float(amount.quantize(Decimal("0.01")))


def validate_image_url(url: str) -> bool:
    raw = str(url or "").strip()
    if not raw:
        return True
    try:
        parsed = urlparse(raw)
    except Exception:
        return False
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.fragment
    ):
        return False
    return parsed.hostname.lower().rstrip(".") in IMAGE_HOSTS


def parse_expiry(value: str, *, now: datetime | None = None, enabled: bool = False) -> str:
    raw = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OfferValidationError("Validade inválida. Use AAAA-MM-DDTHH:MM:SSZ.") from exc
    if parsed.tzinfo is None:
        raise OfferValidationError("A validade precisa informar o fuso horário, como Z.")
    parsed = parsed.astimezone(timezone.utc)
    if enabled and parsed <= (now or datetime.now(timezone.utc)):
        raise OfferValidationError("Um achado publicado precisa ter validade futura.")
    return parsed.isoformat().replace("+00:00", "Z")


def build_offer_payload(values: dict, *, existing: dict | None = None, now: datetime | None = None) -> dict:
    existing = existing or {}
    title = " ".join(str(values.get("title") or "").strip().split())
    if len(title) < 4:
        raise OfferValidationError("Informe um título com pelo menos 4 caracteres.")
    if len(title) > 180:
        raise OfferValidationError("O título pode ter no máximo 180 caracteres.")

    url = str(values.get("url") or "").strip()
    if not validate_offer_url(url, OFFER_HOSTS):
        raise OfferValidationError("Use um link HTTPS permitido do Mercado Livre.")

    image_url = str(values.get("image_url") or "").strip() or None
    if not validate_image_url(image_url or ""):
        raise OfferValidationError("A imagem deve usar HTTPS no domínio http2.mlstatic.com.")
    image_alt = " ".join(str(values.get("image_alt") or "").strip().split())
    if image_url and len(image_alt) < 4:
        raise OfferValidationError("Descreva a imagem para acessibilidade.")

    category = " ".join(str(values.get("category") or "Outros").strip().split())
    if category not in CATEGORIES:
        raise OfferValidationError("Selecione uma categoria válida.")

    try:
        sort_order = int(str(values.get("sort_order") or 1000).strip())
    except ValueError as exc:
        raise OfferValidationError("A ordem precisa ser um número inteiro.") from exc
    if sort_order < 0 or sort_order > 999_999:
        raise OfferValidationError("A ordem deve ficar entre 0 e 999999.")

    enabled = bool(values.get("enabled"))
    expires_at = parse_expiry(str(values.get("expires_at") or ""), now=now, enabled=enabled)
    subtitle = " ".join(str(values.get("subtitle") or "").strip().split())[:500]
    provider = " ".join(str(values.get("provider") or "Mercado Livre").strip().split())[:80]

    return {
        "title": title,
        "subtitle": subtitle,
        "provider": provider or "Mercado Livre",
        "url": url,
        "original_url": url,
        "image_url": image_url,
        "image_alt": image_alt[:240],
        "category": category,
        "search_tags": normalize_tags(values.get("search_tags")),
        "sort_order": sort_order,
        "enabled": enabled,
        "expires_at": expires_at,
        "platform": "all",
        "currency": "BRL",
        "price": parse_optional_money(values.get("price")),
        "source": "owner_panel",
        "sponsored": False,
        "product_key": existing.get("product_key") or uuid4().hex,
    }


def filter_admin_offers(rows: list[dict], query: str = "", status: str = "all", category: str = "all") -> list[dict]:
    needle = str(query or "").strip().casefold()
    selected_category = str(category or "all").casefold()
    selected_status = str(status or "all").casefold()
    result = []
    for row in rows or []:
        if selected_status == "published" and not row.get("enabled"):
            continue
        if selected_status == "draft" and row.get("enabled"):
            continue
        if selected_category != "all" and str(row.get("category") or "").casefold() != selected_category:
            continue
        haystack = " ".join(
            str(row.get(key) or "") for key in ("title", "subtitle", "provider", "category", "search_tags")
        ).casefold()
        if needle and needle not in haystack:
            continue
        result.append(row)
    return result
