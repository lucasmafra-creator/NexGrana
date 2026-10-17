"""Read-only native QA preflight. Never installs, logs in or publishes."""
import argparse,hashlib,json,platform,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

def check(command,timeout=45):
 try:
  r=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
  return {'status':'PASS' if r.returncode==0 else 'BLOCKED','exit_code':r.returncode}
 except (OSError,subprocess.TimeoutExpired) as exc:return {'status':'BLOCKED','reason':type(exc).__name__}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--report',default='native-environment-report.json');args=parser.parse_args()
 flutter=shutil.which('flutter');adb=shutil.which('adb')
 gates={'windows_host':{'status':'PASS' if platform.system()=='Windows' else 'BLOCKED'},
 'flutter_doctor':check([flutter,'doctor','-v']) if flutter else {'status':'BLOCKED','reason':'Flutter ausente'},
 'adb':{'status':'BLOCKED','reason':'ADB ausente'},
 'physical_device_tests':{'status':'MANUAL_REQUIRED'},'supabase_staging':{'status':'MANUAL_REQUIRED'},
 'installed_sim_labs_comparison':{'status':'MANUAL_REQUIRED'}}
 if adb:
  r=subprocess.run([adb,'devices'],capture_output=True,text=True,timeout=15)
  devices=[line.split()[0] for line in r.stdout.splitlines()[1:] if len(line.split())==2 and line.split()[1]=='device']
  gates['adb']={'status':'PASS' if r.returncode==0 else 'BLOCKED','authorized_device_count':len(devices),
                'device_identifiers_sha256':[hashlib.sha256(x.encode()).hexdigest() for x in devices]}
 report={'created_at':datetime.now(timezone.utc).isoformat(),'host':platform.system(),'python':platform.python_version(),
 'gates':gates,'build_generated':False,'installed':False,'device_tested':False}
 Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print('Relatório criado. PASS de ferramenta não significa app instalado ou homologado.')
 return 0 if all(gates[x]['status']=='PASS' for x in ('windows_host','flutter_doctor','adb')) else 2
if __name__=='__main__':raise SystemExit(main())
