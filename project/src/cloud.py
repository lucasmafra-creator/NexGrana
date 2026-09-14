import json
import os
import uuid
import time
import threading
from datetime import datetime
from pathlib import Path

from supabase import create_client
from services.finance_engine import day
import logging
from httpx import TransportError
logger = logging.getLogger(__name__)


def storage_dir() -> Path:
    base = os.getenv("FLET_APP_STORAGE_DATA")
    if base:
        p = Path(base)
    else:
        p = Path(__file__).resolve().parent.parent / ".data"
    p.mkdir(parents=True, exist_ok=True)
    return p


CONFIG_PATH = storage_dir() / "cloud_config.json"
SESSION_PATH = storage_dir() / "cloud_session.json"
CACHE_PATH = storage_dir() / "offline_cache.json"

# Public client configuration. This is intentionally the publishable key,
# never a service_role/secret key.
DEFAULT_SUPABASE_URL = "https://idiyziffdzxcqmshzsws.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_asMuC_w3q9fvR1rpEAZ1zQ_jEekiUPx"


def save_config(url: str, anon_key: str):
    CONFIG_PATH.write_text(
        json.dumps({"url": url.strip(), "anon_key": anon_key.strip()}, indent=2),
        encoding="utf-8",
    )


def load_config():
    # End users should not need to configure the backend.
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if cfg.get("url") and cfg.get("anon_key"):
                return cfg
        except Exception:
            pass
    return {"url": DEFAULT_SUPABASE_URL, "anon_key": DEFAULT_SUPABASE_KEY}


