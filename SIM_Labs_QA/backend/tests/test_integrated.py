import io, json, zipfile
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Feedback, Task
from app.integration_models import Artifact, Evidence, Receipt, Job, Release
from app.operations import cycle, compare_manifests
from app.local_auth import hash_password
from app.config import settings

def h(name='Mafra'): return {'X-Dev-Actor':name}
def release(c,version='TEST DATA 0.3'):
    r=c.post('/api/v1/releases',headers=h(),json={'version':version}); assert r.status_code==201,r.text;return r.json()
def archive(entries):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        for k,v in entries.items(): z.writestr(k,v)
    return stream.getvalue()
def package(description='TEST DATA: Chat perde foco',evidence='print.txt'):
    records=[{'feedback_id':'TEST-DATA-FB-1','title':'TEST DATA: chat','kind':'Bug / Feedback','category':'UX/UI','description':description,'expected':'Manter teclado e histórico','evidence':['evidencias/'+evidence],'platform':'Android','screen':'Chat'}]
    return archive({'SIM_LABS_INGEST.json':json.dumps({'release':'TEST DATA 0.3','records':records}),'evidencias/'+evidence:'TEST DATA: transporte; não é screenshot real. '+evidence})
def import_it(c,data): return c.post('/api/v1/collector/package',headers=h(),files={'file':('collector.zip',data,'application/zip')})
def evidence(c,rel=''):
    r=c.post('/api/v1/evidence',headers=h(),data={'release_id':rel},files={'file':('TEST_DATA.txt',b'TEST DATA manual evidence','text/plain')});assert r.status_code==201,r.text;return r.json()
def build(c,rel,data,name='source.zip',platform='Fonte'):
    return c.post(f'/api/v1/releases/{rel["id"]}/artifacts',headers=h(),data={'platform':platform},files={'file':(name,data,'application/octet-stream')})

def test_local_login_default_actor_guard(client,monkeypatch):
    monkeypatch.setitem(settings.__dict__,'allow_dev_actors',False)
    monkeypatch.setitem(settings.__dict__,'local_admin_password_hash',hash_password('TEST_DATA_password'))
    assert client.get('/api/v1/products',headers=h()).status_code==401
    assert client.post('/api/v1/auth/login',json={'password':'bad'}).status_code==401
    r=client.post('/api/v1/auth/login',json={'password':'TEST_DATA_password'}); assert r.status_code==200,r.text
    assert client.get('/api/v1/products',headers={'Authorization':'Bearer '+r.json()['token']}).status_code==200

def test_import_ids_evidence_and_dedup(client):
    r=import_it(client,package());assert r.status_code==200,r.text
    assert r.json()['created']==1 and r.json()['attachments']==1
    assert import_it(client,package()).json()['duplicates']==1
    with SessionLocal() as db:
        cycle(db);cycle(db)
        assert len(list(db.scalars(select(Feedback))))==1
        assert len(list(db.scalars(select(Task))))==1
        assert len(list(db.scalars(select(Evidence))))==1
        assert db.scalar(select(Receipt)).external_id=='TEST-DATA-FB-1'
    f=client.get('/api/v1/inbox',headers=h()).json()[0]
    assert f['external_id']=='TEST-DATA-FB-1'
    ev=f['evidence'][0]; assert 'path' not in ev
    assert client.get(f'/api/v1/evidence/{ev["id"]}/download').status_code==401
    assert b'TEST DATA' in client.get(f'/api/v1/evidence/{ev["id"]}/download',headers=h()).content

def test_updates_keep_task_identity(client):
    import_it(client,package())
    with SessionLocal() as db: cycle(db);task_id=db.scalar(select(Task)).id
    r=import_it(client,package('TEST DATA nova descrição'));assert r.json()['updated']==1
    with SessionLocal() as db:
        cycle(db); assert db.scalar(select(Task)).id==task_id
        assert 'nova descrição' in db.scalar(select(Task)).description

def test_parts_merge_attachments(client):
    import_it(client,package());r=import_it(client,package(evidence='second.txt'))
    assert r.json()['duplicates']==1 and r.json()['attachments']==1
    with SessionLocal() as db: assert len(list(db.scalars(select(Evidence))))==2

def test_zip_traversal_rejected(client):
    bad=archive({'../outside.txt':'bad','SIM_LABS_INGEST.json':json.dumps({'records':[]})})
    assert import_it(client,bad).status_code==422

def test_duplicate_archive_path_rejected(client):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z: z.writestr('SIM_LABS_INGEST.json','{}');z.writestr('SIM_LABS_INGEST.json','{}')
    assert import_it(client,b.getvalue()).status_code==422

def test_invalid_field_type_not_persisted(client):
    bad=archive({'SIM_LABS_INGEST.json':json.dumps({'records':[{'feedback_id':'X','description':42}]})})
    assert import_it(client,bad).status_code==422
    with SessionLocal() as db: assert db.scalar(select(Feedback)) is None

