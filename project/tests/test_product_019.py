import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

from services.analytics import AnalyticsAdapter
from services.performance import PerformanceMonitor
from services.offers import Recommendation, rank_recommendations, validate_offer_url
from services.nex_engine import Context, NexEngine


class FakeCloud:
    online=True
    def _hid(self): return 'h1'
    def list_goals(self): return []
    def list_acquisitions(self,active_only=True): return []

class FakeApp:
    def __init__(self):
        self.cloud=FakeCloud(); self.preferences={}
    def _norm(self,text): return str(text).lower()
    def members(self): return [{'id':'m1','display_name':'Mafra'}]
    def dashboard_data(self):
        return {
            'month':'09/2026','as_of':'2026-09-14','income':1000,'expense':600,
            'balance':500,'pending_month':100,'projected_balance':400,
            'pending_rows':[{'description':'Internet','amount':100,'expense_date':'2026-09-20'}],
            'categories':[('Transporte',250)],
            'projected_monthly_result':300,
        }
    def financial_analysis(self): return {'free_margin':200}
    def financial_chat_response(self,text): return 'fallback'

class Product019Tests(unittest.TestCase):
    def test_analytics_is_off_by_default_and_rejects_financial_payload(self):
        a=AnalyticsAdapter()
        self.assertFalse(a.track('useful_action_completed',action_type='goal',success=True))
        a.enabled=True
        self.assertTrue(a.track('useful_action_completed',action_type='goal',success=True))
        with self.assertRaises(ValueError):
            a.track('useful_action_completed',action_type='goal',success=True,amount=100)

    def test_offer_ranking_is_independent_from_commission(self):
        rows=[
            Recommendation('a','Produto A',0.8,'fit'),
            Recommendation('b','Produto B',0.9,'fit'),
        ]
        self.assertEqual([r.key for r in rank_recommendations(rows)],['b','a'])
        self.assertTrue(validate_offer_url('https://meli.la/abc',{'meli.la'}))
        self.assertFalse(validate_offer_url('http://meli.la/abc',{'meli.la'}))
        self.assertFalse(validate_offer_url('https://user:pass@meli.la/abc',{'meli.la'}))

    def test_performance_monitor_summary(self):
        p=PerformanceMonitor()
        for n in (10,20,30,40,50): p.record('nav',n)
        summary=p.summary('nav')
        self.assertEqual(summary['count'],5)
        self.assertGreaterEqual(summary['p95_ms'],40)

    def test_nex_quick_actions_are_deterministic(self):
        engine=NexEngine(FakeApp())
        base=dict(source='quick',household_id='h1',member_id='m1',month='09/2026')
        month=engine.respond('Como está meu mês?',Context(**base,action='month_summary'))
        self.assertIn('R$ 1.000,00',month)
        bills=engine.respond('Próximas contas',Context(**base,action='next_bills'))
        self.assertIn('Internet',bills)
        save=engine.respond('Me ajude a economizar',Context(**base,action='save_money'))
        self.assertIn('Transporte',save)

    def test_journey_has_ten_steps(self):
        engine=NexEngine(FakeApp())
        ctx=Context(source='journey',household_id='h1',member_id='m1',month='09/2026',action='continue_journey',payload={'title':'Doces','progress':8})
        text=engine.respond('continuar',ctx)
        self.assertIn('Etapa 9/10',text)
        self.assertIn('Revisar o resultado',text)

if __name__=='__main__': unittest.main()
