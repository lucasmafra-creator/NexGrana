"""CEO-controlled commercial catalog, independent of household financial data."""
import json,uuid
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select,func,update
from ..db import get_db
from ..auth import get_current_principal
from ..models import now
from ..promotion_models import PromotionSource,PromotionOffer,PromotionRun
from .. import promotions as service
from ..operations import audit
from .integrated import scoped,ceo,item,out
router=APIRouter()
class SourceInput(BaseModel):
 product_slug:str='nexgrana'
 name:str=Field(min_length=3,max_length=100)
 kind:str='awin_jsonl'
 url:str=Field(max_length=500)
 token_env:str=Field(default='',max_length=100)
 approved_hosts:list[str]=Field(min_length=1,max_length=30)
 authorization_note:str=Field(min_length=12,max_length=1000)
 keywords:list[str]=Field(default_factory=list,max_length=20)
 interval_seconds:int=Field(default=86400,ge=900,le=604800)
 enabled:bool=False
 auto_approve:bool=False
 revision:int|None=None
class OfferInput(BaseModel):
 product_slug:str='nexgrana'
 approved_hosts:list[str]=Field(min_length=1,max_length=30)
 payload:dict
 revision:int|None=None
class ChangeInput(BaseModel):
 revision:int
 action:str
class ImportInput(BaseModel):
 product_slug:str='nexgrana'
 approved_hosts:list[str]=Field(min_length=1,max_length=30)
 offers:list[dict]=Field(min_length=1,max_length=500)
def clean_source(data):
 try:
  service.validate_source(data.kind,data.url,data.token_env)
  hosts=sorted(set(service.host_name(h) for h in data.approved_hosts))
  keywords=[k.strip()[:80] for k in data.keywords if k.strip()]
 except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc)) from None
 return dict(name=data.name,kind=data.kind,url=data.url,token_env=data.token_env,
  approved_hosts_json=service.dump(hosts),keywords_json=service.dump(keywords),authorization_note=data.authorization_note,
  enabled=data.enabled,auto_approve=data.auto_approve,interval_seconds=data.interval_seconds)
def clean_offer(data):
 try:return service.normalize_offer(data.payload,[service.host_name(h) for h in data.approved_hosts])
 except (ValueError,TypeError,KeyError,OverflowError) as exc:raise HTTPException(422,str(exc)) from None
@router.get('/promotions')
def overview(product_slug:str='nexgrana',p=Depends(get_current_principal),db=Depends(get_db)):
 product=scoped(db,p,product_slug)
 sources=[{**out(s),'approved_hosts':json.loads(s.approved_hosts_json),'keywords':json.loads(s.keywords_json)} for s in db.scalars(select(PromotionSource).where(PromotionSource.product_id==product.id))]
 offers=[{**out(o),'payload':json.loads(o.payload_json)} for o in db.scalars(select(PromotionOffer).where(PromotionOffer.product_id==product.id,PromotionOffer.status!='archived').order_by(PromotionOffer.updated_at.desc()).limit(500))]
 runs=[out(r) for r in db.scalars(select(PromotionRun).where(PromotionRun.product_id==product.id).order_by(PromotionRun.created_at.desc()).limit(30))]
 return {'sources':sources,'offers':offers,'runs':runs,'publication':'Exportação/ponte explícita; nenhuma publicação automática pelo coletor','external_status':'NOT_CONFIGURED' if not any(s['enabled'] for s in sources) else 'REVIEW','can_manage':p.name=='Mafra' and 'executive' in p.roles}
@router.post('/promotion-sources',status_code=201)
def create_source(data:SourceInput,p=Depends(get_current_principal),db=Depends(get_db)):
 product=scoped(db,p,data.product_slug);ceo(p)
 row=PromotionSource(product_id=product.id,**clean_source(data));db.add(row);db.flush()
 audit(db,'promotion.source.created',product.id,row.id,'Fonte autorizada configurada; chave não armazenada',p);db.commit();return out(row)
@router.patch('/promotion-sources/{id}')
def edit_source(id:str,data:SourceInput,p=Depends(get_current_principal),db=Depends(get_db)):
 row=item(db,PromotionSource,id,p);ceo(p)
 if data.revision!=row.revision:raise HTTPException(409,'Fonte mudou; recarregue')
 values={**clean_source(data),'revision':row.revision+1,'next_run_at':now()}
 changed=db.execute(update(PromotionSource).where(PromotionSource.id==id,PromotionSource.revision==data.revision).values(**values))
 if not changed.rowcount:raise HTTPException(409,'Fonte mudou; recarregue')
 db.refresh(row);audit(db,'promotion.source.updated',row.product_id,id,'Configuração revisada',p);db.commit();return out(row)
