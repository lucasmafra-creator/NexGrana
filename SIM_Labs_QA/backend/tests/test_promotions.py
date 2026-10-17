"""Synthetic feed contracts; no claim of a live partner integration."""
import json,sys,importlib.util
from pathlib import Path
from datetime import datetime,timedelta,timezone
import httpx,pytest
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Product,now
from app.promotion_models import PromotionSource,PromotionOffer,PromotionRun,PromotionControl
from app.engine_models import EngineConfig,EngineJob
from app import promotions as svc,engine
H={'X-Dev-Actor':'Mafra'}
def payload(**kw):
 at=datetime.now(timezone.utc)
 return {'title':'TEST DATA Rice','url':'https://www.partner.com.br/rice','price':'12.90','verified_at':at.isoformat(),'expires_at':(at+timedelta(hours=23)).isoformat(),'availability':'in_stock',**kw}
def offer(c,**kw):
 response=c.post('/api/v1/promotion-offers',headers=H,json={'approved_hosts':['www.partner.com.br'],'payload':payload(**kw)})
 assert response.status_code==201,response.text
 return response.json()
def source(c,**kw):
 response=c.post('/api/v1/promotion-sources',headers=H,json={'name':'TEST DATA Partner','url':'https://api.awin.com/publishers/123/awinfeeds/download/456-retail-pt_BR.jsonl','approved_hosts':['www.partner.com.br'],'authorization_note':'TEST DATA authorized synthetic feed only','enabled':True,**kw})
 assert response.status_code==201,response.text
 return response.json()
def review(c,row,action='approve'):
 return c.post('/api/v1/promotion-offers/'+row['id']+'/review',headers=H,json={'revision':row['revision'],'action':action})
def test_private_permissions_and_scope(client):
 assert client.get('/api/v1/promotions').status_code==401
 assert client.post('/api/v1/promotion-offers',headers={'X-Dev-Actor':'Niel'},json={'approved_hosts':['www.partner.com.br'],'payload':payload()}).status_code==403
 assert client.get('/api/v1/promotion-catalog',headers={'X-Dev-Actor':'Niel'}).status_code==403
 assert client.get('/api/v1/promotions?product_slug=not-existing',headers=H).status_code==404
@pytest.mark.parametrize('change',[{'url':'http://www.partner.com.br/x'},{'url':'https://www.partner.com.br.evil.com/x'},{'url':'https://user:secret@www.partner.com.br/x'},{'price':'NaN'},{'price':'1.001'},{'price':-1},{'verified_at':None},{'affiliate':'false'},{'expires_at':'2099-01-01T00:00:00Z'}])
def test_invalid_offers_never_written(client,change):
 r=client.post('/api/v1/promotion-offers',headers=H,json={'approved_hosts':['www.partner.com.br'],'payload':payload(**change)})
 assert r.status_code==422,r.text
 assert client.get('/api/v1/promotions',headers=H).json()['offers']==[]
def test_revision_approval_pause_archive_and_no_auto_publish(client):
 row=offer(client)
 assert not client.get('/api/v1/promotion-catalog',headers=H).json()['offers'][0]['enabled']
 approved=review(client,row).json();assert approved['status']=='approved'
 catalog=client.get('/api/v1/promotion-catalog',headers=H).json();assert catalog['offers'][0]['enabled'];assert catalog['contains_user_finances'] is False
 assert review(client,row,'pause').status_code==409
 paused=review(client,approved,'pause').json();assert not client.get('/api/v1/promotion-catalog',headers=H).json()['offers'][0]['enabled']
 review(client,paused,'archive');assert client.get('/api/v1/promotions',headers=H).json()['offers']==[]
 assert len(client.get('/api/v1/promotion-catalog',headers=H).json()['offers'])==1 # explicit disabled tombstone
 assert client.get('/api/v1/promotion-catalog',headers=H).json()['offers'][0]['enabled'] is False
 assert client.patch('/api/v1/promotion-offers/'+row['id'],headers=H,json={'revision':row['revision'],'approved_hosts':['www.partner.com.br'],'payload':payload()}).status_code==409

