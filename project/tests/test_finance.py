import sys
from pathlib import Path
import unittest
from datetime import date
from decimal import Decimal
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from services.finance_engine import snapshot, split_amount, expense_status, goal_scenarios, affordable_acquisitions, amount, day, monthly_goal_commitments, analysis_summary

class FinanceTests(unittest.TestCase):
    def income(self,value=100,received='2026-08-31',mid='mafra',**kw):
        return dict(id='i',amount=value,member_id=mid,received_at=received,receipt_status='received',**kw)
    def expense(self,value=714,due='07/09/2026',**kw):
        return dict(id='e',amount=value,expense_date=due,payer_member_id='mafra',payment_status=kw.pop('payment_status','scheduled'),**kw)
    def snap(self,i=None,e=None,month='09/2026',today=date(2026,9,3)):
        return snapshot([self.income()] if i is None else i,e or [],month,today=today)
    def test_rollover(self):
        self.assertEqual(self.snap()['balance'],100)
        self.assertEqual(self.snap(month='08/2026',today=date(2026,8,31))['balance'],100)
        self.assertEqual(self.snap()['member_balance']['mafra'],100)
    def test_future_does_not_debit(self):
        d=self.snap(e=[self.expense()]);self.assertEqual(d['balance'],100);self.assertEqual(d['projected_balance'],-614)
    def test_overdue_is_not_paid(self):
        d=self.snap(e=[self.expense(due='01/09/2026')]);self.assertEqual(d['balance'],100);self.assertEqual(d['overdue'],714)
    def test_manual_payment(self):
        d=self.snap(e=[self.expense(payment_status='paid',paid_at='2026-09-02')]);self.assertEqual(d['balance'],-614);self.assertEqual(d['pending_month'],0)
    def test_cancelled(self):
        d=self.snap(e=[self.expense(payment_status='cancelled')]);self.assertEqual(d['balance'],100);self.assertEqual(d['pending_month'],0)
    def test_automatic(self):
        d=self.snap(e=[self.expense(due='01/09/2026',automatic_debit=True)]);self.assertEqual(d['balance'],-614)
    def test_auto_future(self):
        self.assertEqual(self.snap(e=[self.expense(automatic_debit=True)])['balance'],100)
    def test_receipt_future(self):
        d=self.snap(i=[self.income(received='2026-09-10')]);self.assertEqual(d['balance'],0);self.assertEqual(d['expected_income'],100)
    def test_receipt_unknown(self):
        d=self.snap(i=[self.income(received=None)]);self.assertEqual(d['balance'],0);self.assertTrue(d['issues'])
    def test_paid_later_month(self):
        e=self.expense(50,'25/08/2026',payment_status='paid',paid_at='2026-09-02')
        self.assertEqual(self.snap(e=[e])['expense'],50)
        self.assertEqual(self.snap(e=[e],month='08/2026')['balance'],100)
    def test_shared_once(self):
        e=self.expense(60,payment_status='paid',paid_at='2026-09-02',expense_shares=[{'member_id':'mafra','amount':30},{'member_id':'karol','amount':30}])
        d=self.snap(e=[e]);self.assertEqual(d['balance'],40);self.assertEqual(sum(d['member_balance'].values()),40)
    def test_invalid_share_does_not_change_family(self):
        e=self.expense(60,payment_status='paid',paid_at='2026-09-02',expense_shares=[{'member_id':'mafra','amount':80}])
        d=self.snap(e=[e]);self.assertEqual(sum(d['member_balance'].values()),40);self.assertTrue(d['issues'])
    def test_rounding_shares(self):
        s=split_amount('100',['a','b','c']);self.assertEqual(sum(x[1] for x in s),100);self.assertEqual(s[0][1],Decimal('33.34'))
    def test_duplicate_ids(self):
        i=self.income();self.assertEqual(self.snap(i=[i,i])['balance'],100)
    def test_installments_are_distinct(self):
        e1=self.expense(40,'01/09/2026',payment_status='paid',paid_at='2026-09-01');e2={**e1,'id':'e2','expense_date':'01/10/2026','payment_status':'scheduled','paid_at':None}
        self.assertEqual(self.snap(e=[e1,e2])['balance'],60)
    def test_price_limit_is_full_price(self):
        data=dict(balance=10000,projected_balance=10000,projected_monthly_result=10000)
        items=[dict(item='PS5',estimated=4000,saved=3980,priority='Alta'),dict(item='Livro',estimated=50,saved=0)]
        rows,_=affordable_acquisitions(items,data,price_limit=50);self.assertEqual([r['item'] for r in rows],['Livro'])
    def test_no_margin_no_purchase(self):
        rows,_=affordable_acquisitions([dict(estimated=50)],dict(balance=1000,projected_balance=1000,projected_monthly_result=-10));self.assertEqual(rows,[])
    def test_reserve(self):
        rows,_=affordable_acquisitions([dict(estimated=50)],dict(balance=100,projected_balance=100,projected_monthly_result=100),reserve=80);self.assertEqual(rows,[])
    def test_goals(self):
        g=dict(id='g',target_amount=300,saved_amount=0,target_date='2026-11-30')
        s=goal_scenarios(g,200,500,entry=60,today=date(2026,9,3));self.assertEqual(s['keep'],100);self.assertEqual(s['plus_one'],75);self.assertEqual(s['after_entry'],80)
    def test_other_goals(self):
        g=dict(id='g',target_amount=300,saved_amount=0,target_date='2026-11-30');other={**g,'id':'g2','status':'active'}
        s=goal_scenarios(g,150,500,[other],today=date(2026,9,3));self.assertFalse(s['fits']);self.assertEqual(s['free'],50)
    def test_saved_goal_not_reserved_twice(self):
        data=dict(balance=500,projected_balance=500,projected_monthly_result=500)
        goal=dict(id='g',status='active',target_amount=1000,saved_amount=900,target_date='2026-10-31')
        # Only the remaining R$100 over two months is a future commitment.
        self.assertEqual(monthly_goal_commitments([goal],today=date(2026,9,3)),Decimal('50.00'))
        rows,budget=affordable_acquisitions([dict(item='Livro',estimated=200,priority='Média',status='active')],data,[goal],today=date(2026,9,3))
        self.assertEqual([r['item'] for r in rows],['Livro'])
        self.assertEqual(budget,450.0)

    def test_paused_goal_does_not_commit_margin(self):
        goal=dict(id='g',status='paused',target_amount=1000,saved_amount=0,target_date='2026-10-31')
        self.assertEqual(monthly_goal_commitments([goal],today=date(2026,9,3)),Decimal('0.00'))

    def test_analysis_summary_uses_safe_margin(self):
        data=dict(income=1000,expense=400,pending_month=200,balance=900,projected_balance=700,projected_monthly_result=400)
        goal=dict(id='g',status='active',target_amount=300,saved_amount=0,target_date='2026-11-30')
        a=analysis_summary(data,[goal],[40,30,10,20],minimum_reserve=100,today=date(2026,9,3))
        self.assertEqual(a['goal_monthly_commitment'],100.0)
        self.assertEqual(a['safe_margin'],300.0)
        self.assertAlmostEqual(sum(a['allocation_amounts']),300.0,places=2)
    def test_invalid_money(self):
        for v in ('NaN','Infinity','-Infinity'):
            with self.assertRaises(ValueError):amount(v)
    def test_dates(self):
        self.assertEqual(day('03/09/2026'),day('2026-09-03'))
        with self.assertRaises(ValueError):day('31/02/2026')

if __name__=='__main__':unittest.main()
