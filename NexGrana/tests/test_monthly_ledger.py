import sys
from pathlib import Path
import unittest
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from services.monthly_ledger import opening_balance_for_month, month_is_closed
from services.finance_engine import snapshot


class MonthlyLedgerTests(unittest.TestCase):
    def setUp(self):
        self.members = [{"id": "m1", "display_name": "Mafra"}]
        self.incomes = [{
            "id": "income-sep", "amount": "200.79", "member_id": "m1",
            "month": "09/2026", "received_at": "2026-09-30", "receipt_status": "received",
        }]
        self.expenses = []
        self.closures = [{
            "id": "closed-sep-family", "month_start": "2026-09-01", "member_id": None,
            "status": "closed", "closing_balance": 200.79,
        }, {
            "id": "closed-sep-member", "month_start": "2026-09-01", "member_id": "m1",
            "status": "closed", "closing_balance": 200.79,
        }]

    def test_unconfirmed_prior_month_does_not_carry(self):
        self.assertEqual(opening_balance_for_month(
            self.incomes, self.expenses, [], "10/2026", self.members, "m1"), 0)

    def test_confirmed_month_carries_forward_once(self):
        opening = opening_balance_for_month(
            self.incomes, self.expenses, self.closures, "10/2026", self.members, "m1")
        self.assertEqual(float(opening), 200.79)
        october = snapshot([], [], "10/2026", self.members,
                           today=date(2026, 10, 1),
                           opening_balance=opening, opening_member_id="m1")
        self.assertEqual(october["balance"], 200.79)
        self.assertEqual(october["member_balance"]["m1"], 200.79)

    def test_late_expense_in_closed_month_recalculates_next_opening(self):
        late_expense = {
            "id": "late-sep", "amount": 30, "expense_date": "30/09/2026",
            "month": "09/2026", "payer_member_id": "m1", "payment_status": "paid",
        }
        opening = opening_balance_for_month(
            self.incomes, [late_expense], self.closures, "10/2026", self.members, "m1")
        self.assertEqual(float(opening), 170.79)

    def test_member_and_family_closures_are_independent(self):
        member_only = [row for row in self.closures if row["member_id"] == "m1"]
        self.assertTrue(month_is_closed(member_only, "09/2026", "m1"))
        self.assertFalse(month_is_closed(member_only, "09/2026", None))
        self.assertEqual(float(opening_balance_for_month(
            self.incomes, self.expenses, member_only, "10/2026", self.members, None)), 0)

    def test_continuity_stops_at_first_unconfirmed_month(self):
        closures = [row for row in self.closures if row["month_start"] != "2026-09-01"]
        closures += [{"month_start": "2026-08-01", "member_id": "m1", "status": "closed"}]
        opening = opening_balance_for_month(
            self.incomes, self.expenses, closures, "10/2026", self.members, "m1")
        self.assertEqual(float(opening), 0)


if __name__ == "__main__":
    unittest.main()