def test_atomic_import_and_replay(client):
 items=[{**payload(),'external_id':'stable-1'},{**payload(url='https://evil.com/x'),'external_id':'bad'}]
 r=client.post('/api/v1/promotion-import',headers=H,json={'approved_hosts':['www.partner.com.br'],'offers':items});assert r.status_code==422
 assert client.get('/api/v1/promotions',headers=H).json()['offers']==[]
 body={'approved_hosts':['www.partner.com.br'],'offers':items[:1]}
 assert client.post('/api/v1/promotion-import',headers=H,json=body).json()['created']==1
 assert client.post('/api/v1/promotion-import',headers=H,json=body).json()['unchanged']==1

def test_feed_contract_incomplete_and_dedup_pause(client):
 s=source(client)
 raw={'id':'SKU1','title':'TEST DATA Rice','link':'https://www.partner.com.br/rice','price':'19.90 BRL','sale_price':'12.90 BRL','availability':'in_stock'}
 with SessionLocal() as db:
  src=db.get(PromotionSource,s['id']);rows,skipped=svc.decode_feed(src,json.dumps(raw).encode());assert skipped==0;assert rows[0][1]['price']==12.9;assert rows[0][1]['affiliate'] is False
  with pytest.raises(ValueError):svc.decode_feed(src,(json.dumps(raw)+'\n{"error":"incomplete"}').encode())
  with pytest.raises(ValueError,match='duplicado'):svc.decode_feed(src,(json.dumps(raw)+'\n'+json.dumps(raw)).encode())
  result={'rows':rows,'skipped':0,'sha256':'a'*64};assert svc.apply_collection(db,src,result)['created']==1;db.commit()
  row=db.scalar(select(PromotionOffer));row.status='paused';row.approved_sha256='';db.commit()
  svc.apply_collection(db,src,{**result,'rows':[(rows[0][0],{**rows[0][1],'price':11.9})]});db.commit();assert row.status=='paused'
  assert not svc.catalog(db,src.product_id)['offers'][0]['enabled']

def test_source_endpoint_and_secret_validation(client):
 base={'name':'TEST DATA source','approved_hosts':['www.partner.com.br'],'authorization_note':'TEST DATA valid note'}
 for url in ['http://api.awin.com/x','https://127.0.0.1/x','https://api.awin.com.evil.com/publishers/1/awinfeeds/download/2-retail-en_GB.jsonl','https://api.awin.com/publishers/1/awinfeeds/download/2-retail-en_GB.jsonl?token=secret']:
  assert client.post('/api/v1/promotion-sources',headers=H,json={**base,'url':url}).status_code==422
 assert client.post('/api/v1/promotion-sources',headers=H,json={**base,'url':'https://api.awin.com/publishers/1/awinfeeds/download/2-retail-en_GB.jsonl','token_env':'secret-value'}).status_code==422

def test_http_redirect_rate_size_and_missing_token(client,monkeypatch):
 s=source(client,token_env='SIM_PROMO_TEST_TOKEN')
 with SessionLocal() as db:
  src=db.get(PromotionSource,s['id'])
  with pytest.raises(ValueError,match='Credencial'):svc.fetch_bytes(src)
  monkeypatch.setenv('SIM_PROMO_TEST_TOKEN','TEST DATA hidden token')
  for status in [302,429,403]:
   with httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(status,headers={'Location':'http://127.0.0.1/secret'}))) as fake:
    with pytest.raises(ValueError):svc.fetch_bytes(src,fake)
  monkeypatch.setattr(svc,'MAX_BYTES',5)
  with httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,content=b'123456'))) as fake:
   with pytest.raises(ValueError,match='limite'):svc.fetch_bytes(src,fake)

def dispatch():
 with SessionLocal() as db:
  engine.ensure(db);engine.schedule_promotions(db);db.commit();return engine.claim(db)

def test_scheduler_global_gate_and_fenced_collection(client,monkeypatch):
 s=source(client);source(client,name='TEST DATA second')
 token=dispatch();assert token
 monkeypatch.setattr(svc,'prepare_collection',lambda src:{'rows':[('sku1',svc.normalize_offer(payload(),['www.partner.com.br']))],'skipped':0,'sha256':'b'*64})
 engine.execute(*token)
 with SessionLocal() as db:
  assert db.get(EngineJob,token[0]).status=='completed';assert db.scalar(select(PromotionRun)).status=='PASS'
  engine.schedule_promotions(db);db.commit();assert len(list(db.scalars(select(EngineJob))))==1
  assert len(svc.catalog(db,db.get(PromotionSource,s['id']).product_id)['offers'])==1
 engine.execute(*token)
 with SessionLocal() as db:assert len(list(db.scalars(select(PromotionRun))))==1

