import sys
from pathlib import Path
import unittest
from datetime import date
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from services.finance_engine import (
    snapshot,
    split_amount,
    expense_status,
    goal_scenarios,
    affordable_acquisitions,
    amount,
    day,
    monthly_goal_commitments,
    analysis_summary,
)


class FinanceTests(unittest.TestCase):
    def income(self, value=100, received="2026-09-01", mid="mafra", month="09/2026", rid="i", **kw):
        return dict(
            id=rid,
            amount=value,
            member_id=mid,
            month=month,
            received_at=received,
            receipt_status="received",
            **kw,
        )

    def expense(self, value=714, due="07/09/2026", payer="mafra", rid="e", **kw):
        return dict(
            id=rid,
            amount=value,
            expense_date=due,
            payer_member_id=payer,
            payment_status=kw.pop("payment_status", "scheduled"),
            **kw,
        )

    def snap(self, i=None, e=None, month="09/2026", today=date(2026, 9, 3)):
        return snapshot([self.income()] if i is None else i, e or [], month, today=today)

    def test_monthly_income_enters_balance(self):
        data = self.snap()
        self.assertEqual(data["income"], 100)
        self.assertEqual(data["balance"], 100)
        self.assertEqual(data["member_balance"]["mafra"], 100)

    def test_other_month_income_is_ignored(self):
        august = self.income(received="2026-08-31", month="08/2026")
        data = self.snap(i=[august])
        self.assertEqual(data["income"], 0)
        self.assertEqual(data["balance"], 0)

    def test_future_expense_does_not_debit(self):
        data = self.snap(e=[self.expense()])
        self.assertEqual(data["balance"], 100)
        self.assertEqual(data["pending_month"], 714)
        self.assertEqual(data["projected_balance"], -614)

    def test_due_date_debits_automatically(self):
        data = self.snap(e=[self.expense(due="01/09/2026")])
        self.assertEqual(data["expense"], 714)
        self.assertEqual(data["balance"], -614)
        self.assertEqual(data["pending_month"], 0)

    def test_expense_changes_exactly_on_day_twenty(self):
        bill = self.expense(10, due="20/09/2026")
        before = self.snap(e=[bill], today=date(2026, 9, 19))
        on_due = self.snap(e=[bill], today=date(2026, 9, 20))
        self.assertEqual(before["balance"], 100)
        self.assertEqual(before["pending_month"], 10)
        self.assertEqual(on_due["balance"], 90)
        self.assertEqual(on_due["pending_month"], 0)
        self.assertEqual(expense_status(bill, date(2026, 9, 19)), "scheduled")
        self.assertEqual(expense_status(bill, date(2026, 9, 20)), "paid")

    def test_paid_flag_does_not_debit_before_due_date(self):
        bill = self.expense(payment_status="paid", paid_at="2026-09-02")
        data = self.snap(e=[bill])
        self.assertEqual(data["balance"], 100)
        self.assertEqual(data["pending_month"], 714)

    def test_cancelled_expense_is_ignored(self):
        data = self.snap(e=[self.expense(payment_status="cancelled")])
        self.assertEqual(data["balance"], 100)
        self.assertEqual(data["pending_month"], 0)

    def test_automatic_due_expense_debits(self):
        data = self.snap(e=[self.expense(due="01/09/2026", automatic_debit=True)])
        self.assertEqual(data["balance"], -614)

    def test_automatic_future_expense_stays_future(self):
        data = self.snap(e=[self.expense(automatic_debit=True)])
        self.assertEqual(data["balance"], 100)
        self.assertEqual(data["pending_month"], 714)

    def test_income_is_summed_by_competence_without_inventing_day(self):
        data = self.snap(i=[self.income(received="2026-09-30")])
        self.assertEqual(data["income"], 100)
        self.assertEqual(data["balance"], 100)
        self.assertEqual(data["expected_income"], 0)

    def test_income_with_month_and_no_date_is_valid(self):
        data = self.snap(i=[self.income(received=None)])
        self.assertEqual(data["income"], 100)
        self.assertEqual(data["balance"], 100)
        self.assertEqual(data["issues"], [])

    def test_income_without_month_or_date_is_rejected(self):
        data = self.snap(i=[self.income(received=None, month=None)])
        self.assertEqual(data["income"], 0)
        self.assertEqual(data["balance"], 0)
        self.assertTrue(data["issues"])

    def test_prior_month_expense_is_ignored(self):
        data = self.snap(e=[self.expense(due="31/08/2026")])
        self.assertEqual(data["expense"], 0)
        self.assertEqual(data["pending_month"], 0)
        self.assertEqual(data["balance"], 100)
        self.assertEqual(data["prior_overdue"], 0)

    def test_payment_date_does_not_move_expense_between_months(self):
        old = self.expense(50, due="25/08/2026", payment_status="paid", paid_at="2026-09-02")
        september = self.snap(e=[old])
        august = self.snap(i=[], e=[old], month="08/2026", today=date(2026, 9, 3))
        self.assertEqual(september["expense"], 0)
        self.assertEqual(september["balance"], 100)
        self.assertEqual(august["expense"], 50)
        self.assertEqual(august["balance"], -50)

    def test_shared_expense_is_subtracted_once(self):
        bill = self.expense(
            60,
            due="01/09/2026",
            expense_shares=[
                {"member_id": "mafra", "amount": 30},
                {"member_id": "karol", "amount": 30},
            ],
        )
        data = self.snap(e=[bill])
        self.assertEqual(data["balance"], 40)
        self.assertEqual(sum(data["member_balance"].values()), 40)

    def test_invalid_share_does_not_change_family_total(self):
        bill = self.expense(
            60,
            due="01/09/2026",
            expense_shares=[{"member_id": "mafra", "amount": 80}],
        )
        data = self.snap(e=[bill])
        self.assertEqual(sum(data["member_balance"].values()), 40)
        self.assertEqual(data["balance"], 40)
        self.assertTrue(data["issues"])

    def test_rounding_shares(self):
        shares = split_amount("100", ["a", "b", "c"])
        self.assertEqual(sum(item[1] for item in shares), 100)
        self.assertEqual(shares[0][1], Decimal("33.34"))

    def test_duplicate_ids_are_counted_once(self):
        row = self.income()
        self.assertEqual(self.snap(i=[row, row])["balance"], 100)

    def test_installments_in_other_month_are_ignored(self):
        september = self.expense(40, "01/09/2026", rid="e1")
        october = self.expense(40, "01/10/2026", rid="e2")
        self.assertEqual(self.snap(e=[september, october])["balance"], 60)

    def test_mafra_karol_balance_and_future_bill_exactly(self):
        incomes = [
            self.income("2016.00", mid="mafra", rid="income-mafra"),
            self.income("1783.09", mid="karol", rid="income-karol"),
        ]
        expenses = [
            self.expense("1815.21", due="01/09/2026", payer="mafra", rid="expense-mafra"),
            self.expense("1700.44", due="01/09/2026", payer="karol", rid="expense-karol"),
            self.expense("10.00", due="20/09/2026", payer="mafra", rid="future-20"),
        ]
        data = snapshot(incomes, expenses, "09/2026", today=date(2026, 9, 14))
        self.assertAlmostEqual(data["income"], 3799.09, places=2)
        self.assertAlmostEqual(data["expense"], 3515.65, places=2)
        self.assertAlmostEqual(data["balance"], 283.44, places=2)
        self.assertAlmostEqual(data["member_balance"]["mafra"], 200.79, places=2)
        self.assertAlmostEqual(data["member_balance"]["karol"], 82.65, places=2)
        self.assertAlmostEqual(sum(data["member_balance"].values()), data["balance"], places=2)
        self.assertAlmostEqual(data["pending_month"], 10.00, places=2)
        self.assertAlmostEqual(data["projected_balance"], 273.44, places=2)

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
