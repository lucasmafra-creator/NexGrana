import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit,parse_qs

SCRIPT=Path(__file__).resolve().parents[1]/'open_authenticated_central.py'
spec=importlib.util.spec_from_file_location('open_authenticated_central',SCRIPT)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Response:
    def __init__(self,value):self.stream=io.BytesIO(json.dumps(value).encode())
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,*args):return self.stream.read(*args)
    def __iter__(self):return self
    def __next__(self):return next(self.stream)
    def __getattr__(self,name):return getattr(self.stream,name)

class FakeOpener:
    def __init__(self,health,login):self.health=health;self.login=login;self.calls=[]
    def open(self,req,timeout):
        self.calls.append(req)
        value=self.health if req.full_url.endswith('/health') else self.login
        return Response(value)

class AuthenticatedCentralTests(unittest.TestCase):
    def fixture(self):
        root=Path(tempfile.mkdtemp())/'SIM_Labs_QA';root.mkdir()
        instance=hashlib.sha256(root.resolve().as_posix().lower().rstrip('/').encode()).hexdigest()[:16]
        health={'status':'ok','service':module.SERVICE,'phase':module.PHASE,'instance_id':instance}
        return root,health
    def test_authenticated_url_is_one_time_fragment_after_identity_check(self):
        root,health=self.fixture();opener=FakeOpener(health,{'token':'TEST_DATA_LOCAL_SESSION','name':'Mafra','mode':'local-private'})
        url=module.session_url(8000,'TEST_DATA_PASSWORD',root,opener)
        self.assertEqual(urlsplit(url).netloc,'127.0.0.1:8000')
        self.assertEqual(parse_qs(urlsplit(url).fragment)['sim-session'],['TEST_DATA_LOCAL_SESSION'])
        self.assertEqual(len(opener.calls),2)
        self.assertEqual(json.loads(opener.calls[1].data),{'password':'TEST_DATA_PASSWORD'})
    def test_wrong_copy_is_rejected_before_password_is_sent(self):
        root,health=self.fixture();health['instance_id']='another-copy'
        opener=FakeOpener(health,{'token':'unused','name':'Mafra','mode':'local-private'})
        with self.assertRaises(RuntimeError):module.session_url(8000,'TEST_DATA_PASSWORD',root,opener)
        self.assertEqual(len(opener.calls),1)
    def test_expired_login_response_does_not_open_browser_url(self):
        root,health=self.fixture();opener=FakeOpener(health,{'detail':'Senha incorreta'})
        with self.assertRaises(RuntimeError):module.session_url(8000,'TEST_DATA_PASSWORD',root,opener)
        self.assertEqual(len(opener.calls),2)

if __name__=='__main__':unittest.main()
