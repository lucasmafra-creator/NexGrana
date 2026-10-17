"""Lease-coordinated local operations; imported code is never executed."""
import os, signal, time, uuid
from datetime import timedelta
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .db import SessionLocal
from .models import now
from .integration_models import Lease
from .operations import cycle
from .liveops import heartbeat
_STOP=False
OWNER=str(uuid.uuid4())

def _stop(*_):
    global _STOP
    _STOP=True

def acquire(db):
    insert=sqlite_insert if db.get_bind().dialect.name=='sqlite' else pg_insert
    db.execute(insert(Lease).values(key='operations',owner=OWNER,expires_at=now()).on_conflict_do_nothing(index_elements=['key']))
    row=db.execute(update(Lease).where(Lease.key=='operations', (Lease.expires_at<now()) | (Lease.owner==OWNER)).values(owner=OWNER,expires_at=now()+timedelta(seconds=210)))
    db.commit(); return row.rowcount==1

def main():
    signal.signal(signal.SIGINT,_stop); signal.signal(signal.SIGTERM,_stop)
    print('SIM Labs integrado · operações locais iniciadas',flush=True)
    while not _STOP:
        try:
            with SessionLocal() as db:
                if acquire(db):
                    heartbeat(db,'running','AUTOMAÇÃO: fila, inspeção estática e triagem. Sem execução de código importado.')
                    count=cycle(db)
                    heartbeat(db,'running',f'Rodada concluída: {count} feedbacks triados. Auditorias e relatórios registrados.')
        except Exception as exc:
            print(f'operations_error={type(exc).__name__}',flush=True)
            with SessionLocal() as db: heartbeat(db,'degraded',f'Rodada interrompida: {type(exc).__name__}; consulte os logs locais.')
        for _ in range(5):
            if _STOP: break
            time.sleep(1)
    with SessionLocal() as db:
        row=db.get(Lease,'operations')
        if row and row.owner==OWNER:
            row.expires_at=now(); db.commit(); heartbeat(db,'stopped','Operação pausada')
if __name__=='__main__': main()
