"""Manual trusted-source QA/patch runner. Folder isolation is NOT an OS sandbox."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

SKIP={".git",".venv","venv","node_modules","__pycache__",".runtime","data",".data","scratch","dist","release","backups"}
def allowed_files(root):
    for current,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if d not in SKIP and not (Path(current)/d).is_symlink()]
        for name in files:
            path=Path(current)/name
            if path.is_symlink() or name.startswith(".env") or path.suffix.lower() in {".db",".sqlite",".sqlite3",".log",".pid",".pyc"}:continue
            yield path

def inventory(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in allowed_files(root)}

def patch_paths(text):
    paths=[]
    for line in text.splitlines():
        if line.startswith(('GIT binary patch','Binary files','rename from ','rename to ','copy from ','copy to ')) or 'mode 120000' in line:
            raise ValueError('Patch binário, rename, copy e symlink não permitidos')
        if line.startswith('diff --git '):
            tokens=line.split()
            if len(tokens)!=4:raise ValueError('Caminhos de patch precisam ser simples e sem aspas')
            for raw in tokens[2:]:
                path=PurePosixPath(raw[2:])
                if not raw.startswith(('a/','b/')) or path.is_absolute() or '..' in path.parts or '\\' in raw or path.suffix!='.py' or not path.parts or path.parts[0] not in {'src','tests'}:
                    raise ValueError('Diff fora dos arquivos Python permitidos')
        if line.startswith(("--- ","+++ ")):
            raw=line[4:].split("\t",1)[0]
            if raw=="/dev/null":continue
            if not raw.startswith(("a/","b/")):raise ValueError("Patch precisa de caminhos a/ e b/ sem aspas")
            path=PurePosixPath(raw[2:])
            if path.is_absolute() or ".." in path.parts or "\\" in raw or path.suffix!=".py" or path.parts[0] not in {"src","tests"}:
                raise ValueError("Patch permitido somente em arquivos Python de src/ e tests/")
            paths.append(path.as_posix())
    if not paths:raise ValueError("Patch sem arquivos Python reconhecidos")
    return sorted(set(paths))

def stop_owned_process(proc):
    if proc.poll() is not None:return
    if os.name=="nt":
        subprocess.run(["taskkill","/PID",str(proc.pid),"/T","/F"],capture_output=True,timeout=15,check=False)
    else:
        os.killpg(proc.pid,signal.SIGKILL)
    proc.wait(timeout=15)

def run_fixed(command,cwd,env,timeout):
    import threading
    chunks=[];limit=2*1024*1024;size=0;overflow=[]
    proc=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                          start_new_session=os.name!="nt",creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=="nt" else 0)
    def collect():
        nonlocal size
        while block:=proc.stdout.read(4096):
            size+=len(block)
            if size>limit:
                overflow.append(True);stop_owned_process(proc);break
            chunks.append(block)
    reader=threading.Thread(target=collect,daemon=True);reader.start()
    timed_out=False
    try:proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:timed_out=True;stop_owned_process(proc)
    reader.join(timeout=10);proc.stdout.close()
    text=b"".join(chunks).decode("utf-8","replace")
    text=re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}","[e-mail redigido]",text)
    text=re.sub(r"(?i)(password|senha|token|api_key|authorization)\s*[:=]\s*\S+",r"\1=[redigido]",text)
    return {"command":command,"exit_code":proc.returncode,"status":"FAIL" if timed_out or overflow or proc.returncode else "PASS","timed_out":timed_out,"output_limit_exceeded":bool(overflow),"log":text}

def execute(source,python,patch=None,timeout=900):
    source=Path(source).resolve();python=Path(python).absolute()
    # Preserve the venv symlink path: resolving it selects the base interpreter.
    if not (source/"src/main.py").is_file() or not (source/"tests").is_dir():raise ValueError("Fonte NexGrana com src/main.py e tests/ necessária")
    if not python.is_file():raise ValueError("Interpretador Python configurado ausente")
    before=inventory(source)
    report={"schema":"sim-labs.trusted-source-run/1.0","source_manifest_sha256":hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),"started_at":time.strftime("%Y-%m-%dT%H:%M:%S%z"),"network_isolation":False,"filesystem_sandbox":False,"mode":"MANUAL_TRUSTED_CODE","checks":[],"patch_applied_to_official_source":False}
    with tempfile.TemporaryDirectory(prefix="sim-nex-qa-") as folder:
        root=Path(folder)/"source";root.mkdir()
        for file in allowed_files(source):
            target=root/file.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
        env={k:v for k,v in os.environ.items() if k in {"PATH","SystemRoot","WINDIR","TEMP","TMP","HOME","USERPROFILE","LANG"}}
        env.update(PYTHONIOENCODING="utf-8",FLET_APP_STORAGE_DATA=str(Path(folder)/"test-state"),NEX_ONLINE_ENABLED="0")
        if patch:
            text=Path(patch).read_text(encoding="utf-8");report["patch_paths"]=patch_paths(text)
            candidate=Path(folder)/"candidate.patch";candidate.write_text(text,encoding="utf-8")
            git=shutil.which("git")
            if not git:raise ValueError("Git ausente para conferir o patch")
            check=run_fixed([git,"apply","--check",str(candidate)],root,env,30);report["checks"].append(check)
            if check["status"]!="PASS":report["status"]="FAIL";return report
            applied=run_fixed([git,"apply",str(candidate)],root,env,30);report["checks"].append(applied)
            if applied["status"]!="PASS":report["status"]="FAIL";return report
            report["patch_sha256"]=hashlib.sha256(text.encode()).hexdigest()
        failures=[]
        for file in root.rglob("*.py"):
            try:ast.parse(file.read_text(encoding="utf-8-sig"),filename=file.relative_to(root).as_posix())
            except (SyntaxError,UnicodeError) as exc:failures.append({"file":file.relative_to(root).as_posix(),"error":type(exc).__name__})
        report["checks"].append({"kind":"python_syntax","status":"FAIL" if failures else "PASS","findings":failures})
        if not failures:
            report["checks"].append(run_fixed([str(python),"-m","unittest","discover","-s","tests","-v"],root,env,timeout))
        after=inventory(root)
        report["changed_files"]=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
    report["official_source_unchanged"]=before==inventory(source)
    report["status"]="PASS" if report["official_source_unchanged"] and all(c["status"]=="PASS" for c in report["checks"]) else "FAIL"
    report["finished_at"]=time.strftime("%Y-%m-%dT%H:%M:%S%z")
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source");parser.add_argument("--python",default=sys.executable)
    parser.add_argument("--patch");parser.add_argument("--timeout",type=int,default=900)
    parser.add_argument("--report",default="nexgrana-run-report.json")
    parser.add_argument("--allow-trusted-code",action="store_true")
    args=parser.parse_args()
    if not args.allow_trusted_code:parser.error("Execução manual exige --allow-trusted-code. Sem sandbox do SO, não execute código recebido de terceiros.")
    if not 1<=args.timeout<=1800:parser.error("Timeout permitido: 1 a 1800 segundos")
    report=execute(args.source,args.python,args.patch,args.timeout)
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Resultado:",report["status"],"— fonte oficial preservada; relatório:",args.report)
    return 0 if report["status"]=="PASS" else 1

if __name__=="__main__":raise SystemExit(main())
