import sys
import unittest
import os
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cloud import Cloud, ReauthenticationRequired, SessionUnavailable
from services.market import receipt_comparison, product_values


class MarketCloudTests(unittest.TestCase):
    class Vault:
        def __init__(self):
            self.values = {}

        def read(self, key, default=None):
            return self.values.get(key, default)

        def write(self, key, value):
            self.values[key] = value

        def remove(self, key):
            self.values.pop(key, None)

        def clear_keys(self, keys):
            for key in keys:
                self.remove(key)

    class ExpiredError(Exception):
        code = 'PGRST303'
        message = 'JWT expired'

    def test_receipt_preserves_gross_total_and_reports_difference(self):
        rows = [{'product_name': 'Arroz', 'quantity': '2.5', 'unit_price': '3.20'}]
        result = receipt_comparison(rows, '9.00', '1.00')
        self.assertEqual(result, dict(cart=Decimal('8'), receipt=Decimal('9'), cashback=Decimal('1'), difference=Decimal('1'), net=Decimal('8')))

    def test_invalid_quantities_and_cashback(self):
        for quantity in ('NaN', 'Infinity', '-1', '0', 'invalid'):
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                product_values('Produto', quantity, '1')
        with self.assertRaises(ValueError):
            receipt_comparison([], '1', '2')

    def test_planned_list_items_only_count_when_picked(self):
        items=[{'product_name':'Arroz','quantity':2,'unit_price':'10','source_list_item_id':'planned','picked':False},
               {'product_name':'Leite','quantity':1,'unit_price':'6','source_list_item_id':'planned2','picked':True},
               {'product_name':'Extra','quantity':1,'unit_price':'3'}]
        self.assertEqual(receipt_comparison(items,'9')['cart'],Decimal('9'))

    def test_shopping_list_payload_is_scoped_and_rejects_invalid_money(self):
        cloud=Cloud()
        cloud.user=SimpleNamespace(id="user-1")
        cloud.household={"id":"house-1"}
        cloud._enqueue_upsert=lambda table,row:row
        cloud._flush_operation=lambda row:row
        created=cloud.add_shopping_list("Compra do mês","900","member-1")
        self.assertEqual(created["household_id"],"house-1")
        self.assertFalse(created["shared"])
        self.assertEqual(created["member_id"],"member-1")
        item=cloud.add_shopping_list_item(created["id"],"Arroz",2,"24.90")
        self.assertEqual(item["created_by"],"user-1")
        self.assertEqual(item["household_id"],"house-1")
        self.assertEqual(item["purchased"],False)
        for bad in ("NaN","-10","tela confusa"):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                cloud.add_shopping_list("Lista",bad)

    def test_shopping_list_edit_remains_scoped_and_rejects_invalid_budget(self):
        cloud=Cloud();cloud.user=SimpleNamespace(id="user-1");cloud.household={"id":"house-1"}
        cloud._enqueue_update=lambda table,row_id,values:(table,row_id,values)
        cloud._enqueue_delete=lambda table,row_id:(table,row_id)
        cloud._flush_operation=lambda row:row
        self.assertEqual(cloud.update_shopping_list("list-1","Mercado","80.50"),
                         ("shopping_lists","list-1",{"name":"Mercado","budget":80.5}))
        self.assertEqual(cloud.delete_shopping_list("list-1"),("shopping_lists","list-1"))
        for invalid in ("NaN","-1"):
            with self.assertRaises(ValueError):cloud.update_shopping_list("list-1","Mercado",invalid)

    def test_qa_reset_rpc_always_names_active_household(self):
        cloud=Cloud()
        cloud.user=SimpleNamespace(id="user-1")
        cloud.household={"id":"house-current"}
        cloud.client=Mock()
        cloud._run_network=lambda op,**kwargs:op()
        cloud.clear_local_cache=Mock()
        cloud.reset_qa_workspace("RESETAR_TESTE")
        args=cloud.client.rpc.call_args.args
        self.assertEqual(args[1]["p_household_id"],"house-current")
        with self.assertRaises(ValueError):cloud.reset_qa_workspace("RESET")

    def test_retry_only_transport_errors(self):
        cloud = Cloud()
        operation = Mock(side_effect=ValueError('schema'))
        with patch('cloud.time.sleep') as sleep, self.assertRaises(ValueError):
            cloud._run_network(operation)
        self.assertEqual(operation.call_count, 1)
        sleep.assert_not_called()
        operation = Mock(side_effect=[ConnectionError(), ['ok']])
        with patch('cloud.time.sleep'):
            self.assertEqual(cloud._run_network(operation), ['ok'])
        self.assertTrue(cloud.online)

    def test_missing_offline_cache_is_not_empty_finances(self):
        cloud = Cloud()
        cloud.user = SimpleNamespace(id='a')
        cloud.household = {'id': 'h'}
        cloud.client = Mock()
        cloud._run_network = Mock(side_effect=ConnectionError())
        with self.assertRaisesRegex(RuntimeError, 'sem cópia offline'):
            cloud.list_income('09/2026')
        cloud._cache_set('income:*, household_members(display_name)', [{'id': '1', 'month': '09/2026', 'amount': 42}])
        self.assertEqual(cloud.list_income('09/2026')[0]['amount'], 42)
        cloud.user = SimpleNamespace(id='b')
        with self.assertRaises(RuntimeError):
            cloud.list_income('09/2026')

    def test_authorization_errors_do_not_return_old_cache(self):
        cloud = Cloud()
        cloud.user = SimpleNamespace(id='a')
        cloud.household = {'id': 'h'}
        cloud.client = Mock()
        cloud._cache_set('income:*', [{'amount': 100}])
        cloud._run_network = Mock(side_effect=PermissionError())
        with self.assertRaises(PermissionError):
            cloud.fetch_all('income')

    def test_expired_jwt_refreshes_once_and_retries_read(self):
        vault = self.Vault()
        vault.write('cloud_session.json', {'access_token': 'old', 'refresh_token': 'refresh'})
        cloud = Cloud(vault=vault)
        cloud.user = SimpleNamespace(id='u')
        session = SimpleNamespace(access_token='new', refresh_token='new-refresh', user=cloud.user)
        cloud.client = SimpleNamespace(auth=Mock(refresh_session=Mock(return_value=SimpleNamespace(session=session, user=cloud.user))))
        operation = Mock(side_effect=[self.ExpiredError(), ['ok']])

        self.assertEqual(cloud._run_network(operation), ['ok'])
        self.assertEqual(operation.call_count, 2)
        cloud.client.auth.refresh_session.assert_called_once_with('refresh')
        self.assertEqual(vault.read('cloud_session.json')['access_token'], 'new')
        self.assertEqual(cloud.session_state, 'authenticated')

    def test_refresh_failure_requires_login_and_removes_only_session(self):
        vault = self.Vault()
        vault.write('cloud_session.json', {'access_token': 'old', 'refresh_token': 'refresh'})
        vault.write('cache:kept', {'safe': True})
        cloud = Cloud(vault=vault)
        cloud.user = SimpleNamespace(id='u')
        cloud.household = {'id': 'h'}
        cloud.client = SimpleNamespace(auth=Mock(refresh_session=Mock(side_effect=ValueError('revoked'))))

        with self.assertRaises(ReauthenticationRequired):
            cloud._run_network(Mock(side_effect=self.ExpiredError()))
        self.assertIsNone(vault.read('cloud_session.json'))
        self.assertEqual(vault.read('cache:kept'), {'safe': True})
        self.assertIsNone(cloud.user)
        self.assertEqual(cloud.session_state, 'reauthentication_required')

    def test_network_failure_during_refresh_keeps_persisted_session(self):
        vault = self.Vault()
        original = {'access_token': 'old', 'refresh_token': 'refresh'}
        vault.write('cloud_session.json', original)
        cloud = Cloud(vault=vault)
        cloud.user = SimpleNamespace(id='u')
        cloud.client = SimpleNamespace(auth=Mock(refresh_session=Mock(side_effect=ConnectionError())))

        with self.assertRaises(SessionUnavailable):
            cloud._run_network(Mock(side_effect=self.ExpiredError()))
        self.assertEqual(vault.read('cloud_session.json'), original)
        self.assertEqual(cloud.session_state, 'offline_with_local_session')

    def test_refresh_generation_prevents_duplicate_refresh(self):
        vault = self.Vault()
        vault.write('cloud_session.json', {'access_token': 'old', 'refresh_token': 'refresh'})
        user = SimpleNamespace(id='u')
        session = SimpleNamespace(access_token='new', refresh_token='new-refresh', user=user)
        auth = Mock(refresh_session=Mock(return_value=SimpleNamespace(session=session, user=user)))
        cloud = Cloud(vault=vault)
        cloud.user = user
        cloud.client = SimpleNamespace(auth=auth)

        cloud._refresh_session(observed_generation=0)
        cloud._refresh_session(observed_generation=0)
        auth.refresh_session.assert_called_once()

    def test_auth_redirect_rejects_localhost(self):
        with patch.dict(os.environ,{'NEXGRANA_AUTH_REDIRECT_URL':'http://localhost:3000'},clear=False):
            with self.assertRaisesRegex(ValueError,'HTTPS pública'):
                Cloud.auth_redirect_url()
        with patch.dict(os.environ,{'NEXGRANA_AUTH_REDIRECT_URL':'https://conta.nexgrana.example/confirmar'},clear=False):
            self.assertEqual(Cloud.auth_redirect_url(),'https://conta.nexgrana.example/confirmar')

    def test_offline_context_is_bound_to_saved_session_user(self):
        vault=self.Vault()
        vault.write('cloud_session.json',{'access_token':'a','refresh_token':'r','user_id':'u1','email':'qa@example.test'})
        vault.write('identity-context:u1',{'profile':{'full_name':'QA'},'household':{'id':'h1'},'member':{'id':'m1'}})
        cloud=Cloud(vault=vault)
        self.assertTrue(cloud._restore_identity_context())
        self.assertEqual(cloud.user.id,'u1')
        self.assertEqual(cloud.household['id'],'h1')
        vault.write('cloud_session.json',{'access_token':'b','refresh_token':'r2','user_id':'u2'})
        cloud.user=cloud.household=None
        self.assertFalse(cloud._restore_identity_context())
        self.assertIsNone(cloud.household)

    def test_offline_income_is_queued_with_stable_id_and_cached(self):
        vault=self.Vault()
        cloud=Cloud(vault=vault)
        cloud.user=SimpleNamespace(id='u')
        cloud.household={'id':'h'}
        cloud.session_state='authenticated'
        execute=Mock(side_effect=ConnectionError())
        upsert=Mock(return_value=SimpleNamespace(execute=execute))
        cloud.client=SimpleNamespace(table=Mock(return_value=SimpleNamespace(upsert=upsert)))
        row=cloud.add_income('m','10','09/2026','Teste',received_at='2026-09-18')
        self.assertEqual(row['_sync_state'],'pending')
        self.assertTrue(row['id'])
        self.assertEqual(cloud.pending_sync_count(),1)
        cached=cloud.list_income('09/2026')
        self.assertEqual(cached[0]['id'],row['id'])
        self.assertEqual(cached[0]['amount'],10.0)

    def test_privacy_choice_survives_offline_and_syncs_later(self):
        vault=self.Vault()
        cloud=Cloud(vault=vault)
        cloud.user=SimpleNamespace(id='u')
        cloud.household={'id':'h'}
        failed_execute=Mock(side_effect=ConnectionError())
        failed_upsert=Mock(return_value=SimpleNamespace(execute=failed_execute))
        cloud.client=SimpleNamespace(table=Mock(return_value=SimpleNamespace(upsert=failed_upsert)))
        result=cloud.set_privacy_consent('external_ai',True)
        self.assertTrue(result['local'])
        self.assertTrue(cloud._cache_get(cloud._privacy_cache_key())['external_ai'])
        self.assertTrue(cloud._cache_get(cloud._privacy_pending_key())['external_ai'])
        ok_execute=Mock(return_value=SimpleNamespace(data=[]))
        ok_upsert=Mock(return_value=SimpleNamespace(execute=ok_execute))
        cloud.client=SimpleNamespace(table=Mock(return_value=SimpleNamespace(upsert=ok_upsert)))
        self.assertEqual(cloud.sync_pending_consents(),1)
        self.assertEqual(cloud._cache_get(cloud._privacy_pending_key()),{})

    def test_offline_context_opens_without_network_and_falls_back_to_own_member(self):
        cloud=Cloud(vault=self.Vault())
        cloud.user=SimpleNamespace(id='u')
        cloud.household={'id':'h'}
        cloud.member={'id':'m','display_name':'QA','status':'active'}
        cloud.profile={'full_name':'QA'}
        cloud.session_state='offline_with_local_session'
        cloud.client=Mock()
        cloud._run_network=Mock(side_effect=AssertionError('network must not run'))
        cloud.load_context()
        self.assertEqual(cloud.list_members(),[cloud.member])
        cloud._run_network.assert_not_called()

    def test_queue_is_overlaid_after_crash_between_queue_and_cache(self):
        vault=self.Vault()
        cloud=Cloud(vault=vault)
        cloud.user=SimpleNamespace(id='u')
        cloud.household={'id':'h'}
        cloud.session_state='offline_with_local_session'
        queue=cloud._sync_queue()
        local={'id':'i1','household_id':'h','member_id':'m','amount':15.0,'month':'09/2026','received_at':'2026-09-18','_operation_id':'op1'}
        queue.enqueue('income','i1',0,{'operation':'upsert','table':'income','server':dict(local),'local':dict(local)},'op1')
        cloud._cache_set('income:*, household_members(display_name)',[])
        cloud.client=Mock()
        cloud._run_network=Mock(side_effect=ConnectionError())
        rows=cloud.refresh_table('income','*, household_members(display_name)')
        self.assertEqual(rows[0]['id'],'i1')
        self.assertEqual(rows[0]['_sync_state'],'queued')

    def test_sync_summary_separates_pending_and_rejected(self):
        vault=self.Vault()
        cloud=Cloud(vault=vault)
        cloud.user=SimpleNamespace(id='u')
        cloud.household={'id':'h'}
        queue=cloud._sync_queue()
        queue.enqueue('income','i1',0,{'operation':'upsert','table':'income','local':{'id':'i1'}},'op1')
        queue.enqueue('income','i2',0,{'operation':'upsert','table':'income','local':{'id':'i2'}},'op2')
        queue.apply_one(lambda row: (_ for _ in ()).throw(ValueError('RLS')))
        self.assertEqual(cloud.sync_summary(),{'queued':1,'conflict':0,'rejected':1,'total':2})

    def test_offline_update_and_delete_preserve_order_and_optimistic_view(self):
        vault=self.Vault()
        cloud=Cloud(vault=vault)
        cloud.user=SimpleNamespace(id='u')
        cloud.household={'id':'h'}
        cloud.session_state='authenticated'
        cloud._cache_set('income:*, household_members(display_name)',[
            {'id':'i1','household_id':'h','member_id':'m','amount':10.0,'month':'09/2026','received_at':'2026-09-01'},
        ])
        request=Mock()
        request.eq.return_value=request
        request.select.return_value=request
        request.execute.side_effect=ConnectionError()
        update=Mock(return_value=request)
        cloud.client=SimpleNamespace(table=Mock(return_value=SimpleNamespace(update=update)))
        updated=cloud.update_income('i1','m',20,'09/2026','corrigida',received_at='2026-09-01')
        self.assertEqual(updated['_sync_state'],'pending')
        self.assertEqual(cloud.list_income('09/2026')[0]['amount'],20.0)
        deleted=cloud.delete_income('i1')
        self.assertEqual(deleted['_sync_state'],'pending_delete')
        self.assertEqual(cloud.list_income('09/2026'),[])
        unresolved=cloud._sync_queue().unresolved()
        self.assertEqual([row['payload']['operation'] for row in unresolved],['update','delete'])

    def test_mutation_ack_requires_returned_matching_row(self):
        cloud=Cloud(vault=self.Vault())
        cloud.user=SimpleNamespace(id='u')
        cloud.household={'id':'h'}
        request=Mock()
        request.eq.return_value=request
        request.select.return_value=request
        client=SimpleNamespace(table=Mock(return_value=SimpleNamespace(
            update=Mock(return_value=request),delete=Mock(return_value=request))))
        cloud.client=client
        for operation in ('update','delete'):
            mutation={'row_id':'i1','payload':{'table':'income','operation':operation,'server':{'amount':20}}}
            request.execute.return_value=SimpleNamespace(data=[])
            self.assertEqual(cloud._send_mutation(mutation),{'conflict':True})
            request.execute.return_value=SimpleNamespace(data=[{'id':'other'}])
            self.assertEqual(cloud._send_mutation(mutation),{'conflict':True})
            request.execute.return_value=SimpleNamespace(data=[{'id':'i1'}])
            self.assertEqual(cloud._send_mutation(mutation),{'ok':True})
        self.assertEqual(request.select.call_count,6)


if __name__ == '__main__':
    unittest.main()
