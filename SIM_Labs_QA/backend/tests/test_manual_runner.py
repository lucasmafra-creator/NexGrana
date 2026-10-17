import importlib.util,sys
from pathlib import Path
import pytest

SCRIPT=Path(__file__).resolve().parents[2]/'scripts/nexgrana_runner.py'
spec=importlib.util.spec_from_file_location('trusted_runner',SCRIPT)
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

@pytest.mark.parametrize('text',[
 '--- a/src/../../escape.py\n+++ b/src/../../escape.py',
 '--- a/src/file.bat\n+++ b/src/file.bat',
 'diff --git a/.env b/.env\nGIT binary patch\n--- a/src/good.py\n+++ b/src/good.py',
 'diff --git a/src/link.py b/src/link.py\nnew file mode 120000\n--- /dev/null\n+++ b/src/link.py',
])
def test_patch_paths_reject_escape_and_binary(text):
 with pytest.raises(ValueError):runner.patch_paths(text)

def test_manual_runner_changes_only_copy_and_strips_secrets(tmp_path,monkeypatch):
 (tmp_path/'src').mkdir();(tmp_path/'tests').mkdir()
 source=tmp_path/'src/main.py';source.write_text('VALUE=1\n')
 (tmp_path/'.env').write_text('PRIVATE=TEST_DATA')
 (tmp_path/'tests/test_local.py').write_text("import unittest,os\nfrom pathlib import Path\nclass QA(unittest.TestCase):\n def test_copy(self):\n  assert 'PRIVATE_QA_KEY' not in os.environ\n  assert not Path('.env').exists()\n  Path('src/main.py').write_text('VALUE=2\\n')\n")
 monkeypatch.setenv('PRIVATE_QA_KEY','TEST_DATA')
 report=runner.execute(tmp_path,sys.executable,timeout=10)
 assert report['status']=='PASS' and report['official_source_unchanged']
 assert report['changed_files']==['src/main.py']
 assert source.read_text()=='VALUE=1\n'
 assert report['filesystem_sandbox'] is False and report['network_isolation'] is False


def test_runner_preserves_virtualenv_interpreter_symlink(tmp_path,monkeypatch):
 (tmp_path/'src').mkdir();(tmp_path/'tests').mkdir()
 (tmp_path/'src/main.py').write_text('VALUE=1\n')
 executable=tmp_path/'venv-python';executable.symlink_to(sys.executable)
 captured=[]
 def check(command,*args):
  captured.append(command)
  return {'status':'PASS','exit_code':0}
 monkeypatch.setattr(runner,'run_fixed',check)
 assert runner.execute(tmp_path,executable)['status']=='PASS'
 assert captured[0][0]==str(executable.absolute())
