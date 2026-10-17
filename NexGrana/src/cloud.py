import json
import os
import uuid
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

from supabase import create_client
from services.finance_engine import day
from services.sync import SyncQueue
from build_config import AUTH_REDIRECT_URL
import logging
from httpx import TransportError
logger = logging.getLogger(__name__)


class ReauthenticationRequired(RuntimeError):
    """A sessão não pode ser renovada e um novo login é necessário."""


class SessionUnavailable(RuntimeError):
    """A sessão existe, mas não pôde ser validada por falta de conectividade."""


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
AUTH_REDIRECT_ENV = "NEXGRANA_AUTH_REDIRECT_URL"
PASSWORD_MIN_LENGTH = max(6, int(os.getenv("NEXGRANA_PASSWORD_MIN_LENGTH", "6")))

# Public client configuration. This is intentionally the publishable key,
# never a service_role/secret key.
DEFAULT_SUPABASE_URL = "https://idiyziffdzxcqmshzsws.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_asMuC_w3q9fvR1rpEAZ1zQ_jEekiUPx"
DEFAULT_TABLE_SELECTS = {
    "income": "*, household_members(display_name)",
    "expenses": "*, household_members!expenses_payer_member_id_fkey(display_name), expense_shares(*, household_members(display_name))",
    "acquisitions": "*, household_members(display_name)",
    "financial_goals": "*",
    "market_items": "*",
    "market_trips": "*",
    "monthly_closures": "*",
}


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
        self.month_closures_error = None
        self._auth_lock = threading.RLock()
        self.session_state = "unauthenticated"
        self.session_generation = 0

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

    def _sync_queue(self):
        if not self.vault:
            return None
        return SyncQueue(self.vault,self._scope())

    def _cache_upsert(self,table,row):
        """Aplica a visão otimista em todas as cópias da tabela deste escopo."""
        if not self.vault:
            return
        prefix="cache:"+self._scope()+":"+table+":"
        names=[name for name in self.vault.read('cache-index',[]) if str(name).startswith(prefix)]
        if not names:
            key=table+":"+DEFAULT_TABLE_SELECTS.get(table,"*")
            self._cache_set(key,[dict(row)])
            return
        for name in names:
            rows=list(self._memory_cache.get(name,self.vault.read(name,[])) or [])
            rows=[item for item in rows if str(item.get('id'))!=str(row.get('id'))]
            rows.append(dict(row))
            self._memory_cache[name]=rows
            self.vault.write(name,rows)

    def _cache_delete(self,table,row_id):
        if not self.vault:
            return
        prefix="cache:"+self._scope()+":"+table+":"
        for name in self.vault.read('cache-index',[]):
            if not str(name).startswith(prefix):
                continue
            rows=list(self._memory_cache.get(name,self.vault.read(name,[])) or [])
            rows=[item for item in rows if str(item.get('id'))!=str(row_id)]
            self._memory_cache[name]=rows
            self.vault.write(name,rows)

    def _cache_find(self,table,row_id):
        if not self.vault:
            return None
        prefix="cache:"+self._scope()+":"+table+":"
        for name in self.vault.read('cache-index',[]):
            if not str(name).startswith(prefix):
                continue
            rows=self._memory_cache.get(name,self.vault.read(name,[])) or []
            found=next((item for item in rows if str(item.get('id'))==str(row_id)),None)
            if found:return dict(found)
        return None

    def _enqueue_upsert(self,table,row,server_payload=None,operation_id=None,transport="table"):
        queue=self._sync_queue()
        if queue is None:
            raise RuntimeError("Armazenamento protegido indisponível para salvar offline")
        op_id=str(operation_id or uuid.uuid4())
        local={**row,"_sync_state":"pending","_operation_id":op_id}
        queue.enqueue(table,str(row['id']),int(row.get('version') or 0),{
            "operation":"upsert","table":table,"transport":transport,
            "server":server_payload or row,"local":local,"before":self._cache_find(table,row['id']),
        },op_id)
        # A fila é gravada primeiro: uma queda entre as duas escritas não perde a operação.
        self._cache_upsert(table,local)
        return local

    def _enqueue_update(self,table,row_id,values,server_payload=None,operation_id=None,transport="table"):
        queue=self._sync_queue()
        if queue is None:
            raise RuntimeError("Armazenamento protegido indisponível para salvar offline")
        before=self._cache_find(table,row_id) or {"id":row_id,"household_id":self._hid()}
        op_id=str(operation_id or uuid.uuid4())
        local={**before,**values,"id":row_id,"household_id":self._hid(),"_sync_state":"pending","_operation_id":op_id}
        queue.enqueue(table,str(row_id),int(before.get('version') or 0),{
            "operation":"update","table":table,"transport":transport,
            "server":server_payload or values,"local":local,"before":before,
        },op_id)
        self._cache_upsert(table,local)
        return local

    def _enqueue_delete(self,table,row_id,operation_id=None):
        queue=self._sync_queue()
        if queue is None:
            raise RuntimeError("Armazenamento protegido indisponível para excluir offline")
        before=self._cache_find(table,row_id) or {"id":row_id,"household_id":self._hid()}
        op_id=str(operation_id or uuid.uuid4())
        queue.enqueue(table,str(row_id),int(before.get('version') or 0),{
            "operation":"delete","table":table,"before":before,
            "local":{"id":row_id,"household_id":self._hid(),"_operation_id":op_id},
        },op_id)
        self._cache_delete(table,row_id)
        return {"id":row_id,"_sync_state":"pending_delete","_operation_id":op_id}

    def _send_mutation(self,mutation):
        payload=mutation.get('payload') or {}
        table=payload.get('table')
        server=payload.get('server') or {}
        operation=payload.get('operation') or 'upsert'
        transport=payload.get('transport') or 'table'
        if transport in {'expense_rpc','expense_rpc_replace'}:
            self.client.rpc('save_expense_batch',{'p_rows':[server],'p_replace':transport.endswith('replace')}).execute()
        elif transport=='market_receipt_rpc':
            self.client.rpc('confirm_market_receipt',server).execute()
        elif transport=='market_finalize_rpc':
            self.client.rpc('finalize_market_expense_safe',server).execute()
            # A retry may meet an expense subsequently edited in Despesas.
            # Read authoritative fields before marking the cached ledger synced.
            confirmed=self.client.table('expenses').select(DEFAULT_TABLE_SELECTS['expenses']).eq('id',server['p_expense']).eq('household_id',self._hid()).single().execute().data
            if not isinstance(confirmed,dict) or str(confirmed.get('id'))!=str(server['p_expense']):
                raise RuntimeError('O servidor não confirmou a despesa desta compra')
            payload['local'].update(confirmed)
        elif transport=='monthly_batch_rpc':
            self.client.rpc('save_month_closures_safe',server).execute()
        elif transport in {'goal_rpc','market_trip_rpc','market_action_rpc'}:
            try:
                self.client.rpc({'goal_rpc':'update_goal_safe','market_trip_rpc':'update_market_trip_safe','market_action_rpc':'mutate_market_safe'}[transport],server).execute()
            except Exception as exc:
                message=str(exc).casefold()
                if 'version' in message or 'conflit' in message:
                    return {"conflict":True}
                raise
        elif operation=='update':
            response=self.client.table(table).update(server).eq('id',mutation.get('row_id')).eq('household_id',self._hid()).select('id').execute()
            if not isinstance(getattr(response,'data',None),list) or not any(
                str(row.get('id'))==str(mutation.get('row_id')) for row in response.data if isinstance(row,dict)
            ):
                return {'conflict':True}
        elif operation=='delete':
            response=self.client.table(table).delete().eq('id',mutation.get('row_id')).eq('household_id',self._hid()).select('id').execute()
            if not isinstance(getattr(response,'data',None),list) or not any(
                str(row.get('id'))==str(mutation.get('row_id')) for row in response.data if isinstance(row,dict)
            ):
                return {'conflict':True}
        else:
            self.client.table(table).upsert(server,on_conflict='id').execute()
        return {"ok":True}

    def flush_pending(self,limit=30):
        queue=self._sync_queue()
        if queue is None or not self.client:
            return []
        results=[]
        for _ in range(max(1,int(limit))):
            row=queue.apply_one(self._send_mutation)
            if not row:
                break
            results.append(row)
            payload=row.get('payload') or {}
            operation=payload.get('operation') or 'upsert'
            local=dict(payload.get('local') or {})
            if operation=='delete' and row.get('state')=='synced':
                self._cache_delete(payload.get('table'),row.get('row_id'))
                self.online=True
            elif local and row.get('state')=='synced':
                local['_sync_state']='synced'
                self._cache_upsert(payload.get('table'),local)
                self.online=True
            elif row.get('state') in {'rejected','conflict'} and (payload.get('table')=='monthly_closures' or payload.get('transport')=='market_finalize_rpc') and operation=='upsert':
                before=payload.get('before')
                if before:self._cache_upsert(payload['table'],before)
                else:self._cache_delete(payload['table'],row.get('row_id'))
            elif row.get('state') in {'rejected','conflict'} and operation in {'update','delete'}:
                before=dict(payload.get('before') or {})
                if before:
                    before['_sync_state']=row.get('state')+'_'+operation
                    self._cache_upsert(payload.get('table'),before)
            elif row.get('state')=='queued':
                self.online=False
            if payload.get('transport')=='market_finalize_rpc' and row.get('state')=='synced':
                posted=local.get('_market_trip_result')
                if posted:self._cache_upsert('market_trips',{**posted,'_sync_state':'synced'})
            if row.get('state')=='queued':
                break
        return results

    def _flush_operation(self,local):
        results=self.flush_pending()
        op_id=str(local.get('_operation_id') or '')
        result=next((row for row in results if str(row.get('id'))==op_id),None)
        if result and result.get('state')=='rejected':
            raise RuntimeError("O servidor recusou o registro. Revise os campos ou sua permissão.")
        if result and result.get('state')=='conflict':
            raise RuntimeError("O registro mudou em outro dispositivo. Atualize antes de tentar novamente.")
        if result and result.get('state')=='synced':
            return {**((result.get("payload") or {}).get("local") or local),"_sync_state":"synced"}
        return local

    def pending_sync_count(self):
        queue=self._sync_queue()
        return len(queue.unresolved()) if queue else 0

    def sync_summary(self):
        queue=self._sync_queue()
        rows=queue.unresolved() if queue else []
        return {
            "queued":sum(1 for row in rows if row.get("state")=="queued"),
            "conflict":sum(1 for row in rows if row.get("state")=="conflict"),
            "rejected":sum(1 for row in rows if row.get("state")=="rejected"),
            "total":len(rows),
        }

    def retry_rejected_sync(self):
        queue=self._sync_queue()
        if not queue:
            return []
        retried=[]
        for row in queue.unresolved():
            if row.get("state")=="rejected":
                retried.append(queue.retry(row["id"]))
        return retried

    def discard_sync_errors(self):
        """Descarta só mutações recusadas/conflitantes e restaura a visão remota anterior."""
        queue=self._sync_queue()
        if not queue:
            return []
        discarded=[]
        for row in queue.unresolved():
            if row.get("state") not in {"rejected","conflict"}:
                continue
            payload=row.get("payload") or {}
            operation=payload.get("operation") or "upsert"
            table=payload.get("table")
            before=dict(payload.get("before") or {})
            if operation in {"update","delete"} and before:
                before.pop("_sync_state",None)
                self._cache_upsert(table,before)
            else:
                self._cache_delete(table,row.get("row_id"))
            discarded.append(queue.cancel(row["id"]))
        return discarded

    @staticmethod
    def _error_fields(ex):
        payload = {}
        for item in getattr(ex, "args", ()):
            if isinstance(item, dict):
                payload.update(item)
        return {
            "code": str(getattr(ex, "code", None) or payload.get("code") or ""),
            "message": str(getattr(ex, "message", None) or payload.get("message") or ex),
            "status": getattr(ex, "status_code", None) or payload.get("status_code") or payload.get("status"),
        }

    @classmethod
    def _is_expired_auth_error(cls, ex):
        fields = cls._error_fields(ex)
        message = fields["message"].casefold()
        code = fields["code"].upper()
        try:
            status = int(fields["status"])
        except (TypeError, ValueError):
            status = 0
        mentions_token = any(word in message for word in ("jwt", "token", "session"))
        invalid_token = any(word in message for word in ("expired", "invalid", "claims", "malformed"))
        return (status == 401 and mentions_token) or (
            code in {"PGRST301", "PGRST303"} and mentions_token and invalid_token
        )

    def _saved_session(self):
        if not self.vault:
            return {}
        value = self.vault.read(SESSION_PATH.name, {})
        return value if isinstance(value, dict) else {}

    def gateway_access_token(self):
        """Token curto da sessão para autenticar o gateway próprio.

        A chave do provedor de IA nunca passa pelo cliente. O refresh token
        também nunca é exposto a esta fronteira.
        """
        if self.session_state not in {"authenticated", "offline_with_local_session"}:
            return None
        return str(self._saved_session().get("access_token") or "") or None

    def _persist_session(self, session):
        if not session:
            return
        access = getattr(session, "access_token", None)
        refresh = getattr(session, "refresh_token", None)
        if access and refresh:
            user = getattr(session, "user", None) or self.user
            self._secure_write_json(SESSION_PATH, {
                "access_token": access,
                "refresh_token": refresh,
                "user_id": str(getattr(user, "id", "") or ""),
                "email": str(getattr(user, "email", "") or ""),
            })

    def _persist_identity_context(self):
        """Guarda somente o contexto autorizado da sessão atual no cofre local."""
        if not (self.vault and self.user):
            return
        uid = str(self.user.id)
        self.vault.write("identity-context:" + uid, {
            "profile": self.profile,
            "household": self.household,
            "member": self.member,
        })

    def _restore_identity_context(self):
        """Restaura identidade/contexto apenas para o usuário da sessão cifrada."""
        saved = self._saved_session()
        uid = str(saved.get("user_id") or "")
        if not (self.vault and uid):
            return False
        context = self.vault.read("identity-context:" + uid, {})
        if not isinstance(context, dict) or not context.get("household"):
            return False
        self.user = SimpleNamespace(id=uid, email=str(saved.get("email") or ""))
        self.profile = context.get("profile")
        self.household = context.get("household")
        self.member = context.get("member")
        return True

    @staticmethod
    def auth_redirect_url():
        """Retorna callback explícito e seguro; nunca herda localhost no cliente."""
        value = str(os.getenv(AUTH_REDIRECT_ENV, "") or AUTH_REDIRECT_URL or "").strip()
        if not value:
            return None
        parsed = urlparse(value)
        host = (parsed.hostname or "").casefold()
        if parsed.scheme != "https" or not host or host in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError(
                f"{AUTH_REDIRECT_ENV} precisa ser uma URL HTTPS pública, sem localhost"
            )
        return value

    @staticmethod
    def password_requirements():
        return f"Use pelo menos {PASSWORD_MIN_LENGTH} caracteres. Evite reutilizar senhas de outros serviços."

    @staticmethod
    def password_min_length():
        return PASSWORD_MIN_LENGTH

    def _clear_session_only(self):
        if self.vault:
            self.vault.remove(SESSION_PATH.name)
        self.user = self.profile = self.household = self.member = None
        self.session_state = "reauthentication_required"
        self.session_generation += 1

    def _refresh_session(self, observed_generation=None):
        """Renova uma sessão uma única vez, coordenando requisições concorrentes."""
        with self._auth_lock:
            if observed_generation is not None and observed_generation != self.session_generation:
                if self.session_state == "authenticated":
                    return True
                if self.session_state == "reauthentication_required":
                    raise ReauthenticationRequired("Sua sessão expirou. Entre novamente para continuar.")
            if not self.client:
                raise ReauthenticationRequired("Sua sessão expirou. Entre novamente para continuar.")
            refresh_token = self._saved_session().get("refresh_token")
            if not refresh_token:
                self._clear_session_only()
                raise ReauthenticationRequired("Sua sessão expirou. Entre novamente para continuar.")
            self.session_state = "refreshing"
            try:
                response = self.client.auth.refresh_session(refresh_token)
                session = getattr(response, "session", None)
                if not session:
                    raise ValueError("refresh sem sessão")
                self._persist_session(session)
                self.user = getattr(response, "user", None) or getattr(session, "user", None) or self.user
                self.session_generation += 1
                self.session_state = "authenticated"
                self.online = True
                self.last_network_error = None
                return True
            except (TransportError, ConnectionError, TimeoutError) as ex:
                self.session_state = "offline_with_local_session"
                self.online = False
                self.last_network_error = type(ex).__name__
                raise SessionUnavailable("Sem conexão para renovar sua sessão. Tente novamente.") from None
            except ReauthenticationRequired:
                raise
            except Exception:
                self._clear_session_only()
                raise ReauthenticationRequired("Sua sessão expirou. Entre novamente para continuar.") from None

    def _run_network(self, fn, attempts=3, *, retry_auth=True):
        last = None
        transport_attempt = 0
        auth_retried = False
        observed_generation = self.session_generation
        while transport_attempt < max(1, attempts):
            try:
                result = fn()
                self.online = True
                self.last_network_error = None
                if self.user:
                    self.session_state = "authenticated"
                return result
            except Exception as ex:
                last = ex
                self.last_network_error = type(ex).__name__
                if retry_auth and not auth_retried and self._is_expired_auth_error(ex):
                    self._refresh_session(observed_generation)
                    auth_retried = True
                    continue
                if not isinstance(ex, (TransportError, ConnectionError, TimeoutError)):
                    raise
                self.online = False
                transport_attempt += 1
                if transport_attempt < attempts:
                    time.sleep(0.45 * (2 ** (transport_attempt - 1)))
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
        self.session_state = "restoring"
        if self.vault and self.vault.read(SESSION_PATH.name):
            try:
                saved = self._saved_session()
                access = saved.get("access_token")
                refresh = saved.get("refresh_token")
                if access and refresh:
                    restored = self.client.auth.set_session(access, refresh)
                    if restored.session:
                        self._persist_session(restored.session)
                        self.user = getattr(restored, "user", None) or getattr(restored.session, "user", None)
                        self.session_generation += 1
                        self.session_state = "authenticated"
            except (TransportError, ConnectionError, TimeoutError):
                # Rede indisponível não invalida credenciais persistidas.
                self.session_state = "offline_with_local_session"
                self.online = False
                self._restore_identity_context()
            except Exception:
                self._clear_session_only()
        self.client.auth.on_auth_state_change(self._auth_changed)
        if self.session_state == "restoring":
            self.session_state = "unauthenticated"
        return self.client

    def _auth_changed(self,event,session):
        with self._auth_lock:
            if session:
                if self.vault:
                    self._persist_session(session)
                self.user = getattr(session, "user", None) or self.user
                self.session_state = "authenticated"
                self.session_generation += 1
            else:
                if self.vault:
                    self.vault.remove(SESSION_PATH.name)
                event_name=str(event or "").casefold()
                if "signed_out" in event_name or "user_deleted" in event_name:
                    self.user = self.profile = self.household = self.member = None
                    self.session_state = "unauthenticated"
                    self.session_generation += 1

    def sign_up(self, email, password, full_name):
        if not self.client:
            self.connect()
        options = {"data": {"full_name": full_name.strip()}}
        redirect = self.auth_redirect_url()
        if redirect:
            options["email_redirect_to"] = redirect
        result = self.client.auth.sign_up({
            "email": email.strip(),
            "password": password,
            "options": options,
        })
        if result.session:
            self.user = getattr(result, "user", None) or getattr(result.session, "user", None)
            self._persist_session(result.session)
        return result

    def resend_signup_confirmation(self, email):
        if not self.client:
            self.connect()
        options = {}
        redirect = self.auth_redirect_url()
        if redirect:
            options["email_redirect_to"] = redirect
        return self._run_network(lambda: self.client.auth.resend({
            "type": "signup",
            "email": email.strip(),
            "options": options,
        }), attempts=1, retry_auth=False)

    def request_password_reset(self, email):
        if not self.client:
            self.connect()
        redirect = self.auth_redirect_url()
        def send():
            if redirect:
                return self.client.auth.reset_password_email(
                    email.strip(), {"redirect_to": redirect}
                )
            return self.client.auth.reset_password_email(email.strip())
        return self._run_network(send, attempts=1, retry_auth=False)

    def sign_in(self, email, password):
        if not self.client:
            self.connect()

        result = self.client.auth.sign_in_with_password({
            "email": email.strip(),
            "password": password,
        })

        self.user = result.user
        if result.session:
            self._persist_session(result.session)
            self.session_generation += 1
            self.session_state = "authenticated"

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
        self.session_state = "unauthenticated"
        self.session_generation += 1

    def current_user(self):
        if not self.client:
            return None

        if self.session_state == "offline_with_local_session" and self.user:
            return self.user

        result = self._run_network(lambda: self.client.auth.get_user(), attempts=1)
        self.user = result.user
        return self.user

    def load_context(self):
        if not self.user:
            return
        # A identidade já foi validada em uma sessão anterior e está cifrada no
        # dispositivo. Sem rede, não bloqueamos a abertura do app tentando
        # consultar novamente o mesmo contexto.
        if self.session_state == "offline_with_local_session" and self.household:
            return
        uid = str(self.user.id)
        profile_rows = self._run_network(
            lambda: self.client.table("profiles").select("*").eq("id", uid).limit(1).execute().data
        )
        self.profile = profile_rows[0] if profile_rows else None

        memberships = self._run_network(
            lambda: self.client.table("household_members")
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
        self._persist_identity_context()

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

        # The server enrolls only a new empty individual space owned by a QA
        # tester. An old personal workspace is never marked for deletion here.
        if db_mode == 'individual' and self.is_qa_tester():
            self.client.rpc('enroll_new_qa_workspace',{'p_household_id':household['id']}).execute()
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

    def is_qa_tester(self):
        if not self.user:
            return False
        rows=self._run_network(lambda:self.client.table("qa_testers").select("user_id")
            .eq("user_id",str(self.user.id)).eq("enabled",True).limit(1).execute().data,attempts=1)
        return bool(rows)

    def reset_qa_workspace(self, confirmation):
        if confirmation != "RESETAR_TESTE":
            raise ValueError("Confirmação de homologação inválida")
        current_household=self._hid()
        result=self._run_network(lambda:self.client.rpc("reset_qa_workspace",{
            "p_confirmation":confirmation,
            "p_household_id":current_household,
        }).execute(),attempts=1)
        self.clear_local_cache()
        self.profile = self.household = self.member = None
        if self.vault and self.user:
            self.vault.remove("identity-context:"+str(self.user.id))
        return result

    def enroll_owned_qa_workspace(self, confirmation):
        if confirmation != 'VINCULAR_TESTE':
            raise ValueError('Confirmação de ambiente de teste inválida')
        return self._run_network(lambda:self.client.rpc('enroll_owned_qa_workspace',{
            'p_household_id':self._hid(),'p_confirmation':confirmation,
        }).execute(),attempts=1)

    def list_members(self):
        if not self.household:
            return []
        if self.session_state == "offline_with_local_session" and self._cache_get("household_members:*") is None:
            rows=[self.member] if self.member else []
            return [row for row in rows if row]
        try:
            rows=self.fetch_all("household_members")
        except RuntimeError:
            # Primeiro uso offline pode ter identidade cifrada, mas ainda não a
            # lista completa. Mostra somente o perfil autorizado dessa sessão.
            rows=[self.member] if self.member else []
        return sorted((r for r in rows if r and r.get("status", "active") == "active"), key=lambda r: r.get("created_at") or "")

    def _hid(self):
        if not self.household:
            raise RuntimeError("Nenhuma conta financeira selecionada.")
        return self.household["id"]

    def add_income(self, member_id, amount, month, note, received_at=None, row_id=None, operation_id=None):
        if float(amount)<=0 or not received_at:
            raise ValueError("Informe valor positivo e data real de recebimento")
        payload={
            "id":str(row_id or uuid.uuid4()),
            "household_id": self._hid(),
            "member_id": member_id,
            "amount": float(amount),
            "month": day(received_at).strftime("%m/%Y"),
            "received_at": day(received_at).isoformat(),
            "receipt_status": "received",
            "note": note.strip(),
            "created_by": str(self.user.id),
        }
        return self._flush_operation(self._enqueue_upsert("income",payload,operation_id=operation_id))

    def update_income(self, row_id, member_id, amount, month, note, received_at=None):
        if float(amount)<=0 or not received_at:
            raise ValueError("Informe valor positivo e data real de recebimento")
        payload={
            "id":row_id,
            "household_id":self._hid(),
            "member_id":member_id,
            "amount":float(amount),
            "month":day(received_at).strftime("%m/%Y"),
            "received_at":day(received_at).isoformat(),
            "receipt_status":"received",
            "note":(note or "").strip(),
        }
        values={key:value for key,value in payload.items() if key not in {'id','household_id'}}
        return self._flush_operation(self._enqueue_update("income",row_id,values))

    def update_expense(self,row_id,payer_member_id,kind,category,description,amount,expense_date,month,automatic_debit=False,shares=None):
        payload=dict(id=row_id,household_id=self._hid(),payer_member_id=payer_member_id,kind=kind,category=category,
            description=description.strip(),amount=float(amount),expense_date=expense_date,month=month,automatic_debit=automatic_debit,
            shares=[dict(member_id=m,amount=float(v)) for m,v in shares or []])
        local={key:value for key,value in payload.items() if key!='shares'}
        local['expense_shares']=[dict(member_id=row['member_id'],amount=row['amount']) for row in payload['shares']]
        return self._flush_operation(self._enqueue_update(
            "expenses",row_id,local,server_payload=payload,transport="expense_rpc_replace"
        ))

    def list_income(self, month):
        return sorted((r for r in self.all_income() if r.get("month") == month), key=lambda r: r.get("created_at") or "", reverse=True)
    def delete_income(self, row_id):
        return self._flush_operation(self._enqueue_delete("income",row_id))

    def add_expense(
        self, payer_member_id, kind, category, description, amount, expense_date,
        month, installments_total=1, installment_number=1, installment_group="",
        automatic_debit=False, shares=None, row_id=None, operation_id=None
    ):
        """Cria despesa + rateios na mesma transação SQL.

        O caminho antigo fazia INSERT da despesa e depois dos rateios, podendo
        deixar registro parcial em falha de rede. Toda inclusão passa pela RPC
        idempotente a partir desta versão.
        """
        value=float(amount)
        share_rows=list(shares or [(payer_member_id,value)])
        row_id=str(row_id or uuid.uuid4())
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
        local={key:value for key,value in payload.items() if key!='shares'}
        local['expense_shares']=[dict(member_id=row['member_id'],amount=row['amount']) for row in payload['shares']]
        return self._flush_operation(self._enqueue_upsert(
            "expenses",local,server_payload=payload,operation_id=operation_id,transport="expense_rpc"
        ))

    def list_expenses(self, month):
        return [r for r in self.all_expenses_full() if r.get("month") == month]
    def delete_expense(self, row_id):
        return self._flush_operation(self._enqueue_delete("expenses",row_id))

    def list_month_closures(self):
        return self.fetch_all("monthly_closures", "*")

    def _month_closure_payload(self, month, member_id, opening_balance, closing_balance):
        if isinstance(month, str) and "/" in month:
            mm, yyyy = month.split("/", 1)
            start = day(f"01/{int(mm):02d}/{int(yyyy):04d}")
        else:
            start = day(month)
        month_start = start.replace(day=1).isoformat()
        scope = str(member_id or "family")
        row_id = str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"nexgrana-month-closure:{self._hid()}:{scope}:{month_start}",
        ))
        payload = {
            "id": row_id,
            "household_id": self._hid(),
            "member_id": str(member_id) if member_id else None,
            "month_start": month_start,
            "opening_balance": float(opening_balance),
            "closing_balance": float(closing_balance),
            "status": "closed",
            "closed_by": str(self.user.id),
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
        return payload

    def save_month_closure(self, month, member_id, opening_balance, closing_balance):
        return self.save_month_closures(month,[(member_id,opening_balance,closing_balance)])[0]

    def save_month_closures(self,month,scopes):
        payloads=[self._month_closure_payload(month,*scope) for scope in scopes]
        if not payloads:raise ValueError('Fechamento sem perfis')
        previous={row['id']:self._cache_find('monthly_closures',row['id']) for row in payloads}
        queued=[self._enqueue_upsert('monthly_closures',row,server_payload={'p_rows':payloads},transport='monthly_batch_rpc') for row in payloads]
        results=self.flush_pending(limit=max(30,len(queued)))
        ids={row['_operation_id'] for row in queued}
        if any(r.get('id') in ids and r.get('state') in {'rejected','conflict'} for r in results):
            for row in payloads:
                if previous[row['id']]:self._cache_upsert('monthly_closures',previous[row['id']])
                else:self._cache_delete('monthly_closures',row['id'])
            raise RuntimeError('Fechamento recusado. Atualize o ambiente de teste e revise as permissões antes de confirmar novamente.')
        states={r['id']:r for r in self.list_month_closures()}
        return [states.get(row['id'],row) for row in queued]

    def add_acquisition(self, member_id, item, priority, estimated, saved, note, row_id=None, operation_id=None):
        payload={
            "id":str(row_id or uuid.uuid4()),
            "household_id": self._hid(),
            "member_id": member_id,
            "item": item.strip(),
            "priority": priority,
            "estimated": float(estimated),
            "saved": float(saved),
            "note": note.strip(),
            "status": "active",
            "created_by": str(self.user.id),
        }
        return self._flush_operation(self._enqueue_upsert("acquisitions",payload,operation_id=operation_id))

    def update_acquisition(self, row_id, **values):
        return self._flush_operation(self._enqueue_update("acquisitions",row_id,values))

    def finish_acquisition(self, row_id):
        values={
            "status": "completed",
            "completed_at": datetime.now().date().isoformat(),
        }
        return self._flush_operation(self._enqueue_update("acquisitions",row_id,values))

    def delete_acquisition(self, row_id):
        return self._flush_operation(self._enqueue_delete("acquisitions",row_id))

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

    def add_goal(self, name, target_amount, saved_amount, target_date, strategy,member_id=None,acquisition_id=None,row_id=None,operation_id=None):
        payload={
            "id":str(row_id or uuid.uuid4()),
            "household_id": self._hid(),
            "name": name.strip(),
            "member_id":member_id,"acquisition_id":acquisition_id,
            "target_amount": float(target_amount),
            "saved_amount": float(saved_amount),
            "target_date": target_date,
            "strategy": strategy,
            "status": "active",
            "created_by": str(self.user.id),
        }
        return self._flush_operation(self._enqueue_upsert("financial_goals",payload,operation_id=operation_id))

    def update_goal(self, row_id, expected_version=None, **values):
        if expected_version is None:
            raise ValueError("Versão da meta obrigatória; atualize a tela antes de editar")
        allowed={"name","target_amount","target_date","strategy","member_id","status"}
        unexpected=set(values)-allowed
        if unexpected:
            raise ValueError("Campos de meta não editáveis diretamente: "+", ".join(sorted(unexpected)))
        server={
            'p_goal':row_id,
            'p_expected_version':int(expected_version),
            'p_name':values.get('name') or '',
            'p_target':float(values.get('target_amount') or 0),
            'p_target_date':values.get('target_date'),
            'p_strategy':values.get('strategy') or 'Equilibrada',
            'p_member':values.get('member_id'),
            'p_status':values.get('status') or 'active',
        }
        local={**values,"version":int(expected_version)+1}
        return self._flush_operation(self._enqueue_update(
            "financial_goals",row_id,local,server_payload=server,transport="goal_rpc"
        ))

    def delete_goal(self, row_id):
        return self._flush_operation(self._enqueue_delete("financial_goals",row_id))

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
                    if completed and result:
                        rid=result.get("id") if isinstance(result,dict) else None
                        if rid:self.finish_acquisition(rid)
                    counts["acquisitions"] += 1

        old.close()
        return counts

# NOTE: Mercado methods are attached to Cloud below to keep compatibility with existing installs.
def _list_market_trips(self, limit=50):
    return sorted((r for r in self.fetch_all('market_trips') if not r.get('deleted_at')),key=lambda r:r.get('created_at') or '',reverse=True)[:limit]
def _add_market_trip(self, market_name, budget=0):
    payload={"id":str(uuid.uuid4()),"household_id":self._hid(),"market_name":market_name.strip(),"budget":float(budget or 0),"shopping_date":datetime.now().date().isoformat(),"status":"open","created_by":str(self.user.id)}
    return self._flush_operation(self._enqueue_upsert("market_trips",payload))
def _list_market_items(self, trip_id):
    return [r for r in self.fetch_all('market_items') if str(r.get('trip_id'))==str(trip_id) and not r.get('deleted_at')]
def _add_market_item(self, trip_id, product_name, quantity, unit_price, category):
    payload={"id":str(uuid.uuid4()),"trip_id":trip_id,"household_id":self._hid(),"product_name":product_name.strip(),"quantity":float(quantity),"unit_price":float(unit_price),"category":category,"created_by":str(self.user.id)}
    return self._flush_operation(self._enqueue_upsert("market_items",payload))
def _finish_market_trip(self,trip_id,cart_total,receipt_total,cashback_amount=0):
    from services.finance_engine import amount
    receipt=amount(receipt_total);cashback=amount(cashback_amount)
    if receipt<0 or cashback<0 or cashback>receipt:raise ValueError('Confira os valores da nota.')
    server={'p_trip':str(trip_id),'p_expected':float(amount(cart_total)),'p_receipt':float(receipt),'p_cashback':float(cashback)}
    return self._flush_operation(self._enqueue_update('market_trips',trip_id,
       {'status':'closed','cart_total':server['p_expected'],'receipt_total':float(receipt),'cashback_amount':float(cashback)},
       server_payload=server,transport='market_receipt_rpc'))
Cloud.list_market_trips=_list_market_trips
Cloud.add_market_trip=_add_market_trip
Cloud.list_market_items=_list_market_items
Cloud.add_market_item=_add_market_item
Cloud.finish_market_trip=_finish_market_trip

def _finalize_market_expense(self,trip_id,cart_total,receipt_total,cashback_amount,member_id,expense_date):
    from services.finance_engine import amount
    from datetime import date
    trip=self._cache_find('market_trips',trip_id)
    if not trip:raise ValueError('Atualize a compra antes de finalizar.')
    if str(trip.get('created_by'))!=str(self.user.id):raise PermissionError('Apenas quem criou a compra pode lançá-la.')
    value=amount(receipt_total);cashback=amount(cashback_amount)
    if value<=0 or cashback<0 or cashback>value:raise ValueError('Confira total da nota e cashback.')
    due=date.fromisoformat(str(expense_date));month=due.strftime('%m/%Y')
    expense_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'nexgrana:market-expense:'+str(trip_id)))
    existing=self._cache_find('expenses',expense_id)
    request={'p_trip':str(trip_id),'p_expected':float(amount(cart_total)),'p_receipt':float(value),
             'p_cashback':float(cashback),'p_member':str(member_id),'p_date':due.isoformat(),'p_expense':expense_id}
    if existing:
        prior=existing.get('_market_request')
        if prior and prior!=request:raise ValueError('Esta compra já possui um lançamento. Revise em Despesas.')
        if prior:return existing
        self._run_network(lambda:self.client.rpc('finalize_market_expense_safe',request).execute(),attempts=1)
        return {**existing,'_sync_state':'synced'}
    # Queue is the recovery record. Never close the trip until the atomic RPC succeeds.
    local={'id':expense_id,'household_id':self._hid(),'payer_member_id':str(member_id),'kind':'Variável',
           'category':'Alimentação','description':'Compra em '+str(trip.get('market_name') or 'Mercado'),
           'amount':float(value),'expense_date':due.isoformat(),'month':month,'installments_total':1,
           'installment_number':1,'installment_group':'','automatic_debit':False,'payment_status':'scheduled',
           'created_by':str(self.user.id),'expense_shares':[{'member_id':str(member_id),'amount':float(value)}],
           '_market_request':request,'_market_trip_result':{**trip,'status':'closed','cart_total':float(amount(cart_total)),
              'receipt_total':float(value),'cashback_amount':float(cashback),'ledger_expense_id':expense_id}}
    return self._flush_operation(self._enqueue_upsert('expenses',local,server_payload=request,
                  operation_id=expense_id,transport='market_finalize_rpc'))

