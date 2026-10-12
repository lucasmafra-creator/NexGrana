import tempfile
import sys
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_multiplataforma


class BuildProvenanceTests(unittest.TestCase):
    def test_flet_build_uses_platform_crypto_wheels_and_supported_python(self):
        project = tomllib.loads((build_multiplataforma.ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        flet = project["tool"]["flet"]

        self.assertEqual(project["project"]["requires-python"], ">=3.11,<3.13")
        self.assertIn("cryptography==43.0.1", flet["android"]["dependencies"])
        self.assertIn("pillow==12.2.0", flet["android"]["dependencies"])
        self.assertIn("cryptography==48.0.0", flet["windows"]["dependencies"])
        self.assertIn("pillow==12.3.0", flet["windows"]["dependencies"])

    def test_generated_flet_storage_and_local_secrets_do_not_change_source_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "NexGrana"
            (root / "src").mkdir(parents=True)
            (root / "src" / "main.py").write_text("print('source')\n", encoding="utf-8")

            generated = root / "src" / ".flet" / "storage" / "data"
            generated.mkdir(parents=True)
            (generated / "vault").write_text("local-only", encoding="utf-8")
            (root / ".env").write_text("API_KEY=local-only", encoding="utf-8")
            (root / ".env.local").write_text("TOKEN=local-only", encoding="utf-8")
            gateway_data = root / "gateway"
            gateway_data.mkdir()
            for suffix in (".db-wal", ".db-shm", ".db-journal"):
                (gateway_data / f"local{suffix}").write_bytes(b"temporary database state")

            with patch.object(build_multiplataforma, "ROOT", root):
                before = build_multiplataforma.source_provenance()
                (generated / "FontManifest.json").write_text("new flutter cache", encoding="utf-8")
                (gateway_data / "local.db-wal").write_bytes(b"changed temporary database state")
                after = build_multiplataforma.source_provenance()

            self.assertEqual(before["source_file_count"], 1)
            self.assertEqual(before["source_manifest_sha256"], after["source_manifest_sha256"])


if __name__ == "__main__":
    unittest.main()
