"""Local QA bootstrap with stable, persistent local credentials.

The clear-text local password is kept only in .runtime/PRIMEIRO_ACESSO.txt.
The .env stores only its PBKDF2 hash. Re-running bootstrap never rotates an
existing password; if the hash drifted, it is synchronized to the password
already stored in PRIMEIRO_ACESSO.txt.
"""
from pathlib import Path
import json, os, secrets, sqlite3, sys
from datetime import datetime
from contextlib import closing
from dotenv import dotenv_values
from .local_auth import hash_password, verify_password

ROOT=Path(__file__).resolve().parents[2]

def _qa_port() -> int:
    try:
        port=int(str(os.getenv("SIM_LABS_PORT","8000")).strip())
    except ValueError as exc:
        raise SystemExit("SIM_LABS_PORT invalida") from exc
    if not 1024 <= port <= 65535:
        raise SystemExit("SIM_LABS_PORT fora da faixa permitida")
    return port

def _read_persisted_password(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("Senha:"):
                return line.split(":",1)[1].strip()
    except OSError:
        return ""
    return ""

def _write_first_access(path: Path, password: str, base_url: str) -> None:
    path.write_text(
        "SIM Labs QA — primeiro acesso local\n"
        "Senha: "+password+"\n"
        "URL: "+base_url+"\n"
        "Guarde este arquivo no seu computador; não compartilhe.\n",
        encoding="utf-8",
    )

def _sync_first_access_url(path: Path, base_url: str) -> None:
    if not path.is_file():
        return
    lines=path.read_text(encoding="utf-8-sig").splitlines()
    output=[]; found=False
    for line in lines:
        if line.startswith("URL:"):
            output.append("URL: "+base_url); found=True
        else:
            output.append(line)
    if not found:
        output.append("URL: "+base_url)
    path.write_text("\n".join(output)+"\n",encoding="utf-8")

def _write_env_atomic(path: Path, values: dict) -> None:
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text("\n".join(f"{k}={v}" for k,v in values.items() if v is not None)+"\n",encoding="utf-8")
    temp.replace(path)

def main():
    if sys.version_info<(3,11):
        raise SystemExit("Use Python 3.11 ou superior (recomendado 3.14 ou 3.12).")
    runtime=ROOT/".runtime"; runtime.mkdir(exist_ok=True)
    port=_qa_port(); base_url=f"http://127.0.0.1:{port}"
    (runtime/"qa_port.txt").write_text(str(port),encoding="ascii")
    envfile=ROOT/".env"
    first_access=runtime/"PRIMEIRO_ACESSO.txt"
    values=dict(dotenv_values(envfile)) if envfile.exists() else {}
    if values.get("APP_ENV","local") not in {"local","dev","test"}:
        raise SystemExit("Este iniciador atende ambiente local/QA. Use a documentação de produção para servidores.")

    persisted_password=_read_persisted_password(first_access)
    stored_hash=str(values.get("LOCAL_ADMIN_PASSWORD_HASH") or "").strip()
    credential_state="preserved"
    if persisted_password:
        if not stored_hash or not verify_password(persisted_password,stored_hash):
            values["LOCAL_ADMIN_PASSWORD_HASH"]=hash_password(persisted_password)
            credential_state="synchronized"
        _sync_first_access_url(first_access,base_url)
    elif not stored_hash:
        password=secrets.token_urlsafe(14)
        _write_first_access(first_access,password,base_url)
        values["LOCAL_ADMIN_PASSWORD_HASH"]=hash_password(password)
        credential_state="created-once"
    else:
        credential_state="hash-preserved-first-access-file-missing"

    if not values.get("SESSION_SIGNING_KEY"):
        values["SESSION_SIGNING_KEY"]=secrets.token_urlsafe(48)
    if not values.get("FEEDBACK_INGEST_TOKEN"):
        values["FEEDBACK_INGEST_TOKEN"]=secrets.token_urlsafe(48)
    values.update({
        "APP_ENV":"local",
        "AUTO_INIT_DB":"0",
        "ALLOW_DEV_ACTORS":"0",
        "INGEST_PRODUCT_SLUG":"nexgrana",
        "STORAGE_DIR":"../data/private",
    })
    values.setdefault("DATABASE_URL","sqlite:///./sim_labs.db")
    _write_env_atomic(envfile,values)

    connection={"endpoint":base_url+"/api/v1","token":values["FEEDBACK_INGEST_TOKEN"]}
    (runtime/"collector_connection.json").write_text(json.dumps(connection),encoding="utf-8")

    import subprocess
    env={**os.environ,**values,"SIM_LABS_PORT":str(port)}
    if values["DATABASE_URL"].startswith("sqlite:///"):
        db_path=Path(values["DATABASE_URL"][10:])
        if not db_path.is_absolute():
            db_path=(ROOT/"backend"/db_path).resolve()
        if db_path.exists():
            backup_dir=ROOT/"backups"; backup_dir.mkdir(exist_ok=True)
            dest=backup_dir/("sim_labs_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".db")
            with closing(sqlite3.connect(db_path)) as source, closing(sqlite3.connect(dest)) as backup:
                with backup:
                    source.backup(backup)
            print("Backup operacional criado antes da migração.")

    subprocess.run([sys.executable,"-m","alembic","upgrade","head"],cwd=ROOT/"backend",env=env,check=True)
    subprocess.run([sys.executable,"-m","app.seed"],cwd=ROOT/"backend",env=env,check=True)
    print("Credencial local estável: "+credential_state+". Valor não exibido.")
    print("Central QA preparada. Nenhuma alteração aplicada ao banco do NexGrana.")

if __name__=="__main__":
    main()