def test_queue_audit_never_executes_code(client,tmp_path):
    rel=release(client);marker=tmp_path/'must_not_exist'
    data=archive({'project/main.py':f'open({str(marker)!r},"w").write("executed")','project/pyproject.toml':'version="0.1"'})
    r=build(client,rel,data);assert r.status_code==201,r.text
    with SessionLocal() as db:
        cycle(db);a=db.scalar(select(Artifact));job=db.scalar(select(Job))
        assert job.status=='completed';assert a.status=='blocked'
        assert json.loads(a.report_json)['comparison']['baseline_available'] is False
    assert not marker.exists()

def test_syntax_failure_opens_task(client):
    rel=release(client);build(client,rel,archive({'bad.py':'def broken('}))
    with SessionLocal() as db:
        cycle(db);assert db.scalar(select(Artifact)).status=='fail';assert db.scalar(select(Task)).priority=='P1'

def test_repeated_build_upload(client):
    rel=release(client);data=archive({'main.py':'print("TEST DATA")'})
    a=build(client,rel,data).json();b=build(client,rel,data).json()
    assert a['id']==b['id'] and b['duplicate']

def test_channel_summary_and_mission(client):
    assert client.post('/api/v1/messages',headers=h(),json={'body':'/resumo'}).status_code==201
    assert client.post('/api/v1/messages',headers=h(),json={'body':'TEST DATA: revisar navegação','kind':'mission'}).status_code==201
    messages=client.get('/api/v1/messages',headers=h()).json()
    assert len(messages)==4;assert any('Resumo real' in m['body'] for m in messages);assert any(m['task_id'] for m in messages)

def test_decision_gate_blocks_unverified(client):
    rel=release(client);r=client.post(f'/api/v1/releases/{rel["id"]}/request-decision',headers=h());assert r.status_code==200,r.text
    d=r.json()
    assert client.patch(f'/api/v1/decisions/{d["id"]}',headers=h(),json={'choice':'approve','reason':'TEST DATA approval'}).status_code==409
    assert client.patch(f'/api/v1/decisions/{d["id"]}',headers=h(),json={'choice':'changes','reason':'TEST DATA falta evidência'}).status_code==200
    with SessionLocal() as db: assert db.get(Release,rel['id']).status=='changes_requested'

def test_manual_pass_requires_release_evidence(client):
    rel=release(client);payload={'platform':'Android','check_id':'android_chat_keyboard','status':'PASS','note':'TEST DATA cenário'}
    assert client.post(f'/api/v1/releases/{rel["id"]}/manual-checks',headers=h(),json=payload).status_code==422
    ev=evidence(client,rel['id']);payload['evidence_id']=ev['id']
    assert client.post(f'/api/v1/releases/{rel["id"]}/manual-checks',headers=h(),json=payload).status_code==200
    other=release(client,'TEST DATA outra')
    assert client.post(f'/api/v1/releases/{other["id"]}/manual-checks',headers=h(),json=payload).status_code==422

def test_closure_requires_regression_and_evidence(client):
    client.post('/api/v1/messages',headers=h(),json={'body':'TEST DATA corrigir navegação','kind':'mission'})
    t=client.get('/api/v1/tasks',headers=h()).json()[0]
    assert client.patch(f'/api/v1/missions/{t["id"]}',headers=h(),json={'status':'done'}).status_code==422
    ev=evidence(client);body={'status':'done','evidence_id':ev['id'],'steps':'TEST DATA abrir e navegar','expected':'TEST DATA conteúdo consistente'}
    assert client.patch(f'/api/v1/missions/{t["id"]}',headers=h(),json=body).status_code==200
    assert client.get('/api/v1/company',headers=h()).json()['xp']==10
    client.patch(f'/api/v1/missions/{t["id"]}',headers=h(),json=body)
    assert len(client.get('/api/v1/regressions',headers=h()).json())==1

def test_daily_report_once(client):
    with SessionLocal() as db: cycle(db);cycle(db)
    assert len(client.get('/api/v1/daily',headers=h()).json())==1

def test_diff_hashes_wrapper_and_focus():
    diff=compare_manifests({'old/src/chat.py':{'sha256':'1'},'old/x.txt':{'sha256':'2'}},{'new/src/chat.py':{'sha256':'3'},'new/y.txt':{'sha256':'4'}})
    assert diff['changed']==['src/chat.py'];assert diff['added']==['y.txt'];assert diff['removed']==['x.txt'];assert 'Chat / teclado' in diff['focus']