Cloud.finalize_market_expense=_finalize_market_expense


def _start_market_trip_from_list(self,list_id,market_name):
    name=str(market_name or '').strip()
    if not name or len(name)>100:raise ValueError('Informe o nome do mercado (até 100 caracteres)')
    # One server transaction creates a snapshot; retries return the same open
    # session. Never optimistically create a partial cart in the local queue.
    result=self._run_network(lambda:self.client.rpc('start_market_trip_from_list',{
        'p_list':str(list_id),'p_market':name}).execute(),attempts=1)
    trip_id=str(result.data or '')
    if not trip_id:raise RuntimeError('O servidor não confirmou a compra')
    self.refresh_table('market_trips')
    self.refresh_table('market_items')
    return next((row for row in self.list_market_trips() if str(row.get('id'))==trip_id),None) or {'id':trip_id}

Cloud.start_market_trip_from_list=_start_market_trip_from_list

def _update_market_trip(self, trip_id, **values):
    from services.finance_engine import amount
    before=self._cache_find('market_trips',trip_id)
    if before is None:raise RuntimeError('Atualize a compra antes de editar o limite.')
    name=str(values.get('market_name',before.get('market_name')) or '').strip()
    budget=amount(values.get('budget',before.get('budget') or 0))
    if not name or len(name)>120 or budget<0:raise ValueError('Informe mercado e limite não negativo.')
    operation=str(uuid.uuid4())
    server={'p_trip':str(trip_id),'p_name':name,'p_budget':float(budget),
        'p_expected_budget':float(before.get('budget') or 0),'p_operation':operation}
    result=self._flush_operation(self._enqueue_update('market_trips',trip_id,{'market_name':name,'budget':float(budget)},
        server_payload=server,operation_id=operation,transport='market_trip_rpc'))
    if self.vault:self.vault.write('market-undo:'+self._scope(),{'kind':'budget','row_id':trip_id,
        'before':{'market_name':before.get('market_name'),'budget':before.get('budget') or 0},
        'after':{'market_name':name,'budget':float(budget)}})
    return result