class Cloud:
    def __init__(self, vault=None):
        self.vault = vault
        self._memory_cache = {}
        self.client = None
        self.user = None
        self.profile = None
        self.household = None
        self.member = None
        self.online = True
        self.last_network_error = None
        self._auth_lock = threading.RLock()

    def _secure_write_json(self, path, payload):
        if not self.vault:
            raise RuntimeError("Armazenamento seguro indisponível")
        self.vault.write(path.name,payload)

    def _scope(self):
        if not self.user or not self.household:
            raise RuntimeError("Autenticação e família obrigatórias")
        return str(self.user.id)+":"+str(self.household["id"])

    def _cache_set(self,key,value):
        name="cache:"+self._scope()+":"+key
        self._memory_cache[name]=value
        if self.vault:
            self.vault.write(name,value)
            keys=self.vault.read('cache-index',[])
            if name not in keys:
                self.vault.write('cache-index',keys+[name])

    def _cache_get(self,key,default=None):
        name="cache:"+self._scope()+":"+key
        if name in self._memory_cache:
            return self._memory_cache[name]
        return self.vault.read(name,default) if self.vault else default

    def _run_network(self, fn, attempts=3):
        last = None
        for i in range(max(1, attempts)):
            try:
                result = fn()
                self.online = True
                self.last_network_error = None
                return result
            except Exception as ex:
                last = ex
                self.last_network_error = type(ex).__name__
                if not isinstance(ex, (TransportError, ConnectionError, TimeoutError)):
                    raise
                self.online = False
                if i < attempts - 1:
                    time.sleep(0.45 * (2 ** i))
        raise last

    def clear_local_cache(self):
        self._memory_cache.clear()
        if self.vault:
            self.vault.clear_keys(self.vault.read('cache-index',[]))
            self.vault.remove('cache-index')
        """Remove somente cache financeiro local; não apaga dados da nuvem."""
        try:
            CACHE_PATH.unlink(missing_ok=True)
        except Exception:
            pass

    def configured(self):
        cfg = load_config()
        return bool(cfg.get("url") and cfg.get("anon_key"))

    def connect(self):
        cfg = load_config()
        if not cfg.get("url") or not cfg.get("anon_key"):
            raise RuntimeError("Supabase ainda não foi configurado.")
        self.client = create_client(cfg["url"], cfg["anon_key"])
        if self.vault and self.vault.read(SESSION_PATH.name):
            try:
                saved = self.vault.read(SESSION_PATH.name)
                access = saved.get("access_token")
                refresh = saved.get("refresh_token")
                if access and refresh:
                    restored = self.client.auth.set_session(access, refresh)
                    if restored.session:
                        self._secure_write_json(SESSION_PATH, {"access_token":restored.session.access_token,"refresh_token":restored.session.refresh_token})
            except Exception:
                # Sessão cifrada inválida/corrompida: remova do cofre, não um
                # arquivo plaintext que já não existe.
                self.vault.remove(SESSION_PATH.name)
        self.client.auth.on_auth_state_change(self._auth_changed)
        return self.client

    def _auth_changed(self,event,session):
        if not self.vault:
            return
        with self._auth_lock:
            if session:
                self._secure_write_json(SESSION_PATH,{"access_token":session.access_token,"refresh_token":session.refresh_token})
            else:
                self.vault.remove(SESSION_PATH.name)

    def sign_up(self, email, password, full_name):
        if not self.client:
            self.connect()
        result = self.client.auth.sign_up({
            "email": email.strip(),
            "password": password,
            "options": {"data": {"full_name": full_name.strip()}},
        })
        if result.session:
            self._secure_write_json(SESSION_PATH, {
                "access_token": result.session.access_token,
                "refresh_token": result.session.refresh_token,
            })
        return result

    def sign_in(self, email, password):
        if not self.client:
            self.connect()

        result = self.client.auth.sign_in_with_password({
            "email": email.strip(),
            "password": password,
        })

        self.user = result.user
        if result.session:
            self._secure_write_json(SESSION_PATH, {
                "access_token": result.session.access_token,
                "refresh_token": result.session.refresh_token,
            })

        if self.user:
            self.load_context()

        return result

    def sign_out(self):
        if self.client:
            try:
                self.client.auth.sign_out()
            except Exception:
                pass
        # Sessão e cache financeiro local são dados sensíveis. Em dispositivo
        # compartilhado eles não devem permanecer depois de sair da conta.
        for path in (SESSION_PATH, CACHE_PATH):
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
        if self.vault:
            self.vault.clear()
        self._memory_cache.clear()
        self.client = None
        self.user = self.profile = self.household = self.member = None

    def current_user(self):
        if not self.client:
            return None

        result = self.client.auth.get_user()
        self.user = result.user
        return self.user

    def load_context(self):
        if not self.user:
            return
        uid = str(self.user.id)
        profile_rows = (
            self.client.table("profiles").select("*").eq("id", uid).limit(1).execute().data
        )
        self.profile = profile_rows[0] if profile_rows else None

        memberships = (
            self.client.table("household_members")
            .select("*, households(*)")
            .eq("user_id", uid)
            .eq("status", "active")
            .limit(1)
            .execute()
            .data
        )
        if memberships:
            self.member = memberships[0]
            self.household = memberships[0].get("households")
        else:
            self.member = self.household = None

    def create_workspace(
        self,
        mode: str,
        household_name: str,
        display_name: str,
        member_names=None,
    ):
        uid = str(self.user.id)
        db_mode = "individual" if mode == "Individual" else "family"
        code = uuid.uuid4().hex[:16].upper()

        household = (
            self.client.table("households")
            .insert({
                "name": household_name.strip() or display_name.strip() or "Minha conta",
                "mode": db_mode,
                "owner_id": uid,
                "invite_code": code,
            })
            .execute()
            .data[0]
        )

        _owner_row = (
            self.client.table("household_members")
            .insert({
                "household_id": household["id"],
                "user_id": uid,
                "display_name": display_name.strip() or "Usuário",
                "role": "owner",
                "status": "active",
            })
            .execute()
            .data[0]
        )

        # Cria espaços financeiros para os outros integrantes da família.
        if db_mode == "family":
            clean_names = []
            for name in member_names or []:
                n = (name or "").strip()
                if n and n.lower() != (display_name or "").strip().lower():
                    if n.lower() not in [x.lower() for x in clean_names]:
                        clean_names.append(n)

            for name in clean_names[:6]:
                self.client.table("household_members").insert({
                    "household_id": household["id"],
                    "user_id": None,
                    "display_name": name,
                    "role": "member",
                    "status": "active",
                }).execute()

        self.load_context()
        return household

    def join_family(self, invite_code: str, display_name: str):
        if not self.client:
            self.connect()

        result = self.client.rpc(
            "join_household_by_code",
            {
                "p_code": invite_code.strip().upper(),
                "p_display_name": display_name.strip(),
            },
        ).execute()

        self.load_context()
        return result

    def list_members(self):
        if not self.household:
            return []
        return sorted((r for r in self.fetch_all("household_members") if r.get("status") == "active"), key=lambda r: r.get("created_at") or "")

    def _hid(self):
        if not self.household:
            raise RuntimeError("Nenhuma conta financeira selecionada.")
        return self.household["id"]

    def add_income(self, member_id, amount, month, note, received_at=None):
        if float(amount)<=0 or not received_at:
            raise ValueError("Informe valor positivo e data real de recebimento")
        return self.client.table("income").insert({
            "household_id": self._hid(),
            "member_id": member_id,
            "amount": float(amount),
            "month": day(received_at).strftime("%m/%Y"),
                "received_at": day(received_at).isoformat(),
                "receipt_status": "received",
            "note": note.strip(),
            "created_by": str(self.user.id),
        }).execute()

    def update_income(self, row_id, member_id, amount, month, note, received_at=None):
        if float(amount)<=0 or not received_at:
            raise ValueError("Informe valor positivo e data real de recebimento")
        return (
            self.client.table("income")
            .update({
                "member_id": member_id,
                "amount": float(amount),
                "month": day(received_at).strftime("%m/%Y"),
                "received_at": day(received_at).isoformat(),
                "receipt_status": "received",
                "note": (note or "").strip(),
            })
            .eq("id", row_id)
            .eq("household_id", self._hid())
            .execute()
        )

    def update_expense(self,row_id,payer_member_id,kind,category,description,amount,expense_date,month,automatic_debit=False,shares=None):
        payload=dict(id=row_id,household_id=self._hid(),payer_member_id=payer_member_id,kind=kind,category=category,
            description=description.strip(),amount=float(amount),expense_date=expense_date,month=month,automatic_debit=automatic_debit,
            shares=[dict(member_id=m,amount=float(v)) for m,v in shares or []])
        return self.client.rpc('save_expense_batch',{'p_rows':[payload],'p_replace':True}).execute()

    def list_income(self, month):
        return sorted((r for r in self.all_income() if r.get("month") == month), key=lambda r: r.get("created_at") or "", reverse=True)
    def delete_income(self, row_id):
        return self.client.table("income").delete().eq("id", row_id).eq("household_id", self._hid()).execute()

    def add_expense(
        self, payer_member_id, kind, category, description, amount, expense_date,
        month, installments_total=1, installment_number=1, installment_group="",
        automatic_debit=False, shares=None
    ):
        """Cria despesa + rateios na mesma transação SQL.

        O caminho antigo fazia INSERT da despesa e depois dos rateios, podendo
        deixar registro parcial em falha de rede. Toda inclusão passa pela RPC
        idempotente a partir desta versão.
        """
        value=float(amount)
        share_rows=list(shares or [(payer_member_id,value)])
        row_id=str(uuid.uuid4())
        payload={
            "id":row_id,
            "household_id":self._hid(),
            "payer_member_id":payer_member_id,
            "kind":kind,
            "category":category,
            "description":description.strip(),
            "amount":value,
            "expense_date":expense_date,
            "month":month,
            "installments_total":int(installments_total),
            "installment_number":int(installment_number),
            "installment_group":installment_group or "",
            "automatic_debit":bool(automatic_debit),
            "shares":[{"member_id":m,"amount":float(v)} for m,v in share_rows],
        }
        self.client.rpc('save_expense_batch',{'p_rows':[payload],'p_replace':False}).execute()
        return payload

    def list_expenses(self, month):
        return [r for r in self.all_expenses_full() if r.get("month") == month]
    def delete_expense(self, row_id):
        return self.client.table("expenses").delete().eq("id", row_id).eq("household_id", self._hid()).execute()

    def add_acquisition(self, member_id, item, priority, estimated, saved, note):
        return self.client.table("acquisitions").insert({
            "household_id": self._hid(),
            "member_id": member_id,
            "item": item.strip(),
            "priority": priority,
            "estimated": float(estimated),
            "saved": float(saved),
            "note": note.strip(),
            "status": "active",
            "created_by": str(self.user.id),
        }).execute()

    def update_acquisition(self, row_id, **values):
        return self.client.table("acquisitions").update(values).eq("id", row_id).eq("household_id", self._hid()).execute()

    def finish_acquisition(self, row_id):
        return self.client.table("acquisitions").update({
            "status": "completed",
            "completed_at": datetime.now().date().isoformat(),
        }).eq("id", row_id).eq("household_id", self._hid()).execute()

    def delete_acquisition(self, row_id):
        return self.client.table("acquisitions").delete().eq("id", row_id).eq("household_id", self._hid()).execute()

    def list_acquisitions(self, active_only=True):
        return [r for r in self.all_acquisitions() if not active_only or r.get("status") == "active"]
    def all_income(self, limit=None):
        return self.fetch_all("income", "*, household_members(display_name)")

    def all_expenses_full(self, limit=None):
        return self.fetch_all("expenses", "*, household_members!expenses_payer_member_id_fkey(display_name), expense_shares(*, household_members(display_name))")

    def all_acquisitions(self, limit=None):
        return self.fetch_all("acquisitions", "*, household_members(display_name)")

    def all_expenses(self, limit=None):
        return self.fetch_all("expenses", "*, household_members!expenses_payer_member_id_fkey(display_name)")

    def list_goals(self):
        return sorted(self.fetch_all("financial_goals"), key=lambda r: r.get("target_date") or "9999")

    def add_goal(self, name, target_amount, saved_amount, target_date, strategy,member_id=None,acquisition_id=None):
        return self.client.table("financial_goals").insert({
            "household_id": self._hid(),
            "name": name.strip(),
            "member_id":member_id,"acquisition_id":acquisition_id,
            "target_amount": float(target_amount),
            "saved_amount": float(saved_amount),
            "target_date": target_date,
            "strategy": strategy,
            "status": "active",
            "created_by": str(self.user.id),
        }).execute()

    def update_goal(self, row_id, expected_version=None, **values):
        if expected_version is None:
            raise ValueError("Versão da meta obrigatória; atualize a tela antes de editar")
        allowed={"name","target_amount","target_date","strategy","member_id","status"}
        unexpected=set(values)-allowed
        if unexpected:
            raise ValueError("Campos de meta não editáveis diretamente: "+", ".join(sorted(unexpected)))
        return self.client.rpc('update_goal_safe',{
            'p_goal':row_id,
            'p_expected_version':int(expected_version),
            'p_name':values.get('name') or '',
            'p_target':float(values.get('target_amount') or 0),
            'p_target_date':values.get('target_date'),
            'p_strategy':values.get('strategy') or 'Equilibrada',
            'p_member':values.get('member_id'),
            'p_status':values.get('status') or 'active',
        }).execute()

    def delete_goal(self, row_id):
        return self.client.table("financial_goals").delete().eq("id", row_id).eq("household_id", self._hid()).execute()

    # ---------- WALLET ----------
    def list_wallets(self):
        return (
            self.client.table("wallet_accounts").select("*, household_members(display_name)")
            .eq("household_id", self._hid())
            .order("created_at", desc=True)
            .execute().data
        )

    def add_wallet(self, member_id, name, wallet_type, limit_amount, closing_day, due_day):
        return self.client.table("wallet_accounts").insert({
            "household_id": self._hid(),
            "member_id": member_id,
            "name": name.strip(),
            "wallet_type": wallet_type,
            "limit_amount": float(limit_amount or 0),
            "closing_day": int(closing_day or 0),
            "due_day": int(due_day or 0),
            "created_by": str(self.user.id),
        }).execute()

    def delete_wallet(self, row_id):
        return self.client.table("wallet_accounts").delete().eq("id", row_id).eq("household_id", self._hid()).execute()

    # ---------- SEMESTER SUMMARIES ----------
    def list_semester_summaries(self):
        return (
            self.client.table("semester_summaries").select("*")
            .eq("household_id", self._hid())
            .order("period_start", desc=True)
            .execute().data
        )

    def save_semester_summary(self, period_start, period_end, income, expense, balance, categories):
        existing = (
            self.client.table("semester_summaries").select("id")
            .eq("household_id", self._hid()).eq("period_start", period_start)
            .limit(1).execute().data
        )
        payload = {
            "household_id": self._hid(), "period_start": period_start, "period_end": period_end,
            "total_income": float(income), "total_expense": float(expense), "balance": float(balance),
            "categories": categories, "created_by": str(self.user.id),
        }
        if existing:
            return self.client.table("semester_summaries").update(payload).eq("id", existing[0]["id"]).execute()
        return self.client.table("semester_summaries").insert(payload).execute()

    def delete_months_data(self, months):
        """Bloqueado: apagar histórico quebra saldo contínuo e trilha de auditoria.

        A versão pública só poderá oferecer expurgo após backup validado,
        política de retenção e fluxo administrativo explícito.
        """
        raise RuntimeError("Exclusão destrutiva do histórico está desativada por segurança")

    def clear_current_financial_data(self):
        """Bloqueado até existir importação transacional com rollback validado."""
        raise RuntimeError("Limpeza destrutiva de dados está desativada por segurança")

    def replace_with_legacy_sqlite(self, path):
        """Bloqueado: não substitui dados de nuvem sem backup/rollback atômico."""
        raise RuntimeError("Importação destrutiva legada está desativada nesta versão")

    def migrate_legacy_sqlite(self, path):
        import sqlite3

        old = sqlite3.connect(path)
        old.row_factory = sqlite3.Row
        c = old.cursor()

        members = self.list_members()
        by_name = {m["display_name"].strip().lower(): m for m in members}

        # Compatibility names for legacy Mafra/Karol database.
        default_member = members[0] if members else None
        mafra = by_name.get("mafra") or default_member
        karol = by_name.get("karol") or default_member

        counts = {"income": 0, "expenses": 0, "acquisitions": 0}

        tables = {r[0] for r in c.execute("select name from sqlite_master where type='table'")}

        if "rendas" in tables:
            for r in c.execute("select * from rendas"):
                member = mafra if str(r["pessoa"]).lower() == "mafra" else karol
                if member:
                    self.add_income(member["id"], r["valor"], r["mes"], r["observacao"] or "")
                    counts["income"] += 1

        if "income" in tables:
            for r in c.execute("select * from income"):
                member = mafra if str(r["person"]).lower() == "mafra" else karol
                if member:
                    self.add_income(member["id"], r["amount"], r["month"], r["note"] or "")
                    counts["income"] += 1

        source_expenses = "despesas" if "despesas" in tables else ("expenses" if "expenses" in tables else None)
        if source_expenses:
            for r in c.execute(f"select * from {source_expenses}"):
                keys = set(r.keys())
                if source_expenses == "despesas":
                    person = r["pessoa"]
                    kind = r["tipo"]
                    category = r["categoria"]
                    desc = r["descricao"]
                    amount = r["valor"]
                    date_text = r["data"]
                    month = r["mes"] if "mes" in keys and r["mes"] else date_text[3:]
                    total = r["parcelas_total"] if "parcelas_total" in keys else 1
                    num = r["parcela_numero"] if "parcela_numero" in keys else 1
                    group = r["grupo_parcelamento"] if "grupo_parcelamento" in keys else ""
                    auto = r["debito_automatico"] if "debito_automatico" in keys else 0
                    shares = []
                    if str(person).lower() == "casal":
                        if mafra and "valor_mafra" in keys and r["valor_mafra"]:
                            shares.append((mafra["id"], r["valor_mafra"]))
                        if karol and "valor_karol" in keys and r["valor_karol"]:
                            shares.append((karol["id"], r["valor_karol"]))
                        payer = mafra or karol
                    else:
                        payer = mafra if str(person).lower() == "mafra" else karol
                        if payer:
                            shares = [(payer["id"], amount)]
                else:
                    person = r["person"]
                    kind = r["kind"]
                    category = r["category"]
                    desc = r["description"]
                    amount = r["amount"]
                    date_text = r["expense_date"]
                    month = r["month"]
                    total = r["installments_total"]
                    num = r["installment_number"]
                    group = r["installment_group"]
                    auto = r["automatic_debit"]
                    payer = mafra if str(person).lower() == "mafra" else karol
                    shares = [(payer["id"], amount)] if payer else []

                if payer:
                    self.add_expense(
                        payer["id"], kind, category, desc, amount, date_text, month,
                        total, num, group, bool(auto), shares
                    )
                    counts["expenses"] += 1

        source_acq = "aquisicoes" if "aquisicoes" in tables else ("acquisitions" if "acquisitions" in tables else None)
        if source_acq:
            for r in c.execute(f"select * from {source_acq}"):
                keys = set(r.keys())
                if source_acq == "aquisicoes":
                    person = r["pessoa"]
                    item = r["item"]
                    priority = r["prioridade"]
                    estimated = r["valor_estimado"]
                    saved = r["valor_guardado"]
                    note = r["observacao"] or ""
                    completed = bool(r["concluida"]) if "concluida" in keys else False
                else:
                    person = r["person"]
                    item = r["item"]
                    priority = r["priority"]
                    estimated = r["estimated"]
                    saved = r["saved"]
                    note = r["note"] or ""
                    completed = str(r["status"]).lower() not in ("ativa", "active")
                member = mafra if str(person).lower() == "mafra" else karol
                if member:
                    result = self.add_acquisition(member["id"], item, priority, estimated, saved, note)
                    if completed and result.data:
                        self.finish_acquisition(result.data[0]["id"])
                    counts["acquisitions"] += 1

        old.close()
        return counts