@router.post('/promotion-sources/{id}/collect')
def collect(id:str,p=Depends(get_current_principal),db=Depends(get_db)):
 row=item(db,PromotionSource,id,p);ceo(p)
 if not row.enabled:raise HTTPException(409,'Ative a fonte autorizada antes de coletar')
 row.next_run_at=now();db.commit()
 # The Engine enforces a shared 30-second gate, including manual requests.
 return {'status':'QUEUED_FOR_SCHEDULER','source_id':id,'requires_engine':True}
@router.post('/promotion-offers',status_code=201)
def create_offer(data:OfferInput,p=Depends(get_current_principal),db=Depends(get_db)):
 product=scoped(db,p,data.product_slug);ceo(p)
 if db.scalar(select(func.count(PromotionOffer.id)).where(PromotionOffer.product_id==product.id))>=500:raise HTTPException(409,'Limite de 500 registros por catálogo')
 row,_=service.upsert_offer(db,product.id,'manual:'+str(uuid.uuid4()),clean_offer(data))
 audit(db,'promotion.offer.created',product.id,row.id,'Rascunho para revisão',p);db.commit();return out(row)
@router.patch('/promotion-offers/{id}')
def edit_offer(id:str,data:OfferInput,p=Depends(get_current_principal),db=Depends(get_db)):
 row=item(db,PromotionOffer,id,p);ceo(p)
 if row.revision!=data.revision:raise HTTPException(409,'Oferta mudou; recarregue antes de editar')
 payload=clean_offer(data)
 changed=db.execute(update(PromotionOffer).where(PromotionOffer.id==id,PromotionOffer.revision==data.revision).values(payload_json=service.dump(payload),content_sha256=service.digest(payload),revision=data.revision+1,approved_sha256='',status='draft',updated_at=now()))
 if not changed.rowcount:raise HTTPException(409,'Oferta mudou; recarregue')
 db.refresh(row)
 audit(db,'promotion.offer.updated',row.product_id,id,'Nova revisão exige aprovação',p);db.commit();return out(row)
@router.post('/promotion-offers/{id}/review')
def review(id:str,data:ChangeInput,p=Depends(get_current_principal),db=Depends(get_db)):
 row=item(db,PromotionOffer,id,p);ceo(p)
 if row.revision!=data.revision:raise HTTPException(409,'Oferta mudou; recarregue antes de revisar')
 if data.action not in {'approve','pause','archive'}:raise HTTPException(422,'Ação inválida')
 if data.action=='approve':
  try:service.normalize_offer(json.loads(row.payload_json),[service.host_name(urlsplit(json.loads(row.payload_json)['url']).hostname)])
  except ValueError as exc:raise HTTPException(422,str(exc)) from None
  if json.loads(row.payload_json).get('availability')=='out_of_stock':raise HTTPException(422,'Produto sem estoque')
 status={'approve':'approved','pause':'paused','archive':'archived'}[data.action]
 changed=db.execute(update(PromotionOffer).where(PromotionOffer.id==id,PromotionOffer.revision==data.revision).values(status=status,approved_sha256=row.content_sha256 if data.action=='approve' else '',revision=data.revision+1,updated_at=now()))
 if not changed.rowcount:raise HTTPException(409,'Oferta mudou; recarregue')
 db.refresh(row)
 audit(db,'promotion.offer.'+data.action,row.product_id,id,'Revisão '+str(row.revision),p);db.commit();return out(row)
@router.post('/promotion-import')
def import_offers(data:ImportInput,p=Depends(get_current_principal),db=Depends(get_db)):
 product=scoped(db,p,data.product_slug);ceo(p)
 if len(service.dump(data.offers).encode())>service.MAX_BYTES:raise HTTPException(413,'Importação até 8MB')
 # Validate the complete batch before any write; partial imports never happen.
 validated=[]
 try:
  hosts=[service.host_name(h) for h in data.approved_hosts]
  seen=set()
  for raw in data.offers:
   origin=str(raw.get('external_id',''))
   if not origin or len(origin)>150 or origin in seen:raise ValueError('external_id único e obrigatório')
   seen.add(origin);validated.append(('import:'+origin,service.normalize_offer(raw,hosts)))
  existing=set(db.scalars(select(PromotionOffer.origin_key).where(PromotionOffer.product_id==product.id)))
  if len(existing|{key for key,_ in validated})>500:raise ValueError('Limite total de 500 registros')
 except (ValueError,TypeError,KeyError) as exc:raise HTTPException(422,str(exc)) from None
 counts={'created':0,'updated':0,'unchanged':0}
 for key,payload in validated:
  _,kind=service.upsert_offer(db,product.id,key,payload);counts[kind]+=1
 audit(db,'promotion.import',product.id,'',service.dump(counts),p);db.commit();return counts
@router.get('/promotion-catalog')
def export_catalog(product_slug:str='nexgrana',p=Depends(get_current_principal),db=Depends(get_db)):
 product=scoped(db,p,product_slug);ceo(p)
 try:return service.catalog(db,product.id)
 except ValueError as exc:raise HTTPException(422,str(exc)) from None
