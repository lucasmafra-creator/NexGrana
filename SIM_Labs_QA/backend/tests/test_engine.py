import io, zipfile
from datetime import timedelta
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Product, now
from app.engine import ensure, schedule_tick, enqueue, claim, recover, execute, fail
from app.engine_models import EngineConfig, EngineJob, EngineWorker, EngineIncident
from app.integration_models import Artifact, Release, Evidence
from app.operations import store_bytes

def test_scheduler_dedup_pause():
    with SessionLocal() as db:
        schedule_tick(db); first=len(list(db.scalars(select(EngineJob))))
        assert first>0
        schedule_tick(db); assert len(list(db.scalars(select(EngineJob))))==first
        db.get(EngineConfig,'scheduler').paused=True; db.commit(); assert claim(db) is None

def test_queue_report_evidence_and_fence():
    with SessionLocal() as db:
        ensure(db); p=db.scalar(select(Product)); j=enqueue(db,p.id,'qa','manual','test'); db.commit()
        token=claim(db); assert token[0]==j.id; assert claim(db) is None
    execute(*token)
    with SessionLocal() as db:
        j=db.get(EngineJob,token[0]); assert j.status=='completed'; assert db.get(Evidence,j.evidence_id)
        before=db.get(EngineWorker,'qa').completed
    execute(*token)
    with SessionLocal() as db: assert db.get(EngineWorker,'qa').completed==before

def test_recovery_exhausts_retry_and_unlocks():
    with SessionLocal() as db:
        ensure(db); p=db.scalar(select(Product)); j=enqueue(db,p.id,'qa','manual','retry'); db.commit()
        for attempt in range(1,4):
            j.available_at=now()-timedelta(seconds=1); db.commit(); token=claim(db); assert token[1]==attempt
            j.lease_until=now()-timedelta(seconds=1); db.commit(); recover(db); db.refresh(j)
        assert j.status=='failed'; assert db.get(EngineWorker,'qa').status=='idle'
        assert db.scalar(select(EngineIncident))

def test_bad_worker_does_not_block_other():
    with SessionLocal() as db:
        ensure(db); p=db.scalar(select(Product)); j=enqueue(db,p.id,'qa','manual','bad'); db.commit(); token=claim(db)
        fail(db,*token,'Timeout90s'); assert db.get(EngineWorker,'qa').status=='idle'
        other=enqueue(db,p.id,'security','manual','good'); db.commit(); assert claim(db)[0]==other.id

def test_assets_detect_corruption_and_preserve_original():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z: z.writestr('src/assets/nex/social.png',b'not a png')
    data=buf.getvalue(); path,sha=store_bytes(data,'source.zip')
    with SessionLocal() as db:
        ensure(db); p=db.scalar(select(Product)); r=Release(product_id=p.id,version='asset-test'); db.add(r); db.flush()
        a=Artifact(product_id=p.id,release_id=r.id,filename='source.zip',platform='Fonte',path=str(path),sha256=sha,size_bytes=len(data)); db.add(a); db.flush()
        j=enqueue(db,p.id,'ux','asset_review','asset-test',a.id); db.commit(); token=claim(db)
    execute(*token)
    with SessionLocal() as db:
        j=db.get(EngineJob,token[0]); assert j.status=='completed'; assert 'FAIL' in j.result_json; assert 'BLOCKED' in j.result_json
        assert path.read_bytes()==data

def test_engine_permissions_and_manual(client):
    assert client.get('/api/v1/engine').status_code==401
    h={'X-Dev-Actor':'Mafra'}
    assert client.get('/api/v1/engine',headers=h).status_code==200
    assert client.post('/api/v1/engine/run',headers=h,json={'worker':'qa'}).status_code==201
    assert client.patch('/api/v1/engine/schedules/hourly',headers=h,json={'interval_seconds':1}).status_code==422
    assert client.patch('/api/v1/engine/pause',headers=h,json={'paused':True}).status_code==200


def test_manual_jobs_precede_scheduled_backlog():
    with SessionLocal() as db:
        ensure(db); p=db.scalar(select(Product))
        enqueue(db,p.id,'qa','daily','older-scheduled')
        manual=enqueue(db,p.id,'qa','manual','manual-priority'); db.commit()
        assert claim(db)[0]==manual.id


def test_altered_evidence_cannot_be_downloaded(client):
    h={'X-Dev-Actor':'Mafra'}
    uploaded=client.post('/api/v1/evidence',headers=h,files={'file':('original.txt',b'original')})
    assert uploaded.status_code==201
    with SessionLocal() as db:
        e=db.get(Evidence,uploaded.json()['id'])
        from pathlib import Path
        Path(e.path).write_bytes(b'changed')
    assert client.get('/api/v1/evidence/'+uploaded.json()['id']+'/download',headers=h).status_code==409
