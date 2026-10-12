import sqlite3,zipfile,time,os
from dotenv import dotenv_values
from sqlalchemy.engine import make_url
from contextlib import closing
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2]
def database_path():
    configured=os.getenv('DATABASE_URL') or dotenv_values(ROOT/'.env').get('DATABASE_URL') or 'sqlite:///./sim_labs.db'
    url=make_url(configured)
    if url.get_backend_name()!='sqlite' or not url.database or url.database==':memory:':
        raise ValueError('Backup local exige um arquivo SQLite configurado')
    path=Path(url.database)
    return path if path.is_absolute() else ROOT/'backend'/path

def main():
    database=database_path()
    if not database.is_file():
        raise FileNotFoundError('Banco SQLite configurado ausente; backup não concluído')
    dest=ROOT/'backups';dest.mkdir(exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    snapshot=dest/('database_'+stamp+'.db')
    if database.exists():
        # Connection context managers commit/rollback; they do not close.
        with closing(sqlite3.connect(database)) as source,closing(sqlite3.connect(snapshot)) as backup:
            with backup:
                source.backup(backup)
    out=dest/('SIM_Labs_Backup_'+stamp+'.zip')
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        if snapshot.exists():archive.write(snapshot,'backend/sim_labs.db')
        for folder in ('data','Collector/data','.runtime'):
            source=ROOT/folder
            if source.exists():
                for file in source.rglob('*'):
                    if file.is_file() and file.suffix not in {'.pid','.log'}:archive.write(file,file.relative_to(ROOT).as_posix())
        if (ROOT/'.env').exists():archive.write(ROOT/'.env','.env')
    with zipfile.ZipFile(out) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('Backup inválido; snapshot preservado para revisão.')
    remove_snapshot(snapshot)
    print('Backup completo criado: '+str(out))
    print('Inclui configuracao privada, banco local e evidencias. Guarde no seu computador.')

def remove_snapshot(snapshot):
    """Retry transient antivirus locks; preserve the snapshot if still locked."""
    for attempt in range(4):
        try:
            snapshot.unlink(missing_ok=True)
            return True
        except PermissionError:
            if attempt < 3:
                time.sleep(0.1 * (attempt + 1))
    print('Snapshot preservado: outro processo ainda mantém o arquivo aberto.')
    return False
if __name__=='__main__':main()
