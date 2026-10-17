"""Exercise real migrations separately from tests' create_all database."""
import os, subprocess, sys, sqlite3
from pathlib import Path

def test_upgrade_from_liveops_preserves_existing_rows(tmp_path):
    backend=Path(__file__).resolve().parents[1]
    dbfile=tmp_path/'upgrade.db'
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(dbfile),'AUTO_INIT_DB':'0'}
    def migrate(target):
        r=subprocess.run([sys.executable,'-m','alembic','upgrade',target],cwd=backend,env=env,capture_output=True,text=True)
        assert r.returncode==0,r.stderr
    migrate('0002_liveops')
    with sqlite3.connect(dbfile) as db:
        db.execute("INSERT INTO products(id,slug,name,status,created_at) VALUES('TEST-ID','test-old','TEST DATA old product','active','2026-10-02')")
        db.execute("INSERT INTO feedbacks(id,human_id,product_id,category,title,description,severity,priority,status,source,created_at,updated_at) VALUES('TEST-FB','SIM-0099','TEST-ID','bug','TEST DATA old feedback','Preserve me','S2','P2','new','collector','2026-10-02','2026-10-02')")
    migrate('head')
    with sqlite3.connect(dbfile) as db:
        assert db.execute('SELECT description FROM feedbacks WHERE id=?',('TEST-FB',)).fetchone()[0]=='Preserve me'
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='0007_qa_operations'
        tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'releases','integration_receipts','evidence','messages','jobs','decisions'}<=tables


def test_upgrade_03_preserves_all_operational_tables(tmp_path):
    backend=Path(__file__).resolve().parents[1]; dbfile=tmp_path/'v03.db'
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(dbfile),'AUTO_INIT_DB':'0'}
    subprocess.run([sys.executable,'-m','alembic','upgrade','0003_integrated'],cwd=backend,env=env,check=True,capture_output=True)
    with sqlite3.connect(dbfile) as db:
        db.execute("INSERT INTO products VALUES('P','old','TEST old','active','2026-10-03')")
        db.execute("INSERT INTO releases VALUES('R','P','0.3-test','Preserve release','candidate','2026-10-03')")
        db.execute("INSERT INTO messages VALUES('M','P','Mafra','human','Preserve channel',NULL,'2026-10-03')")
        db.execute("INSERT INTO project_configs VALUES('P','Preserve config','Windows,Android','local','{}')")
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='alembic_version'")]
        before={n:db.execute('SELECT * FROM '+n+' ORDER BY 1').fetchall() for n in names}
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=backend,env=env,check=True,capture_output=True)
    with sqlite3.connect(dbfile) as db:
        for n,rows in before.items():
            after=db.execute('SELECT * FROM '+n+' ORDER BY 1').fetchall()
            assert all(row in after for row in rows),n
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='0007_qa_operations'