# NOTE: Mercado methods are attached to Cloud below to keep compatibility with existing installs.
def _list_market_trips(self, limit=50):
    return sorted(self.fetch_all('market_trips'),key=lambda r:r.get('created_at') or '',reverse=True)[:limit]
def _add_market_trip(self, market_name, budget=0):
    return (self.client.table("market_trips").insert({"household_id":self._hid(),"market_name":market_name.strip(),"budget":float(budget or 0),"shopping_date":datetime.now().date().isoformat(),"status":"open","created_by":str(self.user.id)}).execute())
def _list_market_items(self, trip_id):
    return [r for r in self.fetch_all('market_items') if str(r.get('trip_id'))==str(trip_id)]
def _add_market_item(self, trip_id, product_name, quantity, unit_price, category):
    return self.client.table("market_items").insert({"trip_id":trip_id,"household_id":self._hid(),"product_name":product_name.strip(),"quantity":float(quantity),"unit_price":float(unit_price),"category":category,"created_by":str(self.user.id)}).execute()
def _finish_market_trip(self, trip_id, cart_total, receipt_total, cashback_amount=0):
    return self.client.rpc('confirm_market_receipt',{'p_trip':trip_id,'p_expected':float(cart_total),'p_receipt':float(receipt_total),'p_cashback':float(cashback_amount or 0)}).execute()
