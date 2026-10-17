import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.journeys import journey_badges, journey_level, journey_steps, journey_xp
from services.product_copy import dashboard_labels, is_family_mode, space_label


class ProductExperienceTests(unittest.TestCase):
    def test_individual_copy_never_claims_family_scope(self):
        household = {"mode": "individual"}
        labels = dashboard_labels(household)
        self.assertFalse(is_family_mode(household))
        self.assertEqual(labels["consolidated_title"], "Seu panorama individual")
        self.assertNotIn("familiar", labels["consolidated_balance"])
        self.assertEqual(space_label(household, "individual", "familiar"), "individual")

    def test_family_copy_is_explicit(self):
        household = {"mode": "family"}
        labels = dashboard_labels(household)
        self.assertTrue(is_family_mode(household))
        self.assertEqual(labels["consolidated_title"], "Consolidado da família")
        self.assertIn("rateios", labels["profiles_tutorial"])

    def test_journey_has_ten_actionable_steps_and_specialization(self):
        generic = journey_steps("Limpeza residencial")
        meals = journey_steps("Marmitas e refeições")
        self.assertEqual(len(generic), 10)
        self.assertEqual(len(meals), 10)
        self.assertNotEqual(generic[0], meals[0])
        self.assertIn("porção", meals[3][0].casefold())
        self.assertTrue(all(name and detail for name, detail in meals))

    def test_journey_rewards_derive_only_from_real_progress(self):
        self.assertEqual(journey_level(0), ("Explorador", 1))
        self.assertEqual(journey_xp(0, {}), 0)
        self.assertEqual(journey_badges(0, {}), [])
        self.assertIn("🏆 Ciclo concluído", journey_badges(10, {}))
        self.assertEqual(journey_xp(2, {"notes": "evidência"}), 220)


if __name__ == "__main__":
    unittest.main()
