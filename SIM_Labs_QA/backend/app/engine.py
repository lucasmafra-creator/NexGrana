"""Persistent scheduler, fenced queue claims and isolated, time-limited audit jobs."""
import json, multiprocessing, signal, time, uuid, hashlib, zipfile, io, httpx
from datetime import timedelta, timezone
from pathlib import Path
from PIL import Image
from sqlalchemy import select, update, func, case
from .db import SessionLocal
from .models import Product, Task, now
from .integration_models import Artifact, Evidence, Decision, RegressionCase, TestRun
from .engine_models import EngineConfig, EngineWorker, EngineSchedule, EngineJob, EngineIncident
from .operations import dump, store_bytes, audit, notify
from .promotion_models import PromotionSource,PromotionOffer,PromotionRun,PromotionControl
from . import promotions
from .liveops import next_human_id
WORKERS={'qa':'QA e regressao','security':'Seguranca estatica','ux':'UX e identidade visual','product':'Produto e prioridades','engineering':'Arquitetura e divida tecnica','marketing':'Hipoteses de crescimento','performance':'Baseline e desempenho','redteam':'Contestacao dos gates','release':'Readiness sem publicar'}
INTERVALS={'hourly':3600,'six_hours':21600,'daily':86400,'weekly':604800,'monthly':2592000}
STOP=False
MAX_ATTEMPTS=3
TIMEOUT=90

def ensure(db):
    if not db.get(EngineConfig,'scheduler'): db.add(EngineConfig(key='scheduler'))
    if not db.get(EngineWorker,'promotions'): db.add(EngineWorker(key='promotions',specialty='Ofertas e fontes autorizadas'))
    if not db.get(PromotionControl,'feeds'): db.add(PromotionControl(key='feeds'))
    for key,specialty in WORKERS.items():
        if not db.get(EngineWorker,key): db.add(EngineWorker(key=key,specialty=specialty))
    for key,seconds in INTERVALS.items():
        if not db.get(EngineSchedule,key): db.add(EngineSchedule(key=key,interval_seconds=seconds))
    db.commit()

def enqueue(db,product_id,worker,kind,dedup,artifact_id=None):
    old=db.scalar(select(EngineJob).where(EngineJob.dedup_key==dedup))
    if old: return old
    job=EngineJob(product_id=product_id,worker_key=worker,kind=kind,dedup_key=dedup,artifact_id=artifact_id)
    db.add(job); db.flush(); return job

def incident(db,key,detail,severity='P2'):
    row=db.scalar(select(EngineIncident).where(EngineIncident.key==key))
    if not row: db.add(EngineIncident(key=key,detail=detail[:400],severity=severity))

def schedule_tick(db):
    ensure(db); config=db.get(EngineConfig,'scheduler'); config.heartbeat_at=now()
    if config.paused: db.commit(); return
    import shutil
    from .operations import private_root
    if shutil.disk_usage(private_root()).free<100*1024**2: incident(db,'disk_low','Menos de 100MB livres no armazenamento operacional. Verificar disco.','P1')
    products=list(db.scalars(select(Product).where(Product.status=='active')))
    for s in db.scalars(select(EngineSchedule).where(EngineSchedule.enabled==True,EngineSchedule.next_run_at<=now())):
        due=s.next_run_at.isoformat()
        for p in products:
            for w in (('qa','release') if s.key=='hourly' else WORKERS):
                enqueue(db,p.id,w,s.key,f'{s.key}:{due}:{p.id}:{w}')
        s.next_run_at=now()+timedelta(seconds=s.interval_seconds)
    for a in db.scalars(select(Artifact).where(Artifact.filename.ilike('%.zip'))):
        enqueue(db,a.product_id,'ux','asset_review',f'asset:{a.id}:{a.sha256}',a.id)
    schedule_promotions(db)
    db.commit()

def schedule_promotions(db):
    source=db.scalar(select(PromotionSource).join(Product,Product.id==PromotionSource.product_id).where(PromotionSource.enabled==True,PromotionSource.next_run_at<=now(),Product.status=='active').order_by(PromotionSource.next_run_at).limit(1))
    if not source:return
    # One global dispatch / 30s; the promotion worker serializes actual requests.
    if db.scalar(select(EngineJob.id).where(EngineJob.worker_key=='promotions',EngineJob.status.in_(['queued','running']))):return
    taken=db.execute(update(PromotionControl).where(PromotionControl.key=='feeds',PromotionControl.next_dispatch_at<=now()).values(next_dispatch_at=now()+timedelta(seconds=30)))
    if not taken.rowcount:return
    due=source.next_run_at.isoformat();source.next_run_at=now()+timedelta(seconds=source.interval_seconds)
    job=enqueue(db,source.product_id,'promotions','promotion_collect','promotion:'+source.id+':'+due)
    job.result_json=dump({'source_id':source.id,'revision':source.revision})