def _market_budget_history(self,trip_id):
    return [r for r in self.fetch_all('market_budget_events') if str(r.get('trip_id'))==str(trip_id)]

def _market_mutable_snapshot(kind,row):
    keys=('product_name','quantity','unit_price','category','picked','deleted_at') if kind=='item' else ('deleted_at',)
    result={key:row.get(key) for key in keys}
    if kind=='item':result['picked']=bool(result['picked'])
    if result.get('deleted_at'):
        from datetime import timezone
        result['deleted_at']=datetime.fromisoformat(str(result['deleted_at']).replace('Z','+00:00')).astimezone(timezone.utc).isoformat(timespec='microseconds')
    return result

def _market_action(self,kind,row_id,values,undo=None):
    from datetime import timezone
    table='market_items' if kind=='item' else 'market_trips'
    before=self._cache_find(table,row_id)
    if not before:raise ValueError('Atualize o registro antes de alterar.')
    if str(before.get('created_by'))!=str(self.user.id):raise PermissionError('Altere somente registros criados por você.')
    expected=_market_mutable_snapshot(kind,before)
    operation=str(uuid.uuid4())
    server={'p_kind':kind,'p_id':str(row_id),'p_operation':operation,'p_expected':expected,'p_values':values,'p_undo':undo}
    result=self._flush_operation(self._enqueue_update(table,row_id,values,server_payload=server,
                                 operation_id=operation,transport='market_action_rpc'))
    if self.vault:self.vault.write('market-undo:'+self._scope(),{'kind':kind,'row_id':row_id,'operation':operation,
                              'before':expected,'after':{**expected,**values}} if not undo else None)
    return result

