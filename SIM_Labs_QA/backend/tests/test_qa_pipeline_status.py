import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.routers import qa_pipeline


class PipelineStatusRecoveryTests(unittest.TestCase):
    def test_dead_run_becomes_blocked_and_releases_only_its_own_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            latest = root / "latest.json"
            lock = root / "active.lock"
            state_root = root / "qa_pipeline"
            run_id = "dead-run-123"
            state = {
                "run_id": run_id,
                "pid": 48712,
                "status": "RUNNING",
                "report_path": str(state_root / "runs" / run_id / "pipeline-report.json"),
                "log_path": str(state_root / "runs" / run_id / "pipeline.log"),
            }
            latest.write_text(json.dumps(state), encoding="utf-8")
            lock.write_text(json.dumps({"run_id": run_id, "pid": 48712}), encoding="utf-8")

            with patch.object(qa_pipeline, "LATEST_PATH", latest), \
                 patch.object(qa_pipeline, "LOCK_PATH", lock), \
                 patch.object(qa_pipeline, "STATE_ROOT", state_root), \
                 patch.object(qa_pipeline, "_pid_is_running", return_value=False):
                result = qa_pipeline._safe_status()

            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("encerrou", result["blockers"][0])
            self.assertFalse(lock.exists())
            self.assertEqual(json.loads(latest.read_text(encoding="utf-8"))["status"], "BLOCKED")

    def test_live_run_remains_running_and_keeps_its_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            latest = root / "latest.json"
            lock = root / "active.lock"
            state_root = root / "qa_pipeline"
            run_id = "live-run-456"
            latest.write_text(json.dumps({
                "run_id": run_id,
                "pid": 48713,
                "status": "RUNNING",
                "report_path": str(state_root / "runs" / run_id / "pipeline-report.json"),
            }), encoding="utf-8")
            lock.write_text(json.dumps({"run_id": run_id, "pid": 48713}), encoding="utf-8")

            with patch.object(qa_pipeline, "LATEST_PATH", latest), \
                 patch.object(qa_pipeline, "LOCK_PATH", lock), \
                 patch.object(qa_pipeline, "STATE_ROOT", state_root), \
                 patch.object(qa_pipeline, "_pid_is_running", return_value=True):
                result = qa_pipeline._safe_status()

            self.assertEqual(result["status"], "RUNNING")
            self.assertTrue(lock.exists())

    def test_incomplete_report_does_not_keep_a_dead_run_running(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state_root = root / "qa_pipeline"
            run_id = "partial-run-789"
            run_dir = state_root / "runs" / run_id
            run_dir.mkdir(parents=True)
            report = run_dir / "pipeline-report.json"
            report.write_text(json.dumps({"status": "RUNNING"}), encoding="utf-8")
            latest = root / "latest.json"
            latest.write_text(json.dumps({
                "run_id": run_id,
                "pid": 48714,
                "status": "RUNNING",
                "report_path": str(report),
            }), encoding="utf-8")
            lock = root / "active.lock"

            with patch.object(qa_pipeline, "LATEST_PATH", latest), \
                 patch.object(qa_pipeline, "LOCK_PATH", lock), \
                 patch.object(qa_pipeline, "STATE_ROOT", state_root), \
                 patch.object(qa_pipeline, "_pid_is_running", return_value=False):
                result = qa_pipeline._safe_status()

            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("encerrou", result["blockers"][0])

    def test_finished_report_releases_only_its_dead_run_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state_root = root / "qa_pipeline"
            run_id = "finished-run-321"
            run_dir = state_root / "runs" / run_id
            run_dir.mkdir(parents=True)
            report = run_dir / "pipeline-report.json"
            report.write_text(json.dumps({
                "status": "BLOCKED",
                "finished_at": "2026-10-09T20:00:00+00:00",
                "summary": {"tests_passed": 1},
            }), encoding="utf-8")
            latest = root / "latest.json"
            latest.write_text(json.dumps({
                "run_id": run_id,
                "pid": 48715,
                "status": "RUNNING",
                "report_path": str(report),
            }), encoding="utf-8")
            lock = root / "active.lock"
            lock.write_text(json.dumps({"run_id": run_id, "pid": 48715}), encoding="utf-8")

            with patch.object(qa_pipeline, "LATEST_PATH", latest), \
                 patch.object(qa_pipeline, "LOCK_PATH", lock), \
                 patch.object(qa_pipeline, "STATE_ROOT", state_root), \
                 patch.object(qa_pipeline, "_pid_is_running", return_value=False):
                result = qa_pipeline._safe_status()

            self.assertEqual(result["status"], "BLOCKED")
            self.assertFalse(lock.exists())


if __name__ == "__main__":
    unittest.main()