def recover(db):
    for j in db.scalars(select(EngineJob).where(EngineJob.status=='running',EngineJob.lease_until<now())):
        j.status='queued' if j.attempts<MAX_ATTEMPTS else 'failed'
        j.available_at=now()+timedelta(seconds=min(300,2**j.attempts*5)); j.lease_until=None
        j.error='Lease expirada; trabalho interrompido recuperado'
        db.get(EngineWorker,j.worker_key).status='idle'
        audit(db,'engine.recovered',j.product_id,j.id,j.error)
        if j.status=='failed': incident(db,'job:'+j.id,j.error,'P1')
    db.commit()

def claim(db):
    if db.get(EngineConfig,'scheduler').paused: return None
    for j in db.scalars(select(EngineJob).join(EngineWorker,EngineWorker.key==EngineJob.worker_key).where(EngineJob.status=='queued',EngineJob.available_at<=now(),EngineWorker.paused==False,EngineWorker.status!='running').order_by(case((EngineJob.kind=='manual',0),(EngineJob.kind=='asset_review',1),(EngineJob.kind=='promotion_collect',2),else_=3),EngineJob.created_at).limit(30)):
        # Worker lock and job claim share the same transaction; concurrent engines cannot claim twice.
        lock=db.execute(update(EngineWorker).where(EngineWorker.key==j.worker_key,EngineWorker.status!='running',EngineWorker.paused==False).values(status='running'))
        got=db.execute(update(EngineJob).where(EngineJob.id==j.id,EngineJob.status=='queued').values(status='running',attempts=EngineJob.attempts+1,started_at=now(),lease_until=now()+timedelta(seconds=TIMEOUT+30))) if lock.rowcount else None
        if got and got.rowcount: db.commit(); db.refresh(j); return (j.id,j.attempts)
        db.rollback()
    return None

def review_assets(a):
    results=[]; defects=[]
    with zipfile.ZipFile(a.path) as z:
        entries=z.infolist()
        if len(entries)>20000 or sum(i.file_size for i in entries)>1024**3: raise ValueError('ArchiveLimit')
        images=[i for i in entries if i.filename.lower().endswith(('.png','.webp','.jpg','.jpeg')) and ('nex' in i.filename.lower() or 'skin' in i.filename.lower())]
        for i in images[:150]:
            if i.file_size>16*1024**2: results.append({'file':i.filename,'status':'BLOCKED','reason':'Limite de imagem'}); continue
            try:
                data=z.read(i); im=Image.open(io.BytesIO(data)); im.verify()
                im=Image.open(io.BytesIO(data)); w,h=im.size
                reasons=[]
                if min(w,h)<128: reasons.append('Resolucao menor que 128px; avaliar tamanho de uso')
                if '/cards/' in i.filename.replace('\\','/') and min(w,h)<512: reasons.append('Preview de card abaixo de 512px: revisar texto separado, nitidez e escala de uso')
                if im.mode not in ('RGBA','LA'): reasons.append('Sem canal alpha; validar fundo da skin')
                result={'file':i.filename,'sha256':hashlib.sha256(data).hexdigest(),'width':w,'height':h,'mode':im.mode,'technical_status':'REVIEW' if reasons else 'PASS','findings':reasons,'visual_identity':'BLOCKED','visual_reason':'Sem avaliador visual configurado; coruja canonica, olhos, oculos e anatomia precisam de comparacao visual.'}
                results.append(result)
            except Exception:
                defects.append(i.filename); results.append({'file':i.filename,'technical_status':'FAIL','reason':'Imagem invalida ou insegura'})
    return {'status':'FAIL' if defects else 'BLOCKED','images':results,'count':len(results),'truncated':len(images)>150,'defects':defects,'automatic_actions':['Inventario e hashes','Validacao de decodificacao e resolucao','Plano de retrabalho preservando o original'],'remediation_prompt':'Corrija apenas roupa/acessorios da skin festiva ou causa social. Preserve a coruja roxa Nex, olhos grandes laranja/castanhos, oculos redondos, bico/pes laranja e peito claro; chibi 3D premium. Use referencia canonica e skin original anexadas. Gere candidata separada e compare antes/depois; nao sobrescreva a aprovada.','image_generation':'BLOCKED: provedor de imagem e referencia visual aprovados ainda nao configurados. Nenhuma melhoria estetica foi declarada executada.'}

