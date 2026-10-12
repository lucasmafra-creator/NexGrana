import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

QA=Path(__file__).resolve().parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
stop=load('rescue_stop',QA/'backend/stop_local.py')
runner=load('rescue_runner',QA/'scripts/run_release_pipeline.py')

class StopRegression(unittest.TestCase):
    def row(self,pid,module='app.supervisor'):
        executable=stop.ROOT/'backend'/'.venv'/'Scripts'/'python.exe'
        return {'ProcessId':pid,'CommandLine':f'"{executable}" -m {module}'}
    def test_supervisor_tree_can_end_child_before_next_stop(self):
        rows=[self.row(1),self.row(2,'uvicorn app.main:app')];calls=[]
        def terminate(pid):calls.append(pid);rows.clear();return 0
        self.assertEqual(stop.stop_windows(lambda:list(rows),terminate,lambda _:None),0)
        self.assertEqual(calls,[1])
    def test_reused_pid_is_preserved(self):
        owned=self.row(2);foreign={'ProcessId':2,'CommandLine':'C:/other/python.exe -m uvicorn app.main:app'}
        sequence=iter([[owned],[foreign],[foreign]])
        calls=[]
        self.assertEqual(stop.stop_windows(lambda:next(sequence),calls.append,lambda _:None),0)
        self.assertEqual(calls,[])
    def test_live_owned_process_is_failure(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(stop.stop_windows(lambda:[self.row(1)],lambda _:1,lambda _:None),1)
    def test_other_copy_never_matches(self):
        row=self.row(1);row['CommandLine']=row['CommandLine'].replace(str(stop.ROOT),str(stop.ROOT)+'_OTHER')
        self.assertFalse(stop.owned_windows(row))

class PackagingRegression(unittest.TestCase):
    def test_collector_installs_test_dependency(self):
        lines=(QA/'Collector/requirements.txt').read_text().splitlines()
        self.assertIn('pytest==9.1.1',lines)
    def test_nex_gateway_dependencies_are_checked_and_declared(self):
        project=QA.parent/'NexGrana'
        requirements=(project/'requirements-qa.txt').read_text(encoding='utf-8').lower()
        gateway=(project/'gateway/requirements.txt').read_text(encoding='utf-8').lower()
        self.assertIn('-r gateway/requirements.txt',requirements)
        self.assertIn('fastapi==',gateway)
        self.assertIn('uvicorn[standard]==',gateway)
        self.assertIn('fastapi',runner.NEX_QA_MODULES)
        self.assertIn('uvicorn',runner.NEX_QA_MODULES)
    def test_nested_requirement_change_invalidates_qa_venv_stamp(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'gateway').mkdir()
            (root/'requirements-qa.txt').write_text('-r requirements.txt\n-r gateway/requirements.txt\n',encoding='utf-8')
            (root/'requirements.txt').write_text('flet==1.0\n',encoding='utf-8')
            nested=root/'gateway/requirements.txt';nested.write_text('fastapi==1.0\n',encoding='utf-8')
            before=runner.requirements_tree_sha256(root/'requirements-qa.txt')
            nested.write_text('fastapi==1.1\n',encoding='utf-8')
            after=runner.requirements_tree_sha256(root/'requirements-qa.txt')
            self.assertNotEqual(before,after)
    def test_old_binary_cannot_satisfy_new_build(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);nex=root/'NexGrana';old=nex/'dist/old/app.exe';old.parent.mkdir(parents=True);old.write_bytes(b'old')
            flutter=root/'flutter';(flutter/'bin').mkdir(parents=True);(flutter/'bin/flutter.bat').touch()
            with patch.object(runner.platform,'system',return_value='Windows'),patch.dict(os.environ,{'NEX_FLUTTER_ROOT':str(flutter)}),patch.object(runner,'run',return_value={'status':'PASS','log':'build.log'}):
                result=runner.build_target(root,nex,'windows',Path(sys.executable),root/'logs')
            self.assertEqual(result['status'],'FAIL')

class CredentialRegression(unittest.TestCase):
    def test_two_bootstraps_preserve_password_hash_and_signing_key(self):
        sys.path.insert(0,str(QA/'backend'))
        from app import bootstrap
        from dotenv import dotenv_values
        from app.local_auth import verify_password
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'backend').mkdir()
            with patch.object(bootstrap,'ROOT',root),patch('subprocess.run'),patch.dict(os.environ,{'SIM_LABS_PORT':'8012'}),contextlib.redirect_stdout(io.StringIO()):
                bootstrap.main()
                first=(root/'.runtime/PRIMEIRO_ACESSO.txt').read_text()
                env1=dict(dotenv_values(root/'.env'))
                bootstrap.main()
                self.assertEqual(first,(root/'.runtime/PRIMEIRO_ACESSO.txt').read_text())
                env2=dict(dotenv_values(root/'.env'));self.assertEqual(env1,env2)
                password=bootstrap._read_persisted_password(root/'.runtime/PRIMEIRO_ACESSO.txt')
                self.assertTrue(verify_password(password,env2['LOCAL_ADMIN_PASSWORD_HASH']))
                # Restore a drifted hash to the SAME saved password, including BOM files.
                (root/'.runtime/PRIMEIRO_ACESSO.txt').write_text(first,encoding='utf-8-sig')
                envfile=root/'.env';envfile.write_text(envfile.read_text().replace(env1['LOCAL_ADMIN_PASSWORD_HASH'],'invalid'))
                bootstrap.main()
                self.assertEqual(password,bootstrap._read_persisted_password(root/'.runtime/PRIMEIRO_ACESSO.txt'))
                self.assertTrue(verify_password(password,dict(dotenv_values(envfile))['LOCAL_ADMIN_PASSWORD_HASH']))

if __name__=='__main__':unittest.main()
