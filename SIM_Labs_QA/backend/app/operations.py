from __future__ import annotations
import ast, hashlib, io, json, stat, time, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session
from .config import settings
from .models import Product, Feedback, Task, AuditEvent, now, uid
from .integration_models import Artifact, Release, Evidence, Receipt, TestRun, Decision, Message, Job, DailyReport, RegressionCase
from .liveops import next_human_id, triage_feedbacks
from .qa.artifact_core import inspect_build, _zip_safety, import_feedback_package, MANUAL_CHECKS, _read_zip_json

MAX_UPLOAD=450*1024*1024
MAX_EXPANDED=1024*1024*1024
MAX_SINGLE=200*1024*1024
MAX_RECORDS=1000

def dump(value): return json.dumps(value,ensure_ascii=False,default=str)
def audit(db,action,product_id,object_id=None,reason='',principal=None):
    db.add(AuditEvent(actor_member_id=principal.member_id if principal else None, actor_type='human' if principal else 'automation',action=action,object_type=action.split('.')[0],object_id=object_id,product_id=product_id,reason=reason))
def notify(db, product_id, body):
    db.add(Message(product_id=product_id,sender='SIM · Orquestrador',kind='automation',body=body))
def private_root():
    root=Path(settings.storage_dir).resolve(); root.mkdir(parents=True,exist_ok=True); return root

def store_bytes(data,filename):
    suffix=Path(filename).suffix.lower()[:12]
    dest=private_root()/(uid()+suffix)
    dest.write_bytes(data)
    return dest, hashlib.sha256(data).hexdigest()

def validate_archive(path):
    try:
        with zipfile.ZipFile(path) as z:
            checks,infos=_zip_safety(z)
            if any(x['status'] in {'FAIL','BLOCKED'} for x in checks): raise ValueError('ZIP inseguro, criptografado ou acima dos limites.')
            if sum(i.file_size for i in infos)>MAX_EXPANDED: raise ValueError('ZIP excede 1 GB descompactado.')
            names=set()
            for i in infos:
                key=i.filename.replace('\\','/')
                if key in names: raise ValueError('ZIP tem caminhos repetidos.')
                names.add(key)
                if ':' in key or i.file_size>MAX_SINGLE: raise ValueError('Caminho ou tamanho de entrada não permitido.')
    except zipfile.BadZipFile as exc: raise ValueError('Arquivo ZIP inválido.') from exc

def category_for(record):
    value=(str(record.get('category',''))+' '+str(record.get('kind',''))).lower()
    if 'seguran' in value: return 'security'
    if 'ux' in value: return 'ux'
    if 'performance' in value: return 'performance'
    if 'bug' in value or 'problema' in value: return 'bug'
    return 'improvement'

