"""Explicit local release intake. Never launches a binary or publishes a release."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import httpx

def validate_endpoint(value):
    parsed=urlsplit(value)
    if parsed.scheme not in {"http","https"} or parsed.hostname not in {"127.0.0.1","::1"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Use a API local em 127.0.0.1 ou ::1; não enviar credenciais para outro servidor")
    if parsed.path.rstrip("/")!="/api/v1":raise ValueError("O caminho da API deve ser /api/v1")
    return value.rstrip("/")

def register(client,artifact,version,platform,token):
    path=Path(artifact)
    if not path.is_file() or path.suffix.lower() not in {".exe",".apk",".aab",".zip",".msi",".msix"}:
        raise ValueError("Escolha um EXE/APK/AAB/ZIP/MSI/MSIX existente")
    if path.stat().st_size>450*1024*1024:raise ValueError("Artefato excede 450 MB")
    data=path.read_bytes()
    if not data:raise ValueError("Artefato vazio")
    sha=hashlib.sha256(data).hexdigest()
    headers={"Authorization":"Bearer "+token}
    response=client.get("releases",headers=headers);response.raise_for_status()
    release=next((r for r in response.json() if r["version"]==version),None)
    if release is None:
        response=client.post("releases",headers=headers,json={"product_slug":"nexgrana","version":version,"notes":"Candidata registrada por ação explícita; sem publicação ou execução automática."})
        if response.status_code==409:
            response=client.get("releases",headers=headers);response.raise_for_status()
            release=next((r for r in response.json() if r["version"]==version),None)
            if not release:raise ValueError("Conflito de release; confira o painel")
        else:
            response.raise_for_status();release=response.json()
    if release.get("status")=="stable":raise ValueError("Release estável é imutável; informe outra candidata")
    response=client.post(f"releases/{release['id']}/artifacts",headers=headers,data={"platform":platform},files={"file":(path.name,data,"application/octet-stream")})
    response.raise_for_status();record=response.json()
    if record.get("sha256")!=sha:raise ValueError("O hash recebido pela Central não coincide com os bytes enviados")
    return {"version":version,"release_id":release["id"],"artifact_id":record["id"],"filename":path.name,"platform":platform,"sha256":sha,"size_bytes":len(data),"status":record.get("status"),"registered":True,"executed":False,"installed":False,"published":False,"duplicate":record.get("duplicate",False)}

def attach_runner_report(client,release_id,path,token,task_ids=()):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>3*1024*1024:
        raise ValueError('Relatório JSON existente de até 3 MB necessário')
    data=path.read_bytes();report=json.loads(data)
    if not isinstance(report,dict) or report.get('schema')!='sim-labs.trusted-source-run/1.0':
        raise ValueError('Schema do relatório não reconhecido')
    headers={'Authorization':'Bearer '+token}
    response=client.post('evidence',headers=headers,data={'release_id':release_id},files={'file':(path.name,data,'application/json')})
    response.raise_for_status();evidence=response.json()
    if evidence.get('sha256')!=hashlib.sha256(data).hexdigest():raise ValueError('Hash do relatório divergiu')
    response=client.post(f'releases/{release_id}/runner-reports',headers=headers,json={'evidence_id':evidence['id'],'task_ids':list(task_ids)})
    response.raise_for_status()
    return {'evidence_id':evidence['id'],'test_run_id':response.json()['id'],'status':response.json()['status'],'executed_by_engine':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact");parser.add_argument("--version",required=True)
    parser.add_argument("--platform",choices=["Windows","Android","Fonte","Web"],required=True)
    parser.add_argument("--endpoint",default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--report",default="release-intake-report.json")
    parser.add_argument('--runner-report',help='JSON do runner manual; não comprova execução deste binário')
    parser.add_argument('--task-id',action='append',default=[])
    args=parser.parse_args();endpoint=validate_endpoint(args.endpoint)
    with httpx.Client(base_url=endpoint+"/",timeout=60,follow_redirects=False,trust_env=False) as client:
        response=client.get("health");response.raise_for_status()
        token=os.environ.get("SIM_LABS_SESSION_TOKEN")
        if not token:
            password=getpass.getpass("Senha da Central local (não será gravada): ")
            response=client.post("auth/login",json={"password":password});password=None
            response.raise_for_status();token=response.json()["token"]
        report=register(client,args.artifact,args.version,args.platform,token)
        if args.runner_report:
            report['runner_report']=attach_runner_report(client,report['release_id'],args.runner_report,token,args.task_id)
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Artefato registrado e hash confirmado. Consulte Releases & QA; instalação, teste em dispositivo e publicação continuam etapas próprias.")

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,httpx.HTTPError) as exc:
        # HTTP request bodies and credentials are never echoed.
        print("Registro bloqueado: "+(str(exc) if isinstance(exc,ValueError) else type(exc).__name__))
        raise SystemExit(1)
