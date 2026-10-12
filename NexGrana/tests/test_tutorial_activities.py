import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from services.tutorial_activities import practice_income, practice_goal, practice_basket, practice_investment


class TutorialActivityTests(unittest.TestCase):
    def test_income_is_practice_and_competence_is_explicit(self):
        row=practice_income("Aula", "200,00", "20/09/2026")
        self.assertEqual(row["competence"],"09/2026")
        self.assertEqual(str(row["amount"]),"200.00")
        for invalid in ("", "tela confusa", "-10"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                practice_income("Aula",invalid,"20/09/2026")

    def test_goal_progress_and_monthly_need(self):
        row=practice_goal("10.000,00","2.000,00",10)
        self.assertEqual(str(row["progress"]),"20.0")
        self.assertEqual(str(row["monthly"]),"800.00")

    def test_basket_exact_change_and_edit(self):
        items=[{"name":"Arroz","quantity":2,"price":"24,90"}]
        self.assertEqual(str(practice_basket(items,"100,00")["remaining"]),"50.20")
        items[0]["quantity"]=3
        self.assertEqual(str(practice_basket(items,"100,00")["remaining"]),"25.30")
        self.assertTrue(practice_basket(items,"20,00")["over_budget"])

    def test_investment_is_projection_without_real_record(self):
        result=practice_investment("100,00","100,00",12,"0")
        self.assertEqual(str(result["total_invested"]),"1300.00")
        self.assertEqual(result["total_invested"],result["net_result"])


if __name__=="__main__":
    unittest.main()
