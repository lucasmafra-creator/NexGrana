from __future__ import annotations
import hashlib, hmac, json, re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..db import get_db
from ..auth import Principal, get_current_principal
from ..permissions import require_any
from ..config import settings
from ..models import Product, Feedback, Task, AuditEvent, Sector, TeamMember, now
from ..integration_models import Release, Artifact, Evidence, Receipt, TestRun, RunnerReportReceipt, Decision, Message, Job, RegressionCase, DailyReport, ProjectConfig
from .. import ai_advisor
from ..operations import dump, audit, notify, store_bytes, ingest_records, import_package, release_gate, CHECKS, MAX_UPLOAD, daily_report, evidence_valid
from ..liveops import next_human_id, classify_feedback
from .live import _product_for_slug
router=APIRouter()

def out(row):
    return {c.name:getattr(row,c.name) for c in row.__table__.columns if c.name not in {'path','manifest_json','metadata_json','content_hash'}}

def ceo(p,product=None):
    if p.name!='Mafra' or 'executive' not in p.roles: raise HTTPException(403,'Decisão reservada ao CEO Mafra')

def scoped(db,p,slug): return _product_for_slug(db,p,slug)

def item(db,model,id,p):
    row=db.get(model,id)
    if not row: raise HTTPException(404,'Registro não encontrado')
    from ..permissions import can_access_product
    if not can_access_product(p,row.product_id): raise HTTPException(403,'Projeto não autorizado')
    return row

async def upload_bytes(file):
    chunks=[]; size=0
    while chunk:=await file.read(1024*1024):
        size+=len(chunk)
        if size>MAX_UPLOAD: raise HTTPException(413,'Limite de arquivo: 450 MB')
        chunks.append(chunk)
    data=b''.join(chunks)
    if not data: raise HTTPException(422,'Arquivo vazio')
    return data

class ReleaseInput(BaseModel):
    product_slug:str='nexgrana'
    version:str=Field(min_length=1,max_length=80)
    notes:str=Field(default='',max_length=20000)

@router.post('/releases',status_code=201)
def create_release(data:ReleaseInput,p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,data.product_slug); ceo(p)
    if db.scalar(select(Release).where(Release.product_id==product.id,Release.version==data.version)): raise HTTPException(409,'Versão já cadastrada')
    row=Release(product_id=product.id,version=data.version,notes=data.notes)
    db.add(row); db.flush(); audit(db,'release.created',product.id,row.id,data.version,p); db.commit(); return out(row)

@router.get('/releases')
def releases(product_slug:str='nexgrana',p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug)
    return [{**out(r),'gate':release_gate(db,r),'artifacts':[out(a) for a in db.scalars(select(Artifact).where(Artifact.release_id==r.id))]} for r in db.scalars(select(Release).where(Release.product_id==product.id).order_by(Release.created_at.desc()).limit(100))]

@router.post('/releases/{release_id}/artifacts',status_code=201)
async def upload_artifact(release_id:str,file:UploadFile=File(...),platform:str=Form('Fonte'),p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    release=item(db,Release,release_id,p); ceo(p)
    if release.status=='stable': raise HTTPException(409,'Versão estável é imutável; crie uma candidata')
    if platform not in {'Windows','Android','Fonte','Web'}: raise HTTPException(422,'Plataforma inválida')
    filename=Path((file.filename or 'arquivo').replace('\\','/')).name[:200]
    if Path(filename).suffix.lower() not in {'.zip','.apk','.aab','.exe','.msi','.msix','.appx'}: raise HTTPException(422,'Tipo de build não suportado')
    data=await upload_bytes(file); sha=hashlib.sha256(data).hexdigest()
    existing=db.scalar(select(Artifact).where(Artifact.release_id==release.id,Artifact.sha256==sha))
    if existing: return {**out(existing),'duplicate':True}
    path,_=store_bytes(data,filename)
    row=Artifact(product_id=release.product_id,release_id=release.id,filename=filename,platform=platform,path=str(path),sha256=sha,size_bytes=len(data))
    db.add(row); db.flush(); db.add(Job(product_id=release.product_id,artifact_id=row.id))
    audit(db,'artifact.queued',release.product_id,row.id,filename,p)
    notify(db,release.product_id,f'Build {filename} recebido na release {release.version}. Auditoria estrutural enfileirada.')
    db.commit(); return out(row)

@router.post('/collector/package')
async def collector_package(file:UploadFile=File(...),product_slug:str=Form('nexgrana'),p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug); ceo(p)
    data=await upload_bytes(file); path,_=store_bytes(data,'collector.zip')
    try: return import_package(db,product,path,p)
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409,"Envio concorrente reconhecido; reenvie para reconciliar os IDs.") from exc
    except (ValueError,KeyError,TypeError) as exc:
        db.rollback(); raise HTTPException(422,str(exc)) from exc
    finally: path.unlink(missing_ok=True)

