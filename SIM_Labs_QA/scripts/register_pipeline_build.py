"""Register the current successful Windows bundle locally; never run or publish it."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'SIM_Labs_QA'

def package_windows_build(report,root):
    root=Path(root).resolve()
    tests=report.get('tests',[])
    if not tests or any(row.get('status')!='PASS' for row in tests):
        raise ValueError('Testes desta execucao nao foram aprovados.')
    build=next((row for row in report.get('builds',[]) if row.get('target')=='windows'),{})
    if build.get('status')!='BUILD OK':raise ValueError('Esta execucao nao gerou build Windows aprovado.')
    artifacts=[]
    for item in build.get('artifacts',[]):
        path=(root/item['path']).resolve()
        if not path.is_relative_to(root/'NexGrana/dist') or not path.is_file():raise ValueError('Artefato fora do diretorio de build.')
        if path.stat().st_size!=item['size_bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('Hash do build mudou; registro bloqueado.')
        if path.suffix.lower()=='.exe':artifacts.append(path)
    branded=[p for p in artifacts if 'nexgrana' in p.stem.lower()]
    chosen=branded if len(branded)==1 else artifacts
    if len(chosen)!=1:raise ValueError('Executavel principal ambiguo; registro automatico bloqueado.')
    exe=chosen[0];folder=exe.parent
    output=folder.parent/'NexGrana-Windows-QA.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob('*')):
            if path.is_symlink():raise ValueError('Link nao permitido no artefato.')
            if path.is_file():archive.write(path,Path('NexGrana')/path.relative_to(folder))
    return output

def main():
    import httpx
    import launch_authenticated_pipeline as access
    from register_release import register
    state=json.loads((QA/'.runtime/one_click_qa.json').read_text(encoding='utf-8-sig'))
    run_id=state.get('run_id','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',run_id):raise ValueError('Execucao atual nao identificada.')
    report_path=QA/'data/qa_pipeline/runs'/run_id/'pipeline-report.json'
    report=json.loads(report_path.read_text(encoding='utf-8-sig'))
    if report.get('run_id')!=run_id:raise ValueError('Relatorio pertence a outra execucao.')
    artifact=package_windows_build(report,ROOT)
    port=access._port(QA);api=access.LocalAPI(f'http://127.0.0.1:{port}')
    access._check_identity(api,QA);token=access._login(api,QA)
    with httpx.Client(base_url=f'http://127.0.0.1:{port}/api/v1/',timeout=120,follow_redirects=False,trust_env=False) as client:
        receipt=register(client,artifact,'0.24.0-qa-'+run_id[:8],'Windows',token)
    receipt['run_id']=run_id
    (report_path.parent/'release-intake.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print('BUILD REGISTRADO em Releases & QA: ZIP Windows completo, hash confirmado; smoke nativo e publicacao pendentes.')
    print('Arquivo local: '+str(artifact))
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('REGISTRO BLOQUEADO: '+(str(exc) if isinstance(exc,ValueError) else type(exc).__name__))
        raise SystemExit(2)