Cloud.list_market_trips=_list_market_trips
Cloud.add_market_trip=_add_market_trip
Cloud.list_market_items=_list_market_items
Cloud.add_market_item=_add_market_item
Cloud.finish_market_trip=_finish_market_trip

def _update_market_trip(self, trip_id, **values):
    clean={}
    if "market_name" in values: clean["market_name"]=str(values["market_name"]).strip()
    if "budget" in values: clean["budget"]=float(values["budget"] or 0)
    return self.client.table("market_trips").update(clean).eq("id",trip_id).eq("household_id",self._hid()).execute()

def _delete_market_trip(self, trip_id):
    # Foreign-key cascade makes removal atomic in the supported schema.
    return self.client.table("market_trips").delete().eq("id",trip_id).eq("household_id",self._hid()).execute()

def _update_market_item(self, item_id, **values):
    clean={}
    if "product_name" in values: clean["product_name"]=str(values["product_name"]).strip()
    if "quantity" in values: clean["quantity"]=float(values["quantity"])
    if "unit_price" in values: clean["unit_price"]=float(values["unit_price"])
    if "category" in values: clean["category"]=values["category"]
    return self.client.table("market_items").update(clean).eq("id",item_id).eq("household_id",self._hid()).execute()

def _delete_market_item(self, item_id):
    return self.client.table("market_items").delete().eq("id",item_id).eq("household_id",self._hid()).execute()