class IngestInput(BaseModel):
    schema_version:str=Field(default='sim-labs.feedback-ingest/1.0',alias='schema')
    product_slug:str='nexgrana'
    release:str=Field(default='',max_length=80)
    records:list[dict]=Field(max_length=1000)

@router.post('/collector/ingest')
def collector_ingest(data:IngestInput,x_sim_ingest_token:str|None=Header(default=None,alias='X-SIM-Ingest-Token'),db:Session=Depends(get_db)):
    if not settings.feedback_ingest_token: raise HTTPException(503,'Integração não configurada')
    if not x_sim_ingest_token or not hmac.compare_digest(x_sim_ingest_token,settings.feedback_ingest_token): raise HTTPException(401,'Credencial da integração inválida')
    if data.product_slug!=settings.ingest_product_slug: raise HTTPException(403,'Credencial limitada ao projeto configurado')
    if data.schema_version!='sim-labs.feedback-ingest/1.0': raise HTTPException(422,'Schema não suportado')
    product=db.scalar(select(Product).where(Product.slug==data.product_slug))
    if not product: raise HTTPException(404,'Projeto não cadastrado')
    try: return ingest_records(db,product,data.records,data.release)
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409,'Envio concorrente; reenvie para reconciliar.') from exc
    except ValueError as exc:
        db.rollback(); raise HTTPException(422,str(exc)) from exc

@router.post('/collector/ingest-package')
async def collector_token_package(file:UploadFile=File(...),x_sim_ingest_token:str|None=Header(default=None,alias='X-SIM-Ingest-Token'),db:Session=Depends(get_db)):
    if not settings.feedback_ingest_token or not x_sim_ingest_token or not hmac.compare_digest(x_sim_ingest_token,settings.feedback_ingest_token): raise HTTPException(401,'Credencial da integração inválida')
    product=db.scalar(select(Product).where(Product.slug==settings.ingest_product_slug))
    if not product: raise HTTPException(404,'Projeto não cadastrado')
    data=await upload_bytes(file); path,_=store_bytes(data,'collector.zip')
    try: return import_package(db,product,path)
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(409,"Envio concorrente reconhecido; reenvie para reconciliar os IDs.") from exc
    except (ValueError,KeyError,TypeError) as exc:
        db.rollback(); raise HTTPException(422,str(exc)) from exc
    finally: path.unlink(missing_ok=True)

@router.get('/inbox')
def inbox(product_slug:str='nexgrana',p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug)
    rows=list(db.scalars(select(Feedback).where(Feedback.product_id==product.id).order_by(Feedback.created_at.desc()).limit(200)))
    result=[]
    for row in rows:
        receipt=db.scalar(select(Receipt).where(Receipt.feedback_id==row.id))
        result.append({**out(row),'external_id':receipt.external_id if receipt else None,'platform':receipt.platform if receipt else None,'screen':receipt.screen if receipt else None,'release_version':receipt.release_version if receipt else None,'evidence':[out(e) for e in db.scalars(select(Evidence).where(Evidence.feedback_id==row.id))]})
    return result