def _delete_market_trip(self,trip_id):
    from datetime import timezone
    return _market_action(self,'trip',trip_id,{'deleted_at':datetime.now(timezone.utc).isoformat()})

def _update_market_item(self,item_id,**values):
    from services.market import product_values
    before=self._cache_find('market_items',item_id)
    if not before:raise ValueError('Atualize o produto antes de editar.')
    name,qty,price=product_values(values.get('product_name',before.get('product_name')),
        values.get('quantity',before.get('quantity')),values.get('unit_price',before.get('unit_price')))
    clean={'product_name':name,'quantity':float(qty),'unit_price':float(price),
           'category':str(values.get('category',before.get('category')) or 'Outros')}
    if 'picked' in values:clean['picked']=bool(values['picked'])
    return _market_action(self,'item',item_id,clean)

def _delete_market_item(self,item_id):
    from datetime import timezone
    return _market_action(self,'item',item_id,{'deleted_at':datetime.now(timezone.utc).isoformat()})

def _undo_market_action(self):
    record=self.vault.read('market-undo:'+self._scope(),None) if self.vault else None
    if not record:raise ValueError('Nenhuma ação disponível para desfazer neste perfil.')
    if record['kind']=='budget':
        current=self._cache_find('market_trips',record['row_id']) or {}
        if any(current.get(k)!=v for k,v in record['after'].items()):raise ValueError('O limite mudou. Atualize antes de desfazer.')
        result=_update_market_trip(self,record['row_id'],**record['before'])
        self.vault.write('market-undo:'+self._scope(),None)
        return result
    table='market_items' if record['kind']=='item' else 'market_trips'
    current=self._cache_find(table,record['row_id'])
    if not current or _market_mutable_snapshot(record['kind'],current)!=record['after']:
        raise ValueError('O registro mudou depois desta ação. Atualize antes de desfazer.')
    return _market_action(self,record['kind'],record['row_id'],record['before'],undo=record['operation'])

