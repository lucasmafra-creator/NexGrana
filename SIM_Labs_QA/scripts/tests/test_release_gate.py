import importlib.util
import unittest
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_runner_gate", SCRIPT_ROOT / "run_release_pipeline.py")
runner = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(runner)


class ReleaseGateTests(unittest.TestCase):
    def test_android_status_does_not_hide_a_passed_windows_gate(self):
        tests = [{"name": "unit", "status": "PASS"}, {"name": "financial", "status": "PASS"}]
        builds = [
            {"target": "windows", "status": "BUILD OK"},
            {"target": "apk", "status": "BLOCKED", "reason": "Android SDK unavailable"},
        ]
        self.assertTrue(runner.is_ready_for_windows_qa(tests, builds))

    def test_windows_build_is_required_for_ready_status(self):
        tests = [{"name": "unit", "status": "PASS"}]
        builds = [
            {"target": "windows", "status": "BLOCKED"},
            {"target": "apk", "status": "BUILD OK"},
        ]
        self.assertFalse(runner.is_ready_for_windows_qa(tests, builds))

    def test_every_test_category_must_pass(self):
        tests = [{"name": "unit", "status": "PASS"}, {"name": "profile_isolation", "status": "BLOCKED"}]
        builds = [{"target": "windows", "status": "BUILD OK"}]
        self.assertFalse(runner.is_ready_for_windows_qa(tests, builds))


if __name__ == "__main__":
    unittest.main()