def review_sector(db,j):
    tasks=list(db.scalars(select(Task).where(Task.product_id==j.product_id,Task.status!='done')))
    critical=[t.human_id for t in tasks if t.priority in ('P0','P1')]
    regressions=db.scalar(select(func.count(RegressionCase.id)).where(RegressionCase.product_id==j.product_id)) or 0
    runs=list(db.scalars(select(TestRun).where(TestRun.product_id==j.product_id).order_by(TestRun.created_at.desc()).limit(30)))
    advice={'qa':'Executar cenarios de regressao na build e anexar evidencias reais.','security':'Inspecao do app importado nao cobre RLS, duas contas ou sessao: executar em ambiente autorizado.','ux':'Validar 360/390/412px, teclado/chat, scroll e identidade Nex com capturas.','product':'Priorizar P0/P1 antes de novas funcionalidades; revisar passos e redundancia com uso observado.','engineering':'Fonte importada nao e executada automaticamente; preparar patch revisado em checkout isolado.','marketing':'Hipotese: melhorar onboarding pode elevar ativacao. Sem metricas de usuarios, testar antes de concluir.','performance':'Sem baseline comparavel nao ha ganho comprovado; medir startup, memoria, consultas e offline.','redteam':'Questionar offline, duas contas, clique duplo, dados invalidos e evidencias antigas.','release':'Nenhuma publicacao automatica; gates Windows/Android e decisao do CEO permanecem.'}
    integrity=[]
    if j.worker_key=='security':
        from .operations import private_root
        for e in db.scalars(select(Evidence).where(Evidence.product_id==j.product_id).order_by(Evidence.created_at.desc()).limit(200)):
            path=Path(e.path).resolve()
            try:
                path.relative_to(private_root())
                if not path.is_file(): raise ValueError('EvidenceMissing')
                h=hashlib.sha256()
                with path.open('rb') as f:
                    for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
                if h.hexdigest()!=e.sha256: raise ValueError('EvidenceHashMismatch')
                integrity.append({'id':e.id,'status':'PASS'})
            except Exception as exc: integrity.append({'id':e.id,'status':'FAIL','reason':type(exc).__name__})
    return {'integrity_recent_200':integrity,'status':'FAIL' if any(e['status']=='FAIL' for e in integrity) else ('BLOCKED' if critical else 'REVIEW'),'worker':j.worker_key,'schedule':j.kind,'observed':{'open_missions':len(tasks),'critical_open':critical,'regression_cases':regressions,'recent_test_runs':[{'id':r.id,'kind':r.kind,'status':r.status} for r in runs]},'recommendation':advice[j.worker_key],'limitations':'Auditoria dos registros operacionais; nao equivale a testes executados no app ou curso concluido.','metrics_source':'Banco operacional local','app_runtime_validation':'BLOCKED'}

