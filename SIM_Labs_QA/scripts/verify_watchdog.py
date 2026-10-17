"""Linux process-restart validation on a disposable copy; Windows remains unvalidated."""
from pathlib import Path
import os, sys, tempfile, shutil, subprocess, time, signal, json
ROOT=Path(__file__).resolve().parents[1]
def wait_for(fn,seconds=25):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        if value:=fn(): return value
        time.sleep(.2)
    raise AssertionError('Watchdog check timed out')
def main():
    if os.name=='nt': raise SystemExit('Este probe foi preparado para Linux; use o checklist Windows.')
    with tempfile.TemporaryDirectory(prefix='sim_watchdog_') as folder:
        root=Path(folder)
        shutil.copytree(ROOT/'backend',root/'backend',ignore=shutil.ignore_patterns('.venv','__pycache__','*.db*','tests','.pytest_cache'))
        env={**os.environ,'APP_ENV':'test','AUTO_INIT_DB':'0','DATABASE_URL':'sqlite:///'+str(root/'ops.db'),'STORAGE_DIR':str(root/'private'),'SIM_AI_PROVIDER':'none'}
        for module,args in [('alembic',['upgrade','head']),('app.seed',[])]:
            subprocess.run([sys.executable,'-m',module,*args],cwd=root/'backend',env=env,check=True,capture_output=True)
        with (root/'test.log').open('w') as log:
            supervisor=subprocess.Popen([sys.executable,'-m','app.supervisor'],cwd=root/'backend',env=env,stdout=log,stderr=log,start_new_session=True)
            try:
                runtime=root/'.runtime'
                def pid(name):
                    try: return int((runtime/(name+'.pid')).read_text())
                    except (OSError,ValueError): return None
                def state():
                    try:return json.loads((runtime/'status_24_7.json').read_text())
                    except (OSError,ValueError):return {}
                def owned_worker():
                    value=state().get('children',{}).get('worker',{})
                    candidate=pid('worker')
                    if not candidate or value.get('pid')!=candidate or not value.get('alive'):return None
                    try:os.kill(candidate,0)
                    except ProcessLookupError:return None
                    return candidate
                # Registered children in this disposable invocation; works in PID namespaces.
                old=wait_for(owned_worker)
                os.kill(old,signal.SIGKILL)
                new=wait_for(lambda:owned_worker() if owned_worker()!=old else None)
                assert state()['children']['engine']['alive']
                print('WATCHDOG LINUX PASS: own worker process killed, restarted with different PID; engine stays alive; source and data in disposable copy.')
            finally:
                supervisor.terminate()
                try: supervisor.wait(timeout=12)
                except subprocess.TimeoutExpired: os.killpg(supervisor.pid,signal.SIGKILL);supervisor.wait()
if __name__=='__main__':main()
