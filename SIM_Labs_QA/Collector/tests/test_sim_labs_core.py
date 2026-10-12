import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from src.sim_labs_core import import_feedback_package, inspect_build, render_report_markdown


class SimLabsCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def make_zip(self, path, files):
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, value in files.items():
                payload = value if isinstance(value, bytes) else value.encode("utf-8")
                archive.writestr(name, payload)
        return path

    def test_inspection_hashes_source_and_links_feedback_ids(self):
        package = self.make_zip(self.root / "source.zip", {
            "pyproject.toml": '[project]\nversion = "0.24.1"\n',
            "tests/test_smoke.py": "def test_smoke():\n    assert True\n",
            "SIM_LABS_INGEST.json": json.dumps({
                "schema": "sim-labs.feedback-ingest/1.0",
                "release": "0.24.1",
                "records": [{"feedback_id": "stable-feedback-1"}],
            }),
        })
        report = inspect_build(package, "Multiplataforma")
        self.assertEqual(report["overall"], "PASS")
        self.assertEqual(report["version"], "0.24.1")
        self.assertEqual(report["feedback_ids"], ["stable-feedback-1"])
        self.assertEqual(len(report["sha256"]), 64)
        self.assertTrue(any(check["id"] == "zip_crc" and check["status"] == "PASS" for check in report["checks"]))
        self.assertIn("não fecha o feedback", render_report_markdown(report))

    def test_feedback_import_merges_contract_record_with_full_manifest(self):
        feedback_id = "stable-feedback-2"
        package = self.make_zip(self.root / "collector.zip", {
            "manifest.json": json.dumps({
                "schema": "nexgrana.update_collector/0.3.1",
                "version_under_test": "0.24.0 QA",
                "items": [{"id": feedback_id, "title": "Título completo", "description": "Narrativa com contexto"}],
            }),
            "SIM_LABS_INGEST.json": json.dumps({
                "schema": "sim-labs.feedback-ingest/1.0",
                "release": "0.24.0 QA",
                "records": [{"feedback_id": feedback_id, "number": 7, "severity": "P2", "status": "Aberto"}],
            }),
        })
        result = import_feedback_package(package)
        self.assertEqual(len(result["records"]), 1)
        row = result["records"][0]
        self.assertEqual(row["feedback_id"], feedback_id)
        self.assertEqual(row["title"], "Título completo")
        self.assertEqual(row["description"], "Narrativa com contexto")
        self.assertEqual(row["number"], 7)

    def test_zip_traversal_is_rejected_before_feedback_import(self):
        package = self.make_zip(self.root / "unsafe.zip", {
            "../outside.txt": "no",
            "manifest.json": json.dumps({
                "schema": "nexgrana.update_collector/0.3.1",
                "items": [{"id": "unsafe-id"}],
            }),
        })
        report = inspect_build(package)
        self.assertEqual(report["overall"], "FAIL")
        with self.assertRaises(ValueError):
            import_feedback_package(package)


if __name__ == "__main__":
    unittest.main()
