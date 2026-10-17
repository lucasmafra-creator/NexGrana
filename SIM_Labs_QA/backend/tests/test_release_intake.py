import importlib.util, hashlib, json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('latest_build',Path(__file__).resolve().parents[2]/'scripts/register_latest_build.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def report(tmp_path,status='built',relative='NexGrana.exe',digest=None):
 artifact=tmp_path/'NexGrana.exe';artifact.write_bytes(b'TEST_DATA_NOT_EXECUTABLE')
 path=tmp_path/'build-report.json'
 path.write_text(json.dumps([{'target':'windows','status':status,'artifact_metadata':[{'path':relative,'size_bytes':artifact.stat().st_size,'sha256':digest or hashlib.sha256(artifact.read_bytes()).hexdigest()}]}]))
 return path,artifact

def test_selects_matching_artifact_without_executing(tmp_path):
 path,artifact=report(tmp_path);assert module.select_artifact(path,'windows')==artifact

@pytest.mark.parametrize('case',['blocked','hash','escape'])
def test_rejects_invalid_build(tmp_path,case):
 path,_=report(tmp_path,status='blocked' if case=='blocked' else 'built',relative='../outside.exe' if case=='escape' else 'NexGrana.exe',digest='0'*64 if case=='hash' else None)
 with pytest.raises(ValueError):module.select_artifact(path,'windows')
