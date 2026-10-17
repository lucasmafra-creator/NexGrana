"""Authorized-feed collection. No scraping, prices invented or secret persistence."""
import hashlib,ipaddress,json,os,re,time,uuid
from datetime import datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit,urlunsplit
import httpx
from sqlalchemy import select,update,or_
from .models import now
from .promotion_models import PromotionSource,PromotionOffer,PromotionRun,PromotionControl
MAX_BYTES=8*1024*1024
MAX_OFFERS=500

def dump(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(value):return hashlib.sha256(dump(value).encode()).hexdigest()
def utc(value):
 dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
 if dt.tzinfo is None:raise ValueError('Informe data e fuso horário')
 return dt.astimezone(timezone.utc)
def host_name(value):
 host=str(value).strip().lower()
 if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?',host) or '.' not in host or '..' in host:raise ValueError('Domínio inválido')
 try:ipaddress.ip_address(host)
 except ValueError:pass
 else:raise ValueError('Não use IP como domínio de parceiro')
 if host.endswith(('.local','.localhost','.internal','.invalid','.test')) or host=='localhost':raise ValueError('Domínio de parceiro precisa ser público')
 return host

def safe_link(value,hosts):
 raw=str(value or '').strip();u=urlsplit(raw)
 if len(raw)>2000 or u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443) or u.fragment:raise ValueError('Use URL HTTPS de parceiro autorizado')
 if u.hostname.lower() not in set(hosts):raise ValueError('Domínio não autorizado para esta fonte')
 return urlunsplit(('https',u.hostname.lower(),u.path or '/',u.query,''))

def validate_source(kind,url,token_env):
 u=urlsplit(url)
 if u.scheme!='https' or u.username or u.password or u.query or u.fragment or u.port not in (None,443):raise ValueError('Endpoint HTTPS oficial sem credenciais na URL')
 if kind=='awin_jsonl':
  valid=u.hostname=='api.awin.com' and re.fullmatch(r'/publishers/\d+/awinfeeds/download/\d+-retail-[a-zA-Z_]{2,12}\.jsonl',u.path)
 elif kind=='mercado_item':valid=u.hostname=='api.mercadolibre.com' and re.fullmatch(r'/items/MLB\d+',u.path)
 else:raise ValueError('Conector não suportado')
 if not valid:raise ValueError('Use o endpoint oficial documentado para o conector')
 if token_env and not re.fullmatch(r'SIM_PROMO_[A-Z0-9_]{1,70}_TOKEN',token_env):raise ValueError('Informe somente o nome SIM_PROMO_..._TOKEN; nunca cole a chave no painel')

def money(value):
 if value is None or value=='':return None
 try:d=Decimal(str(value))
 except InvalidOperation:raise ValueError('Preço inválido') from None
 if not d.is_finite() or d<0 or d>Decimal('999999999999.99') or d.quantize(Decimal('.01'))!=d:raise ValueError('Preço BRL inválido')
 return float(d)

def normalize_offer(raw,hosts,provider='Parceiro',at=None):
 at=at or now();at=at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at.astimezone(timezone.utc)
 if not isinstance(raw,dict):raise ValueError('Oferta precisa ser um objeto JSON')
 if type(raw.get('affiliate',False)) is not bool:raise ValueError('affiliate precisa ser booleano explícito')
 title=' '.join(str(raw.get('title') or '').split())
 if not 4<=len(title)<=180:raise ValueError('Título deve ter 4 a 180 caracteres')
 url=safe_link(raw.get('url'),hosts);price=money(raw.get('price'));previous=money(raw.get('previous_price'))
 expiry=utc(raw.get('expires_at'))
 if expiry<=at or expiry>at+timedelta(days=7):raise ValueError('Validade precisa ser futura, até 7 dias')
 verified=utc(raw['verified_at']) if raw.get('verified_at') else None
 if price is not None and (verified is None or verified>at+timedelta(minutes=5) or verified<at-timedelta(hours=24)):raise ValueError('Preço precisa de verificação recente e explícita')
 if raw.get('currency','BRL')!='BRL':raise ValueError('Somente BRL nesta rodada')
 availability=str(raw.get('availability') or 'unknown')
 if availability not in {'in_stock','out_of_stock','unknown'}:raise ValueError('Disponibilidade inválida')
 return {'title':title,'subtitle':str(raw.get('subtitle') or '')[:500],'provider':str(raw.get('provider') or provider)[:80],
  'url':url,'original_url':url,'category':str(raw.get('category') or 'Outros')[:80],
  'price':price,'previous_price':previous,'currency':'BRL','verified_at':verified.isoformat() if verified else None,
  'expires_at':expiry.isoformat(),'availability':availability,'affiliate':bool(raw.get('affiliate',False)),
  'platform':'all','sponsored':False,'image_url':None,'image_alt':'','sort_order':1000,'search_tags':[],
  'source':'sim_labs','enabled':False}

