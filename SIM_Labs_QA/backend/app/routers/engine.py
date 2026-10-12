from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from ..db import get_db
from ..auth import get_current_principal
from .integrated import ceo, scoped, out
from ..engine import ensure, enqueue, WORKERS
from ..engine_models import EngineConfig, EngineWorker, EngineSchedule, EngineJob, EngineIncident, LearningNote
from ..operations import audit
from ..models import now
import uuid
router=APIRouter(prefix='/engine')

@router.get('')
def status(product_slug:str='nexgrana',p=Depends(get_current_principal),db=Depends(get_db)):
    product=scoped(db,p,product_slug); ceo(p); ensure(db)
    c=db.get(EngineConfig,'scheduler')
    return {'config':out(c),'workers':[out(w) for w in db.scalars(select(EngineWorker))],'schedules':[out(s) for s in db.scalars(select(EngineSchedule))],'jobs':[out(j) for j in db.scalars(select(EngineJob).where(EngineJob.product_id==product.id).order_by(EngineJob.created_at.desc()).limit(150))],'incidents':[out(i) for i in db.scalars(select(EngineIncident))],'learning':[out(i) for i in db.scalars(select(LearningNote).where(LearningNote.product_id==product.id))]}

class Pause(BaseModel):
    paused:bool
@router.patch('/pause')
def pause(data:Pause,p=Depends(get_current_principal),db=Depends(get_db)):
    ceo(p); ensure(db); db.get(EngineConfig,'scheduler').paused=data.paused
    audit(db,'engine.pause',None,reason=str(data.paused),principal=p); db.commit(); return {'paused':data.paused}
@router.patch('/workers/{key}')
def worker(key:str,data:Pause,p=Depends(get_current_principal),db=Depends(get_db)):
    ceo(p); ensure(db); w=db.get(EngineWorker,key)
    if not w: raise HTTPException(404,'Worker desconhecido')
    w.paused=data.paused; audit(db,'engine.worker_pause',None,reason=key+':'+str(data.paused),principal=p); db.commit(); return out(w)
class ScheduleInput(BaseModel):
    interval_seconds:int=Field(ge=60,le=31536000)
    enabled:bool=True
@router.patch('/schedules/{key}')
def schedule(key:str,data:ScheduleInput,p=Depends(get_current_principal),db=Depends(get_db)):
    ceo(p); ensure(db); s=db.get(EngineSchedule,key)
    if not s: raise HTTPException(404,'Horario desconhecido')
    from datetime import timedelta
    s.interval_seconds=data.interval_seconds; s.enabled=data.enabled; s.next_run_at=now()+timedelta(seconds=data.interval_seconds)
    audit(db,'engine.schedule',None,reason=f'{key}:{data.interval_seconds};enabled={data.enabled}',principal=p); db.commit(); return out(s)
class RunInput(BaseModel):
    product_slug:str='nexgrana'
    worker:str='qa'
@router.post('/run',status_code=201)
def run(data:RunInput,p=Depends(get_current_principal),db=Depends(get_db)):
    product=scoped(db,p,data.product_slug); ceo(p); ensure(db)
    if data.worker not in WORKERS: raise HTTPException(422,'Worker desconhecido')
    j=enqueue(db,product.id,data.worker,'manual','manual:'+str(uuid.uuid4())); audit(db,'engine.manual',product.id,j.id,'Auditoria solicitada',p); db.commit(); return out(j)
class NoteInput(BaseModel):
    product_slug:str='nexgrana'
    source:str=Field(min_length=1,max_length=200)
    concept:str=Field(min_length=1,max_length=200)
    application:str=Field(min_length=1,max_length=10000)
@router.post('/learning',status_code=201)
def learning(data:NoteInput,p=Depends(get_current_principal),db=Depends(get_db)):
    product=scoped(db,p,data.product_slug); ceo(p)
    n=LearningNote(product_id=product.id,source=data.source,concept=data.concept,application=data.application); db.add(n); db.flush()
    audit(db,'engine.learning_note',product.id,n.id,'Anotacao fornecida pelo usuario; curso nao validado',p); db.commit(); return out(n)
