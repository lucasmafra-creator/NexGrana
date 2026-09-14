import sys,unittest,tempfile
from pathlib import Path
from datetime import datetime,timezone
from cryptography.fernet import Fernet,InvalidToken
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.privacy import Vault,write_backup,read_backup
from services.sync import SyncQueue
from services.affiliate import active_offers,DISCLOSURE
from ui.responsive import bucket

class ServiceTests(unittest.TestCase):
    def setUp(self):
        # Named directories avoid Windows temporary-dir ACL incompatibility in the runner.
        import uuid
        self.root=Path(__file__).resolve().parent/'scratch'/uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.vault=Vault(self.root,Fernet.generate_key())
    def tearDown(self):
        for p in self.root.iterdir():p.unlink()
        self.root.rmdir()
    def test_encryption(self):
        self.vault.write('cache:A',{'amount':123,'note':'private-secret'})
        self.assertEqual(self.vault.read('cache:A')['amount'],123)
        self.assertNotIn(b'private-secret',next(self.root.iterdir()).read_bytes())
        self.assertIsNone(self.vault.read('cache:B'))
    def test_tampering(self):
        self.vault.write('a',{})
        p=next(self.root.iterdir());p.write_bytes(p.read_bytes()[:-10]+b'tampering!')
        with self.assertRaises(InvalidToken):self.vault.read('a')
    def test_clear(self):
        self.vault.write('session',{'token':'secret'});self.vault.write('cache',{})
        self.vault.clear();self.assertEqual(list(self.root.iterdir()),[])
    def test_backup_round_trip(self):
        payload={'format':'nexgrana-snapshot','version':1,'tables':{'income':[{'id':'preserved','received_at':'2026-09-03'}]}}
        p=self.root/'backup.db';write_backup(p,payload);self.assertEqual(read_backup(p.resolve()),payload)
    def test_queue_idempotent(self):
        q=SyncQueue(self.vault,'A');q.enqueue('income','id',0,{'amount':1},'op');q.enqueue('income','id',0,{'amount':1},'op')
        self.assertEqual(len(self.vault.read('queue:A')),1)
        with self.assertRaises(ValueError):q.enqueue('income','id',0,{'amount':2},'op')
    def test_queue_conflict(self):
        q=SyncQueue(self.vault,'A');q.enqueue('income','id',1,{})
        self.assertEqual(q.apply_one(lambda r:{'conflict':True})['state'],'conflict')
        self.assertIsNone(q.apply_one(lambda r:{}))
    def test_queue_retry(self):
        q=SyncQueue(self.vault,'A');q.enqueue('income','id',1,{})
        def fail(r):raise TimeoutError()
        self.assertEqual(q.apply_one(fail)['attempts'],1)
        self.assertEqual(q.backoff(20),300)
    def test_queue_backoff_and_manual_retry(self):
        from datetime import timedelta
        q=SyncQueue(self.vault,'B');row=q.enqueue('expense','x',2,{'amount':10},'op2')
        now=datetime(2026,9,13,12,0,tzinfo=timezone.utc)
        # Force deterministic due time for this test.
        rows=self.vault.read('queue:B');rows[0]['next_attempt_at']=now.isoformat().replace('+00:00','Z');self.vault.write('queue:B',rows)
        def fail(r):raise ConnectionError()
        failed=q.apply_one(fail,now=now)
        self.assertEqual(failed['attempts'],1)
        self.assertEqual(q.pending(now=now),[])
        q.retry('op2',now=now)
        self.assertEqual(len(q.pending(now=now)),1)
        synced=q.apply_one(lambda r:{'ok':True},now=now)
        self.assertEqual(synced['state'],'synced')

    def test_queue_cancel_conflict(self):
        q=SyncQueue(self.vault,'C');q.enqueue('goal','g',1,{},'op3')
        self.assertEqual(q.cancel('op3')['state'],'cancelled')
        q.enqueue('goal','g2',1,{},'op4')
        self.assertEqual(q.apply_one(lambda r:{'conflict':True})['state'],'conflict')
        self.assertEqual(len(q.conflicts()),1)
    def test_offers(self):
        row=dict(url='https://meli.la/abc',enabled=True,expires_at='2026-10-01T00:00:00Z')
        now=datetime(2026,9,3,tzinfo=timezone.utc)
        self.assertEqual(len(active_offers([row],now)),1)
        self.assertEqual(active_offers([{**row,'url':'https://evil.test/x'}],now),[])
        self.assertEqual(active_offers([{**row,'url':'https://meli.la/x?email=secret'}],now),[])
        self.assertEqual(active_offers([{**row,'expires_at':'2026-01-01T00:00:00Z'}],now),[])
        self.assertIn('comissão',DISCLOSURE)
    def test_breakpoints(self):
        expected=['phone','phone','phone','tablet','wide','wide']
        self.assertEqual([bucket(w) for w in (360,390,430,768,1366,1920)],expected)
        self.assertNotEqual(bucket(899),bucket(900))

if __name__=='__main__':unittest.main()