def ingest_records(db, product, records, release='', source='collector', archive=None, principal=None):
    if not isinstance(records,list) or len(records)>MAX_RECORDS: raise ValueError('Lista records inválida ou acima de 1000 itens.')
    ids=[]
    for r in records:
        if not isinstance(r,dict): raise ValueError('Cada feedback deve ser um objeto.')
        external=str(r.get('feedback_id') or r.get('id') or '').strip()
        if not external or len(external)>150 or external in ids: raise ValueError('IDs externos ausentes, repetidos ou longos.')
        ids.append(external)
        if not isinstance(r.get('evidence',[]),list): raise ValueError('evidence deve ser uma lista.')
        for name in ('title','description','expected','current','notes','solution'):
            if r.get(name) is not None and not isinstance(r[name],str): raise ValueError(f'{name} deve ser texto.')
            if len(r.get(name) or '')>20000: raise ValueError(f'{name} excede o limite.')
    created=updated=duplicates=attachments=0
    for r,external in zip(records,ids):
        canonical={k:v for k,v in r.items() if k not in {'evidence','imported_at','created_at','number','release'}}
        digest=hashlib.sha256(dump(canonical).encode()).hexdigest()
        receipt=db.scalar(select(Receipt).where(Receipt.product_id==product.id,Receipt.source==source,Receipt.external_id==external))
        if receipt:
            feedback=db.get(Feedback,receipt.feedback_id)
            if receipt.content_hash!=digest:
                receipt.content_hash=digest
                feedback.description=r.get('description') or feedback.description
                feedback.title=(r.get('title') or feedback.title)[:180]
                feedback.expected=r.get('expected') or feedback.expected
                feedback.observed=r.get('current') or feedback.observed
                if feedback.status in {'resolved','dismissed'}:
                    feedback.status='new'
                    task=db.scalar(select(Task).where(Task.source_feedback_id==feedback.id))
                    if task: task.status='open'
                else: feedback.status='new'
                task=db.scalar(select(Task).where(Task.source_feedback_id==feedback.id))
                if task:
                    task.title=f'Revisar {feedback.human_id}: {feedback.title}'[:180]
                    task.description=feedback.description
                updated+=1
                audit(db,'collector.updated',product.id,feedback.id,f'ID externo {external}',principal)
            else: duplicates+=1
        else:
            feedback=Feedback(human_id=next_human_id(db,'SIM'),product_id=product.id,created_by_member_id=principal.member_id if principal else None,category=category_for(r),title=(r.get('title') or 'Feedback sem título')[:180],description=r.get('description') or 'Sem descrição',expected=r.get('expected'),observed=r.get('current'),source=source)
            raw_priority=str(r.get('priority') or '')[:2]
            if raw_priority in {'P0','P1','P2','P3'}: feedback.priority=raw_priority
            db.add(feedback); db.flush()
            receipt=Receipt(product_id=product.id,source=source,external_id=external,feedback_id=feedback.id,release_version=str(release or '')[:80],platform=str(r.get('platform') or 'Multiplataforma')[:40],screen=str(r.get('screen') or '')[:160],content_hash=digest,metadata_json=dump(r))
            db.add(receipt); db.flush(); created+=1
            audit(db,'collector.imported',product.id,feedback.id,f'ID externo {external}',principal)
        if release: receipt.release_version=str(release)[:80]
        receipt.platform=str(r.get('platform') or receipt.platform)[:40]
        receipt.screen=str(r.get('screen') or receipt.screen)[:160]
        receipt.metadata_json=dump(r)
        if archive:
            for entry in r.get('evidence',[]):
                if not isinstance(entry,str): raise ValueError('Referência de evidência inválida.')
                # Paths are already archive-validated. Match only a unique suffix/root path.
                normalized=entry.replace('\\','/')
                candidates=[i for i in archive.infolist() if i.filename.replace('\\','/')==normalized or i.filename.replace('\\','/').endswith('/'+normalized)]
                if len(candidates)!=1: continue
                info=candidates[0]
                if info.is_dir() or info.file_size>MAX_SINGLE: continue
                content=archive.read(info); sha=hashlib.sha256(content).hexdigest()
                existing=db.scalar(select(Evidence).where(Evidence.feedback_id==feedback.id,Evidence.sha256==sha))
                if existing: continue
                filename=PurePosixPath(normalized).name[:200]
                path,_=store_bytes(content,filename)
                db.add(Evidence(product_id=product.id,feedback_id=feedback.id,filename=filename,path=str(path),sha256=sha,size_bytes=len(content)))
                attachments+=1
    db.flush()
    notify(db,product.id,f'Collector recebido: {created} novos, {updated} atualizados, {duplicates} reenvios reconhecidos; {attachments} evidências. Triagem automática por regras na próxima rodada.')
    db.commit()
    return {'created':created,'updated':updated,'duplicates':duplicates,'attachments':attachments,'external_ids':ids}

def import_package(db,product,path,principal=None):
    validate_archive(path)
    with zipfile.ZipFile(path) as validation_archive:
        _, raw_ingest=_read_zip_json(validation_archive,validation_archive.infolist(),'SIM_LABS_INGEST.json')
        if raw_ingest and raw_ingest.get('schema') not in {None,'sim-labs.feedback-ingest/1.0'}:
            raise ValueError('Schema de ingestão não suportado.')
    package=import_feedback_package(path)
    if not isinstance(package.get('release'),(str,type(None))): raise ValueError('Versão do pacote deve ser texto.')
    with zipfile.ZipFile(path) as archive:
        return ingest_records(db,product,package['records'],package.get('release'),archive=archive,principal=principal)

