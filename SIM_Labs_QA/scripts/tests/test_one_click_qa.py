import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("one_click_qa", SCRIPT_ROOT / "launch_authenticated_pipeline.py")
one_click_qa = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(one_click_qa)


class FakeLocalAPI:
    def __init__(self, qa_root, password, run_id):
        self.qa_root = qa_root
        self.password = password
        self.run_id = run_id
        self.posts = 0
        self.status_reads = 0
        self.password_ok = False

    def call(self, path, *, method="GET", payload=None, token=None):
        if path == "/api/v1/health":
            instance_path = self.qa_root.resolve().as_posix().lower().rstrip("/")
            return {
                "status": "ok",
                "service": one_click_qa.EXPECTED_SERVICE,
                "phase": one_click_qa.EXPECTED_PHASE,
                "instance_id": hashlib.sha256(instance_path.encode()).hexdigest()[:16],
            }
        if path == "/api/v1/auth/login" and method == "POST":
            self.password_ok = payload.get("password") == self.password
            if self.password_ok:
                return {"token": "TEST_DATA_SESSION_TOKEN"}
            raise one_click_qa.APIError(401, "login denied")
        if path == "/api/v1/qa/pipeline/status":
            self.status_reads += 1
            if self.posts == 0:
                return {"status": "NOT_RUN"}
            if self.status_reads == 2:
                report_dir = self.qa_root / "data" / "qa_pipeline" / "runs" / self.run_id
                report_dir.mkdir(parents=True, exist_ok=True)
                (report_dir / "pipeline-report.json").write_text(json.dumps({
                    "status": "PRONTA PARA QA REAL",
                    "summary": {"tests_passed": 2, "tests_blocked_or_failed": 0,
                                "native_builds_generated": 1, "windows_build_status": "BUILD OK",
                                "android_build_status": "BLOCKED"},
                    "tests": [{"name": "smoke", "status": "PASS"}],
                    "builds": [{"target": "windows", "status": "BUILD OK"},
                               {"target": "apk", "status": "BLOCKED"}],
                    "blockers": [],
                }), encoding="utf-8")
                return {"status": "PRONTA PARA QA REAL", "run_id": self.run_id}
            return {"status": "RUNNING", "run_id": self.run_id}
        if path == "/api/v1/qa/pipeline" and method == "POST":
            if token != "TEST_DATA_SESSION_TOKEN":
                raise one_click_qa.APIError(401, "unauthorized")
            self.posts += 1
            return {"status": "RUNNING", "run_id": self.run_id}
        raise AssertionError(f"Unexpected API request: {method} {path}")


class OneClickQATests(unittest.TestCase):
    def test_simulated_local_flow_runs_once_and_never_prints_credential(self):
        secret = "TEST_DATA_ONE_CLICK_PASSWORD"
        run_id = "a1b2c3d4e5f607182930abcdef123456"
        with tempfile.TemporaryDirectory() as folder:
            package_root = Path(folder)
            qa_root = package_root / "SIM_Labs_QA"
            runtime = qa_root / ".runtime"
            runtime.mkdir(parents=True)
            (runtime / "qa_port.txt").write_text("8012", encoding="ascii")
            (runtime / "PRIMEIRO_ACESSO.txt").write_text(f"Senha: {secret}\n", encoding="utf-8")
            api = FakeLocalAPI(qa_root, secret, run_id)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = one_click_qa.run_pipeline(qa_root, max_wait_seconds=3,
                                                   poll_seconds=0.001, api=api)

            self.assertEqual(result, 0)
            self.assertTrue(api.password_ok)
            self.assertEqual(api.posts, 1, "the QA pipeline must only receive one start request")
            self.assertNotIn(secret, output.getvalue())
            self.assertNotIn("TEST_DATA_SESSION_TOKEN", output.getvalue())
            self.assertIn("Android build: BLOCKED", output.getvalue())
            saved = json.loads((runtime / "one_click_qa.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "PRONTA PARA QA REAL")
            self.assertEqual(saved["run_id"], run_id)

    def test_running_pipeline_is_attached_without_posting_again(self):
        class FakeAPI:
            posts = 0
            def call(self, path, **kwargs):
                if path.endswith("/status"):
                    return {"status": "RUNNING", "run_id": "existing-run"}
                self.posts += 1
                raise AssertionError("duplicate pipeline request")

        api = FakeAPI()
        state, started_here = one_click_qa._start_or_attach(api, "token", poll_seconds=0.001)
        self.assertEqual(state["run_id"], "existing-run")
        self.assertFalse(started_here)
        self.assertEqual(api.posts, 0)

    def test_http_409_attaches_to_active_run_without_retrying_post(self):
        class FakeAPI:
            def __init__(self):
                self.status_reads = 0
                self.posts = 0
            def call(self, path, **kwargs):
                if path.endswith("/status"):
                    self.status_reads += 1
                    return ({"status": "NOT_RUN"} if self.status_reads == 1 else
                            {"status": "RUNNING", "run_id": "concurrent-run"})
                self.posts += 1
                raise one_click_qa.APIError(409, "conflict")

        api = FakeAPI()
        state, started_here = one_click_qa._start_or_attach(
            api, "token", poll_seconds=0.001, reconciliation_seconds=1)
        self.assertEqual(state["run_id"], "concurrent-run")
        self.assertFalse(started_here)
        self.assertEqual(api.posts, 1)

    def test_ambiguous_post_failure_checks_status_and_never_reposts(self):
        class FakeAPI:
            def __init__(self):
                self.status_reads = 0
                self.posts = 0
            def call(self, path, **kwargs):
                if path.endswith("/status"):
                    self.status_reads += 1
                    return ({"status": "NOT_RUN"} if self.status_reads == 1 else
                            {"status": "RUNNING", "run_id": "accepted-before-timeout"})
                self.posts += 1
                raise one_click_qa.APIError(None, "connection lost after accept")

        api = FakeAPI()
        state, started_here = one_click_qa._start_or_attach(
            api, "token", poll_seconds=0.001, reconciliation_seconds=1)
        self.assertEqual(state["run_id"], "accepted-before-timeout")
        self.assertFalse(started_here)
        self.assertEqual(api.posts, 1)

    def test_server_error_after_post_reconciles_status_without_retry(self):
        class FakeAPI:
            def __init__(self):
                self.status_reads = 0
                self.posts = 0
            def call(self, path, **kwargs):
                if path.endswith("/status"):
                    self.status_reads += 1
                    return ({"status": "NOT_RUN"} if self.status_reads == 1 else
                            {"status": "RUNNING", "run_id": "server-error-after-accept"})
                self.posts += 1
                raise one_click_qa.APIError(503, "service unavailable after mutation")

        api = FakeAPI()
        state, started_here = one_click_qa._start_or_attach(
            api, "token", poll_seconds=0.001, reconciliation_seconds=1)
        self.assertEqual(state["run_id"], "server-error-after-accept")
        self.assertFalse(started_here)
        self.assertEqual(api.posts, 1)


if __name__ == "__main__":
    unittest.main()