def execute(job_id,attempt):
    begin=time.monotonic()
    try:
        with SessionLocal() as db:
            j=db.get(EngineJob,job_id)
            if not j or j.status!='running' or j.attempts!=attempt: return
            prepared=None;source_id=None;source_revision=None
            if j.kind=='promotion_collect':
                request=json.loads(j.result_json);source_id=request['source_id'];source_revision=request['revision']
                source=db.get(PromotionSource,source_id)
                if not source or not source.enabled or source.revision!=source_revision:
                    result={'status':'BLOCKED','reason':'Fonte pausada ou configuração alterada','published_to_nexgrana':False}
                else:
                    try:
                        prepared=promotions.prepare_collection(source)
                        result={'status':'PASS'}
                    except (ValueError,httpx.HTTPError) as exc:
                        # Sanitized errors never persist URLs, headers or credentials.
                        reason=str(exc) if isinstance(exc,ValueError) else type(exc).__name__
                        result={'status':'EXTERNAL_BLOCKER','reason':reason[:200],'published_to_nexgrana':False}
            else:result=review_assets(db.get(Artifact,j.artifact_id)) if j.kind=='asset_review' else review_sector(db,j)
        # Fence late results after timeout/recovery. Write only in final transaction.
        with SessionLocal() as db:
            j=db.get(EngineJob,job_id)
            if not j or j.status!='running' or j.attempts!=attempt: return
            if source_id:
                source=db.get(PromotionSource,source_id)
                if not source or not source.enabled or source.revision!=source_revision:
                    result={'status':'BLOCKED','reason':'Fonte pausada ou configuração alterada durante coleta','published_to_nexgrana':False}
                elif prepared is not None:
                    fenced=db.execute(update(PromotionSource).where(PromotionSource.id==source_id,PromotionSource.revision==source_revision,PromotionSource.enabled==True).values(last_run_at=now()))
                    if not fenced.rowcount:result={'status':'BLOCKED','reason':'Fonte alterada antes da persistência','published_to_nexgrana':False}
                    else:
                        try:result=promotions.apply_collection(db,source,prepared)
                        except ValueError as exc:
                            result={'status':'BLOCKED','reason':str(exc)[:200],'published_to_nexgrana':False}
                            source.last_status='BLOCKED';source.last_error=result['reason']
                            db.add(PromotionRun(product_id=j.product_id,source_id=source_id,status='BLOCKED',reason=result['reason']))
                else:
                    source.last_status=result['status'];source.last_error=result.get('reason','');source.last_run_at=now()
                    db.add(PromotionRun(product_id=j.product_id,source_id=source_id,status=result['status'],reason=source.last_error))
            path,sha=store_bytes(dump(result).encode(),'engine_report.json')
            e=Evidence(product_id=j.product_id,release_id=db.get(Artifact,j.artifact_id).release_id if j.artifact_id else None,filename='engine_report.json',path=str(path),sha256=sha,size_bytes=path.stat().st_size,kind='engine_report')
            db.add(e); db.flush(); j.evidence_id=e.id; j.result_json=dump(result); j.status='completed'; j.finished_at=now(); j.lease_until=None; j.duration_ms=int((time.monotonic()-begin)*1000)
            w=db.get(EngineWorker,j.worker_key); w.status='idle'; w.completed+=1; w.last_run_at=now(); w.last_error=''
            bad=[e for e in result.get('integrity_recent_200',[]) if e['status']=='FAIL']
            for finding in bad:
                key='integrity:'+finding['id']
                if not db.scalar(select(EngineIncident).where(EngineIncident.key==key)):
                    incident(db,key,'Integridade de evidencia comprometida: '+finding['id'],'P0')
                    db.add(Task(human_id=next_human_id(db,'TASK'),product_id=j.product_id,title='Integridade de evidencia comprometida',description=dump(finding),owner_sector='security',priority='P0'))
                    db.add(Decision(product_id=j.product_id,title='Revisar integridade da evidencia',problem=dump(finding),impact='Arquivo ausente, fora do armazenamento privado ou hash divergente; nao usar para homologacao.',recommendation='Preservar arquivos e backup, investigar origem e registrar nova evidencia real.'))
                    notify(db,j.product_id,'P0 de integridade encaminhado ao CEO com relatorio. Nenhuma evidencia foi apagada.')
            if result.get('defects'):
                db.add(Task(human_id=next_human_id(db,'TASK'),product_id=j.product_id,title='Corrigir assets Nex invalidos',description=dump(result),owner_sector='ux',priority='P1'))
                notify(db,j.product_id,'Assets invalidos detectados. Missao criada e relatorio com hashes anexado.')
            audit(db,'engine.completed',j.product_id,j.id,f'{j.worker_key}; {j.kind}; evidence={e.id}; duration_ms={j.duration_ms}; result={result["status"]}')
            db.commit()
    except Exception as exc:
        with SessionLocal() as db: fail(db,job_id,attempt,type(exc).__name__)

def fail(db,job_id,attempt,error):
    j=db.get(EngineJob,job_id)
    if not j or j.status!='running' or j.attempts!=attempt: return
    j.error=error[:200]; j.lease_until=None
    j.status='queued' if j.attempts<MAX_ATTEMPTS else 'failed'
    j.available_at=now()+timedelta(seconds=min(300,2**j.attempts*5))
    w=db.get(EngineWorker,j.worker_key); w.status='idle'; w.last_error=j.error
    if j.status=='failed': incident(db,'job:'+j.id,'Falha apos 3 tentativas: '+j.error,'P1')
    audit(db,'engine.failed',j.product_id,j.id,f'attempt={attempt}; {j.error}')
    db.commit()

def stop(*_):
    global STOP
    STOP=True

def main():
    signal.signal(signal.SIGINT,stop); signal.signal(signal.SIGTERM,stop)
    ctx=multiprocessing.get_context('spawn'); active={}
    try:
        while not STOP:
            with SessionLocal() as db:
                schedule_tick(db); recover(db)
                # Multiple supervisor invocations are harmless for queue claims; installer prevents duplicates.
                while len(active)<2:
                    token=claim(db)
                    if not token: break
                    p=ctx.Process(target=execute,args=token); p.start(); active[token]=(p,time.monotonic())
                for token,(p,started) in list(active.items()):
                    if p.is_alive() and time.monotonic()-started>TIMEOUT:
                        p.terminate(); p.join(3)
                        if p.is_alive(): p.kill(); p.join(3)
                        fail(db,*token,'Timeout90s')
                    if not p.is_alive():
                        p.join(); fail(db,*token,'ProcessoInterrompido'); del active[token]
            time.sleep(1)
    finally:
        for token,(p,_) in active.items():
            p.terminate(); p.join(3)
            with SessionLocal() as db: fail(db,*token,'ParadaControlada')

if __name__=='__main__': main()
