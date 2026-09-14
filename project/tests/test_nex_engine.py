import sys
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from services.nex_engine import Context, NexEngine


class FakeCloud:
    online = True
    def __init__(self):
        self.household = {"id": "h1"}
        self.member = {"id": "m1"}
    def _hid(self): return "h1"
    def list_goals(self):
        return [{
            "id":"g1","name":"Notebook","target_amount":1200,"saved_amount":200,
            "target_date":"2026-12-31","status":"active","member_id":"m1"
        }]
    def list_acquisitions(self, active_only=True):
        return [{"id":"a1","item":"Mouse","estimated":80,"saved":0,"priority":"Média","status":"active"}]


class FakeApp:
    def __init__(self):
        self.cloud = FakeCloud()
        self.preferences = {"minimum_reserve": 100}
    def members(self): return [{"id":"m1","display_name":"Mafra"}]
    def _norm(self, text): return str(text).lower()
    def dashboard_data(self):
        return {
            "projected_monthly_result": 500,
            "projected_balance": 700,
            "balance": 800,
            "as_of":"2026-09-13",
        }
    def financial_chat_response(self, text): return "fallback"


class NexEngineTests(TestCase):
    def setUp(self):
        self.app = FakeApp()
        self.engine = NexEngine(self.app)

    def context(self, **kwargs):
        base = dict(source="test", household_id="h1", member_id="m1", month="09/2026")
        base.update(kwargs)
        return Context(**base)

    def test_goal_simulation_has_numeric_scenarios(self):
        text = self.engine.respond("simule", self.context(entity_id="g1", action="simulate_goal"))
        self.assertIn("+1 mês", text)
        self.assertIn("Margem conservadora", text)
        self.assertIn("Notebook", text)

    def test_acquisition_uses_specific_entity_and_budget(self):
        text = self.engine.respond("posso comprar?", self.context(entity_id="a1", action="evaluate_acquisition"))
        self.assertIn("Mouse", text)
        self.assertIn("comissão", text.lower())

    def test_household_context_guard_does_not_invent(self):
        text = self.engine.respond("simule", Context(source="test", household_id="other", member_id="m1", month="09/2026", action="simulate_goal", entity_id="g1"))
        self.assertIn("Não consegui consultar", text)
        self.assertIn("Não vou estimar", text)


if __name__ == "__main__":
    import unittest
    unittest.main()
