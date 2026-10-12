"""Tutorial Nex 2.0: catálogo, sandbox e máquina de estados.

O sandbox é deliberadamente separado dos lançamentos reais. A única função de
prévia usa o motor financeiro canônico, inclusive para a regra de vencimento.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import StrEnum
from decimal import Decimal, InvalidOperation
import uuid

from .finance_engine import amount, day, snapshot


TUTORIAL_VERSION = "2.0"


class TutorialStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PREVIEW = "preview"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    PENDING_SYNC = "pending_sync"
    SAVED = "saved"
    ERROR = "error"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    DISCARDED = "discarded"


@dataclass(frozen=True)
class TutorialScope:
    user_id: str
    household_id: str
    member_id: str
    session_generation: int

    @property
    def key(self):
        # Refreshing an access token is not a change of owner or household.
        return f"{self.user_id}:{self.household_id}:{self.member_id}"


def training_money(value):
    """Parse explicit Brazilian currency input without silently turning errors into zero."""
    text = str(value if value is not None else "").strip()
    if not text or any(character not in "0123456789.," for character in text):
        raise ValueError("Informe um valor numérico válido")
    if "," in text:
        whole, fraction = text.split(",", 1) if text.count(",") == 1 else ("", "")
        if not whole or not fraction or len(fraction) > 2 or not fraction.isdigit():
            raise ValueError("Use vírgula e até duas casas decimais")
        groups = whole.split(".")
        if not (groups[0].isdigit() and groups[0] and all(len(g) == 3 and g.isdigit() for g in groups[1:])):
            raise ValueError("Confira os separadores do valor")
        normalized = "".join(groups) + "." + fraction
    elif "." in text:
        parts = text.split(".")
        if len(parts) == 2 and len(parts[1]) <= 2 and all(part.isdigit() for part in parts):
            normalized = text
        elif parts[0].isdigit() and all(len(part) == 3 and part.isdigit() for part in parts[1:]):
            normalized = "".join(parts)
        else:
            raise ValueError("Confira os separadores do valor")
    else:
        normalized = text
    try:
        result = Decimal(normalized)
        if not result.is_finite() or result < 0:
            raise ValueError("Informe um valor positivo")
        return amount(result)
    except InvalidOperation as exc:
        raise ValueError("Informe um valor numérico válido") from exc


@dataclass(frozen=True)
class TutorialModule:
    key: str
    title: str
    summary: str
    task: str
    persistence: str
    destination: str = ""


TUTORIAL_MODULES = (
    TutorialModule("welcome","Boas-vindas","Escolha por onde começar e aprenda fazendo.","Conheça as regras essenciais do NexGrana.","Somente progresso"),
    TutorialModule("income","Renda recebida — treino","Renda recebida soma ao saldo da competência.","Pratique origem, valor e data de recebimento.","Real somente após confirmação","income"),
    TutorialModule("expense","Despesa","Uma despesa futura só reduz o saldo no vencimento.","Informe descrição, valor e vencimento e compare o impacto.","Real somente após confirmação","expense"),
    TutorialModule("balance","Saldo hipotético","Entenda saldo atual e projetado sem mexer na conta.","Veja quando a despesa muda cada saldo, sem preencher campos.","Somente explicação"),
    TutorialModule("acquisition","Aquisição","Intenção de comprar: não é despesa nem meta e não debita saldo.","Escolha um desejo, preço e prioridade. Criar meta depois é uma decisão separada.","Aquisição ou só exemplo","acquisition"),
    TutorialModule("goals","Metas","Compromisso com objetivo, valor, prazo, progresso e esforço mensal.","Compare com Aquisição: o desejo vira meta somente quando você decide planejar e acompanhar.","Meta real após confirmação","goals"),
    TutorialModule("investments","Investimentos","Compare prazo, aportes, taxa, custos e impostos declarados.","Faça uma projeção educativa.","Somente simulação","investments"),
    TutorialModule("extra_income","Renda Extra","Escolha um experimento compatível com tempo e habilidade.","Inicie uma Trilha Nex sem promessa de ganho.","Trilha após escolha","extra_income"),
    TutorialModule("market","Mercado","Monte a lista e confira o total antes da compra.","Adicione, edite e remova um produto.","Carrinho após confirmação","market"),
    TutorialModule("offers","Achados","Pesquise ofertas e entenda os links externos de afiliado.","Use busca e filtros sem compra automática.","Sem dado financeiro","offers"),
    TutorialModule("nex","Nex","Converse, escolha um apelido e fixe até cinco assuntos.","Teste o chat e reconheça os modos local/online.","Preferência autorizada","nex"),
    TutorialModule("family","Família e perfis","Entenda perfil ativo, rateio e consolidado.","Veja o que muda entre espaço individual e familiar.","Sem integrante fictício","family"),
    TutorialModule("privacy","Privacidade","Controle consentimentos, cache, fila e reconexão.","Revise o que é local, online e opcional.","Escolhas explícitas","privacy"),
)
MODULE_BY_KEY = {module.key: module for module in TUTORIAL_MODULES}


def tutorial_financial_preview(opening_balance=200, expense=10, due_date="20/09/2026", simulated_today="19/09/2026"):
    """Prévia didática pelo motor real; nunca elegível para commit como renda."""
    due = day(due_date)
    today = day(simulated_today)
    month = due.strftime("%m/%Y")
    opening = amount(opening_balance)
    cost = amount(expense)
    if opening < 0 or cost < 0:
        raise ValueError("Valores do tutorial não podem ser negativos")
    synthetic_income = [{
        "id":"tutorial-opening","member_id":"tutorial","amount":float(opening),
        "month":month,"received_at":date(due.year,due.month,1).isoformat(),
        "_tutorial_only":True,
    }]
    synthetic_expense = [{
        "id":"tutorial-expense","payer_member_id":"tutorial","amount":float(cost),
        "expense_date":due.isoformat(),"category":"Tutorial","description":"Despesa de exemplo",
        "expense_shares":[],"payment_status":"pending","_tutorial_only":True,
    }]
    result=snapshot(synthetic_income,synthetic_expense,month,today=today)
    return {
        "sandbox":True,"month":month,"simulated_today":today.isoformat(),"due_date":due.isoformat(),
        "opening_balance":float(opening),"expense":float(cost),
        "current_balance":result["balance"],"projected_balance":result["projected_balance"],
        "pending":result["pending_month"],"effective_expense":result["expense"],
    }


@dataclass
class TutorialSession:
    scope: TutorialScope
    version: str = TUTORIAL_VERSION
    current_module: str = "welcome"
    statuses: dict = field(default_factory=dict)
    sandbox: dict = field(default_factory=dict)
    commit_ids: dict = field(default_factory=dict)

    def __post_init__(self):
        self.statuses = {key: str(value) for key, value in dict(self.statuses or {}).items() if key in MODULE_BY_KEY}
        self.sandbox = dict(self.sandbox or {})
        self.commit_ids = dict(self.commit_ids or {})
        if self.current_module not in MODULE_BY_KEY:
            self.current_module = "welcome"

    @classmethod
    def from_mapping(cls, scope, value):
        value=value if isinstance(value,dict) else {}
        stored_key=value.get("scope_key")
        # Previous releases included the transient session generation in the key.
        # Accept that legacy record only when its stable identity matches exactly.
        same_scope=(not value and stored_key is None) or stored_key == scope.key or (
            isinstance(stored_key,str) and stored_key.rsplit(":",1)[0] == scope.key
            and stored_key.rsplit(":",1)[-1].isdigit()
        )
        if not same_scope or value.get("version") not in (None,TUTORIAL_VERSION):
            value={}
        return cls(
            scope=scope,current_module=value.get("current_module") or "welcome",
            statuses=value.get("statuses") or {},sandbox=value.get("sandbox") or {},
            commit_ids=value.get("commit_ids") or {},
        )

    def to_mapping(self):
        return {
            "version":self.version,"scope_key":self.scope.key,"current_module":self.current_module,
            "statuses":dict(self.statuses),"sandbox":dict(self.sandbox),"commit_ids":dict(self.commit_ids),
        }

    def start(self, module_key):
        if module_key not in MODULE_BY_KEY:
            raise ValueError("Módulo de tutorial inválido")
        self.current_module=module_key
        if self.statuses.get(module_key) not in {TutorialStatus.COMPLETED.value,TutorialStatus.SAVED.value,TutorialStatus.PENDING_SYNC.value}:
            self.statuses[module_key]=TutorialStatus.IN_PROGRESS.value
        return MODULE_BY_KEY[module_key]

    def preview_balance(self, opening=200, expense=10, due_date="20/09/2026", simulated_today="19/09/2026"):
        self.start("balance")
        preview=tutorial_financial_preview(opening,expense,due_date,simulated_today)
        self.sandbox["balance"]=preview
        self.statuses["balance"]=TutorialStatus.PREVIEW.value
        return preview

    def complete(self, module_key=None, saved=False, pending_sync=False):
        key=module_key or self.current_module
        if key not in MODULE_BY_KEY:
            raise ValueError("Módulo de tutorial inválido")
        if pending_sync:
            status=TutorialStatus.PENDING_SYNC
        elif saved:
            status=TutorialStatus.SAVED
        else:
            status=TutorialStatus.COMPLETED
        self.statuses[key]=status.value
        return status

    def skip(self, module_key=None):
        key=module_key or self.current_module
        self.statuses[key]=TutorialStatus.SKIPPED.value

    def discard(self, module_key=None):
        key=module_key or self.current_module
        self.sandbox.pop(key,None)
        self.statuses[key]=TutorialStatus.DISCARDED.value

    def stable_commit_id(self, module_key=None):
        key=module_key or self.current_module
        if key not in self.commit_ids:
            self.commit_ids[key]=str(uuid.uuid4())
        return self.commit_ids[key]

    @property
    def completed_count(self):
        accepted={TutorialStatus.COMPLETED.value,TutorialStatus.SAVED.value,TutorialStatus.PENDING_SYNC.value}
        return sum(1 for key in MODULE_BY_KEY if self.statuses.get(key) in accepted)

    @property
    def progress(self):
        return self.completed_count / len(TUTORIAL_MODULES)
