"""Fila persistente cifrada para futura sincronização offline.

Importante: esta fila ainda não intercepta mutações financeiras automaticamente.
Ela fornece idempotência, backoff, estados e resolução explícita de conflito para
que escrita offline só seja ativada depois de testes E2E em dispositivo.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from uuid import uuid4


def _now():
    return datetime.now(timezone.utc)


def _iso(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


def _parse(value):
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace('Z','+00:00'))


@dataclass
class Mutation:
    id: str
    scope: str
    entity: str
    row_id: str
    expected_version: int
    payload: dict
    attempts: int = 0
    state: str = 'queued'
    created_at: str = ''
    next_attempt_at: str = ''
    last_error: str = ''


class SyncQueue:
    STATES = {'queued','synced','conflict','cancelled'}

    def __init__(self, vault, scope):
        self.vault, self.scope = vault, scope
        self.key = 'queue:'+scope

    def _rows(self):
        rows=self.vault.read(self.key, [])
        # Migração transparente de filas antigas.
        for row in rows:
            row.setdefault('created_at', _iso(_now()))
            row.setdefault('next_attempt_at', row['created_at'])
            row.setdefault('last_error','')
            row.setdefault('attempts',0)
            row.setdefault('state','queued')
        return rows

    def enqueue(self, entity, row_id, expected_version, payload, operation_id=None):
        rows = self._rows()
        now=_now()
        op = Mutation(
            operation_id or str(uuid4()), self.scope, entity, row_id,
            int(expected_version), payload, created_at=_iso(now), next_attempt_at=_iso(now)
        )
        current=asdict(op)
        existing = next((x for x in rows if x['id'] == op.id), None)
        if existing:
            if any(existing[k] != current[k] for k in ('entity','row_id','payload','expected_version')):
                raise ValueError('UUID reutilizado com conteúdo diferente')
            return dict(existing)
        rows.append(current)
        self.vault.write(self.key, rows)
        return dict(current)

    def pending(self, now=None):
        now=now or _now()
        return [dict(r) for r in self._rows() if r['state']=='queued' and (_parse(r.get('next_attempt_at')) or now) <= now]

    def conflicts(self):
        return [dict(r) for r in self._rows() if r['state']=='conflict']

    def cancel(self, operation_id):
        rows=self._rows()
        row=next((r for r in rows if r['id']==operation_id),None)
        if not row: return None
        if row['state']=='synced': raise ValueError('Operação já sincronizada não pode ser cancelada localmente')
        row['state']='cancelled'; row['last_error']=''
        self.vault.write(self.key,rows)
        return dict(row)

    def retry(self, operation_id, now=None):
        rows=self._rows(); now=now or _now()
        row=next((r for r in rows if r['id']==operation_id),None)
        if not row: return None
        if row['state']=='synced': return dict(row)
        row['state']='queued'; row['next_attempt_at']=_iso(now); row['last_error']=''
        self.vault.write(self.key,rows)
        return dict(row)

    def apply_one(self, sender, now=None):
        now=now or _now()
        rows = self._rows()
        row = next((x for x in rows if x['state'] == 'queued' and (_parse(x.get('next_attempt_at')) or now) <= now), None)
        if not row:
            return None
        try:
            result = sender(dict(row)) or {}
            if result.get('conflict'):
                row['state']='conflict'
                row['last_error']='version_conflict'
            else:
                row['state']='synced'
                row['last_error']=''
        except (TimeoutError, ConnectionError) as exc:
            row['attempts'] += 1
            row['last_error']=type(exc).__name__
            row['next_attempt_at']=_iso(now+timedelta(seconds=self.backoff(row['attempts'])))
        self.vault.write(self.key, rows)
        return dict(row)

    @staticmethod
    def backoff(attempts):
        return min(300, 2 ** min(max(int(attempts),0), 9))
