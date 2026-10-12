"""Bounded process watchdog. Only owns children created by this supervisor."""
from pathlib import Path
import os, signal, subprocess, sys, time, json, urllib.request
STOP=False
ROOT=Path(__file__).resolve().parents[2]
RUNTIME=ROOT/'.runtime'
RUNTIME.mkdir(exist_ok=True)
INSTANCE_TEXT=ROOT.as_posix().lower().rstrip('/')
import hashlib
INSTANCE_ID=hashlib.sha256(INSTANCE_TEXT.encode()).hexdigest()[:16]
EXPECTED_SERVICE='sim-labs-control-center-qa'
EXPECTED_PHASE='Engine 0.4.1-qa.2'

def _port():
    try:
        value=int(os.getenv('SIM_LABS_PORT','8000'))
    except ValueError as exc:
        raise SystemExit('SIM_LABS_PORT invalida') from exc
    if not 1024 <= value <= 65535:
        raise SystemExit('SIM_LABS_PORT fora da faixa permitida')
    return value

PORT=_port()
BASE_URL=f'http://127.0.0.1:{PORT}'

def stop(*_):
    global STOP
    STOP=True

def terminate_owned(p):
    if p.poll() is not None: return
    if os.name=='nt': subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else: p.terminate()

def main():
    lockfile=open(RUNTIME/'supervisor.lock','a+b')
    try:
        if os.name=='nt':
            import msvcrt
            lockfile.seek(0); lockfile.write(b'0'); lockfile.flush(); lockfile.seek(0); msvcrt.locking(lockfile.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lockfile,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        print('Supervisor desta pasta ja esta ativo.',flush=True); return
    signal.signal(signal.SIGINT,stop); signal.signal(signal.SIGTERM,stop)
    (RUNTIME/'supervisor.pid').write_text(str(os.getpid()))
    (RUNTIME/'qa_port.txt').write_text(str(PORT))
    commands={'api':[sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(PORT)],'worker':[sys.executable,'-m','app.worker'],'engine':[sys.executable,'-m','app.engine']}
    children={}; attempts={k:0 for k in commands}; next_at={k:0 for k in commands}; started={}; bad={k:0 for k in commands}; handles=[]
    try:
        while not STOP:
            for name,args in commands.items():
                p=children.get(name)
                if p and p.poll() is not None:
                    attempts[name]+=1; next_at[name]=time.monotonic()+min(300,2**attempts[name]*2); children.pop(name); p=None
                if p and time.monotonic()-started[name]>30:
                    healthy=True
                    if name=='api':
                        try:
                            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(BASE_URL+'/api/v1/health',timeout=2) as r:
                                data=json.load(r); healthy=(data.get('service')==EXPECTED_SERVICE and data.get('phase')==EXPECTED_PHASE and data.get('instance_id')==INSTANCE_ID)
                        except Exception: healthy=False
                    else:
                        try:
                            from .db import SessionLocal
                            from .models import WorkerState, now
                            from .engine_models import EngineConfig
                            from datetime import timezone
                            with SessionLocal() as db:
                                row=db.get(EngineConfig,'scheduler') if name=='engine' else db.get(WorkerState,'main')
                                healthy=bool(row and (now()-row.heartbeat_at.replace(tzinfo=timezone.utc)).total_seconds()<180)
                        except Exception: healthy=False
                    bad[name]=0 if healthy else bad[name]+1
                    if bad[name]>=3:
                        print('watchdog_restart='+name,flush=True); terminate_owned(p); bad[name]=0
                    elif healthy and time.monotonic()-started[name]>600: attempts[name]=0
                if not p and attempts[name]<5 and time.monotonic()>=next_at[name]:
                    out=open(RUNTIME/(name+'.log'),'a',encoding='utf-8'); err=open(RUNTIME/(name+'.err.log'),'a',encoding='utf-8'); handles.extend([out,err])
                    p=subprocess.Popen(args,cwd=ROOT/'backend',stdout=out,stderr=err); children[name]=p; started[name]=time.monotonic()
                    (RUNTIME/(name+'.pid')).write_text(str(p.pid))
                if attempts[name]>=5:
                    from .db import SessionLocal
                    from .engine import incident
                    with SessionLocal() as db: incident(db,'supervisor:'+name,'Reinicios esgotados: '+name,'P1'); db.commit()
            (RUNTIME/'status_24_7.json').write_text(json.dumps({'timestamp':time.time(),'supervisor':os.getpid(),'port':PORT,'children':{k:{'pid':p.pid,'alive':p.poll() is None,'retries':attempts[k]} for k,p in children.items()},'blocked':[k for k,v in attempts.items() if v>=5]}))
            time.sleep(3)
    finally:
        for p in children.values():
            if p.poll() is None: terminate_owned(p)
        for p in children.values():
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill(); p.wait()
        for f in handles: f.close()
if __name__=='__main__': main()
