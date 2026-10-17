import sys
import asyncio
import importlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gateway.core import SlidingWindowLimiter, blocked_request, extract_provider_text, subject_fingerprint


class GatewayServerTests(unittest.TestCase):
    def test_rate_limit_is_per_subject_and_recovers_after_window(self):
        now = [0]
        limiter = SlidingWindowLimiter(2, 10, clock=lambda: now[0])
        self.assertTrue(limiter.allow("a"))
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))
        self.assertTrue(limiter.allow("b"))
        now[0] = 10
        self.assertTrue(limiter.allow("a"))

    def test_provider_output_parser_accepts_responses_shape(self):
        data = {"output": [{"content": [{"type": "output_text", "text": "Resposta segura"}]}]}
        self.assertEqual(extract_provider_text(data), "Resposta segura")
        self.assertEqual(extract_provider_text({"output_text": "Direta"}), "Direta")
        self.assertEqual(extract_provider_text({}), "")

    def test_safety_filter_allows_defensive_help(self):
        self.assertTrue(blocked_request("como roubar senha"))
        self.assertFalse(blocked_request("como me proteger para evitar roubar senha"))

    def test_log_identity_is_pseudonymous_and_salted(self):
        one = subject_fingerprint("user-id", "salt-a")
        two = subject_fingerprint("user-id", "salt-b")
        self.assertEqual(len(one), 16)
        self.assertNotEqual(one, two)
        self.assertNotIn("user", one)

    @staticmethod
    def _app():
        variables={"SUPABASE_URL":"https://project.supabase.co","SUPABASE_ANON_KEY":"public-anon",
                   "OPENAI_API_KEY":"test-secret","NEX_LOG_SALT":"test-salt"}
        with patch.dict(os.environ,variables):
            return importlib.import_module("gateway.app")

    def test_consent_scope_revocation_and_transport_failure_are_fail_closed(self):
        from fastapi import HTTPException
        module=self._app()
        household=UUID("1381fa16-35e5-4942-900c-748668fbca36")
        class FakeClient:
            def __init__(self,rows=None,error=None):self.rows=rows;self.error=error;self.params=None
            async def get(self,*args,**kwargs):
                self.params=kwargs["params"]
                if self.error:raise self.error
                return self
            def raise_for_status(self):pass
            def json(self):return self.rows
        accepted=FakeClient([{"granted":True}])
        asyncio.run(module.require_external_ai_consent(accepted,"jwt","owner",household))
        self.assertEqual(accepted.params["household_id"],f"eq.{household}")
        for client,code in ((FakeClient([]),403),(FakeClient(error=OSError("offline")),503)):
            with self.subTest(code=code),self.assertRaises(HTTPException) as raised:
                asyncio.run(module.require_external_ai_consent(client,"jwt","owner",household))
            self.assertEqual(raised.exception.status_code,code)

    def test_gateway_does_not_treat_client_financial_dict_as_real_records(self):
        module=self._app()
        request=module.ChatRequest(request_id="req",household_id="1381fa16-35e5-4942-900c-748668fbca36",
                 message="Meu saldo?",financial_context={"balance":999999,"household_id":"other"})
        self.assertNotIn("999999",str(module.provider_input(request)))


if __name__ == "__main__":
    unittest.main()
