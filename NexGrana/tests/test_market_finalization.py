import unittest
from unittest.mock import Mock
import test_round_20261006

class MarketFinalizationTests(unittest.TestCase):
 def cloud(self):
  c=test_round_20261006.CloudRoundTests().setup_cloud()
  c.member={'id':'20000000-0000-0000-0000-000000000001'}
  c._cache_upsert('market_trips',{'id':'30000000-0000-0000-0000-000000000001','household_id':c._hid(),'created_by':str(c.user.id),'market_name':'QA','status':'open'})
  return c
 def test_offline_finalization_is_one_pending_expense_and_keeps_trip_open(self):
  c=self.cloud();c._send_mutation=Mock(side_effect=ConnectionError('QA offline'))
  args=('30000000-0000-0000-0000-000000000001',20,21,1,c.member['id'],'2026-10-06')
  first=c.finalize_market_expense(*args);again=c.finalize_market_expense(*args)
  self.assertEqual(first['id'],again['id']);self.assertEqual(len(c._sync_queue().unresolved()),1)
  self.assertEqual(c._cache_find('market_trips',args[0])['status'],'open')
  self.assertEqual(first['amount'],21);self.assertEqual(first['expense_shares'][0]['amount'],21)
 def test_rejected_finalization_removes_optimistic_expense(self):
  c=self.cloud();c._send_mutation=Mock(side_effect=PermissionError('QA denied'))
  with self.assertRaises(RuntimeError):c.finalize_market_expense('30000000-0000-0000-0000-000000000001',20,21,0,c.member['id'],'2026-10-06')
  from cloud import _overlay_unresolved
  self.assertEqual(_overlay_unresolved(c,'expenses',[]),[])
 def test_synced_finalization_closes_trip(self):
  c=self.cloud();c._send_mutation=Mock(return_value={'ok':True})
  row=c.finalize_market_expense('30000000-0000-0000-0000-000000000001',20,21,0,c.member['id'],'2026-10-06')
  self.assertEqual(row['_sync_state'],'synced')
  self.assertEqual(c._cache_find('market_trips','30000000-0000-0000-0000-000000000001')['status'],'closed')
 def test_delete_and_undo_queue_order_and_scope(self):
  c=self.cloud();c._send_mutation=Mock(side_effect=ConnectionError('QA offline'))
  c._cache_upsert('market_items',{'id':'item','trip_id':'trip','household_id':c._hid(),'created_by':str(c.user.id),'product_name':'Arroz','quantity':2,'unit_price':3,'category':'Alimentação','picked':True})
  c.delete_market_item('item');self.assertIsNotNone(c._cache_find('market_items','item')['deleted_at'])
  c.undo_market_action();self.assertIsNone(c._cache_find('market_items','item')['deleted_at'])
  q=c._sync_queue().unresolved();self.assertEqual(len(q),2);self.assertEqual(q[1]['payload']['server']['p_undo'],q[0]['id'])
  c.household={'id':'other'}
  with self.assertRaises(ValueError):c.undo_market_action()
 def test_undo_refuses_later_change(self):
  c=self.cloud();c._send_mutation=Mock(return_value={'ok':True})
  trip='30000000-0000-0000-0000-000000000001';c.delete_market_trip(trip)
  c._cache_upsert('market_trips',{**c._cache_find('market_trips',trip),'deleted_at':None})
  with self.assertRaises(ValueError):c.undo_market_action()

 def test_budget_undo_creates_new_audited_change(self):
  c=self.cloud();c._send_mutation=Mock(return_value={'ok':True})
  trip='30000000-0000-0000-0000-000000000001'
  c.update_market_trip(trip,budget=50)
  c.undo_market_action()
  self.assertEqual(c._cache_find('market_trips',trip)['budget'],0)
  records=c._sync_queue()._rows()
  self.assertEqual(len(records),2)
  self.assertEqual(records[1]['payload']['server']['p_expected_budget'],50)
  self.assertNotEqual(records[0]['id'],records[1]['id'])

 def test_removed_products_never_count_in_budget(self):
  from services.market import budget_summary,product_values
  self.assertEqual(budget_summary([{'product_name':'QA','quantity':1,'unit_price':10,'deleted_at':'2026-10-06T12:00:00Z'}],20)['spent'],0)
  with self.assertRaises(ValueError):product_values('QA',1.2345,10)

 def test_transport_reads_authoritative_ledger_before_confirming_retry(self):
  c=self.cloud();expense_id='40000000-0000-0000-0000-000000000001'
  c.client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value.data={'id':expense_id,'amount':99}
  mutation={'payload':{'table':'expenses','transport':'market_finalize_rpc','server':{'p_expense':expense_id},'local':{'id':expense_id,'amount':21}}}
  self.assertEqual(c._send_mutation(mutation),{'ok':True})
  self.assertEqual(mutation['payload']['local']['amount'],99)