Cloud.undo_market_action=_undo_market_action

Cloud.update_market_trip=_update_market_trip
Cloud.market_budget_history=_market_budget_history
Cloud.delete_market_trip=_delete_market_trip
Cloud.update_market_item=_update_market_item
Cloud.delete_market_item=_delete_market_item


def _list_shopping_lists(self):
    return sorted(self.fetch_all("shopping_lists"),key=lambda r:r.get("created_at") or "",reverse=True)

def _add_shopping_list(self,name,budget=0,member_id=None,shared=False):
    from services.finance_engine import amount
    clean=str(name or "").strip()
    money=amount(budget)
    if not clean or len(clean)>100 or money<0:raise ValueError("Confira nome e orçamento da lista")
    payload={"id":str(uuid.uuid4()),"household_id":self._hid(),"member_id":member_id,
             "name":clean,"budget":float(money),"shared":bool(shared),"created_by":str(self.user.id)}
    return self._flush_operation(self._enqueue_upsert("shopping_lists",payload))

def _update_shopping_list(self,row_id,name,budget):
    from services.finance_engine import amount
    clean=str(name or "").strip()
    value=amount(budget)
    if not clean or len(clean)>100 or value<0:raise ValueError("Confira nome e orçamento da lista")
    return self._flush_operation(self._enqueue_update("shopping_lists",str(row_id),
        {"name":clean,"budget":float(value)}))