def fetch_bytes(source,client=None):
 validate_source(source.kind,source.url,source.token_env)
 token=os.getenv(source.token_env,'') if source.token_env else ''
 if source.token_env and not token:raise ValueError('Credencial da fonte não configurada no ambiente')
 headers={'Accept':'application/json','User-Agent':'SIM-Labs-Authorized-Feeds/0.4'}
 if token:headers['Authorization']='Bearer '+token
 owned=client is None;client=client or httpx.Client(timeout=httpx.Timeout(10,connect=5),trust_env=False,follow_redirects=False)
 try:
  start=time.monotonic();chunks=[];size=0
  with client.stream('GET',source.url,headers=headers) as response:
   if response.status_code==429:raise ValueError('RATE_LIMIT: aguarde o intervalo da fonte')
   if response.status_code!=200:raise ValueError('Fonte não retornou catálogo autorizado: HTTP '+str(response.status_code))
   for chunk in response.iter_bytes():
    size+=len(chunk)
    if size>MAX_BYTES or time.monotonic()-start>30:raise ValueError('Catálogo excedeu limite de tamanho/tempo')
    chunks.append(chunk)
  return b''.join(chunks)
 finally:
  if owned:client.close()

def decode_feed(source,data,at=None):
 at=at or now();at=at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at
 hosts=json.loads(source.approved_hosts_json);keywords=[x.casefold() for x in json.loads(source.keywords_json)]
 rows=[];skipped=0
 if source.kind=='mercado_item':
  record=json.loads(data)
  if not isinstance(record,dict):raise ValueError('Resposta de item precisa ser objeto JSON')
  records=[{'id':record.get('id'),'title':record.get('title'),'url':record.get('permalink'),
   'price':record.get('price'),'previous_price':record.get('original_price'),'currency':record.get('currency_id'),
   'availability':'in_stock' if record.get('status')=='active' and int(record.get('available_quantity') or 0)>0 else 'out_of_stock'}]
 else:
  records=[]
  for line in data.decode('utf8').splitlines():
   if not line.strip():continue
   raw=json.loads(line)
   if not isinstance(raw,dict) or 'error' in raw:raise ValueError('Feed incompleto ou formato inválido; nenhuma atualização aplicada')
   records.append(raw)
   if len(records)>10000:raise ValueError('Feed tem mais de 10000 produtos; forneça catálogo filtrado')
  prepared=[]
  for raw in records:
   raw=raw.get('product_basic',raw)
   if not isinstance(raw,dict):raise ValueError('Produto do feed precisa ser objeto JSON')
   def brl(value):
    if value in (None,''):return None
    match=re.fullmatch(r'(\d+(?:\.\d{1,2})?) BRL',str(value))
    if not match:raise ValueError('Moeda ou preço do feed fora do contrato BRL')
    return match.group(1)
   try:
    base=brl(raw.get('price'));sale=brl(raw.get('sale_price'))
    effective=raw.get('sale_price_effective_date');expiry=at+timedelta(hours=24)
    if raw.get('expiration_date'):expiry=min(expiry,utc(raw['expiration_date']))
    if sale is not None and effective:
     start,end=str(effective).split('/')
     if not utc(start)<=at<=utc(end):sale=None
     else:expiry=min(expiry,utc(end))
    prepared.append({'id':raw.get('id'),'title':raw.get('title'),'url':raw.get('link'),
      'price':sale if sale is not None else base,'previous_price':base if sale is not None else None,
      'currency':'BRL','availability':raw.get('availability','unknown'),'expires_at':expiry.isoformat()})
   except (ValueError,TypeError):skipped+=1
  records=prepared
 seen=set()
 for raw in records:
  key=str(raw.get('id') or '')
  if key and key in seen:raise ValueError('Feed contém ID duplicado; nenhuma atualização aplicada')
  seen.add(key)
  try:
   if len(key)>150:raise ValueError('ID da fonte excede 150 caracteres')
   if not raw.get('id'):raise ValueError('ID da fonte ausente')
   if keywords and not any(k in str(raw.get('title') or '').casefold() for k in keywords):skipped+=1;continue
   # Captured price is provider-reported, not a claim that we bought the item.
   payload=normalize_offer({**raw,'verified_at':at.isoformat(),'expires_at':raw.get('expires_at') or (at+timedelta(hours=24)).isoformat()},hosts,source.name,at)
   rows.append((key,payload))
   if len(rows)>MAX_OFFERS:raise ValueError('Mais de 500 resultados; restrinja palavras-chave')
  except ValueError as exc:
   if '500 resultados' in str(exc):raise
   skipped+=1
 return rows,skipped