def manifest_and_checks(path):
    manifest={}; syntax=[]; assets=[]
    if Path(path).suffix.lower() not in {'.zip','.apk','.aab','.msix','.appx'}: return manifest,syntax,assets
    validate_archive(path)
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir(): continue
            name=info.filename.replace('\\','/')
            digest=hashlib.sha256()
            with archive.open(info) as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
            manifest[name]={'sha256':digest.hexdigest(),'size':info.file_size}
            if name.lower().endswith('.py') and info.file_size<8*1024*1024:
                try: ast.parse(archive.read(info).decode('utf-8-sig'),filename=name)
                except (SyntaxError,UnicodeDecodeError) as exc:
                    syntax.append({'file':name,'line':getattr(exc,'lineno',None),'error':type(exc).__name__})
            if name.lower().endswith(('.png','.jpg','.webp','.gif')) and info.file_size<16*1024*1024:
                try:
                    from PIL import Image
                    with Image.open(io.BytesIO(archive.read(info))) as image:
                        assets.append({'file':name,'width':image.width,'height':image.height,'mode':image.mode,'frames':getattr(image,'n_frames',1)})
                        image.verify()
                except Exception as exc:
                    assets.append({'file':name,'error':type(exc).__name__})
    return manifest,syntax,assets

def compare_manifests(previous,current):
    # Ignore wrapper folder differences; collisions keep original keys.
    def norm(entries):
        keys=list(entries)
        if keys and all('/' in k for k in keys) and len({k.split('/')[0] for k in keys})==1:
            return {k.split('/',1)[1]:v for k,v in entries.items()}
        return entries
    previous,current=norm(previous),norm(current)
    added=sorted(set(current)-set(previous)); removed=sorted(set(previous)-set(current))
    changed=sorted(k for k in set(previous)&set(current) if previous[k]['sha256']!=current[k]['sha256'])
    all_changed=added+removed+changed
    focus=[]
    for label,terms in [('Chat / teclado',['chat','conversation']),('Banco / persistência',['migration','sql','ledger','finance']),('Login / privacidade',['auth','login','privacy','vault']),('Assets / Nex',['asset','skin','.png','.gif']),('UX / navegação',['ui','screen','layout'])]:
        if any(any(term in p.lower() for term in terms) for p in all_changed): focus.append(label)
    return {'added':added,'removed':removed,'changed':changed,'focus':focus,'baseline_available':bool(previous)}

def inspect_artifact(db,artifact):
    path=Path(artifact.path)
    validate_archive(path) if path.suffix.lower() in {'.zip','.apk','.aab','.msix','.appx'} else None
    report=inspect_build(path,artifact.platform)
    manifest,syntax,assets=manifest_and_checks(path)
    if manifest:
        report['checks'].append({'id':'python_ast','label':'Sintaxe Python (sem executar código)','status':'FAIL' if syntax else 'PASS','detail':f'{sum(k.endswith(".py") for k in manifest)} arquivos; {len(syntax)} erros.'})
    report['syntax_errors']=syntax; report['assets']=assets
    release=db.get(Release,artifact.release_id)
    if report.get('version') and report['version']!=release.version:
        report['checks'].append({'id':'version_label','label':'Versão detectada versus rótulo da candidata','status':'WARN','detail':'Pacote: '+str(report['version'])+'; candidata: '+release.version+'. Confira se o rótulo é RC/build ou versão do produto.'})
    previous=db.scalar(select(Artifact).join(Release,Release.id==Artifact.release_id).where(Release.status=='stable',Artifact.product_id==artifact.product_id,Artifact.platform==artifact.platform,Artifact.id!=artifact.id,Artifact.manifest_json!='{}').order_by(Artifact.created_at.desc()))
    report['comparison']=compare_manifests(json.loads(previous.manifest_json) if previous else {},manifest)
    report['baseline_artifact_id']=previous.id if previous else None
    report['name']=artifact.filename
    report.pop('path',None)
    report['checks'].append({'id':'app_journey','label':'Fluxos reais Windows / Android','status':'BLOCKED','detail':'A inspeção não instala nem abre o app. Registre a homologação manual com evidência.'})
    report['overall']='FAIL' if any(c['status']=='FAIL' for c in report['checks']) else 'BLOCKED'
    artifact.report_json=dump(report); artifact.manifest_json=dump(manifest); artifact.status=report['overall'].lower()
    db.add(TestRun(product_id=artifact.product_id,release_id=artifact.release_id,artifact_id=artifact.id,kind='structural',status=artifact.status,result_json=dump(report)))
    audit(db,'artifact.inspected',artifact.product_id,artifact.id,f'Inspeção {report["overall"]}; não é homologação do aplicativo.')
    if report['overall']=='FAIL':
        task=Task(human_id=next_human_id(db,'TASK'),product_id=artifact.product_id,title=f'Auditoria falhou: {artifact.filename}'[:180],description=dump([c for c in report['checks'] if c['status']=='FAIL']),owner_sector='qa',priority='P1',status='open')
        db.add(task)
    notify(db,artifact.product_id,f'Auditoria de {artifact.filename}: {report["overall"]}. Veja a release para resultados, diferenças e itens de validação manual.')
    db.commit()