@router.get('/evidence')
def evidence(product_slug:str='nexgrana',p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug)
    return [out(e) for e in db.scalars(select(Evidence).where(Evidence.product_id==product.id).order_by(Evidence.created_at.desc()).limit(200))]

@router.get('/evidence/{evidence_id}/download')
def evidence_download(evidence_id:str,p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    row=item(db,Evidence,evidence_id,p)
    if not Path(row.path).is_file(): raise HTTPException(404,'Arquivo indisponível')
    if not evidence_valid(row): raise HTTPException(409,'Integridade do arquivo diverge do hash registrado')
    return FileResponse(row.path,filename=row.filename,media_type='application/octet-stream',headers={'X-Content-Type-Options':'nosniff'})

@router.post('/evidence',status_code=201)
async def add_evidence(file:UploadFile=File(...),product_slug:str=Form('nexgrana'),release_id:str=Form(''),feedback_id:str=Form(''),p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug); ceo(p)
    for model,key in ((Release,release_id),(Feedback,feedback_id)):
        if key and item(db,model,key,p).product_id!=product.id: raise HTTPException(422,'Referência pertence a outro projeto')
    data=await upload_bytes(file); filename=Path((file.filename or 'evidencia').replace('\\','/')).name[:200]
    path,sha=store_bytes(data,filename)
    row=Evidence(product_id=product.id,release_id=release_id or None,feedback_id=feedback_id or None,filename=filename,path=str(path),sha256=sha,size_bytes=len(data))
    db.add(row); db.flush(); audit(db,'evidence.added',product.id,row.id,filename,p); db.commit(); return out(row)

class ManualInput(BaseModel):
    platform:str
    check_id:str
    status:str
    note:str=Field(min_length=5,max_length=5000)
    evidence_id:str|None=None

@router.get('/manual-checks')
def manual_checks(p:Principal=Depends(get_current_principal)): return CHECKS

@router.post('/releases/{release_id}/manual-checks')
def add_manual(release_id:str,data:ManualInput,p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    release=item(db,Release,release_id,p); ceo(p)
    if release.status=='stable': raise HTTPException(409,'Versão estável é imutável')
    if data.platform not in {'Windows','Android'} or data.check_id not in {x['id'] for x in CHECKS} or data.status not in {'PASS','FAIL','BLOCKED'}: raise HTTPException(422,'Checklist inválido')
    if data.check_id.startswith('android_') and data.platform!='Android' or data.check_id.startswith('windows_') and data.platform!='Windows': raise HTTPException(422,'Cenário incompatível com plataforma')
    if data.status=='PASS' and not data.evidence_id: raise HTTPException(422,'PASS exige evidência')
    if data.evidence_id:
        evidence=item(db,Evidence,data.evidence_id,p)
        if not evidence_valid(evidence): raise HTTPException(409,'Evidencia ausente ou alterada; registre evidencia real novamente')
        if evidence.product_id!=release.product_id or evidence.release_id!=release.id: raise HTTPException(422,'Evidência deve estar vinculada a esta release')
    row=TestRun(product_id=release.product_id,release_id=release.id,kind='manual',status=data.status.lower(),result_json=dump(data.model_dump()))
    db.add(row); audit(db,'manual.recorded',release.product_id,reason=f'{data.platform}/{data.check_id}: {data.status}',principal=p); db.commit(); return out(row)

@router.get('/test-runs')
def test_runs(product_slug:str='nexgrana',p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug)
    return [out(r) for r in db.scalars(select(TestRun).where(TestRun.product_id==product.id).order_by(TestRun.created_at.desc()).limit(100))]

class RunnerReportInput(BaseModel):
    evidence_id:str
    task_ids:list[str]=Field(default_factory=list,max_length=30)

@router.post('/releases/{release_id}/runner-reports',status_code=201)
def import_runner_report(release_id:str,data:RunnerReportInput,p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    release=item(db,Release,release_id,p);ceo(p)
    if release.status=='stable':raise HTTPException(409,'Release estável é imutável')
    evidence=item(db,Evidence,data.evidence_id,p)
    if evidence.release_id!=release.id or evidence.product_id!=release.product_id or not evidence_valid(evidence):
        raise HTTPException(409,'Evidência precisa pertencer à release e manter integridade')
    if evidence.size_bytes>3*1024*1024:raise HTTPException(422,'Relatório excede 3 MB')
    try:report=json.loads(Path(evidence.path).read_text(encoding='utf-8'))
    except (ValueError,OSError,UnicodeError):raise HTTPException(422,'Relatório JSON inválido') from None
    if not isinstance(report,dict) or report.get('schema')!='sim-labs.trusted-source-run/1.0' or report.get('status') not in {'PASS','FAIL'}:
        raise HTTPException(422,'Schema/status do runner não reconhecido')
    checks=report.get('checks')
    if not isinstance(checks,list) or not checks or len(checks)>20 or any(not isinstance(c,dict) or c.get('status') not in {'PASS','FAIL'} for c in checks):
        raise HTTPException(422,'Relatório sem verificações válidas')
    if report['status']=='PASS' and (report.get('official_source_unchanged') is not True or any(c.get('status')!='PASS' or c.get('exit_code',0)!=0 or c.get('timed_out') or c.get('output_limit_exceeded') for c in checks)):
        raise HTTPException(422,'PASS contradiz o resultado das verificações')
    marker='runner-evidence:'+evidence.id
    receipt=db.get(RunnerReportReceipt,(release.id,evidence.sha256))
    previous=db.get(TestRun,receipt.test_run_id) if receipt else None
    if previous:return {**out(previous),'duplicate':True}
    tasks=[item(db,Task,key,p) for key in dict.fromkeys(data.task_ids)]
    if any(t.product_id!=release.product_id or t.status=='done' for t in tasks):
        raise HTTPException(422,'Missão de outro projeto ou já encerrada')
    result={'marker':marker,'evidence_id':evidence.id,'source_manifest_sha256':report.get('source_manifest_sha256'),
            'checks':checks,'source_preserved':report.get('official_source_unchanged'),
            'origin':'manual_trusted_runner','executed_by_engine':False,
            'scope_note':'Resultado importado de execução manual; não comprova instalação, visual, sandbox ou vínculo desta fonte com um binário.'}
    run=TestRun(product_id=release.product_id,release_id=release.id,kind='imported_runner',status=report['status'].lower(),result_json=dump(result))
    db.add(run);db.flush()
    db.add(RunnerReportReceipt(release_id=release.id,report_sha256=evidence.sha256,evidence_id=evidence.id,test_run_id=run.id))
    try:db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Relatório já importado por outra requisição; atualize a lista.') from None
    for task in tasks:
        task.status='review'
        audit(db,'mission.runner_review',release.product_id,task.id,'Evidência '+evidence.id+'; regressão funcional e decisão de encerramento continuam exigidas.',p)
    audit(db,'runner.report_imported',release.product_id,run.id,'Execução manual importada; nenhuma missão encerrada automaticamente.',p)
    db.commit();return out(run)

@router.post('/releases/{release_id}/request-decision')
def request_decision(release_id:str,p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    release=item(db,Release,release_id,p); ceo(p)
    if release.status=='stable': raise HTTPException(409,'Release já estável')
    decision=db.scalar(select(Decision).where(Decision.release_id==release.id))
    gate=release_gate(db,release)
    if not decision:
        decision=Decision(product_id=release.product_id,release_id=release.id,title=f'Release {release.version}: decisão do CEO',problem='Avaliar candidata com evidências técnicas e homologação real.',impact='Promover define a nova referência estável; não publica em lojas ou servidor.',recommendation='Aprovar somente com gates satisfeitos. Pendências: '+(', '.join(gate['blockers']) or 'nenhuma'))
        db.add(decision)
    else:
        decision.status='pending'; decision.recommendation='Gates atuais: '+(', '.join(gate['blockers']) or 'prontos')
    audit(db,'decision.requested',release.product_id,release.id,principal=p); notify(db,release.product_id,f'Release {release.version} encaminhada à Mesa do CEO. {len(gate["blockers"])} bloqueios técnicos.'); db.commit(); return out(decision)

class DecisionInput(BaseModel):
    choice:str
    reason:str=Field(min_length=5,max_length=5000)

@router.get('/decisions')
def decisions(product_slug:str='nexgrana',p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug); ceo(p)
    return [out(d) for d in db.scalars(select(Decision).where(Decision.product_id==product.id).order_by(Decision.created_at.desc()).limit(100))]

@router.patch('/decisions/{decision_id}')
def decide(decision_id:str,data:DecisionInput,p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    row=item(db,Decision,decision_id,p); ceo(p)
    if data.choice not in {'approve','reject','changes','defer'}: raise HTTPException(422,'Escolha inválida')
    if row.status not in {'pending','defer','changes'}: raise HTTPException(409,'Decisão já encerrada; solicite nova revisão da release')
    release=db.get(Release,row.release_id) if row.release_id else None
    if data.choice=='approve' and release:
        gate=release_gate(db,release,verify_files=True)
        if not gate['ready']: raise HTTPException(409,{'message':'Aprovação bloqueada pelos gates','blockers':gate['blockers']})
        for older in db.scalars(select(Release).where(Release.product_id==release.product_id,Release.status=='stable')): older.status='superseded'
        release.status='stable'
    if release and data.choice in {'reject','changes'}: release.status='rejected' if data.choice=='reject' else 'changes_requested'
    row.status=data.choice; row.reason=data.reason
    audit(db,'decision.'+data.choice,row.product_id,row.id,data.reason,p); notify(db,row.product_id,f'Mafra decidiu {data.choice}: {row.title}. Motivo: {data.reason}')
    db.commit(); return out(row)

class TaskInput(BaseModel):
    status:str
    evidence_id:str|None=None
    steps:str=Field(default='',max_length=10000)
    expected:str=Field(default='',max_length=10000)

@router.patch('/missions/{task_id}')
def task_status(task_id:str,data:TaskInput,p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    task=item(db,Task,task_id,p); ceo(p)
    if data.status not in {'open','in_progress','review','done'}: raise HTTPException(422,'Status inválido')
    if data.status=='done':
        if not data.evidence_id or len(data.steps)<5 or len(data.expected)<5: raise HTTPException(422,'Encerrar exige evidência, passos de regressão e resultado esperado')
        evidence=item(db,Evidence,data.evidence_id,p)
        if not evidence_valid(evidence): raise HTTPException(409,'Evidencia ausente ou alterada; registre evidencia real novamente')
        if evidence.product_id!=task.product_id: raise HTTPException(422,'Evidência de outro projeto')
        case=db.scalar(select(RegressionCase).where(RegressionCase.task_id==task.id))
        if not case:
            case=RegressionCase(product_id=task.product_id,task_id=task.id,title=task.title,steps=data.steps,expected=data.expected,evidence_id=data.evidence_id); db.add(case)
        else: case.steps=data.steps; case.expected=data.expected; case.evidence_id=data.evidence_id
        if task.source_feedback_id: db.get(Feedback,task.source_feedback_id).status='resolved'
    elif task.source_feedback_id:
        feedback=db.get(Feedback,task.source_feedback_id)
        if feedback.status=='resolved': feedback.status='triaged'
    task.status=data.status; audit(db,'task.'+data.status,task.product_id,task.id,principal=p); db.commit(); return out(task)

class MessageInput(BaseModel):
    product_slug:str='nexgrana'
    body:str=Field(min_length=1,max_length=5000)
    kind:str='note'

@router.post('/messages',status_code=201)
def send_message(data:MessageInput,p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,data.product_slug); ceo(p)
    if data.kind not in {'note','mission'}: raise HTTPException(422,'Tipo de mensagem inválido')
    message=Message(product_id=product.id,sender=p.name,kind='human',body=data.body.strip()); db.add(message)
    if data.kind=='mission':
        temp=Feedback(title=data.body[:140],description=data.body,category='suggestion')
        _,priority,sector=classify_feedback(temp)
        task=Task(human_id=next_human_id(db,'TASK'),product_id=product.id,title=data.body[:180],description=data.body,owner_sector=sector,priority=priority)
        db.add(task); db.flush(); message.task_id=task.id
        notify(db,product.id,f'Pedido registrado como missão {task.human_id} em {sector}. A missão ainda não foi executada; acompanhe o resultado e as evidências.')
    elif data.body.strip().lower() in {'/resumo','resumo','status','/status'}:
        tasks=list(db.scalars(select(Task).where(Task.product_id==product.id)))
        decisions=db.scalar(select(func.count(Decision.id)).where(Decision.product_id==product.id,Decision.status=='pending')) or 0
        notify(db,product.id,f'Resumo real: {len(tasks)} missões; {sum(t.status=="done" for t in tasks)} encerradas com registro; {decisions} decisões pendentes. Consulte Releases para gates por versão.')
    else:
        tasks=list(db.scalars(select(Task).where(Task.product_id==product.id)))
        context={'project':product.slug,'tasks_registered':len(tasks),'tasks_done':sum(t.status=='done' for t in tasks),'app_tests_automated':False}
        reply=ai_advisor.advise(data.body,context)
        if reply:
            db.add(Message(product_id=product.id,sender='SIM · Analista IA' if reply['ok'] else 'SIM · Orquestrador',kind='ai' if reply['ok'] else 'automation',body=reply['text']))
            audit(db,'ai.advised' if reply['ok'] else 'ai.unavailable',product.id,reason='Consulta ao modelo local; nenhum comando executado.')
        else:
            notify(db,product.id,'Mensagem registrada no canal do CEO. Para abrir uma tarefa, selecione “Criar missão”; para consultar a operação, envie /resumo. Resposta por automação de regras, sem modelo de IA conectado.')
    audit(db,'message.sent',product.id,reason=data.kind,principal=p); db.commit(); return out(message)

@router.get('/messages')
def messages(product_slug:str='nexgrana',p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug)
    return [out(m) for m in db.scalars(select(Message).where(Message.product_id==product.id).order_by(Message.created_at.desc()).limit(100))][::-1]

@router.get('/regressions')
def regressions(product_slug:str='nexgrana',p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug)
    return [out(r) for r in db.scalars(select(RegressionCase).where(RegressionCase.product_id==product.id).order_by(RegressionCase.created_at.desc()).limit(200))]

@router.get('/daily')
def daily(product_slug:str='nexgrana',p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug)
    return [out(r) for r in db.scalars(select(DailyReport).where(DailyReport.product_id==product.id).order_by(DailyReport.day.desc()).limit(30))]

@router.get('/export')
def export(product_slug:str='nexgrana',p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug); ceo(p)
    models=[Feedback,Task,Release,Artifact,Evidence,TestRun,Decision,Message,RegressionCase,DailyReport]
    data={'schema':'sim-labs.operational-export/1.0','product':out(product),'generated_at':now().isoformat()}
    for model in models: data[model.__tablename__]=[out(r) for r in db.scalars(select(model).where(model.product_id==product.id))]
    return Response(dump(data),media_type='application/json',headers={'Content-Disposition':'attachment; filename=SIM_Labs_Operacao.json'})

@router.get('/company')
def company(product_slug:str='nexgrana',p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,product_slug)
    tasks=list(db.scalars(select(Task).where(Task.product_id==product.id)))
    definitions=[('operations','SIM · Orquestrador','Coordena fila, decisões e relatórios','queue,triage,daily','automatic'),('qa','SIM · QA','Inspeção de pacote, hashes, sintaxe e assets','archive,ast,hash,image_metadata','automatic'),('security','SIM · Security','Revisa escopo, integridade e achados; sem scanner ofensivo ativo','archive_safety,access_checks','rules'),('red_team','SIM · Red Team','Contesta gates e registra suspeitas; sem exploração automática ativa','gate_review,authorized_checks','rules'),('chaos_test','SIM · Chaos Test','Mantém cenários de recuperação QA; injeção de falhas está desativada','scenario_review','planned'),('analytics','SIM · Analista Sênior de Dados & Auditoria Operacional','Consolida apenas métricas registradas e questiona prioridades com evidência','daily_reports,task_counts,history','rules'),('release_manager','SIM · Build & Release','Controla gates e pré-flight; build real depende do host','artifact_intake,build_preflight','planned'),('performance','SIM · Performance','Registra baselines observados; sem benchmark de dispositivo nesta sessão','baseline_review','planned'),('ux','SIM · Experience','Consolida feedback e checklists de fluidez','inbox,manual_checks','manual'),('product','SIM · Product','Organiza missões e critérios de aceite','tasks,regression_cases','rules'),('engineering','SIM · Engineering','Preparação de patches prevista para runner isolado','none','planned'),('marketing','SIM · Growth','Aquisição e campanhas em fase futura','none','planned'),('business','SIM · Ofertas & Parcerias','Revisa fontes autorizadas e ofertas sem afirmar conversões','offers,authorization','rules')]
    agents=[]
    for sector,name,responsibility,tools,mode in definitions:
        owned=[t for t in tasks if t.owner_sector==sector]
        completed=sum(t.status=='done' for t in owned)
        agents.append({'name':name,'department':sector,'responsibility':responsibility,'tools':tools.split(','),'mode':mode,'autonomy':1 if mode=='automatic' else 0,'open_tasks':sum(t.status!='done' for t in owned),'completed_tasks':completed,'xp':completed*10,'level':1+completed//10,'activity':'disponível para automações' if mode=='automatic' else 'aguardando evidência / configuração','limits':'Sem publicar, alterar finanças ou executar código importado.'})
    return {'agents':agents,'team':[out(t) for t in db.scalars(select(TeamMember))],'sectors':[out(s) for s in db.scalars(select(Sector))],'tasks':[out(t) for t in tasks],'xp':sum(t.status=='done' for t in tasks)*10,'level':1+sum(t.status=='done' for t in tasks)//10,'ai_enabled':ai_advisor.status()['enabled'], 'ai':ai_advisor.status(),'capabilities':{'collector':True,'artifact_audit':True,'manual_homologation':True,'generative_ai':ai_advisor.status()['enabled'],'app_runner':False,'patch_generation':False,'remote_24h':False}}

class ConfigInput(BaseModel):
    description:str=Field(default='',max_length=5000)
    platforms:str=Field(default='Windows,Android',max_length=200)
    repository:str=Field(default='',max_length=1000)
    rules:dict=Field(default_factory=dict)

@router.get('/projects/{slug}/config')
def project_config(slug:str,p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,slug)
    row=db.get(ProjectConfig,product.id)
    stable=db.scalar(select(Release).where(Release.product_id==product.id,Release.status=='stable'))
    return {'product':out(product),'description':row.description if row else '', 'platforms':row.platforms if row else 'Windows,Android','repository':row.repository if row else '', 'rules':json.loads(row.rules_json) if row else {}, 'current_version':stable.version if stable else None}

@router.patch('/projects/{slug}/config')
def update_project_config(slug:str,data:ConfigInput,p:Principal=Depends(get_current_principal),db:Session=Depends(get_db)):
    product=scoped(db,p,slug);ceo(p)
    if len(dump(data.rules))>20000:raise HTTPException(422,'Regras excedem o limite')
    row=db.get(ProjectConfig,product.id)
    if not row:row=ProjectConfig(product_id=product.id);db.add(row)
    row.description=data.description;row.platforms=data.platforms;row.repository=data.repository;row.rules_json=dump(data.rules)
    audit(db,'project.configured',product.id,reason='Configuração declarativa; nenhuma regra executada como código.',principal=p);db.commit()
    return project_config(slug,p,db)
