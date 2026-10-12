import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Não foi possível importar {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ManifestConsistencyTests(unittest.TestCase):
    def make_package(self, package_root: Path):
        for tree in ("NexGrana", "SIM_Labs", "SIM_Labs_QA", "tools"):
            directory = package_root / tree
            directory.mkdir(parents=True)
            (directory / "source.txt").write_text("fixture", encoding="utf-8")
        for name in ("REPARAR_E_INICIAR_SIM_LABS_QA.cmd", "REPARAR_E_INICIAR_SIM_LABS_QA.ps1"):
            (package_root / name).write_text("fixture", encoding="utf-8")
        subprocess.run(
            [sys.executable, str(SCRIPT_ROOT / "generate_release_manifest.py"), "--package-root", str(package_root)],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_generator_and_pipeline_verifier_agree_with_live_sqlite_sidecars(self):
        generator = load_module("manifest_generator_test", SCRIPT_ROOT / "generate_release_manifest.py")
        runner = load_module("release_runner_test", SCRIPT_ROOT / "run_release_pipeline.py")

        with tempfile.TemporaryDirectory() as folder:
            package_root = Path(folder)
            self.make_package(package_root)
            launchers = ("REPARAR_E_INICIAR_SIM_LABS_QA.cmd", "REPARAR_E_INICIAR_SIM_LABS_QA.ps1")

            backend = package_root / "SIM_Labs_QA" / "backend"
            backend.mkdir()
            sidecars = [backend / "sim_labs.db-shm", backend / "sim_labs.db-wal", backend / "sim_labs.db-journal"]
            self.assertTrue(all(generator.excluded(Path("SIM_Labs_QA/backend") / path.name) for path in sidecars))

            subprocess.run(
                [sys.executable, str(SCRIPT_ROOT / "generate_release_manifest.py"), "--package-root", str(package_root)],
                check=True,
                capture_output=True,
                text=True,
            )
            manifest = json.loads((package_root / "release_manifest.json").read_text(encoding="utf-8"))
            listed = {item["path"] for item in manifest["source_files"]}
            self.assertTrue(set(launchers).issubset(listed))

            for path in sidecars:
                path.write_bytes(b"temporary sqlite runtime state")
            result = runner.verify_manifest(package_root)
            self.assertEqual(result["status"], "PASS", result)

    def test_overlaid_old_source_is_quarantined_and_manifest_passes(self):
        runner = load_module("release_runner_overlay_test", SCRIPT_ROOT / "run_release_pipeline.py")
        with tempfile.TemporaryDirectory() as folder:
            package_root = Path(folder)
            self.make_package(package_root)
            stale = package_root / "NexGrana" / "removed_from_new_release.py"
            stale.write_text("old user source", encoding="utf-8")

            result = runner.quarantine_unmanifested_source_files(package_root)

            self.assertEqual(result["status"], "PASS", result)
            self.assertEqual(result["quarantined_count"], 1)
            self.assertFalse(stale.exists())
            matches = list((package_root / "SIM_Labs_QA" / ".runtime" / "source-quarantine").rglob("removed_from_new_release.py"))
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0].read_text(encoding="utf-8"), "old user source")
            self.assertTrue(result["manifest"]["status"] == "PASS")

    def test_modified_manifested_source_is_blocked_without_moving_files(self):
        runner = load_module("release_runner_modified_test", SCRIPT_ROOT / "run_release_pipeline.py")
        with tempfile.TemporaryDirectory() as folder:
            package_root = Path(folder)
            self.make_package(package_root)
            tracked = package_root / "NexGrana" / "source.txt"
            tracked.write_text("locally modified", encoding="utf-8")

            result = runner.quarantine_unmanifested_source_files(package_root)

            self.assertEqual(result["status"], "BLOCKED", result)
            self.assertEqual(tracked.read_text(encoding="utf-8"), "locally modified")
            self.assertFalse((package_root / "SIM_Labs_QA" / ".runtime" / "source-quarantine").exists())


if __name__ == "__main__":
    unittest.main()
