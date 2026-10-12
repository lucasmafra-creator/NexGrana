import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.investment_engine import investment_projection


class InvestmentProjectionTests(unittest.TestCase):
    def test_zero_rate_keeps_only_declared_contributions(self):
        result = investment_projection(100, 10, 2, 0)
        self.assertEqual(result["total_invested"], Decimal("120.00"))
        self.assertEqual(result["gross_result"], Decimal("120.00"))
        self.assertEqual(result["hypothetical_gain"], Decimal("0.00"))

    def test_beginning_contribution_earns_one_more_period(self):
        end = investment_projection(0, 100, 1, 10, contribution_timing="end")
        begin = investment_projection(0, 100, 1, 10, contribution_timing="begin")
        self.assertEqual(end["gross_result"], Decimal("100.00"))
        self.assertEqual(begin["gross_result"], Decimal("110.00"))

    def test_annual_rate_uses_monthly_compound_equivalence(self):
        result = investment_projection(100, 0, 12, 12, rate_period="annual")
        self.assertEqual(result["gross_result"], Decimal("112.00"))
        self.assertIn("anual efetiva", result["convention"])

    def test_negative_rate_costs_and_taxes_are_explicit(self):
        result = investment_projection(100, 0, 1, -10, costs=2, taxes=1)
        self.assertEqual(result["gross_result"], Decimal("90.00"))
        self.assertEqual(result["net_result"], Decimal("87.00"))

    def test_invalid_period_rate_and_money_are_rejected(self):
        for args in [
            (0, 0, 0, 0),
            (0, 0, 601, 0),
            (-1, 0, 12, 0),
            (0, 0, 12, -101),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                investment_projection(*args)


if __name__ == "__main__":
    unittest.main()