def test_scope_and_ceo(client):
    for path in ('releases','messages','inbox','evidence','company','test-runs','regressions','daily'):
        assert client.get('/api/v1/'+path).status_code==401
        assert client.get('/api/v1/'+path+'?product_slug=secret',headers=h('Karol')).status_code==404
    assert client.post('/api/v1/messages',headers=h('Karol'),json={'body':'test'}).status_code==403
    assert client.post('/api/v1/releases',headers=h('Karol'),json={'version':'test'}).status_code==403

def test_ingest_token_product_scope(client):
    body={'release':'TEST','records':[{'feedback_id':'X','title':'TEST DATA','description':'test'}]}
    assert client.post('/api/v1/collector/ingest',json=body).status_code==401
    headers={'X-SIM-Ingest-Token':'TEST_DATA_INGEST'}
    r=client.post('/api/v1/collector/ingest',headers=headers,json=body);assert r.status_code==200,r.text
    body['product_slug']='sim-labs-control-center'
    assert client.post('/api/v1/collector/ingest',headers=headers,json=body).status_code==403

def test_export_hides_paths(client):
    evidence(client);data=client.get('/api/v1/export',headers=h()).json()
    assert data['schema']=='sim-labs.operational-export/1.0';assert 'path' not in data['evidence'][0]

def test_leader_lease(client,monkeypatch):
    from app import worker
    with SessionLocal() as db: assert worker.acquire(db)
    monkeypatch.setattr(worker,'OWNER','TEST-DATA-SECOND-WORKER')
    with SessionLocal() as db: assert not worker.acquire(db)

def test_project_config_is_persisted_and_scoped(client):
    body={'description':'TEST DATA projeto','platforms':'Windows,Android','repository':'TEST DATA reference','rules':{'qa_only':True}}
    r=client.patch('/api/v1/projects/nexgrana/config',headers=h(),json=body)
    assert r.status_code==200,r.text
    assert client.get('/api/v1/projects/nexgrana/config',headers=h()).json()['rules']=={'qa_only':True}
    assert client.patch('/api/v1/projects/nexgrana/config',headers=h('Karol'),json=body).status_code==403

def test_complete_testdata_gate_promotes_stable_and_locks_upload(client):
    from app.integration_models import TestRun
    from app.operations import CHECKS, dump
    rel=release(client,'TEST DATA gate fixture')
    ev=evidence(client,rel['id'])
    with SessionLocal() as db:
        row=db.get(Release,rel['id'])
        # Fixtures verify the decision contract, not Windows/Android execution.
        for platform,filename in (('Windows','TEST_DATA.exe'),('Android','TEST_DATA.apk')):
            from app.operations import store_bytes
            data_bytes=('TEST DATA '+platform+' gate fixture, not an executable app').encode()
            path,sha=store_bytes(data_bytes,filename)
            db.add(Artifact(product_id=row.product_id,release_id=row.id,filename=filename,platform=platform,path=str(path),sha256=sha,size_bytes=len(data_bytes),status='blocked'))
            for check in CHECKS:
                if check['id'].startswith('windows_') and platform!='Windows' or check['id'].startswith('android_') and platform!='Android':continue
                data={'platform':platform,'check_id':check['id'],'status':'PASS','note':'TEST DATA fixture only; no device was tested','evidence_id':ev['id']}
                db.add(TestRun(product_id=row.product_id,release_id=row.id,kind='manual',status='pass',result_json=dump(data)))
        db.commit()
    d=client.post(f'/api/v1/releases/{rel["id"]}/request-decision',headers=h()).json()
    r=client.patch(f'/api/v1/decisions/{d["id"]}',headers=h(),json={'choice':'approve','reason':'TEST DATA gate contract only'})
    assert r.status_code==200,r.text
    assert client.get('/api/v1/releases',headers=h()).json()[0]['status']=='stable'
    assert build(client,rel,archive({'x.py':'pass'})).status_code==409

def test_full_backup_contains_database_and_evidence(tmp_path,monkeypatch):
    import sqlite3,zipfile
    from app import backup_local
    (tmp_path/'backend').mkdir();(tmp_path/'data'/'private').mkdir(parents=True)
    with sqlite3.connect(tmp_path/'backend'/'sim_labs.db') as db:
        db.execute('CREATE TABLE testdata(value TEXT)');db.execute("INSERT INTO testdata VALUES('TEST DATA persisted')")
    (tmp_path/'data'/'private'/'TEST_DATA.txt').write_text('TEST DATA file')
    (tmp_path/'.env').write_text('TEST_DATA_CONFIG=1')
    monkeypatch.setattr(backup_local,'ROOT',tmp_path);backup_local.main()
    backups=list((tmp_path/'backups').glob('*.zip'));assert len(backups)==1
    with zipfile.ZipFile(backups[0]) as z:
        assert {'backend/sim_labs.db','data/private/TEST_DATA.txt','.env'}<=set(z.namelist())
        assert z.read('data/private/TEST_DATA.txt')==b'TEST DATA file'
