"""Transparent Nex outfits, compact variants and optional occasion calendar."""
from datetime import date, timedelta


_CUTOUT_ROOT = "nex/skins/cutouts/"

SKINS = {
    "auto": ("Automático por data", None),
    "original": ("Nex original", "nex/nex_hd.png"),
    "welcome": ("Acolhedor", "nex/nex_welcome_v2.png"),
    "thinking": ("Pensativo", "nex/nex_thinking_v2.png"),
    "celebrate": ("Comemorando", "nex/nex_celebrate_v2.png"),
    "winter": ("Edição de dezembro", "nex/nex_winter_v2.png"),
}

_CATALOG = {
    "administrativo": ("Administrativo", "Nex_Administrativo.png", "Profissões", None),
    "ano_novo": ("Ano Novo", "Nex_Ano_Novo.png", "Datas festivas", "1 de janeiro"),
    "carnaval": ("Carnaval", "Nex_Carnaval.png", "Datas festivas", "Data móvel"),
    "casal": ("Casal", "Nex_Casal.png", "Estilo de vida", None),
    "cinema": ("Cinema", "Nex_Cinema.png", "Interesses", None),
    "compras": ("Compras", "Nex_Compras.png", "Interesses", None),
    "conquistas": ("Conquistas", "Nex_Conquistas.png", "Estilo de vida", None),
    "consciencia_negra": ("Consciência Negra", "Nex_Consciencia_Negra.png", "Datas e causas sociais", "20 de novembro"),
    "criativo": ("Criativo", "Nex_Criativo.png", "Profissões", None),
    "dev": ("Dev", "Nex_Dev.png", "Profissões", None),
    "dia_da_mulher": ("Dia da Mulher", "Nex_Dia_da_Mulher.png", "Datas e causas sociais", "8 de março"),
    "economico": ("Econômico", "Nex_Economico.png", "Estilo de vida", None),
    "empreendedor": ("Empreendedor", "Nex_Empreendedor.png", "Profissões", None),
    "estudante": ("Estudante", "Nex_Estudante.png", "Profissões", None),
    "fitness": ("Fitness", "Nex_Fitness.png", "Estilo de vida", None),
    "foco": ("Foco", "Nex_Foco.png", "Estilo de vida", None),
    "freelancer": ("Freelancer", "Nex_Freelancer.png", "Profissões", None),
    "gamer": ("Gamer", "Nex_Gamer.png", "Interesses", None),
    "gastronomia": ("Gastronomia", "Nex_Gastronomia.png", "Interesses", None),
    "halloween": ("Halloween", "Nex_Halloween.png", "Datas festivas", "31 de outubro"),
    "ia": ("IA", "Nex_IA.png", "Interesses", None),
    "investidor": ("Investidor", "Nex_Investidor.png", "Profissões", None),
    "meio_ambiente": ("Meio Ambiente", "Nex_Meio_Ambiente.png", "Datas e causas sociais", "5 de junho"),
    "musica": ("Música", "Nex_Musica.png", "Interesses", None),
    "natal": ("Natal", "Nex_Natal.png", "Datas festivas", "24 e 25 de dezembro"),
    "natureza": ("Natureza", "Nex_Natureza.png", "Interesses", None),
    "operador": ("Operador", "Nex_Operador.png", "Profissões", None),
    "organizado": ("Organizado", "Nex_Organizado.png", "Estilo de vida", None),
    "pascoa": ("Páscoa", "Nex_Pascoa.png", "Datas festivas", "Data móvel"),
    "pet": ("Pet", "Nex_Pet.png", "Interesses", None),
    "planejamento": ("Planejamento", "Nex_Planejamento.png", "Estilo de vida", None),
    "povos_indigenas": ("Povos Indígenas", "Nex_Povos_Indigenas.png", "Datas e causas sociais", "19 de abril"),
    "profissional": ("Profissional", "Nex_Profissional.png", "Profissões", None),
    "tech": ("Tech", "Nex_Tech.png", "Interesses", None),
    "trabalho": ("Trabalho", "Nex_Trabalho.png", "Datas e causas sociais", "1 de maio"),
    "viagem": ("Viagem", "Nex_Viagem.png", "Interesses", None),
}