CHECKS=[{'id':key,'label':label} for key,label in MANUAL_CHECKS]

def evidence_valid(row):
    if row is None: return False
    try:
        path=Path(row.path).resolve(); path.relative_to(private_root())
        h=hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
        return h.hexdigest()==row.sha256
    except (OSError,ValueError): return False

def release_gate(db,release,verify_files=False):
    artifacts=list(db.scalars(select(Artifact).where(Artifact.release_id==release.id)))
    manual=list(db.scalars(select(TestRun).where(TestRun.release_id==release.id,TestRun.kind=='manual').order_by(TestRun.created_at)))
    latest={}
    for run in manual:
        data=json.loads(run.result_json); latest[(data.get('platform'),data.get('check_id'))]=data
    required=[]
    for platform in ('Windows','Android'):
        keys=[c['id'] for c in CHECKS if not (c['id'].startswith('windows_') and platform!='Windows') and not (c['id'].startswith('android_') and platform!='Android')]
        for key in keys:
            check=latest.get((platform,key))
            if not check or check.get('status')!='PASS' or not check.get('evidence_id'): required.append(platform+':'+key)
    blockers=[]
    if verify_files:
        ids={data.get('evidence_id') for data in latest.values() if data.get('status')=='PASS'}
        if any(not evidence_valid(db.get(Evidence,id)) for id in ids): blockers.append('Evidencia ausente ou hash divergente')
        if any(not evidence_valid(a) for a in artifacts): blockers.append('Build ausente ou hash divergente')
    if not any(a.platform=='Windows' and Path(a.filename).suffix.lower() in {'.exe','.msi','.msix','.appx'} for a in artifacts): blockers.append('Build instalável Windows ausente')
    if not any(a.platform=='Android' and Path(a.filename).suffix.lower()=='.apk' for a in artifacts): blockers.append('APK Android ausente')
    if not artifacts or any(a.status in {'queued','running','failed','fail'} for a in artifacts): blockers.append('Auditoria ausente, em andamento ou com falha')
    if required: blockers.append(f'{len(required)} validações manuais pendentes ou sem evidência')
    open_critical=db.scalar(select(func.count(Task.id)).where(Task.product_id==release.product_id,Task.priority.in_(['P0','P1']),Task.status!='done')) or 0
    if open_critical: blockers.append(f'{open_critical} tarefas P0/P1 abertas no projeto')
    return {'ready':not blockers,'blockers':blockers,'pending_checks':required}

