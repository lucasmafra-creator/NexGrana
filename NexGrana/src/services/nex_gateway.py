"""Cliente seguro do gateway conversacional do Nex.

O cliente nunca recebe a chave do provedor. Ele envia uma mensagem reduzida ao
gateway próprio do NexGrana, autenticada pela sessão do usuário. A ausência do
gateway é um estado normal: cálculos e consultas financeiras continuam locais.
"""
from __future__ import annotations

import json
import os
from ipaddress import ip_address
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener


GATEWAY_ENV = "NEXGRANA_NEX_GATEWAY_URL"
ALLOWED_FINANCIAL_FIELDS = {
    "month", "as_of", "income", "expense", "balance", "pending_month",
    "projected_balance", "data_state",
}


class GatewayUnavailable(RuntimeError):
    pass


class _NoAuthRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url,code,"Gateway não pode redirecionar token",headers,fp)


def _safe_urlopen(request,timeout):
    return build_opener(_NoAuthRedirects()).open(request,timeout=timeout)


def validate_gateway_url(value):
    parsed = urlparse(str(value or "").strip())
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        raise ValueError("O gateway do Nex precisa usar HTTPS público")
    if parsed.port not in (None, 443) or parsed.fragment or parsed.query or parsed.path != "/v1/chat":
        raise ValueError("O gateway do Nex precisa usar a porta HTTPS padrão")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("O gateway do Nex não pode apontar para a rede local")
    try:
        address = ip_address(host)
    except ValueError:
        address = None
    if address and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
        raise ValueError("O gateway do Nex não pode apontar para endereço privado")
    return parsed.geturl()


def _history_rows(history) -> list[dict]:
    rows = []
    characters = 0
    for item in reversed((history or [])[-24:]):
        role = str((item or {}).get("role") or "")
        content = " ".join(str((item or {}).get("text") or (item or {}).get("content") or "").split())
        if role in {"user", "assistant"} and content:
            content = content[:1600]
            if characters + len(content) > 12_000:
                break
            rows.append({"role": role, "content": content})
            characters += len(content)
    return list(reversed(rows))


def prepare_gateway_payload(
    message,
    *,
    request_id,
    locale="pt-BR",
    consent=False,
    financial_context=None,
    history=None,
    intent="general",
    preferences=None,
):
    text = " ".join(str(message or "").split()).strip()
    if not text:
        raise ValueError("Mensagem vazia")
    payload = {
        "request_id": str(request_id),
        "message": text[:4000],
        "locale": str(locale or "pt-BR")[:16],
        "history": _history_rows(history),
        "intent": str(intent or "general")[:32],
        "preferences": {
            key: value for key, value in dict(preferences or {}).items()
            if key in {"preferred_name", "tone", "detail"}
        },
        "financial_context": None,
    }
    if consent and financial_context:
        payload["financial_context"] = {
            key: financial_context[key]
            for key in ALLOWED_FINANCIAL_FIELDS
            if key in financial_context
        }
    return payload


class NexGatewayClient:
    def __init__(self, url: str, token_supplier, *, timeout: float = 36.0, opener=_safe_urlopen, sleeper=None):
        self.url = validate_gateway_url(url)
        self.token_supplier = token_supplier
        self.timeout = max(2.0, min(float(timeout), 45.0))
        self.opener = opener
        self.sleeper = sleeper

    @classmethod
    def from_environment(cls, token_supplier):
        try:
            from build_config import NEX_GATEWAY_URL
        except (ImportError, AttributeError):
            NEX_GATEWAY_URL = ""
        value = str(os.getenv(GATEWAY_ENV, "") or NEX_GATEWAY_URL or "").strip()
        return cls(value, token_supplier) if value else None

    def reply(self, payload: dict) -> str:
        token = str(self.token_supplier() or "").strip()
        if not token:
            raise GatewayUnavailable("Sessão indisponível para o modo online")
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = Request(
            self.url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "NexGrana/0.24-qa",
            },
        )
        # A timed-out POST may already have been processed by the provider.
        # Retry only after a server-side, durable request_id receipt exists.
        try:
            with self.opener(request, timeout=self.timeout) as response:
                raw = response.read(131_073)
        except HTTPError as exc:
            if exc.code in {401, 403}:
                raise GatewayUnavailable("Sessão recusada pelo gateway") from exc
            if exc.code == 429:
                raise GatewayUnavailable("Limite temporário do Nex online") from exc
            raise GatewayUnavailable("Gateway indisponível") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise GatewayUnavailable("Gateway indisponível") from exc
        if len(raw) > 131_072:
            raise GatewayUnavailable("Resposta do gateway excedeu o limite")
        try:
            data = json.loads(raw.decode("utf-8"))
            reply = str(data.get("reply") or "").strip()
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
            raise GatewayUnavailable("Resposta inválida do gateway") from exc
        if not reply or len(reply) > 12_000:
            raise GatewayUnavailable("Resposta vazia ou inválida do gateway")
        return reply
