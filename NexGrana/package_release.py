"""Package a tested NexGrana source candidate with a verifiable manifest."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

PROJECT=Path(__file__).resolve().parent
VERSION="0.24.0"
PACKAGE_ROOT="NexGrana_0_24_0_WINDOWS_ANDROID_VISUAL_RC6"
ARCHIVE_NAME=PACKAGE_ROOT+"_CODIGO_FONTE.zip"
GOLDEN_HASH="4fc4e9996f571e75279936030acdb9d51ebc9d0626b1352b50fe461f09563796"
SKIP={".git",".venv","venv","node_modules","build","dist","release","__pycache__",".data",".pytest_cache","scratch"}


def digest(path):
    h=sha256()
    with path.open("rb") as source:
        for block in iter(lambda:source.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def sources():
    for path in sorted(PROJECT.rglob("*")):
        rel=path.relative_to(PROJECT)
        if not path.is_file() or path.is_symlink() or any(part in SKIP for part in rel.parts):continue
        if path.suffix.lower() in {".pyc",".pyo",".zip",".log",".bak"}:continue
        if path.name.startswith((".env","MANIFEST_RELEASE_")):continue
        yield path,rel


def main():
    if digest(PROJECT/"src/assets/nex/nex_hd.png")!=GOLDEN_HASH:
        raise RuntimeError("Golden Nex mudou; interrompendo pacote")
    run=subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-q"],
                       cwd=PROJECT,capture_output=True,text=True,check=False)
    summary=run.stdout+run.stderr
    match=re.search(r"Ran (\d+) tests?",summary)
    if run.returncode or not match:
        raise RuntimeError("Suíte falhou; pacote cancelado:\n"+summary[-3000:])
    sql=subprocess.run(["node","tests/test_sql.mjs"],cwd=PROJECT,capture_output=True,text=True,check=False)
    if sql.returncode:
        raise RuntimeError("Migrações/RLS em PGlite falharam; pacote cancelado:\n"+(sql.stdout+sql.stderr)[-3000:])
    files=list(sources())
    manifest={"product":"NexGrana","version":VERSION,"channel":"QA_VISUAL_RC6_WINDOWS_ANDROID",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "validation":{"python_tests":int(match.group(1)),"python_suite":"passed",
                      "windows_build":"blocked on Linux; no EXE", "android_apk":"not generated; Flutter setup timed out",
                      "nex_online":"frozen; local fallback", "sql_migrations":"PGlite local passed; not applied to Supabase QA",
                      "device_smoke":"not performed", "localization":"Portuguese only; English/Spanish pending"},
        "golden_nex_sha256":GOLDEN_HASH,
        "files":[{"path":relative.as_posix(),"bytes":path.stat().st_size,"sha256":digest(path)}
                 for path,relative in files]}
    manifest_path=PROJECT/"MANIFEST_RELEASE_0_24_0.json"
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    release=PROJECT/"release"
    release.mkdir(exist_ok=True)
    target=release/ARCHIVE_NAME
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for source,relative in files+[(manifest_path,Path(manifest_path.name))]:
            archive.write(source,f"{PACKAGE_ROOT}/project/{relative.as_posix()}")
    from verificar_pacote import verify
    verify(target)
    checksum=release/"SHA256SUMS_0_24_0_VISUAL_RC6.txt"
    checksum.write_text(f"{digest(target)}  {target.name}\n",encoding="utf-8")
    print(json.dumps({"zip":str(target),"sha256":digest(target),"tests_passed":int(match.group(1)),
                      "checksum":str(checksum),"windows":"not built","android":"not built"},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
