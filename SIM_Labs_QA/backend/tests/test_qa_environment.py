import base64
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.qa_environment import inspect_qa_environment, enforce_qa_environment, QAEnvironmentError


def token_for_role(role):
    payload = base64.urlsafe_b64encode(json.dumps({"role": role}).encode()).decode().rstrip("=")
    return "header." + payload + ".signature"


class QAEnvironmentTests(unittest.TestCase):
    def test_local_sqlite_without_external_secrets_is_allowed(self):
        result = inspect_qa_environment({"APP_ENV": "local", "DATABASE_URL": "sqlite:///./qa.db"})
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mode"], "local-only")
        self.assertFalse(result["secret_values_returned"])

    def test_production_mode_is_refused(self):
        with self.assertRaises(QAEnvironmentError):
            enforce_qa_environment({"APP_ENV": "production", "DATABASE_URL": "sqlite:///./qa.db"})

    def test_service_role_is_refused_without_echoing_value(self):
        secret = "test-only-do-not-use"
        result = inspect_qa_environment({"SUPABASE_SERVICE_ROLE_KEY": secret})
        self.assertEqual(result["status"], "BLOCKED")
        self.assertNotIn(secret, json.dumps(result))

    def test_remote_supabase_requires_exact_allowlisted_qa_endpoint(self):
        values = {"SUPABASE_URL": "https://qa-project.supabase.co"}
        self.assertEqual(inspect_qa_environment(values)["status"], "BLOCKED")
        values["SIMLABS_QA_SUPABASE_URL"] = "https://qa-project.supabase.co/"
        values["SIMLABS_QA_SUPABASE_PROJECT_REF"] = "qa-project"
        self.assertEqual(inspect_qa_environment(values)["status"], "PASS")

    def test_remote_database_requires_exact_allowlisted_qa_endpoint(self):
        values = {"DATABASE_URL": "postgresql://user:secret@db.example/qa"}
        self.assertEqual(inspect_qa_environment(values)["status"], "BLOCKED")
        values["SIMLABS_QA_DATABASE_PROJECT_REF"] = "qa-project"
        values["DATABASE_URL"] = "postgresql://user:secret@db.qa-project.supabase.co/qa"
        values["SIMLABS_QA_DATABASE_URL"] = values["DATABASE_URL"]
        self.assertEqual(inspect_qa_environment(values)["status"], "PASS")

    def test_service_role_jwt_is_refused_even_under_generic_key_name(self):
        result = inspect_qa_environment({"SUPABASE_KEY": token_for_role("service_role")})
        self.assertEqual(result["status"], "BLOCKED")

    def test_current_supabase_secret_key_prefix_is_refused_under_any_supabase_key_name(self):
        result = inspect_qa_environment({"SUPABASE_KEY": "sb_secret_test-only"})
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
