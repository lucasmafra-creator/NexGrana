"""Register only a successful, hash-matching NexGrana build, without launching it."""
import argparse,json,hashlib,subprocess,sys
from pathlib import Path

def select_artifact(report,target):
    path=Path(report).resolve();rows=json.loads(path.read_text(encoding='utf8'))
    result=next((r for r in rows if r.get('target')==target),None)
    if not result or result.get('status')!='built':raise ValueError('Build não concluído; registro bloqueado')
    root=path.parent
    candidates=[]
    for record in result.get('artifact_metadata',[]):
        file=(root/record['path']).resolve()
        if not file.is_relative_to(root) or not file.is_file():raise ValueError('Artefato ausente ou fora do diretório de build')
        if file.stat().st_size!=record['size_bytes'] or hashlib.sha256(file.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError('Artefato alterado após o build')
        candidates.append(file)
    expected='.exe' if target=='windows' else '.apk'
    candidates=[p for p in candidates if p.suffix.lower()==expected]
    branded=[p for p in candidates if 'nexgrana' in p.stem.casefold()]
    if len(branded)==1:return branded[0]
    if len(candidates)==1:return candidates[0]
    raise ValueError('Mais de um artefato; selecione o arquivo principal pelo REGISTRAR_BUILD.bat')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_report');parser.add_argument('--version',required=True)
    parser.add_argument('--target',choices=['windows','apk'],default='windows')
    parser.add_argument('--endpoint',default='http://127.0.0.1:8000/api/v1');
    parser.add_argument('--runner-report');parser.add_argument('--receipt',default='release-intake-report.json')
    args=parser.parse_args();artifact=select_artifact(args.build_report,args.target)
    command=[sys.executable,str(Path(__file__).with_name('register_release.py')),str(artifact),'--version',args.version,
             '--platform','Windows' if args.target=='windows' else 'Android','--report',args.receipt,'--endpoint',args.endpoint]
    if args.runner_report:command.extend(['--runner-report',args.runner_report])
    return subprocess.run(command,check=False).returncode
if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError) as exc:print('Registro bloqueado:',str(exc));raise SystemExit(1)