def daily_report(db,product):
    from zoneinfo import ZoneInfo
    local=datetime.now(ZoneInfo('America/Sao_Paulo'))
    day=local.date().isoformat()
    begin=local.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
    end=(local.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)).astimezone(timezone.utc)
    report=db.scalar(select(DailyReport).where(DailyReport.product_id==product.id,DailyReport.day==day))
    if report and (now()-report.created_at.replace(tzinfo=timezone.utc)).total_seconds()<60: return report
    counts={}
    for name,model in [('feedbacks_received',Feedback),('missions_created',Task),('artifacts_received',Artifact),('test_runs_registered',TestRun),('decisions_created',Decision)]:
        counts[name]=db.scalar(select(func.count(model.id)).where(model.product_id==product.id,model.created_at>=begin,model.created_at<end)) or 0
    runs=list(db.scalars(select(TestRun).where(TestRun.product_id==product.id,TestRun.created_at>=begin,TestRun.created_at<end)))
    counts['missions_done_updated_today']=db.scalar(select(func.count(Task.id)).where(Task.product_id==product.id,Task.status=='done',Task.updated_at>=begin,Task.updated_at<end)) or 0
    counts['critical_open']=db.scalar(select(func.count(Task.id)).where(Task.product_id==product.id,Task.status!='done',Task.priority.in_(['P0','P1']))) or 0
    lines=[f'# SIM Labs Daily — {product.name}',f'Data: {day} · janela do dia em America/Sao_Paulo.',*[f'- {k}: {v}' for k,v in counts.items()],f'- Resultados registrados hoje: PASS={sum(r.status in ("passed","pass","PASS") for r in runs)}, FAIL={sum(r.status in ("failed","fail","FAIL") for r in runs)}, BLOCKED={sum(r.status in ("blocked","BLOCKED") for r in runs)}', '- Missoes encerradas: contadas pelo estado done e ultima atualizacao no dia; detalhes no historico.', '- Inspecao estrutural nao equivale a homologacao do app; somente evidencias registradas sustentam resultados.', '- Nenhuma correcao de fonte, ganho de desempenho ou melhoria estetica e presumida.']
    if report: report.body='\n'.join(lines)
    else:
        report=DailyReport(product_id=product.id,day=day,body='\n'.join(lines)); db.add(report)
        notify(db,product.id,'Relatorio diario disponivel com contagem do dia e resultados registrados.')
        audit(db,'daily.generated',product.id,reason=day)
    db.commit(); return report

def cycle(db):
    # Single leader lease is acquired by worker; transactional claims survive crashes.
    triaged=triage_feedbacks(db)
    stamp=now()
    db.execute(update(Job).where(Job.status=='running',Job.lease_until<stamp,Job.attempts<3).values(status='queued',lease_until=None))
    db.execute(update(Job).where(Job.status=='running',Job.lease_until<stamp,Job.attempts>=3).values(status='failed',error='Limite de recuperação após interrupções'))
    db.commit()
    job=db.scalar(select(Job).where(Job.status=='queued').order_by(Job.created_at).limit(1))
    if job:
        claimed=db.execute(update(Job).where(Job.id==job.id,Job.status=='queued').values(status='running',attempts=Job.attempts+1,lease_until=stamp+timedelta(seconds=230)))
        db.commit()
        if claimed.rowcount:
            db.refresh(job)
            artifact=db.get(Artifact,job.artifact_id)
            try:
                artifact.status='running'; db.commit()
                inspect_artifact(db,artifact)
                job.status='completed'; job.error=''
            except Exception as exc:
                db.rollback(); job=db.get(Job,job.id); artifact=db.get(Artifact,job.artifact_id)
                job.status='failed'; job.error=type(exc).__name__+': '+str(exc)[:300]
                artifact.status='failed'
                artifact.report_json=dump({'overall':'FAIL','checks':[{'id':'inspection','label':'Inspeção','status':'FAIL','detail':job.error}]})
                db.add(TestRun(product_id=artifact.product_id,release_id=artifact.release_id,artifact_id=artifact.id,kind='structural',status='failed',result_json=artifact.report_json))
                audit(db,'artifact.failed',artifact.product_id,artifact.id,job.error)
                notify(db,artifact.product_id,'Inspeção bloqueada: '+job.error)
            job.lease_until=None; db.commit()
    for product in db.scalars(select(Product).where(Product.status=='active')): daily_report(db,product)
    return triaged
