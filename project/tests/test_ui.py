import sys,unittest,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
os.environ['FLET_APP_STORAGE_DATA']=str(Path(__file__).resolve().parent/'scratch'/'ui')
import flet as ft
from main import NexGranaCloud

class Page:
    def __init__(self,width=390):
        self.width=width;self.height=844;self.controls=[];self.services=[];self.navigation_bar=None;self.platform='windows';self.dialogs=[]
    def clean(self):self.controls.clear()
    def add(self,c):self.controls.append(c)
    def update(self):pass
    def show_dialog(self,c):self.dialogs.append(c)
    def pop_dialog(self):
        if self.dialogs:self.dialogs.pop()
    def run_task(self,*args):pass

class FakeCloud:
    online=True
    def __init__(self):
        self.user=SimpleNamespace(id='user-a');self.household={'id':'house-a','mode':'family','name':'Família teste','invite_code':'test'}
        self.member={'id':'mafra','display_name':'Mafra','user_id':'user-a','role':'owner'};self.profile={'full_name':'Mafra'}
    def _hid(self):return self.household['id']
    def list_members(self):return [self.member,{'id':'karol','display_name':'Karol','user_id':None,'role':'member'}]
    def all_income(self):return [{'id':'i','amount':1000,'member_id':'mafra','received_at':'2026-09-01','month':'09/2026','note':'Teste'}]
    def all_expenses_full(self):return [{'id':'e','amount':100,'payer_member_id':'mafra','expense_date':'07/09/2026','month':'09/2026','description':'Conta','category':'Outros','kind':'Variável','installments_total':1,'installment_number':1,'payment_status':'scheduled'}]
    def all_expenses(self,**kw):return self.all_expenses_full()
    def list_income(self,month):return self.all_income()
    def list_expenses(self,month):return self.all_expenses_full()
    def list_goals(self):return [{'id':'g','name':'Viagem','target_amount':300,'saved_amount':0,'target_date':'2026-12-31','status':'active','strategy':'Equilibrada'}]
    def list_acquisitions(self,*args):return [{'id':'a','item':'Livro','estimated':50,'saved':0,'priority':'Média','member_id':'mafra','status':'active'}]
    def list_market_trips(self):return []
    def list_affiliate_offers(self):return []

class UITests(unittest.TestCase):
    def app(self,width=390):
        with patch.object(NexGranaCloud,'render_entry'):
            app=NexGranaCloud(Page(width))
        app.cloud=FakeCloud();app.month='09/2026'
        return app
    def test_all_screens_all_sizes(self):
        for width in (360,390,430,768,1366,1920):
            app=self.app(width)
            for method in ('dashboard','income_screen','expenses_screen','acquisitions_screen','market_screen','planning_screen','assistant_screen','chat_screen','extra_income_screen','more_screen'):
                with self.subTest(width=width,screen=method):
                    self.assertIsInstance(getattr(app,method)(),ft.Control)
    def test_dialogs(self):
        app=self.app()
        for method,args in [('income_dialog',()),('expense_dialog',()),('goal_dialog',()),('acq_dialog',()),('goal_edit_dialog',(app.cloud.list_goals()[0],)),('payment_dialog',(app.cloud.all_expenses_full()[0],)),('allocation_dialog',()),('simulate_entry_dialog',(app.cloud.list_goals()[0],)),('privacy_dialog',())]:
            with self.subTest(dialog=method):getattr(app,method)(*args)
    def test_nex_action_has_response(self):
        app=self.app()
        for text in ('bom dia','Como está meu mês?','qual aquisição de uns R$50 posso comprar?','simular meta Viagem'):
            pair=app._process_nex_message(text)
            self.assertEqual(pair[1]['role'],'assistant');self.assertTrue(pair[1]['text'])
            self.assertNotIn('Não consegui consultar',pair[1]['text'])
    def test_no_invented_value_on_failure(self):
        app=self.app()
        app.cloud.all_income=lambda:(_ for _ in ()).throw(ConnectionError())
        pair=app._process_nex_message('Como está meu mês?')
        self.assertIn('Não consegui consultar',pair[1]['text']);self.assertNotIn('R$',pair[1]['text'])

if __name__=='__main__':unittest.main()
