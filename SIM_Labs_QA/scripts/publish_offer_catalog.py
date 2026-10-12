"""Explicit commercial-only bridge. Preview by default, administrator session, no service role."""
import argparse,getpass,hashlib,json,os,re,time
from pathlib import Path
from urllib.parse import urlsplit
import httpx

def local_endpoint(value):
 u=urlsplit(value)
 if u.scheme!='http' or u.hostname not in {'127.0.0.1','localhost','::1'} or u.username or u.password or u.query or u.fragment or u.path.rstrip('/')!='/api/v1':raise ValueError('Use somente a API local /api/v1')
 return value.rstrip('/')
def supabase_endpoint(value,allowed_ref):
 u=urlsplit(value)
 if u.scheme!='https' or not re.fullmatch(r'[a-z0-9]{20}\.supabase\.co',u.hostname or '') or u.port not in (None,443) or u.username or u.password or u.query or u.fragment or u.path not in ('','/') or u.hostname.split('.')[0]!=allowed_ref:raise ValueError('Projeto Supabase não corresponde a --allow-project-ref')
 return value.rstrip('/')
def validate_catalog(manifest):
 if not isinstance(manifest,dict) or manifest.get('schema')!='sim-labs.offer-catalog/1' or manifest.get('contains_user_finances') is not False:raise ValueError('Catálogo inválido')
 if not isinstance(manifest.get('offers'),list) or len(manifest['offers'])>500:raise ValueError('Limite de 500 ofertas')
 if len(json.dumps(manifest).encode())>8*1024**2:raise ValueError('Limite de 8MB')
 return manifest
class Bridge:
 def __init__(self,client,sim_url,sim_token,slug):self.client=client;self.sim_url=local_endpoint(sim_url);self.sim_token=sim_token;self.slug=slug
 def catalog(self):
  response=self.client.get(self.sim_url+'/promotion-catalog',params={'product_slug':self.slug},headers={'Authorization':'Bearer '+self.sim_token})
  if response.status_code!=200:raise ValueError('SIM Labs recusou o catálogo: HTTP '+str(response.status_code))
  return validate_catalog(response.json())
 def login(self,project,key,email,password):
  response=self.client.post(project+'/auth/v1/token',params={'grant_type':'password'},headers={'apikey':key},json={'email':email,'password':password})
  if response.status_code!=200:raise ValueError('Login Supabase recusado: HTTP '+str(response.status_code))
  data=response.json()
  if not data.get('access_token'):raise ValueError('Sessão Supabase ausente')
  return data
 def publish(self,project,key,session,manifest):
  response=self.client.post(project+'/rest/v1/rpc/apply_sim_offer_catalog',headers={'apikey':key,'Authorization':'Bearer '+session['access_token']},json={'p_manifest':validate_catalog(manifest)})
  if response.status_code not in (200,201):raise ValueError('Publicação recusada: HTTP '+str(response.status_code)+'; confira migração, admin, validade e relatório local')
  return response.json()
def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--endpoint',default='http://127.0.0.1:8000/api/v1');parser.add_argument('--project',default='nexgrana')
 parser.add_argument('--output',default='offer-catalog-preview.json');parser.add_argument('--report',default='offer-publication-report.json')
 parser.add_argument('--publish',action='store_true');parser.add_argument('--watch',action='store_true');parser.add_argument('--interval',type=int,default=900)
 parser.add_argument('--supabase-url');parser.add_argument('--allow-project-ref')
 args=parser.parse_args(argv)
 if args.interval<900 or (args.watch and not args.publish):raise ValueError('--watch exige --publish e intervalo mínimo de 900 segundos')
 target=supabase_endpoint(args.supabase_url or '',args.allow_project_ref) if args.publish else None
 # Secrets never appear in command-line args, files or reports.
 endpoint=local_endpoint(args.endpoint)
 token=os.getenv('SIM_PROMO_BRIDGE_SESSION')
 local_password=getpass.getpass('Senha da Central local (oculta): ') if not token else None
 key=(os.getenv('SIM_PROMO_SUPABASE_ANON_KEY') or getpass.getpass('Chave anon/publishable Supabase (oculta): ')) if target else None
 if key and key.startswith('sb_secret_'):raise ValueError('Use chave pública anon/publishable, nunca secret/service role')
 if key and key.count('.')==2:
  import base64
  try:
   claims=json.loads(base64.urlsafe_b64decode(key.split('.')[1]+'='*(-len(key.split('.')[1])%4)))
   if claims.get('role')=='service_role':raise ValueError('service_role não permitido')
  except (json.JSONDecodeError,UnicodeError):raise ValueError('Chave inválida') from None
 email=input('Email do admin de Achados: ').strip() if target else None
 with httpx.Client(timeout=30,follow_redirects=False,trust_env=False) as client:
  next_sim_login=None
  def sim_login():
   response=client.post(endpoint+'/auth/login',json={'password':local_password})
   if response.status_code!=200:raise ValueError('Login SIM Labs recusado: HTTP '+str(response.status_code))
   data=response.json()
   if not data.get('token'):raise ValueError('Sessão SIM Labs ausente')
   return data['token'],time.monotonic()+max(60,int(data.get('expires_in',43200))-60)
  if local_password:token,next_sim_login=sim_login()
  bridge=Bridge(client,endpoint,token,args.project)
  session=bridge.login(target,key,email,getpass.getpass('Senha Supabase (oculta): ')) if target else None
  next_login=time.monotonic()+max(60,int((session or {}).get('expires_in',3600))-60)
  while True:
   if next_sim_login is not None and time.monotonic()>=next_sim_login:
    bridge.sim_token,next_sim_login=sim_login()
   manifest=bridge.catalog();Path(args.output).write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
   report={'status':'PREVIEW','sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),'offer_count':len(manifest['offers']),'enabled_count':sum(bool(o.get('enabled')) for o in manifest['offers']),'contains_user_finances':False}
   if target:
    if time.monotonic()>=next_login:
     response=client.post(target+'/auth/v1/token',params={'grant_type':'refresh_token'},headers={'apikey':key},json={'refresh_token':session['refresh_token']})
     if response.status_code!=200:raise ValueError('Sessão expirou; execute a ponte novamente')
     session=response.json();next_login=time.monotonic()+max(60,int(session.get('expires_in',3600))-60)
    report['result']=bridge.publish(target,key,session,manifest);report['status']='PUBLISHED'
   Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(report['status'],report['offer_count'],'ofertas;',report['enabled_count'],'habilitadas')
   if not args.watch:return 0
   # Long-running user-enabled service. Ctrl+C stops without touching app finances.
   time.sleep(args.interval)
if __name__=='__main__':
 try:raise SystemExit(main())
 except KeyboardInterrupt:print('Ponte encerrada. Nenhuma oferta foi apagada.');raise SystemExit(0)
 except Exception as exc:print('Ponte bloqueada:',str(exc) if isinstance(exc,ValueError) else type(exc).__name__);raise SystemExit(1)
