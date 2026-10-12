"""Textos adaptativos para espaços individuais e familiares."""
from __future__ import annotations


def is_family_mode(household) -> bool:
    return str((household or {}).get("mode") or "individual").strip().lower() == "family"


def space_label(household, individual: str, family: str) -> str:
    return family if is_family_mode(household) else individual


def dashboard_labels(household) -> dict[str, str]:
    family = is_family_mode(household)
    return {
        "consolidated_title": "Consolidado da família" if family else "Seu panorama individual",
        "consolidated_balance": "saldo familiar atual" if family else "saldo atual do seu espaço",
        "empty_person": "Pessoa" if family else "Seu perfil",
        "market_scope": "da família" if family else "do seu espaço",
        "profiles_tutorial": (
            "Confira o perfil selecionado antes de lançar ou consultar valores. Cada pessoa vê o próprio recorte, "
            "e o consolidado familiar respeita os rateios."
            if family
            else "Este espaço é individual: os lançamentos, metas e conversas pertencem ao seu único perfil. "
            "Você pode transformar a organização em família mais tarde pelas configurações."
        ),
    }
