"""Fail-closed environment guard for the QA clone.

This module never prints or returns credential values. Remote services are
allowed only when the operator explicitly pins their exact QA endpoint.
"""
from __future__ import annotations

import base64
import json
import os
from urllib.parse import urlsplit


class QAEnvironmentError(RuntimeError):
    pass


def _normalized_endpoint(value: str) -> str:
    return value.strip().rstrip("/").lower()


def _jwt_role(value: str) -> str | None:
    try:
        payload = value.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
        role = data.get("role")
        return role.lower() if isinstance(role, str) else None
    except Exception:
        return None


def inspect_qa_environment(environ=None) -> dict:
    env = os.environ if environ is None else environ
    reasons: list[str] = []
    app_env = str(env.get("APP_ENV", "local")).strip().lower()
    if app_env in {"prod", "production"}:
        reasons.append("O clone QA não inicia com APP_ENV de produção.")

    privileged_names = ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY", "SUPABASE_SECRET_KEYS", "SUPABASE_SERVICE_ROLE_KEYS")
    privileged_name_present = any(str(env.get(name, "")).strip() for name in privileged_names)
    privileged_key_present = any(
        str(value).strip().lower().startswith("sb_secret_")
        for name, value in env.items()
        if name.upper().startswith("SUPABASE_")
    )
    legacy_privileged_jwt = any(
        _jwt_role(str(env.get(name, ""))) == "service_role"
        for name in ("SUPABASE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_PUBLISHABLE_KEY")
    )
    privileged_present = privileged_name_present or privileged_key_present or legacy_privileged_jwt
    if privileged_present:
        reasons.append("Foi encontrada uma variável de credencial privilegiada; remova-a do clone QA.")

    supabase_url = str(env.get("SUPABASE_URL", "")).strip()
    allowed_supabase_url = str(env.get("SIMLABS_QA_SUPABASE_URL", "")).strip()
    if supabase_url and (not allowed_supabase_url or _normalized_endpoint(supabase_url) != _normalized_endpoint(allowed_supabase_url)):
        reasons.append("SUPABASE_URL não corresponde ao endpoint QA explicitamente autorizado.")
    project_ref = str(env.get("SIMLABS_QA_SUPABASE_PROJECT_REF", "")).strip().lower()
    supabase_host = urlsplit(supabase_url).hostname or ""
    if supabase_url and (not project_ref or not (project_ref.startswith("qa-") or project_ref.startswith("staging-")) or supabase_host != f"{project_ref}.supabase.co"):
        reasons.append("Projeto Supabase QA deve ter referência qa-*/staging-* vinculada ao host permitido.")
    if any(str(env.get(name, "")).strip() for name in ("SUPABASE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_PUBLISHABLE_KEY")) and not supabase_url:
        reasons.append("Há chave Supabase sem URL vinculada; remova a chave ou configure o endpoint QA correto.")

    database_url = str(env.get("DATABASE_URL", "sqlite:///./sim_labs.db")).strip()
    scheme = urlsplit(database_url).scheme.lower()
    remote_database = scheme.startswith(("postgres", "mysql", "mariadb"))
    allowed_database_url = str(env.get("SIMLABS_QA_DATABASE_URL", "")).strip()
    if remote_database and (not allowed_database_url or _normalized_endpoint(database_url) != _normalized_endpoint(allowed_database_url)):
        reasons.append("DATABASE_URL remoto não corresponde ao endpoint QA explicitamente autorizado.")
    database_project_ref = str(env.get("SIMLABS_QA_DATABASE_PROJECT_REF", "")).strip().lower()
    database_host = urlsplit(database_url).hostname or ""
    if remote_database and (not database_project_ref or not (database_project_ref.startswith("qa-") or database_project_ref.startswith("staging-")) or database_host != f"db.{database_project_ref}.supabase.co"):
        reasons.append("Banco remoto só pode usar host do projeto Supabase qa-*/staging- explicitamente separado.")

    return {
        "status": "BLOCKED" if reasons else "PASS",
        "mode": "remote-qa-allowlisted" if (supabase_url or remote_database) and not reasons else "local-only",
        "checks": {
            "production_app_env": "BLOCKED" if app_env in {"prod", "production"} else "PASS",
            "privileged_supabase_credentials": "BLOCKED" if privileged_present else "PASS",
            "supabase_endpoint_allowlist": "BLOCKED" if any("SUPABASE_URL" in reason or "Projeto Supabase" in reason or "chave Supabase" in reason for reason in reasons) else "PASS",
            "database_endpoint_allowlist": "BLOCKED" if any("DATABASE_URL" in reason or "Banco remoto" in reason for reason in reasons) else "PASS",
        },
        "reasons": reasons,
        "secret_values_returned": False,
    }


def enforce_qa_environment(environ=None) -> dict:
    result = inspect_qa_environment(environ)
    if result["status"] != "PASS":
        raise QAEnvironmentError("Inicialização recusada pelo guard QA: " + " ".join(result["reasons"]))
    return result