SKIN_META = {
    "auto": {"category": "Clássicos", "when": "Troca somente nas datas especiais"},
    "original": {"category": "Clássicos", "when": "Sempre disponível"},
    "welcome": {"category": "Clássicos", "when": "Sempre disponível"},
    "thinking": {"category": "Clássicos", "when": "Sempre disponível"},
    "celebrate": {"category": "Clássicos", "when": "Sempre disponível"},
    "winter": {"category": "Clássicos", "when": "Dezembro, fora das datas de Natal"},
}
for _key, (_label, _filename, _category, _when) in _CATALOG.items():
    SKINS[_key] = (_label, _CUTOUT_ROOT + _key + "_v3.png")
    SKIN_META[_key] = {"category": _category, "when": _when or "Escolha manual"}

# A contextual appearance is used only when the account explicitly enables
# contextual switching and allows that exact skin. This keeps new contexts
# from silently changing a user's selected appearance.
CONTEXT_SKINS = {
    "home": ("welcome", "thinking", "celebrate"),
    "chat": ("thinking", "profissional"),
    "investments": ("investidor", "planejamento", "foco"),
    "financial_health": ("economico", "foco", "profissional"),
    "market": ("compras", "gastronomia", "economico"),
    "acquisitions": ("compras", "economico"),
    "extra_income": ("empreendedor", "freelancer"),
    "planning": ("planejamento", "organizado", "foco"),
    "achievements": ("conquistas", "celebrate"),
}


def allowed_auto_skins(preferences) -> set[str]:
    raw = (preferences or {}).get("nex_auto_allowed_skins", [])
    if not isinstance(raw, (list, tuple, set)):
        return set()
    return {key for key in raw if isinstance(key, str) and key in SKINS and key != "auto"}


def easter_sunday(year: int) -> date:
    """Calculate Gregorian Easter Sunday for the local occasion calendar."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day_of_month = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day_of_month)


def occasion_skin(today: date | None = None) -> str | None:
    """Return only an explicitly themed occasion skin for the current date."""
    today = today or date.today()
    easter = easter_sunday(today.year)
    carnival_saturday = easter - timedelta(days=50)
    if carnival_saturday <= today <= easter - timedelta(days=47):
        return "carnaval"
    if easter - timedelta(days=2) <= today <= easter + timedelta(days=1):
        return "pascoa"

    fixed = {
        (1, 1): "ano_novo",
        (3, 8): "dia_da_mulher",
        (4, 19): "povos_indigenas",
        (5, 1): "trabalho",
        (6, 5): "meio_ambiente",
        (10, 31): "halloween",
        (11, 20): "consciencia_negra",
        (12, 24): "natal",
        (12, 25): "natal",
    }
    if (today.month, today.day) in fixed:
        return fixed[(today.month, today.day)]
    if today.month == 12:
        return "winter"
    return None


def selected_skin(preferences, today: date | None = None) -> str | None:
    key = (preferences or {}).get("nex_skin", "auto")
    if key not in SKINS:
        key = "auto"
    if key != "auto":
        return key
    return occasion_skin(today)


def preview_asset(key: str, today: date | None = None) -> str:
    """Return a valid illustration for the catalog, including Auto preview."""
    if key == "auto":
        active = occasion_skin(today)
        return SKINS[active][1] if active and SKINS[active][1] else "nex/nex_hd.png"
    if key in SKINS and SKINS[key][1]:
        return SKINS[key][1]
    return "nex/nex_hd.png"


def skin_asset(preferences, today: date | None = None, role: str | None = None, context: str | None = None):
    preferences = preferences or {}
    key = (preferences.get("nex_skin") or "auto")
    if key not in SKINS:
        key = "auto"
    # An explicit manual selection stays locked. Contextual switching is
    # available only in Auto mode and only for entries on the user's allowlist.
    if key == "auto" and context and preferences.get("nex_context_auto") is True:
        allowed = allowed_auto_skins(preferences)
        key = next((candidate for candidate in CONTEXT_SKINS.get(context, ()) if candidate in allowed), "auto")
    if key == "auto":
        key = selected_skin(preferences, today)
    if key is None:
        return None
    # Auto-by-date is also opt-in per skin. Manual selection remains available
    # regardless of this list.
    if preferences.get("nex_skin", "auto") == "auto" and key not in allowed_auto_skins(preferences):
        return None
    asset = SKINS[key][1]
    if not asset:
        return None
    if key in _CATALOG and role in {"avatar", "compact", "dock"}:
        return _CUTOUT_ROOT + key + "_avatar_v3.png"
    return asset
