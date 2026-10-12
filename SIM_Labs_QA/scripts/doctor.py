"""Read-only diagnostics. No reinstall, database migration or password rotation."""
import ast
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
QA=ROOT/'SIM_Labs_QA'

def probe(command,cwd=ROOT):
    try:
        r=subprocess.run(command,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)
        return {'status':'PASS' if r.returncode==0 else 'FAIL','exit_code':r.returncode,'output':(r.stdout+r.stderr)[-4000:]}
    except (OSError,subprocess.TimeoutExpired) as e:return {'status':'BLOCKED','reason':type(e).__name__}

def diagnose():
    import run_release_pipeline as runner
    report={'host':platform.platform(),'python':sys.version.split()[0],'package':str(ROOT),'manifest':runner.verify_manifest(ROOT),'environment':runner.qa_environment_check(QA)}
    tools={}
    for name,args in [('git',['--version']),('node',['--version']),('npm',['--version']),('java',['-version']),('adb',['version']),('flutter',['doctor','-v'])]:
        path=shutil.which(name);tools[name]=probe([path,*args]) if path else {'status':'NOT_FOUND'}
    if os.name=='nt':
        vswhere=Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
        tools['visual_studio_cpp']=probe([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath']) if vswhere.is_file() else {'status':'NOT_FOUND','action':'Instalar Visual Studio Build Tools com Desktop development with C++ e Windows SDK.'}
    report['tools']=tools
    report['android_sdk']={'configured':bool(os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME')),'build':'NOT_RUN'}
    report['python_environments']={}
    for name,path,modules in [('nex',ROOT/'NexGrana',['flet','flet_cli','flet_charts','flet_camera','flet_secure_storage','supabase','cryptography','PIL','fastapi','uvicorn']),('backend',QA/'backend',['fastapi','uvicorn','sqlalchemy','alembic','pytest','httpx']),('collector',QA/'Collector',['pytest','PIL'])]:
        executable=path/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        code='import importlib.util,json;print(json.dumps({n:bool(importlib.util.find_spec(n)) for n in '+repr(modules)+'}))'
        report['python_environments'][name]=probe([str(executable),'-c',code]) if executable.is_file() else {'status':'NOT_PREPARED','action':'INICIAR.cmd prepara este ambiente ao executar a etapa correspondente.'}
    syntax=[]
    for tree in [ROOT/'NexGrana/src',QA/'backend/app',QA/'scripts']:
        for file in tree.rglob('*.py'):
            try:ast.parse(file.read_text(encoding='utf-8-sig'))
            except (SyntaxError,UnicodeError) as exc:syntax.append({'path':str(file.relative_to(ROOT)),'reason':str(exc)})
    report['syntax']={'status':'PASS' if not syntax else 'FAIL','errors':syntax}
    db=QA/'backend/sim_labs.db'
    if db.exists():
        try:
            with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,timeout=5) as conn:value=conn.execute('PRAGMA quick_check').fetchone()[0]
            report['qa_database']={'status':'PASS' if value=='ok' else 'FAIL','check':value}
        except sqlite3.Error as e:report['qa_database']={'status':'FAIL','reason':type(e).__name__}
    else:report['qa_database']={'status':'NOT_CREATED'}
    runtime=QA/'.runtime';runtime.mkdir(exist_ok=True)
    try:
        check=runtime/'doctor-write-check.tmp';check.write_text('QA');check.unlink();report['runtime_write']='PASS'
    except OSError:report['runtime_write']='FAIL'
    report['assets']={'status':'NOT_RUN','reason':'Pillow nao disponivel no Python deste diagnostico'}
    if importlib.util.find_spec('PIL'):
        from PIL import Image
        images=[];bad=[];hashes={}
        for file in (ROOT/'NexGrana/src/assets').rglob('*'):
            if file.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:continue
            relative=str(file.relative_to(ROOT))
            try:
                with Image.open(file) as im:
                    im.load();images.append({'path':relative,'width':im.width,'height':im.height,'alpha':'A' in im.getbands()})
                hashes.setdefault(hashlib.sha256(file.read_bytes()).hexdigest(),[]).append(relative)
            except Exception as e:bad.append({'path':relative,'reason':type(e).__name__})
        report['assets']={'status':'PASS' if images and not bad else 'BLOCKED','images':images,'invalid':bad,'duplicates':[x for x in hashes.values() if len(x)>1],'visual_edges_and_identity':'MANUAL_REVIEW_REQUIRED'}
    report['native_windows_build']='NOT_RUN' if os.name=='nt' else 'BLOCKED_HOST_LINUX'
    (runtime/'doctor.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DOCTOR: '+str(runtime/'doctor.json'))
    print(json.dumps({k:v for k,v in report.items() if k not in {'assets','python_environments'}},ensure_ascii=False,indent=2))
    return 0 if report['manifest']['status']=='PASS' and report['syntax']['status']=='PASS' and report['environment']['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(diagnose())
