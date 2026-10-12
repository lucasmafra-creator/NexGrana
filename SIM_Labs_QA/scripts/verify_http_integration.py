"""End-to-end HTTP probe on disposable TEST DATA database and port 8765."""
import os,sys,tempfile,time,subprocess,json,hashlib,io,zipfile,re
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.local_auth import hash_password
import httpx

def main():
 with tempfile.TemporaryDirectory(prefix='simlabs_e2e_') as folder:
  temp=Path(folder)
  ingest='TEST_DATA_PRIVATE_INGEST_TOKEN'
  env={**os.environ,'APP_ENV':'test','ALLOW_DEV_ACTORS':'0','AUTO_INIT_DB':'0','DATABASE_URL':'sqlite:///'+str(temp/'qa.db'),'STORAGE_DIR':str(temp/'private'),'LOCAL_ADMIN_PASSWORD_HASH':hash_password('TEST_DATA_HTTP_PASSWORD'),'SESSION_SIGNING_KEY':'TEST_DATA_SESSION_SIGNING_KEY_64_chars_abcdefghijklmnopqrstuvwxyz123','FEEDBACK_INGEST_TOKEN':ingest,'INGEST_PRODUCT_SLUG':'nexgrana'}
  for command in ([sys.executable,'-m','alembic','upgrade','head'],[sys.executable,'-m','app.seed']):
   subprocess.run(command,cwd=ROOT/'backend',env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  with (temp/'api.log').open('w') as log:
   api=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
   worker=subprocess.Popen([sys.executable,'-m','app.worker'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
   engine=subprocess.Popen([sys.executable,'-m','app.engine'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
   try:
    base='http://127.0.0.1:8765/api/v1'
    with httpx.Client(timeout=15,trust_env=False) as c:
     for _ in range(50):
      try:
       if c.get(base+'/health').status_code==200:break
      except httpx.ConnectError:pass
      time.sleep(.1)
     else:raise AssertionError('API did not start')
     html=c.get('http://127.0.0.1:8765/');assert html.status_code==200
     asset=re.search(r'src="([^"]+[.]js)"',html.text).group(1)
     js=c.get('http://127.0.0.1:8765'+asset).content
     assert b'promotion-catalog' in js and b'promotion-sources' in js # updated compiled panel is served
     assert c.get(base+'/products',headers={'X-Dev-Actor':'Mafra'}).status_code==401
     login=c.post(base+'/auth/login',json={'password':'TEST_DATA_HTTP_PASSWORD'});assert login.status_code==200,login.text
     headers={'Authorization':'Bearer '+login.json()['token']}
     rel=c.post(base+'/releases',headers=headers,json={'version':'TEST DATA HTTP'});assert rel.status_code==201,rel.text
     rel=rel.json()
     sys.path.insert(0,str(ROOT/'Collector'/'src'))
     from sim_labs_bridge import send_snapshot
     os.environ['SIM_LABS_URL']=base;os.environ['SIM_LABS_INGEST_TOKEN']=ingest
     attachment=temp/'TEST_DATA.txt';attachment.write_text('TEST DATA actual HTTP evidence transport')
     snapshot=[{'id':'TEST_DATA_HTTP_FB','title':'TEST DATA Android chat','category':'UX/UI','kind':'Bug / Feedback','description':'TEST DATA teclado perde foco','platform':'Android','attachments':[str(attachment)]}]
     result=send_snapshot(snapshot,'TEST DATA HTTP');assert result['created']==1 and result['attachments']==1,result
     result=send_snapshot(snapshot,'TEST DATA HTTP');assert result['duplicates']==1 and result['attachments']==0,result
     source=io.BytesIO()
     with zipfile.ZipFile(source,'w') as z:z.writestr('main.py','print("TEST DATA never executed")')
     upload=c.post(base+f'/releases/{rel["id"]}/artifacts',headers=headers,data={'platform':'Fonte'},files={'file':('TEST_DATA.zip',source.getvalue(),'application/zip')});assert upload.status_code==201,upload.text
     for _ in range(60):
      releases=c.get(base+'/releases',headers=headers).json()
      tasks=c.get(base+'/tasks',headers=headers).json()
      if releases[0]['artifacts'][0]['status']=='blocked' and tasks:break
      time.sleep(.2)
     else:raise AssertionError('worker did not inspect/triage')
     assert len(tasks)==1
     inbox=c.get(base+'/inbox',headers=headers).json()[0]
     assert inbox['external_id']=='TEST_DATA_HTTP_FB' and len(inbox['evidence'])==1
     ev=inbox['evidence'][0]
     assert c.get(base+f'/evidence/{ev["id"]}/download',headers=headers).content==attachment.read_bytes()
     msg=c.post(base+'/messages',headers=headers,json={'body':'/resumo'});assert msg.status_code==201
     assert any('Resumo real' in m['body'] for m in c.get(base+'/messages',headers=headers).json())
     decision=c.post(base+f'/releases/{rel["id"]}/request-decision',headers=headers).json()
     assert c.patch(base+f'/decisions/{decision["id"]}',headers=headers,json={'choice':'approve','reason':'TEST DATA not homologated'}).status_code==409
     queued=c.post(base+'/engine/run',headers=headers,json={'worker':'qa'});assert queued.status_code==201,queued.text
     target=queued.json()['id']
     for _ in range(100):
      state=c.get(base+'/engine',headers=headers).json()
      job=next((j for j in state['jobs'] if j['id']==target),None)
      if job and job['status']=='completed':break
      time.sleep(.2)
     else:
      log.flush(); print((temp/'api.log').read_text());print(json.dumps(state,default=str));raise AssertionError('Isolated engine did not complete report')
     assert c.get(base+'/evidence/'+job['evidence_id']+'/download',headers=headers).status_code==200
     # Commercial flow uses synthetic records, real local HTTP and real Engine process.
     at=datetime.now(timezone.utc)
     offer=c.post(base+'/promotion-offers',headers=headers,json={'approved_hosts':['www.partner.com.br'],'payload':{'title':'TEST DATA Rice','provider':'TEST DATA Partner','url':'https://www.partner.com.br/rice','price':12.9,'verified_at':at.isoformat(),'expires_at':(at+timedelta(hours=1)).isoformat(),'availability':'in_stock','affiliate':False}})
     assert offer.status_code==201,offer.text
     row=offer.json();assert c.get(base+'/promotion-catalog',headers=headers).json()['offers'][0]['enabled'] is False
     approved=c.post(base+'/promotion-offers/'+row['id']+'/review',headers=headers,json={'action':'approve','revision':row['revision']});assert approved.status_code==200
     env_preview={**env,'SIM_PROMO_BRIDGE_SESSION':login.json()['token']}
     preview=subprocess.run([sys.executable,str(ROOT/'scripts/publish_offer_catalog.py'),'--endpoint',base,'--output',str(temp/'catalog.json'),'--report',str(temp/'preview.json')],env=env_preview,capture_output=True,text=True,timeout=20)
     assert preview.returncode==0,preview.stdout+preview.stderr
     assert json.loads((temp/'preview.json').read_text())['status']=='PREVIEW'
     assert json.loads((temp/'catalog.json').read_text())['offers'][0]['enabled'] is True
     paused=c.post(base+'/promotion-offers/'+row['id']+'/review',headers=headers,json={'action':'pause','revision':approved.json()['revision']});assert paused.status_code==200
     assert c.get(base+'/promotion-catalog',headers=headers).json()['offers'][0]['enabled'] is False
     src=c.post(base+'/promotion-sources',headers=headers,json={'name':'TEST DATA missing credentials','kind':'awin_jsonl','url':'https://api.awin.com/publishers/123/awinfeeds/download/456-retail-pt_BR.jsonl','token_env':'SIM_PROMO_ABSENT_TEST_TOKEN','approved_hosts':['www.partner.com.br'],'authorization_note':'TEST DATA synthetic fixture only; no live permission','enabled':True})
     assert src.status_code==201,src.text
     for _ in range(100):
      commercial=c.get(base+'/promotions',headers=headers).json()
      if commercial['runs']:break
      time.sleep(.2)
     else:
      log.flush();print((temp/'api.log').read_text());print(json.dumps(c.get(base+'/engine',headers=headers).json(),default=str));raise AssertionError('Promotion Engine did not report missing credentials')
     assert commercial['runs'][0]['status']=='EXTERNAL_BLOCKER';assert len(commercial['offers'])==1
     print('PROMOTIONS HTTP PASS: authenticated draft/approve/pause/catalog, CLI preview, real Engine credential blocker. No external feed or Supabase publication performed.')
     assert c.patch(base+'/engine/pause',headers=headers,json={'paused':True}).status_code==200
     engine.terminate();engine.wait(timeout=8)
     engine=subprocess.Popen([sys.executable,'-m','app.engine'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log)
     time.sleep(1)
     persisted=c.get(base+'/engine',headers=headers).json()
     assert persisted['config']['paused'] is True
     assert any(j['id']==target and j['status']=='completed' for j in persisted['jobs'])
     print('ENGINE HTTP PASS: isolated process report, evidence download, pause persists after engine restart.')
     print('HTTP E2E PASS: static dashboard served, private login, Collector bridge+attachment, retry dedup, worker triage, build audit, evidence download, CEO channel, blocked unverified approval.')
     print('All records were TEST DATA in a temporary database. No Windows/Android application was launched.')
   finally:
    for process in (engine,worker,api):
     process.terminate()
    for process in (engine,worker,api):
     try:process.wait(timeout=8)
     except subprocess.TimeoutExpired:process.kill();process.wait()
if __name__=='__main__':main()
