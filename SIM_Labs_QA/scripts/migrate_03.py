"""Copy operational 0.3 data into a fresh 0.4 folder, never touch financial data."""
import json, sqlite3, sys, shutil, subprocess, os
from pathlib import Path
from contextlib import closing
ROOT=Path(__file__).resolve().parents[1]
def migrate(source,dest):
    source=source.resolve();dest=dest.resolve()
    if source==dest: raise ValueError('Use pastas diferentes')
    if not (source/'backend/app/integration_models.py').exists(): raise ValueError('Origem nao parece SIM Labs 0.3 integrado')
    if (dest/'backend/sim_labs.db').exists() or (dest/'.env').exists(): raise ValueError('Destino ja inicializado: nao sobrescrever dados existentes. Extraia outra pasta nova.')
    for name in ('supervisor','api','worker','engine'):
        file=source/'.runtime'/(name+'.pid')
        if file.exists():
            try:
                pid=int(file.read_text())
                if os.name=='nt':
                    cmd=subprocess.run(['powershell','-NoProfile','-Command',f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine'],capture_output=True,text=True,check=True).stdout
                    alive=str(source).lower() in cmd.lower()
                else: alive=Path(f'/proc/{pid}').exists()
                if alive: raise ValueError('Pare a versao 0.3 com PARAR_SIM_LABS.bat antes da copia')
            except (OSError,ValueError) as e:
                if isinstance(e,ValueError) and 'Pare a versao' in str(e): raise
    env=source/'.env'
    if env.exists():
        entries=dict(line.split('=',1) for line in env.read_text().splitlines() if '=' in line and not line.startswith('#'))
        if entries.get('DATABASE_URL','sqlite:///./sim_labs.db')!='sqlite:///./sim_labs.db': raise ValueError('Banco personalizado: migracao automatica bloqueada; revisar local e backup')
        shutil.copyfile(env,dest/'.env')
    old=source/'backend/sim_labs.db';new=dest/'backend/sim_labs.db'
    if not old.exists(): raise ValueError('Banco operacional da origem ausente')
    with closing(sqlite3.connect(old)) as db,closing(sqlite3.connect(new)) as target, target:
        db.backup(target)
        version=target.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        if version!='0003_integrated': raise ValueError('Origem precisa estar em 0003_integrated')
        for table in ('artifacts','evidence'):
            for id,path in target.execute(f'SELECT id,path FROM {table}').fetchall():
                try: relative=Path(path).relative_to(source)
                except ValueError: raise ValueError('Evidencia fora da pasta da origem: preserve e revise os caminhos antes de migrar')
                target.execute(f'UPDATE {table} SET path=? WHERE id=?',(str(dest/relative),id))
    for name in ('data','Collector/data'):
        olddir=source/name
        if olddir.exists(): shutil.copytree(olddir,dest/name,dirs_exist_ok=True)
    runtime=dest/'.runtime'; runtime.mkdir(exist_ok=True)
    for name in ('PRIMEIRO_ACESSO.txt','collector_connection.json'):
        f=source/'.runtime'/name
        if f.exists(): shutil.copyfile(f,runtime/name)
    # Collector JSON may contain absolute attachment paths inside the old root.
    for f in (dest/'Collector/data').rglob('*.json'):
        text=f.read_text(encoding='utf-8')
        text=text.replace(json.dumps(str(source))[1:-1],json.dumps(str(dest))[1:-1])
        f.write_text(text,encoding='utf-8')
    print('Copia 0.3 concluida. Origem preservada. Execute INICIAR_SIM_LABS.bat para backup e migracao 0004.')
if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Uso: MIGRAR_0_3.bat "C:\\pasta\\SIM_Labs_Integrado_0_3_0"')
    try: migrate(Path(sys.argv[1]),ROOT)
    except Exception as exc: raise SystemExit('MIGRACAO BLOQUEADA: '+str(exc)+'\nSe uma copia parcial foi criada, preserve-a e use uma nova pasta extraida para tentar novamente.')
