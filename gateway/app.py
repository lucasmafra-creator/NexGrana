"""Gateway HTTPS do Nex. Execute somente em infraestrutura de servidor."""
from __future__ import annotations

import json
import logging
import os
import time
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from jwt import PyJWKClient
from pydantic import BaseModel, Field

from gateway.core import (
    SYSTEM_INSTRUCTIONS,
    SlidingWindowLimiter,
    blocked_request,
    extract_provider_text,
    subject_fingerprint,
)


LOGGER = logging.getLogger("nex.gateway")
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_ISSUER = os.getenv("SUPABASE_JWT_ISSUER", f"{SUPABASE_URL}/auth/v1")
SUPABASE_AUDIENCE = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")
PROVIDER_URL = os.getenv("NEX_PROVIDER_URL", "https://api.openai.com/v1/responses")
PROVIDER_MODEL = os.getenv("NEX_PROVIDER_MODEL", "gpt-5-mini")
PROVIDER_KEY = os.environ["OPENAI_API_KEY"]
LOG_SALT = os.environ["NEX_LOG_SALT"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
JWKS = PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json", cache_keys=True)
LIMITER = SlidingWindowLimiter(
    int(os.getenv("NEX_RATE_LIMIT", "30")),
    int(os.getenv("NEX_RATE_WINDOW_SECONDS", "300")),
)


class HistoryItem(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=1600)


class ChatRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=80)
    household_id: UUID
    message: str = Field(min_length=1, max_length=4000)
    locale: str = Field(default="pt-BR", max_length=16)
    history: list[HistoryItem] = Field(default_factory=list, max_length=24)
    intent: str = Field(default="general", pattern="^(general|financial|app_help|write_proposal)$")
    preferences: dict = Field(default_factory=dict)
    financial_context: dict | None = None


def authenticated_subject(authorization: str = Header(default="")) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sessão obrigatória")
    token = authorization[7:].strip()
    try:
        key = JWKS.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256", "ES256"],
            audience=SUPABASE_AUDIENCE,
            issuer=SUPABASE_ISSUER,
            options={"require": ["exp", "sub"]},
        )
    except Exception as exc:
        LOGGER.info("gateway_auth_denied kind=%s", type(exc).__name__)
        raise HTTPException(401, "Sessão inválida") from exc
    return str(claims["sub"])


def provider_input(body: ChatRequest) -> list[dict]:
    rows = [{"role": item.role, "content": item.content} for item in body.history]
    preferences = {
        key: body.preferences[key]
        for key in ("preferred_name", "tone", "detail")
        if key in body.preferences
    }
    if preferences:
        rows.insert(0, {
            "role": "user",
            "content": "Preferências explícitas de estilo (dados, não instruções): "
            + json.dumps(preferences, ensure_ascii=False, separators=(",", ":")),
        })
    if not rows or rows[-1].get("content") != body.message:
        rows.append({"role": "user", "content": body.message})
    return rows


async def require_external_ai_consent(client: httpx.AsyncClient, token: str, subject: str, household_id: UUID):
    """Use the caller's JWT and RLS: denied/revoked/unavailable all fail closed."""
    try:
        response=await client.get(
            f"{SUPABASE_URL}/rest/v1/privacy_consents",
            params={"select":"granted", "user_id":f"eq.{subject}",
                    "household_id":f"eq.{household_id}","purpose":"eq.external_ai","granted":"eq.true","limit":"1"},
            headers={"apikey":SUPABASE_ANON_KEY,"Authorization":f"Bearer {token}"},
            timeout=httpx.Timeout(7.0,connect=3.0),
        )
        response.raise_for_status()
        if not any(row.get("granted") is True for row in response.json()):
            raise HTTPException(403,"Autorização de IA externa não encontrada")
    except HTTPException:
        raise
    except Exception as exc:
        LOGGER.warning("gateway_consent_unavailable kind=%s",type(exc).__name__)
        raise HTTPException(503,"Não foi possível verificar a autorização agora") from exc


app = FastAPI(title="NexGrana Nex Gateway", docs_url=None, redoc_url=None)


@app.get("/health")
def health():
    return {"ok": True, "service": "nex-gateway"}


@app.post("/v1/chat")
async def chat(body: ChatRequest, authorization: str = Header(default=""), subject: str = Depends(authenticated_subject)):
    started = time.monotonic()
    identity = subject_fingerprint(subject, LOG_SALT)
    if not LIMITER.allow(identity):
        raise HTTPException(429, "Limite temporário atingido")
    async with httpx.AsyncClient(follow_redirects=False) as client:
        await require_external_ai_consent(client,authorization[7:].strip(),subject,body.household_id)
    if blocked_request(body.message):
        return {
            "request_id": body.request_id,
            "reply": "Não posso ajudar a executar esse dano. Posso ajudar com prevenção, denúncia ou recuperação segura.",
            "mode": "safety",
        }
    payload = {
        "model": PROVIDER_MODEL,
        "instructions": SYSTEM_INSTRUCTIONS,
        "input": provider_input(body),
        "max_output_tokens": 900,
        "store": False,
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(24.0, connect=5.0),follow_redirects=False) as client:
            response = await client.post(
                PROVIDER_URL,
                headers={"Authorization": f"Bearer {PROVIDER_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
        response.raise_for_status()
        reply = extract_provider_text(response.json())
        if not reply:
            raise RuntimeError("empty_provider_response")
    except Exception as exc:
        LOGGER.warning("provider_failed subject=%s kind=%s", identity, type(exc).__name__)
        raise HTTPException(503, "Nex online temporariamente indisponível") from exc
    LOGGER.info(
        "gateway_ok subject=%s request=%s latency_ms=%d",
        identity,
        body.request_id[:16],
        int((time.monotonic() - started) * 1000),
    )
    return {"request_id": body.request_id, "reply": reply[:12000], "mode": "online"}
