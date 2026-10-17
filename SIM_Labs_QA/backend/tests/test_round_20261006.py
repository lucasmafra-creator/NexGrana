import json,sqlite3,zipfile
from pathlib import Path
from unittest.mock import patch
from app import backup_local
from test_integrated import h,release

def test_backup_closes_handles_before_unlink(tmp_path,monkeypatch):
 root=tmp_path; (root/"backend").mkdir()
 source=root/"backend/sim_labs.db"
 with sqlite3.connect(source) as db:db.execute("create table t(v)");db.execute("insert into t values(42)")
 monkeypatch.setattr(backup_local,"ROOT",root)
 monkeypatch.setenv("DATABASE_URL", "sqlite:///"+str(source))
 connections=[];connect=sqlite3.connect;remove=backup_local.remove_snapshot
 def tracked(*a,**kw):
  c=connect(*a,**kw);connections.append(c);return c
 def verify(p):
  for c in connections:
   try:c.execute("select 1")
   except sqlite3.ProgrammingError:continue
   raise AssertionError("Connection still open")
  return remove(p)
 monkeypatch.setattr(backup_local.sqlite3,"connect",tracked)
 monkeypatch.setattr(backup_local,"remove_snapshot",verify)
 backup_local.main()
 archives=list((root/"backups").glob("*.zip"));assert len(archives)==1
 with zipfile.ZipFile(archives[0]) as z:assert z.testzip() is None
 assert source.exists() and not list((root/"backups").glob("*.db"))

def test_snapshot_lock_retry_preserves_file(tmp_path,monkeypatch):
 p=tmp_path/"snapshot.db";p.write_bytes(b"QA")
 monkeypatch.setattr(backup_local.time,"sleep",lambda _:None)
 with patch.object(Path,"unlink",side_effect=PermissionError("TEST lock")) as remove:
  assert backup_local.remove_snapshot(p) is False
  assert remove.call_count==4
 assert p.read_bytes()==b"QA"

def upload_report(client,rel,report):
 r=client.post("/api/v1/evidence",headers=h(),data={"release_id":rel["id"]},files={"file":("runner.json",json.dumps(report).encode(),"application/json")})
 assert r.status_code==201,r.text
 return client.post(f"/api/v1/releases/{rel['id']}/runner-reports",headers=h(),json={"evidence_id":r.json()["id"]}),r.json()["id"]

def test_runner_report_import_deduplicates(client):
 rel=release(client)
 report={"schema":"sim-labs.trusted-source-run/1.0","status":"PASS","official_source_unchanged":True,"checks":[{"status":"PASS","exit_code":0}]}
 r,eid=upload_report(client,rel,report);assert r.status_code==201,r.text
 again=client.post(f"/api/v1/releases/{rel['id']}/runner-reports",headers=h(),json={"evidence_id":eid})
 assert again.json()["duplicate"] and again.json()["id"]==r.json()["id"]
 assert json.loads(r.json()["result_json"])["executed_by_engine"] is False
 reupload,_=upload_report(client,rel,report)
 assert reupload.json()["duplicate"] and reupload.json()["id"]==r.json()["id"]

def test_runner_contradictory_pass_and_malformed_checks(client):
 rel=release(client)
 for checks in [[{"status":"FAIL"}],["invalid"]]:
  r,_=upload_report(client,rel,{"schema":"sim-labs.trusted-source-run/1.0","status":"PASS","official_source_unchanged":True,"checks":checks})
  assert r.status_code==422,r.text

def test_runner_receipt_cannot_cross_release(client):
 a=release(client,"QA A");b=release(client,"QA B")
 r,eid=upload_report(client,a,{"schema":"sim-labs.trusted-source-run/1.0","status":"FAIL","checks":[{"status":"FAIL"}]})
 assert r.status_code==201
 r=client.post(f"/api/v1/releases/{b['id']}/runner-reports",headers=h(),json={"evidence_id":eid})
 assert r.status_code==409


def test_backup_uses_configured_database_and_refuses_missing(tmp_path,monkeypatch):
 monkeypatch.setattr(backup_local,'ROOT',tmp_path)
 path=tmp_path/'custom.db'
 monkeypatch.setenv('DATABASE_URL','sqlite:///'+str(path))
 assert backup_local.database_path()==path
 import pytest
 with pytest.raises(FileNotFoundError):backup_local.main()
 assert not (tmp_path/'backups').exists()

def test_backup_reads_env_file_relative_to_backend(tmp_path,monkeypatch):
 monkeypatch.setattr(backup_local,'ROOT',tmp_path)
 monkeypatch.delenv('DATABASE_URL',raising=False)
 (tmp_path/'.env').write_text('DATABASE_URL=sqlite:///custom.db\n')
 assert backup_local.database_path()==tmp_path/'backend/custom.db'
