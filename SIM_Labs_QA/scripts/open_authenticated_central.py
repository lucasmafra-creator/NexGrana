"""Open this QA instance using a short-lived local session; never print its token."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from urllib import error,parse,request
import webbrowser

QA_ROOT=Path(__file__).resolve().parents[1]
SERVICE='sim-labs-control-center-qa'
PHASE='Engine 0.4.1-qa.2'

def session_url(port:int,password:str,qa_root:Path=QA_ROOT,opener=None)->str:
    base=f'http://127.0.0.1:{port}'
    opener=opener or request.build_opener(request.ProxyHandler({}))
    def get(path,payload=None):
        data=json.dumps(payload).encode() if payload is not None else None
        req=request.Request(base+path,data=data,headers={'Content-Type':'application/json'},method='POST' if data else 'GET')
        with opener.open(req,timeout=8) as response:return json.load(response)
    health=get('/api/v1/health')
    expected=hashlib.sha256(qa_root.resolve().as_posix().lower().rstrip('/').encode()).hexdigest()[:16]
    if (health.get('status'),health.get('service'),health.get('phase'),health.get('instance_id')) != ('ok',SERVICE,PHASE,expected):
        raise RuntimeError('A central respondeu, mas a identidade desta pasta nao confere.')
    login=get('/api/v1/auth/login',{'password':password})
    token=login.get('token')
    if not isinstance(token,str) or not token or login.get('name')!='Mafra' or login.get('mode')!='local-private':
        raise RuntimeError('O acesso local nao foi validado; confira a credencial salva desta pasta.')
    return base+'/#sim-session='+parse.quote(token,safe='')

def launch(root:Path=QA_ROOT,open_url=webbrowser.open)->int:
    runtime=root/'.runtime'
    port=int((runtime/'qa_port.txt').read_text(encoding='ascii').strip())
    if not 1024<=port<=65535:raise RuntimeError('Porta local QA invalida.')
    password=''
    for line in (runtime/'PRIMEIRO_ACESSO.txt').read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('Senha:'):
            password=line.split(':',1)[1].strip();break
    if not password:raise RuntimeError('Credencial desta pasta ausente ou invalida.')
    url=session_url(port,password,root)
    if not open_url(url,new=1):raise RuntimeError('O navegador padrao nao abriu a central.')
    print(f'SIM Labs aberto ja autenticado: http://127.0.0.1:{port} (sessao local; segredo oculto).',flush=True)
    return 0

if __name__=='__main__':
    try:raise SystemExit(launch())
    except Exception as exc:
        print('ABERTURA BLOQUEADA: '+str(exc),flush=True);raise SystemExit(2)
