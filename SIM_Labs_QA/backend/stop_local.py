"""Stop verified QA processes; re-query after supervisor tree termination."""
import json
import os
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
MODULE = re.compile(r'(?:^|\s)-m\s+(?:app\.(?:supervisor|worker|engine)(?:\s|$)|uvicorn\s+app\.main:app(?:\s|$))')

def owned_windows(row, root=ROOT):
    command = str(row.get('CommandLine') or '').strip()
    expected = str(root / 'backend' / '.venv' / 'Scripts' / 'python.exe').lower()
    lower = command.lower()
    return (lower.startswith('"'+expected+'" ') or lower.startswith(expected+' ')) and bool(MODULE.search(command))

def windows_processes():
    code = 'Get-CimInstance Win32_Process -Filter "name=\'python.exe\'" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress'
    result = subprocess.run(['powershell.exe','-NoProfile','-Command',code], capture_output=True,text=True,check=True)
    value = json.loads(result.stdout or '[]')
    return [value] if isinstance(value,dict) else (value or [])

def stop_windows(query=windows_processes, terminate=None, pause=time.sleep):
    if terminate is None:
        def terminate(pid):
            # Native stderr stays in Python: PS5.1 cannot turn benign taskkill output into an exception.
            return subprocess.run(['taskkill.exe','/PID',str(pid),'/T','/F'],capture_output=True).returncode
    targets = sorted((r for r in query() if owned_windows(r)),key=lambda r:'app.supervisor' not in r['CommandLine'])
    for row in targets:
        pid = row['ProcessId']
        # Validate again: the previous /T may have already ended this child or its PID may have changed owner.
        if not any(r['ProcessId']==pid and owned_windows(r) for r in query()):
            continue
        terminate(pid)
    for _ in range(15):
        if not any(owned_windows(r) for r in query()):
            return 0
        pause(1)
    print('STOP=FAIL: processos desta copia ainda ativos; nenhuma credencial foi alterada.')
    return 1

def main():
    if os.name == 'nt':
        code=stop_windows()
    else:
        targets=[]
        for proc in Path('/proc').glob('[0-9]*'):
            try:
                if (proc/'cwd').resolve() != ROOT/'backend': continue
                cmd=(proc/'cmdline').read_bytes().decode().replace('\0',' ')
                if MODULE.search(cmd):targets.append((int(proc.name),cmd))
            except (OSError,UnicodeError): pass
        for pid,cmd in sorted(targets,key=lambda x:'app.supervisor' not in x[1]):
            try:os.kill(pid,15)
            except ProcessLookupError:pass
        code=0
    if not code: print('STOP=PASS: processos QA encerrados ou ja ausentes; dados preservados.')
    return code
if __name__=='__main__':
    raise SystemExit(main())
