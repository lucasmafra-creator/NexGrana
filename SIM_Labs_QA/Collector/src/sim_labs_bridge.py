"""Collector transport: standard library, no credentials embedded in the package."""
import io, json, os, uuid, zipfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def connection():
    root=Path(__file__).resolve().parents[2]
    config=root/'.runtime'/'collector_connection.json'
    data=json.loads(config.read_text(encoding='utf-8')) if config.exists() else {}
    endpoint=os.getenv('SIM_LABS_URL') or data.get('endpoint') or 'http://127.0.0.1:8000/api/v1'
    token=os.getenv('SIM_LABS_INGEST_TOKEN') or data.get('token') or ''
    parsed=urlparse(endpoint)
    if parsed.scheme not in {'http','https'} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('URL da central inválida')
    if parsed.scheme=='http' and parsed.hostname not in {'127.0.0.1','localhost','::1'}:
        raise ValueError('Central remota exige HTTPS')
    if not token: raise ValueError('Inicie a central pelo INICIAR_SIM_LABS.bat para configurar a conexão.')
    return endpoint.rstrip('/'),token

def send_snapshot(items,release):
    endpoint,token=connection()
    records=[]; omitted=[]
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as z:
        total=0
        for item in items:
            r={k:item.get(k) for k in ('title','kind','priority','category','platform','screen','description','current','expected','solution','notes','status')}
            r['feedback_id']=str(item['id']); r['evidence']=[]
            for index,raw in enumerate(item.get('attachments',[])):
                path=Path(raw)
                if not path.is_file(): omitted.append(path.name+': ausente'); continue
                size=path.stat().st_size
                if size>200*1024*1024 or total+size>400*1024*1024:
                    omitted.append(path.name+': limite de envio; use pacote separado'); continue
                name='evidencias/'+str(item['id'])+'/'+str(index)+'_'+path.name
                z.write(path,name); r['evidence'].append(name); total+=size
            records.append(r)
        z.writestr('SIM_LABS_INGEST.json',json.dumps({'schema':'sim-labs.feedback-ingest/1.0','release':release,'records':records},ensure_ascii=False))
    boundary='sim'+uuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="collector.zip"\r\nContent-Type: application/zip\r\n\r\n').encode()+buffer.getvalue()+f'\r\n--{boundary}--\r\n'.encode()
    if len(body)>450*1024*1024: raise ValueError('Pacote acima de 450 MB')
    req=Request(endpoint+'/collector/ingest-package',data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary,'X-SIM-Ingest-Token':token},method='POST')
    try:
        with build_opener(NoRedirect).open(req,timeout=120) as response:
            result=json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'Central recusou o envio (HTTP {exc.code}).') from exc
    result['omitted']=omitted
    return result
