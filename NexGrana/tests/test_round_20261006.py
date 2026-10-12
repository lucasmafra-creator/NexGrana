import sys, unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from services.chat_retention import interval,retain_messages
from services.nex_local_knowledge import local_answer
from services.product_scan import candidates_from_tsv
from services.market import budget_summary
from services.qa_diagnostics import qa_failure
from services.monthly_ledger import canonical_month

class RoundTests(unittest.TestCase):
 def test_month_clamp_and_local_timezone(self):
  a,b=interval("month",datetime(2024,3,31,12,tzinfo=timezone(timedelta(hours=-3))))
  self.assertEqual(a,"2024-02-29T15:00:00+00:00")
  self.assertEqual(b,"2024-03-31T15:00:00+00:00")
 def test_year_clamp(self):
  self.assertTrue(interval("year",datetime(2024,2,29,tzinfo=timezone.utc))[0].startswith("2023-02-28"))
 def test_retention_boundaries_scope_and_legacy(self):
  tomb=[{"conversation_id":"A","start":"2026-10-06T10:00:00Z","end":"2026-10-06T11:00:00Z"}]
  rows=[{"id":1,"created_at":"2026-10-06T10:00:00Z"},{"id":2,"created_at":"2026-10-06T09:59:59Z"},{"id":3},{"id":4,"created_at":"2026-10-06T11:00:00Z"}]
  self.assertEqual([r["id"] for r in retain_messages(rows,tomb,"A")],[2,3])
  self.assertEqual(len(retain_messages(rows,tomb,"B")),4)
  remaining=retain_messages(rows,tomb,"A")
  self.assertEqual(retain_messages(remaining,tomb,"A"),remaining)
 def test_naive_time_rejected(self):
  with self.assertRaises(ValueError):interval("hour",datetime(2026,10,6))
 def test_offline_help_without_personal_totals(self):
  self.assertIn("Revisar mês",local_answer("Como fechar o mês?"))
  self.assertIsNone(local_answer("Qual é meu orçamento hoje?"))
  self.assertIsNone(local_answer("qual é a Selic atual?"))
 def test_ocr_candidates_require_name_price_confidence(self):
  header="page_num\tblock_num\tpar_num\tline_num\tconf\ttext\n"
  body="1\t1\t1\t1\t90\tArroz\n1\t1\t1\t1\t95\t12,90\n1\t1\t1\t2\t10\tLixo\n"
  self.assertEqual(candidates_from_tsv(header+body),[{"name":"Arroz","unit_price":"12.90","confidence":92,"source":"local_ocr"}])
 def test_bad_month_rejected(self):
  with self.assertRaises(ValueError):canonical_month("13/2026")

class CloudRoundTests(unittest.TestCase):
 def setup_cloud(self):
  from cloud import Cloud
  from test_market_cloud import MarketCloudTests
  from types import SimpleNamespace
  from unittest.mock import Mock
  c=Cloud(MarketCloudTests.Vault());c.user=SimpleNamespace(id='00000000-0000-0000-0000-000000000001');c.household={'id':'10000000-0000-0000-0000-000000000001'}
  c.client=Mock();c.session_state='authenticated'
  return c
 def test_monthly_batch_offline_queue_keeps_all_scopes(self):
  from unittest.mock import Mock
  c=self.setup_cloud();c._send_mutation=Mock(side_effect=ConnectionError('QA offline'))
  rows=c.save_month_closures('01/2026',[(None,0,20),('20000000-0000-0000-0000-000000000001',0,20)])
  self.assertEqual(len(rows),2)
  queued=c._sync_queue().unresolved()
  self.assertEqual(len(queued),2)
  self.assertTrue(all(len(q['payload']['server']['p_rows'])==2 for q in queued))
 def test_monthly_rejected_batch_does_not_carry(self):
  from unittest.mock import Mock
  c=self.setup_cloud();c._send_mutation=Mock(side_effect=PermissionError('QA denied'))
  with self.assertRaises(RuntimeError):c.save_month_closures('01/2026',[(None,0,20)])
  self.assertEqual(c.list_month_closures(),[])
 def test_budget_conflict_uses_queue_transport_and_original_budget(self):
  from unittest.mock import Mock
  c=self.setup_cloud();c._cache_upsert('market_trips',{'id':'trip','budget':50,'market_name':'QA','household_id':c._hid()})
  c._send_mutation=Mock(return_value={'conflict':True})
  with self.assertRaises(RuntimeError):c.update_market_trip('trip',budget=100)
  q=c._sync_queue().unresolved()[0]
  self.assertEqual(q['payload']['transport'],'market_trip_rpc')
  self.assertEqual(q['payload']['server']['p_expected_budget'],50)
  self.assertEqual(c._cache_find('market_trips','trip')['budget'],50)
 def test_budget_summary_is_decimal_and_negative_remaining(self):
  from decimal import Decimal
  result=budget_summary([{'product_name':'QA','quantity':'2.5','unit_price':'3.20'}],7)
  self.assertEqual(result['spent'],Decimal('8.00'));self.assertEqual(result['remaining'],Decimal('-1.00'))
  with self.assertRaises(ValueError):budget_summary([], -1)