def test_pause_during_fetch_discards_result(client,monkeypatch):
 s=source(client);token=dispatch()
 def fetch(src):
  with SessionLocal() as other:
   row=other.get(PromotionSource,src.id);row.enabled=False;row.revision+=1;other.commit()
  return {'rows':[('sku1',svc.normalize_offer(payload(),['www.partner.com.br']))],'skipped':0,'sha256':'c'*64}
 monkeypatch.setattr(svc,'prepare_collection',fetch);engine.execute(*token)
 with SessionLocal() as db:
  assert db.scalar(select(PromotionOffer)) is None
  assert json.loads(db.get(EngineJob,token[0]).result_json)['status']=='BLOCKED'

def test_missing_credentials_do_not_block_other_workers(client):
 source(client,token_env='SIM_PROMO_MISSING_TOKEN');token=dispatch();engine.execute(*token)
 with SessionLocal() as db:
  result=json.loads(db.get(EngineJob,token[0]).result_json);assert result['status']=='EXTERNAL_BLOCKER'
  assert db.scalar(select(PromotionRun)).status=='EXTERNAL_BLOCKER';assert db.scalar(select(PromotionOffer)) is None
  p=db.scalar(select(Product));job=engine.enqueue(db,p.id,'qa','manual','still-works');db.commit();assert engine.claim(db)[0]==job.id

def test_expiry_stock_and_verification_fail_closed(client):
 row=offer(client);review(client,row)
 with SessionLocal() as db:
  o=db.get(PromotionOffer,row['id']);p=json.loads(o.payload_json);p['verified_at']=(datetime.now(timezone.utc)-timedelta(hours=25)).isoformat();o.payload_json=svc.dump(p);o.content_sha256=svc.digest(p);o.approved_sha256=o.content_sha256;db.commit()
 assert not client.get('/api/v1/promotion-catalog',headers=H).json()['offers'][0]['enabled']
 assert review(client,offer(client,availability='out_of_stock')).status_code==422

def test_bridge_only_commercial_rpc_and_project_fence():
 path=Path(__file__).resolve().parents[2]/'scripts'/'publish_offer_catalog.py'
 spec=importlib.util.spec_from_file_location('promo_bridge',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 with pytest.raises(ValueError):module.local_endpoint('https://evil.com/api/v1')
 with pytest.raises(ValueError):module.supabase_endpoint('https://abcdefghijklmnopqrst.supabase.co','wrong')
 calls=[]
 def transport(req):
  calls.append(req)
  if req.url.path.endswith('/promotion-catalog'):return httpx.Response(200,json={'schema':'sim-labs.offer-catalog/1','contains_user_finances':False,'offers':[]})
  return httpx.Response(200,json={'status':'applied'})
 with httpx.Client(transport=httpx.MockTransport(transport)) as fake:
  bridge=module.Bridge(fake,'http://127.0.0.1:8000/api/v1','TEST TOKEN','nexgrana');manifest=bridge.catalog()
  bridge.publish('https://abcdefghijklmnopqrst.supabase.co','TEST KEY',{'access_token':'TEST SESSION'},manifest)
 assert len(calls)==2 and calls[-1].url.path=='/rest/v1/rpc/apply_sim_offer_catalog'
 assert 'income' not in calls[-1].content.decode() and 'expenses' not in calls[-1].content.decode()


def test_feed_expiration_and_promotion_queue_priority(client):
 s=source(client)
 with SessionLocal() as db:
  src=db.get(PromotionSource,s['id'])
  raw={'id':'SKU-expired','title':'TEST DATA expired offer','link':'https://www.partner.com.br/rice','price':'12.90 BRL','availability':'in_stock','expiration_date':(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()}
  rows,skipped=svc.decode_feed(src,json.dumps(raw).encode());assert rows==[] and skipped==1
  engine.ensure(db);p=db.scalar(select(Product));engine.enqueue(db,p.id,'qa','daily','old-audit')
  engine.schedule_promotions(db);db.commit();token=engine.claim(db)
  assert db.get(EngineJob,token[0]).kind=='promotion_collect'
