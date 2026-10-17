import sys
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from services.nex_conversation import ChatIntent, ChatScope, classify_intent, classify_intent_with_history, preferred_name_command, same_chat_context, same_chat_data_scope


class NexConversationTests(TestCase):
    def test_intent_keeps_casual_chat_out_of_financial_context(self):
        self.assertEqual(classify_intent("fala bro, suave?"),ChatIntent.GENERAL)
        self.assertEqual(classify_intent("quanto tenho de saldo?"),ChatIntent.FINANCIAL)
        self.assertEqual(classify_intent("onde fica o tutorial?"),ChatIntent.APP_HELP)
        self.assertEqual(classify_intent("adicione uma despesa"),ChatIntent.WRITE_PROPOSAL)

    def test_preferred_name_requires_explicit_command(self):
        self.assertEqual(preferred_name_command("pode me chamar de Mafra"),("set","Mafra"))
        self.assertEqual(preferred_name_command("não use apelido"),("clear",""))
        self.assertIsNone(preferred_name_command("Mafra comprou café"))

    def test_async_scope_changes_for_user_conversation_and_generation(self):
        base=ChatScope("u1","h1","m1","09/2026","free",1,"r1")
        self.assertNotEqual(base,ChatScope("u2","h1","m1","09/2026","free",1,"r1"))
        self.assertNotEqual(base,ChatScope("u1","h1","m1","09/2026","pinned",1,"r1"))
        self.assertNotEqual(base,ChatScope("u1","h1","m1","09/2026","free",2,"r1"))

    def test_async_scope_comparison_ignores_request_id_but_keeps_conversation(self):
        base=ChatScope("u1","h1","m1","09/2026","free",1,"r1")
        same_view=ChatScope("u1","h1","m1","09/2026","free",1,"r2")
        another_conversation=ChatScope("u1","h1","m1","09/2026","pinned",1,"r2")
        self.assertTrue(same_chat_context(base,same_view))
        self.assertFalse(same_chat_context(base,another_conversation))
        self.assertTrue(same_chat_data_scope(base,another_conversation))

    def test_short_continuation_keeps_recent_financial_subject(self):
        history=[{"role":"user","text":"Quero comprar uma moto"},{"role":"assistant","text":"Qual o valor?"}]
        self.assertEqual(classify_intent_with_history("E se eu der 5 mil?",history),ChatIntent.FINANCIAL)
        self.assertEqual(classify_intent_with_history("E depois?",[]),ChatIntent.GENERAL)
