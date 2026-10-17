import sys
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from services.tutorial import TUTORIAL_MODULES, TutorialScope, TutorialSession, TutorialStatus, tutorial_financial_preview, training_money


class TutorialTests(TestCase):
    def test_catalog_contains_all_required_modules(self):
        keys={module.key for module in TUTORIAL_MODULES}
        self.assertEqual(keys,{"welcome","balance","income","expense","acquisition","goals","investments","extra_income","market","offers","nex","family","privacy"})

    def test_expense_only_debits_on_due_date_using_canonical_engine(self):
        before=tutorial_financial_preview(200,10,"20/09/2026","19/09/2026")
        due=tutorial_financial_preview(200,10,"20/09/2026","20/09/2026")
        self.assertEqual(before["current_balance"],200)
        self.assertEqual(before["projected_balance"],190)
        self.assertEqual(before["pending"],10)
        self.assertEqual(due["current_balance"],190)
        self.assertEqual(due["projected_balance"],190)
        self.assertEqual(due["effective_expense"],10)

    def test_sandbox_discard_never_creates_commit(self):
        scope=TutorialScope("u","h","m",1)
        session=TutorialSession(scope)
        session.preview_balance()
        session.discard("balance")
        self.assertNotIn("balance",session.sandbox)
        self.assertEqual(session.statuses["balance"],TutorialStatus.DISCARDED.value)
        self.assertEqual(session.commit_ids,{})

    def test_commit_id_is_stable_for_retry_and_progress_is_separate(self):
        session=TutorialSession(TutorialScope("u","h","m",1))
        first=session.stable_commit_id("expense")
        self.assertEqual(first,session.stable_commit_id("expense"))
        session.complete("expense",pending_sync=True)
        self.assertEqual(session.statuses["expense"],TutorialStatus.PENDING_SYNC.value)
        self.assertGreater(session.progress,0)

    def test_new_scope_does_not_accept_old_sandbox_mapping(self):
        old=TutorialSession(TutorialScope("u1","h1","m1",1))
        old.preview_balance()
        restored=TutorialSession.from_mapping(TutorialScope("u2","h1","m1",2),old.to_mapping())
        self.assertEqual(restored.sandbox,{})
        self.assertEqual(restored.statuses,{})

    def test_refresh_preserves_progress_but_change_of_owner_does_not(self):
        first=TutorialSession(TutorialScope("user","home","member",1))
        first.preview_balance()
        restored=TutorialSession.from_mapping(TutorialScope("user","home","member",99),first.to_mapping())
        self.assertEqual(restored.sandbox["balance"]["projected_balance"],190)
        changed=TutorialSession.from_mapping(TutorialScope("user","other","member",99),first.to_mapping())
        self.assertEqual(changed.sandbox,{})

    def test_legacy_key_migrates_only_same_user_household_member(self):
        mapping=TutorialSession(TutorialScope("u","h","m",1)).to_mapping()
        mapping["scope_key"]="u:h:m:13"
        mapping["statuses"]={"income":"completed"}
        self.assertEqual(TutorialSession.from_mapping(TutorialScope("u","h","m",14),mapping).completed_count,1)
        self.assertEqual(TutorialSession.from_mapping(TutorialScope("u","h","other",14),mapping).completed_count,0)

    def test_unscoped_progress_is_not_trusted_for_another_account(self):
        unscoped={"statuses":{"income":"completed"},"sandbox":{"income":{"valor":"999"}}}
        restored=TutorialSession.from_mapping(TutorialScope("other","h","m",1),unscoped)
        self.assertEqual(restored.sandbox,{})
        self.assertEqual(restored.completed_count,0)

    def test_training_money_rejects_invalid_input_and_accepts_brazilian_amount(self):
        self.assertEqual(str(training_money("1.234,50")),"1234.50")
        for invalid in ("", "tela confusa", "NaN", "Infinity", "-5", "1,2,3", "1.2.3", ".", ",5"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                training_money(invalid)