Cloud.update_market_trip=_update_market_trip
Cloud.delete_market_trip=_delete_market_trip
Cloud.update_market_item=_update_market_item
Cloud.delete_market_item=_delete_market_item


def _fetch_all(self,table,select="*"):
    key=table+":"+select
    try:
        rows=[]
        offset=0
        while True:
            page=self._run_network(lambda:self.client.table(table).select(select).eq("household_id",self._hid()).order("id").range(offset,offset+499).execute().data)
            rows.extend(page or [])
            if len(page or [])<500:break
            offset+=500
        self._cache_set(key,rows)
        return rows
    except (TransportError, ConnectionError, TimeoutError):
        cached=self._cache_get(key)
        if cached is None:raise RuntimeError("Dados indisponíveis e sem cópia offline; tente sincronizar") from None
        return cached

def _payment(self,row_id,status,paid_at=None):
    if status not in ("paid","scheduled","cancelled"):raise ValueError("Status inválido")
    paid=day(paid_at).isoformat() if status=="paid" else None
    if paid and day(paid)>datetime.now().date():raise ValueError("Pagamento confirmado não pode estar no futuro")
    return self.client.table("expenses").update({"payment_status":status,"paid_at":paid,"automatic_debit":False}).eq("id",row_id).eq("household_id",self._hid()).execute()