def upsert_offer(db,product_id,origin_key,payload,source_id=None,auto_approve=False):
 hashed=digest(payload);row=db.scalar(select(PromotionOffer).where(PromotionOffer.product_id==product_id,PromotionOffer.origin_key==origin_key))
 eligible=payload.get('availability')!='out_of_stock'
 if not row:
  row=PromotionOffer(product_id=product_id,origin_key=origin_key,payload_json=dump(payload),content_sha256=hashed,source_id=source_id,
   status='approved' if auto_approve and eligible else 'draft',approved_sha256=hashed if auto_approve and eligible else '')
  db.add(row);db.flush();return row,'created'
 if row.content_sha256==hashed:return row,'unchanged'
 # A manual pause survives source refresh; changed terms need new approval by default.
 paused=row.status in {'paused','archived'};row.payload_json=dump(payload);row.content_sha256=hashed;row.revision+=1;row.updated_at=now()
 row.status=row.status if paused else ('approved' if auto_approve and eligible else 'draft')
 row.approved_sha256=hashed if row.status=='approved' else ''
 return row,'updated'

def prepare_collection(source,client=None):
 data=fetch_bytes(source,client);rows,skipped=decode_feed(source,data)
 return {'rows':rows,'skipped':skipped,'sha256':hashlib.sha256(data).hexdigest()}

def apply_collection(db,source,result):
 existing=set(db.scalars(select(PromotionOffer.origin_key).where(PromotionOffer.product_id==source.product_id)))
 if len(existing|{source.id+':'+key for key,_ in result['rows']})>MAX_OFFERS:raise ValueError('Catálogo cheio: limite total de 500 registros; use outro projeto para um novo catálogo')
 counts={'created':0,'updated':0,'unchanged':0}
 for key,payload in result['rows']:
  _,kind=upsert_offer(db,source.product_id,source.id+':'+key,payload,source.id,source.auto_approve);counts[kind]+=1
 source.last_status='PASS';source.last_error='';source.last_run_at=now()
 db.add(PromotionRun(product_id=source.product_id,source_id=source.id,status='PASS',created_count=counts['created'],updated_count=counts['updated'],skipped_count=result['skipped'],payload_sha256=result['sha256']))
 return {'status':'PASS','created':counts['created'],'updated':counts['updated'],'unchanged':counts['unchanged'],'skipped':result['skipped'],
         'source_id':source.id,'feed_sha256':result['sha256'],'published_to_nexgrana':False}

def catalog(db,product_id):
 output=[];hosts=set()
 for row in db.scalars(select(PromotionOffer).where(PromotionOffer.product_id==product_id).order_by(PromotionOffer.id)):
  p=json.loads(row.payload_json);p['id']=row.id;p['product_key']='sim:'+product_id+':'+row.id
  current=datetime.now(timezone.utc)
  fresh=p['price'] is None or bool(p.get('verified_at') and utc(p['verified_at'])>=current-timedelta(hours=24))
  enabled=row.status=='approved' and row.approved_sha256==row.content_sha256 and utc(p['expires_at'])>current and fresh and p.get('availability')!='out_of_stock'
  p['enabled']=enabled;p['campaign']='sim-labs-catalog';hosts.add(urlsplit(p['url']).hostname)
  output.append(p)
 if len(output)>MAX_OFFERS:raise ValueError('Catálogo excede 500 registros; consulte o administrador')
 if len(hosts)>30:raise ValueError('Catálogo excede 30 domínios; use projetos separados por catálogo')
 return {'schema':'sim-labs.offer-catalog/1','origin':product_id,'generated_at':datetime.now(timezone.utc).isoformat(),'partner_hosts':sorted(hosts),
         'offers':output,'contains_user_finances':False}