def _delete_shopping_list(self,row_id):
    return self._flush_operation(self._enqueue_delete("shopping_lists",str(row_id)))

def _list_shopping_list_items(self,list_id):
    return [row for row in self.fetch_all("shopping_list_items") if str(row.get("list_id"))==str(list_id)]

def _add_shopping_list_item(self,list_id,name,quantity=1,unit_price=0):
    from services.market import product_values
    clean,qty,price=product_values(name,quantity,unit_price)
    if len(clean)>150:raise ValueError("Nome do produto muito longo")
    payload={"id":str(uuid.uuid4()),"list_id":str(list_id),"household_id":self._hid(),"name":clean,"quantity":float(qty),
             "unit_price":float(price),"purchased":False,"created_by":str(self.user.id)}
    return self._flush_operation(self._enqueue_upsert("shopping_list_items",payload))

def _update_shopping_list_item(self,row_id,**values):
    from services.market import product_values
    clean={}
    if any(key in values for key in ("name","quantity","unit_price")):
        existing=next((r for r in self.fetch_all("shopping_list_items") if str(r.get("id"))==str(row_id)),None)
        if not existing:raise ValueError("Produto da lista não encontrado")
        name,qty,price=product_values(values.get("name",existing.get("name")),
                                     values.get("quantity",existing.get("quantity")),
                                     values.get("unit_price",existing.get("unit_price")))
        clean.update(name=name,quantity=float(qty),unit_price=float(price))
    if "purchased" in values:clean["purchased"]=bool(values["purchased"])
    if not clean:raise ValueError("Nenhuma alteração informada")
    return self._flush_operation(self._enqueue_update("shopping_list_items",row_id,clean))

