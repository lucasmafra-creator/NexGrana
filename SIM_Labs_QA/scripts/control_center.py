"""Single entry point; credentials stay local and startup verifies actual login."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'SIM_Labs_QA'
RUNTIME=QA/'.runtime'
RUNTIME.mkdir(exist_ok=True)
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_release_pipeline as runner

def backend_python():
    python,state=runner.ensure_python(QA/'backend',QA/'backend/requirements.txt',
        ['fastapi','uvicorn','sqlalchemy','alembic','dotenv','jwt','httpx','pytest','PIL'],True,RUNTIME/'setup','backend')
    if not python: raise RuntimeError('Preparacao bloqueada: '+state.get('reason','ver .runtime/setup'))
    return python

def checked(command,cwd=ROOT):
    result=subprocess.run([str(x) for x in command],cwd=cwd)
    if result.returncode: raise RuntimeError('Etapa falhou (codigo '+str(result.returncode)+'). Consulte a mensagem anterior.')

def start(repair=False,open_browser=True):
    integrity=runner.verify_manifest(ROOT)
    if integrity.get('status')!='PASS':
        reconciled=runner.quarantine_unmanifested_source_files(ROOT)
        if reconciled.get('status')=='PASS':
            integrity=reconciled.get('manifest',{})
            if reconciled.get('quarantined_count'):
                print('Atualizacao sobreposta detectada: '+str(reconciled['quarantined_count'])+' arquivo(s) antigo(s) foram guardados em '+str(reconciled['quarantine_path'])+'.',flush=True)
                print('Senha, banco QA e dados locais foram preservados.',flush=True)
        else:
            mismatches=(reconciled.get('manifest') or integrity).get('mismatches',[])
            details='; '.join(mismatches[:8])
            reason=reconciled.get('reason','')
            suffix=(' Causa: '+reason if reason else '')+(' Divergencias: '+details if details else '')
            raise RuntimeError('Integridade da fonte bloqueada. Nenhum manifesto foi refeito.'+suffix)
    python=backend_python()
    if repair:
        checked([python,QA/'backend/stop_local.py'])
        # bootstrap syncs the hash to the existing password; it does not rotate it.
    if os.name!='nt':raise RuntimeError('Inicializador nativo preparado para Windows; use os testes Linux documentados.')
    checked(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',QA/'START_SIM_LABS_WINDOWS.ps1','-NoBrowser'])
    checked([python,QA/'scripts/validate_qa_startup.py'])
    port=(RUNTIME/'qa_port.txt').read_text().strip()
    url='http://127.0.0.1:'+port
    print('ACESSO VALIDADO. Central desta pasta: '+url,flush=True)
    if open_browser:checked([python,QA/'scripts/open_authenticated_central.py'])
    return python

def doctor():
    python=QA/'backend'/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    return subprocess.call([str(python if python.is_file() else sys.executable),str(QA/'scripts/doctor.py')],cwd=ROOT)

def perform(action):
    if action=='doctor':return doctor()
    if action in ('start','repair'):
        start(repair=action=='repair');return 0
    if action=='access':
        f=RUNTIME/'PRIMEIRO_ACESSO.txt'
        if not f.exists():raise RuntimeError('Inicie a central primeiro para configurar o acesso.')
        if os.name=='nt':subprocess.Popen(['notepad.exe',str(f)])
        else:print('Credencial disponivel apenas no arquivo local; valor nao exibido.')
        return 0
    if action in ('pipeline','build-windows'):
        python=start(open_browser=False)
        checked([python,QA/'scripts/open_authenticated_central.py'])
        code=subprocess.call([str(python),str(QA/'scripts/launch_authenticated_pipeline.py')],cwd=ROOT)
        if code:return code
        return subprocess.call([str(python),str(QA/'scripts/register_pipeline_build.py')],cwd=ROOT)
    if action=='test':
        python=backend_python()
        return subprocess.call([str(python),str(QA/'scripts/run_release_pipeline.py'),'--prepare-deps','--tests-only'],cwd=ROOT)
    if action=='run-nex':
        p,state=runner.ensure_python(ROOT/'NexGrana',ROOT/'NexGrana/requirements-qa.txt',['flet','flet_charts','flet_camera','flet_secure_storage','supabase','cryptography','PIL','fastapi','uvicorn'],True,RUNTIME/'setup','nex')
        if not p:raise RuntimeError(state.get('reason','Ambiente Nex indisponivel'))
        storage=RUNTIME/'nex-preview'
        storage.mkdir(exist_ok=True)
        # Use a local disconnected endpoint until a staging environment is configured.
        config=storage/'cloud_config.json'
        if not config.exists():config.write_text(json.dumps({'url':'http://127.0.0.1:9','anon_key':'QA_OFFLINE_NOT_A_REAL_KEY'}))
        print('PREVIEW OFFLINE: abre a interface; login financeiro exige staging configurado. Nenhum dado de producao sera acessado.')
        env={**os.environ,'APP_ENV':'test','FLET_APP_STORAGE_DATA':str(storage)}
        return subprocess.call([str(p),'src/main.py'],cwd=ROOT/'NexGrana',env=env)
    raise ValueError(action)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',nargs='?',default='menu')
    args=parser.parse_args()
    if args.action!='menu':return perform(args.action)
    options={'1':'start','2':'doctor','3':'test','4':'build-windows','5':'pipeline','6':'run-nex','7':'access','8':'repair'}
    while True:
        print('\nNEXGRANA + SIM LABS QA — RESGATE\n1 Abrir central\n2 Doctor\n3 Testar NexGrana + SIM Labs\n4 Testar, gerar e registrar Windows\n5 Pipeline completo\n6 Abrir NexGrana QA (preview offline)\n7 Ver senha local\n8 Reparar acesso preservando senha\n0 Sair',flush=True)
        choice=input('Escolha: ').strip()
        if choice=='0':return 0
        if choice not in options:continue
        try:
            code=perform(options[choice]);print('ETAPA CONCLUIDA' if code==0 else 'ETAPA BLOQUEADA/FALHOU — veja o relatorio; nao aprovada.')
        except Exception as exc: print('FALHA: '+str(exc))
        input('Enter para voltar ao menu...')
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print('FALHA: '+str(exc));raise SystemExit(2)