def _journey_rows(self,member_id=None):
    mid=str(member_id or (self.member or {}).get('id') or '')
    rows=self.fetch_all("nex_journeys")
    return [r for r in rows if str(r.get('member_id') or '')==mid]

def _journeys(self,member_id=None):
    return {r['title']:int(r.get('progress') or 0) for r in _journey_rows(self,member_id)}

def _save_journey(self,title,progress,member_id=None,status='active',reminder_enabled=None,reminder_days=None,reminder_at=None,metrics=None):
    mid=str(member_id or (self.member or {}).get('id') or '')
    if not mid:
        raise ValueError('Selecione um perfil da família antes de salvar a trilha')
    existing=next((r for r in _journey_rows(self,mid) if r.get('title')==title),{})
    payload={
        "household_id":self._hid(),
        "member_id":mid,
        "title":title,
        "progress":max(0,min(int(progress),10)),
        "status":status or existing.get('status') or 'active',
        "created_by":str(self.user.id),
        "reminder_enabled":bool(existing.get('reminder_enabled')) if reminder_enabled is None else bool(reminder_enabled),
        "reminder_days": (existing.get('reminder_days') or []) if reminder_days is None else list(reminder_days),
        "reminder_at":existing.get('reminder_at') if reminder_at is None else reminder_at,
        "metrics":{**(existing.get('metrics') or {}),**(metrics or {})},
    }
    return self.client.table("nex_journeys").upsert(payload,on_conflict="household_id,member_id,title").execute()

def _set_consent(self,purpose,granted):
    allowed={'reminders','external_ai','affiliate_personalization'}
    if purpose not in allowed: raise ValueError('Finalidade de consentimento inválida')
    payload={"household_id":self._hid(),"user_id":str(self.user.id),"purpose":purpose,
        "granted":bool(granted),"policy_version":"2026-09-13.1","created_by":str(self.user.id)}
    return self.client.table('privacy_consents').upsert(payload,on_conflict='user_id,household_id,purpose').execute()

def _get_consents(self):
    rows=self.fetch_all('privacy_consents')
    return {r.get('purpose'):bool(r.get('granted')) for r in rows if str(r.get('user_id'))==str(self.user.id)}

def _offers(self):
    try:return self.client.table("affiliate_offers").select("*").eq("enabled",True).execute().data or []
    except Exception:return []

Cloud.fetch_all=_fetch_all
Cloud.set_payment=_payment
Cloud.list_journeys=_journey_rows
Cloud.load_journey_progress=_journeys
Cloud.save_journey_progress=_save_journey
Cloud.set_privacy_consent=_set_consent
Cloud.get_privacy_consents=_get_consents
Cloud.list_affiliate_offers=_offers