def _delete_shopping_list_item(self,row_id):
    return self._flush_operation(self._enqueue_delete("shopping_list_items",row_id))

Cloud.list_shopping_lists=_list_shopping_lists
Cloud.add_shopping_list=_add_shopping_list
Cloud.update_shopping_list=_update_shopping_list
Cloud.delete_shopping_list=_delete_shopping_list
Cloud.list_shopping_list_items=_list_shopping_list_items
Cloud.add_shopping_list_item=_add_shopping_list_item
Cloud.update_shopping_list_item=_update_shopping_list_item
Cloud.delete_shopping_list_item=_delete_shopping_list_item


def _fetch_all(self,table,select="*"):
    key=table+":"+select
    cached=self._cache_get(key)
    # Cache só abre imediatamente depois de uma sessão autenticada ou de uma
    # sessão previamente validada que ficou offline. Estados desconhecidos
    # precisam consultar o servidor para não reabrir dados após revogação.
    if cached is not None and self.session_state in {'authenticated','offline_with_local_session'}:
        rows=_overlay_unresolved(self,table,cached)
        self._cache_set(key,rows)
        return rows
    return _refresh_table(self,table,select)

def _overlay_unresolved(self,table,rows):
    """Reconstrói a visão local mesmo se o app caiu após gravar só a fila."""
    rows=list(rows or [])
    queue=self._sync_queue()
    if not queue:
        return rows
    for mutation in queue.unresolved():
        payload=mutation.get('payload') or {}
        if payload.get('table')!=table:
            continue
        operation=payload.get('operation') or 'upsert'
        state=mutation.get('state') or 'queued'
        row_id=str(mutation.get('row_id') or '')
        if (table=='monthly_closures' or payload.get('transport')=='market_finalize_rpc') and operation=='upsert' and state in {'rejected','conflict'}:
            rows=[item for item in rows if str(item.get('id'))!=row_id]
            if payload.get('before'):rows.append(dict(payload['before']))
            continue
        if operation=='delete':
            rows=[item for item in rows if str(item.get('id'))!=row_id]
            if state in {'rejected','conflict'} and payload.get('before'):
                restored=dict(payload['before'])
                restored['_sync_state']=state+'_delete'
                rows.append(restored)
            continue
        if operation=='update' and state in {'rejected','conflict'}:
            local=dict(payload.get('before') or {})
            local['_sync_state']=state+'_update'
        else:
            local=dict(payload.get('local') or {})
            local['_sync_state']=state
        rows=[item for item in rows if str(item.get('id'))!=str(local.get('id'))]
        rows.append(local)
    return rows

def _refresh_table(self,table,select="*"):
    """Busca uma tabela na nuvem e substitui sua cópia cifrada local."""
    key=table+":"+select
    try:
        rows=[]
        offset=0
        while True:
            page=self._run_network(lambda:self.client.table(table).select(select).eq("household_id",self._hid()).order("id").range(offset,offset+499).execute().data)
            rows.extend(page or [])
            if len(page or [])<500:break
            offset+=500
        rows=_overlay_unresolved(self,table,rows)
        self._cache_set(key,rows)
        return rows
    except (TransportError, ConnectionError, TimeoutError):
        cached=self._cache_get(key)
        if cached is None:raise RuntimeError("Dados indisponíveis e sem cópia offline; tente sincronizar") from None
        rows=_overlay_unresolved(self,table,cached)
        self._cache_set(key,rows)
        return rows

def _refresh_core_data(self):
    """Atualiza cópias usadas nas telas sem bloquear a navegação."""
    self.flush_pending()
    specs=(
        ("household_members","*"),
        ("income","*, household_members(display_name)"),
        ("expenses","*, household_members!expenses_payer_member_id_fkey(display_name), expense_shares(*, household_members(display_name))"),
        ("acquisitions","*, household_members(display_name)"),
        ("financial_goals","*"),
        ("market_trips","*"),
        ("market_items","*"),
        ("shopping_lists","*"),
        ("shopping_list_items","*"),
        ("nex_journeys","*"),
        ("monthly_closures","*"),
    )
    changed=False
    for table,select in specs:
        before=self._cache_get(table+":"+select)
        try:
            rows=_refresh_table(self,table,select)
            if table == "monthly_closures":
                self.month_closures_error = None
        except Exception as exc:
            if table != "monthly_closures":
                raise
            # Keep core sync usable when an older server has not received the
            # additive continuity migration yet. The Home screen surfaces it.
            self.month_closures_error = type(exc).__name__
            logger.warning("month_closure_sync_unavailable kind=%s", type(exc).__name__)
            continue
        changed = changed or before != rows
    return changed

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

def _privacy_cache_key(self):
    return "privacy_consents_local"

def _privacy_pending_key(self):
    return "privacy_consents_pending"

def _privacy_payload(self,purpose,granted):
    return {"household_id":self._hid(),"user_id":str(self.user.id),"purpose":purpose,
        "granted":bool(granted),"policy_version":"2026-09-13.1","created_by":str(self.user.id)}

def _sync_pending_consents(self):
    pending=dict(self._cache_get(self._privacy_pending_key(),{}) or {})
    if not pending:
        return 0
    synced=0
    for purpose,granted in list(pending.items()):
        try:
            self.client.table('privacy_consents').upsert(
                self._privacy_payload(purpose,granted),on_conflict='user_id,household_id,purpose'
            ).execute()
        except Exception as exc:
            logger.info('privacy_consent_sync_pending kind=%s',type(exc).__name__)
            self.online=False
            break
        pending.pop(purpose,None)
        synced+=1
    self._cache_set(self._privacy_pending_key(),pending)
    return synced

def _set_consent(self,purpose,granted):
    allowed={'reminders','external_ai','affiliate_personalization'}
    if purpose not in allowed: raise ValueError('Finalidade de consentimento inválida')
    cached=dict(self._cache_get(self._privacy_cache_key(),{}) or {})
    cached[purpose]=bool(granted)
    self._cache_set(self._privacy_cache_key(),cached)
    pending=dict(self._cache_get(self._privacy_pending_key(),{}) or {})
    pending[purpose]=bool(granted)
    self._cache_set(self._privacy_pending_key(),pending)
    payload=self._privacy_payload(purpose,granted)
    try:
        result=self.client.table('privacy_consents').upsert(payload,on_conflict='user_id,household_id,purpose').execute()
        pending.pop(purpose,None)
        self._cache_set(self._privacy_pending_key(),pending)
        return result
    except Exception as exc:
        # No Android/rede instável, a escolha continua salva localmente e pode
        # ser sincronizada em uma próxima sessão, sem bloquear o usuário.
        logger.info('privacy_consent_saved_local kind=%s',type(exc).__name__)
        self.online=False
        return {"local":True,"purpose":purpose,"granted":bool(granted)}

def _get_consents(self):
    cached=dict(self._cache_get(self._privacy_cache_key(),{}) or {})
    pending=dict(self._cache_get(self._privacy_pending_key(),{}) or {})
    try:
        rows=self.fetch_all('privacy_consents')
        remote={r.get('purpose'):bool(r.get('granted')) for r in rows if str(r.get('user_id'))==str(self.user.id)}
        if remote:
            # Uma escolha local ainda pendente é mais nova que a cópia remota.
            # Ela não pode desaparecer ao reabrir o app com rede intermitente.
            cached.update({key:value for key,value in remote.items() if key not in pending})
            self._cache_set(self._privacy_cache_key(),cached)
        if pending:
            self._sync_pending_consents()
    except Exception as exc:
        logger.info('privacy_consent_read_local kind=%s',type(exc).__name__)
    return cached

