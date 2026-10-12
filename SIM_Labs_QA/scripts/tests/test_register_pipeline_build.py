import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('register_pipeline',Path(__file__).resolve().parents[1]/'register_pipeline_build.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class RegistrationTests(unittest.TestCase):
    def fixture(self,root):
        exe=root/'NexGrana/dist/current/windows/NexGrana.exe';exe.parent.mkdir(parents=True)
        exe.write_bytes(b'TEST_DATA_NOT_EXECUTABLE');(exe.parent/'required.dll').write_bytes(b'TEST_DATA_DLL')
        return {'tests':[{'status':'PASS'}],'builds':[{'target':'windows','status':'BUILD OK','artifacts':[{'path':str(exe.relative_to(root)),'size_bytes':exe.stat().st_size,'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}]}]},exe
    def test_complete_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);report,_=self.fixture(root)
            with zipfile.ZipFile(module.package_windows_build(report,root)) as archive:
                self.assertEqual(set(archive.namelist()),{'NexGrana/NexGrana.exe','NexGrana/required.dll'})
    def test_modified_binary_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);report,exe=self.fixture(root);exe.write_bytes(b'CHANGED')
            with self.assertRaises(ValueError):module.package_windows_build(report,root)
    def test_failed_tests_prevent_registration(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);report,_=self.fixture(root);report['tests'][0]['status']='FAIL'
            with self.assertRaises(ValueError):module.package_windows_build(report,root)
    def test_artifact_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);report,_=self.fixture(root);report['builds'][0]['artifacts'][0]['path']='../outside.exe'
            with self.assertRaises(ValueError):module.package_windows_build(report,root)