def _offers(self):
    from services.affiliate import HOSTS
    self._offer_partner_hosts=set(HOSTS)
    try:
        hosts=self._run_network(lambda:self.client.table("offer_partner_hosts").select("host").eq("enabled",True).execute().data)
        self._offer_partner_hosts.update(str(row['host']) for row in hosts or [] if row.get('host'))
    except (ReauthenticationRequired, SessionUnavailable):
        raise
    except Exception:
        # Older schema safely keeps the original Mercado Livre allowlist.
        logger.info('offer_partner_hosts_unavailable')
    try:
        rows=self._run_network(lambda:self.client.table("affiliate_offers").select("*").eq("enabled",True).execute().data)
        return rows or []
    except (ReauthenticationRequired, SessionUnavailable):
        raise
    except Exception:
        # An unavailable catalog is empty; never present test offers as live.
        logger.warning('affiliate_offers_unavailable')
        return []

def _nex_conversations(self,member_id,include_archived=False):
    rows=self.fetch_all("nex_conversations")
    uid=str(self.user.id)
    allowed={"active","archived"} if include_archived else {"active"}
    return sorted([
        row for row in rows
        if str(row.get("member_id") or "")==str(member_id)
        and str(row.get("owner_user_id") or "")==uid
        and str(row.get("status") or "active") in allowed
    ],key=lambda row:row.get("updated_at") or "",reverse=True)

def _ensure_free_conversation(self,member_id):
    current=next((row for row in _nex_conversations(self,member_id) if row.get("kind")=="free"),None)
    if current:return current
    payload={"household_id":self._hid(),"member_id":str(member_id),"owner_user_id":str(self.user.id),
             "kind":"free","status":"active","title":"Chat livre"}
    try:
        return self._run_network(lambda:self.client.table("nex_conversations").insert(payload).execute().data[0])
    except Exception:
        # Uma criação concorrente pode vencer a constraint única; relê antes de falhar.
        current=next((row for row in _nex_conversations(self,member_id) if row.get("kind")=="free"),None)
        if current:return current
        raise

def _nex_messages(self,conversation_id,limit=120):
    rows=self._run_network(lambda:self.client.table("nex_messages").select("*")
        .eq("conversation_id",str(conversation_id)).order("created_at",desc=True).limit(max(1,min(int(limit),200))).execute().data)
    return list(rows or [])[::-1]

def _save_nex_message(self,conversation_id,member_id,role,content,request_id,state="synced",created_at=None):
    if role not in {"user","assistant","system"}:raise ValueError("Remetente inválido")
    text=str(content or "").strip()
    if not text or len(text)>12000:raise ValueError("Mensagem vazia ou longa demais")
    payload={"conversation_id":str(conversation_id),"household_id":self._hid(),"member_id":str(member_id),
             "owner_user_id":str(self.user.id),"logical_role":role,"content":text,
             "request_id":str(request_id) if request_id else None,"state":state,"metadata":{}}
    return self._run_network(lambda:self.client.rpc("save_nex_message_safe",{
        "p_conversation":str(conversation_id),"p_member":str(member_id),"p_role":role,
        "p_content":text,"p_request":str(request_id),"p_created_at":created_at,
    }).execute())

def _purge_nex_messages(self,conversation_id,member_id,start,end,preview=True):
    return self._run_network(lambda:self.client.rpc("purge_nex_messages",{
        "p_conversation":str(conversation_id),"p_member":str(member_id),
        "p_start":start,"p_end":end,"p_preview":bool(preview),
    }).execute().data)

Cloud.purge_nex_messages=_purge_nex_messages

def _pin_nex_conversation(self,conversation_id,title,replace_id=None):
    result=self._run_network(lambda:self.client.rpc("pin_nex_conversation",{
        "p_conversation":str(conversation_id),"p_title":str(title or "Conversa com o Nex")[:120],
        "p_replace":str(replace_id) if replace_id else None,
    }).execute().data)
    if isinstance(result,list):result=result[0] if result else None
    return str(result) if result else None

def _unpin_nex_conversation(self,conversation_id):
    return self._run_network(lambda:self.client.rpc("unpin_nex_conversation",{"p_conversation":str(conversation_id)}).execute())

def _update_nex_conversation(self,conversation_id,*,title=None,status=None):
    payload={}
    if title is not None:
        clean=" ".join(str(title).split())[:120]
        if not clean:raise ValueError("Título vazio")
        payload["title"]=clean
    if status is not None:
        if status not in {"active","archived","deleted"}:raise ValueError("Status inválido")
        payload["status"]=status
        if status=="archived":payload["archived_at"]=datetime.now(timezone.utc).isoformat()
        if status=="deleted":payload["deleted_at"]=datetime.now(timezone.utc).isoformat()
    if not payload:raise ValueError("Nenhuma alteração")
    return self._run_network(lambda:self.client.table("nex_conversations").update(payload)
        .eq("id",str(conversation_id)).eq("owner_user_id",str(self.user.id)).execute())

def _nex_conversation_bundle(self,member_id):
    rows=_nex_conversations(self,member_id)
    for row in rows:
        purges=self._run_network(lambda:self.client.table('nex_message_purges').select('id,range_start,range_end')
            .eq('conversation_id',row['id']).eq('owner_user_id',str(self.user.id)).execute().data)
        row={**row,"messages":_nex_messages(self,row["id"]),"message_purges":list(purges or [])}
        yield row

Cloud.fetch_all=_fetch_all
Cloud.refresh_table=_refresh_table
Cloud.refresh_core_data=_refresh_core_data
Cloud.set_payment=_payment
Cloud.list_journeys=_journey_rows
Cloud.load_journey_progress=_journeys
Cloud.save_journey_progress=_save_journey
Cloud.set_privacy_consent=_set_consent
Cloud.get_privacy_consents=_get_consents
Cloud._privacy_cache_key=_privacy_cache_key
Cloud._privacy_pending_key=_privacy_pending_key
Cloud._privacy_payload=_privacy_payload
Cloud.sync_pending_consents=_sync_pending_consents
Cloud.list_affiliate_offers=_offers
Cloud.list_nex_conversations=_nex_conversations
Cloud.ensure_free_nex_conversation=_ensure_free_conversation
Cloud.list_nex_messages=_nex_messages
Cloud.save_nex_message=_save_nex_message
Cloud.pin_nex_conversation=_pin_nex_conversation
Cloud.unpin_nex_conversation=_unpin_nex_conversation
Cloud.update_nex_conversation=_update_nex_conversation
Cloud.nex_conversation_bundle=_nex_conversation_bundle

def _delete_my_individual_account(self,confirmation):
    if confirmation != 'EXCLUIR MINHA CONTA':
        raise ValueError('Confirmação inválida')
    if not self.online:
        raise ValueError('Conecte-se à internet antes de excluir a conta')
    result=self._run_network(lambda:self.client.rpc('delete_my_individual_account',{
        'p_household_id':self._hid(), 'p_confirmation':confirmation,
    }).execute().data,attempts=1)
    if result is not True:
        raise ValueError('O servidor não confirmou a exclusão')
    # The remote token is revoked with the user. Clear local vault and cache.
    self.sign_out()
    return True

Cloud.delete_my_individual_account=_delete_my_individual_account
