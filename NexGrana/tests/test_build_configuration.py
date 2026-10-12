import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BuildConfigurationTests(unittest.TestCase):
    def test_flet_builds_use_supported_python_and_platform_crypto_wheels(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        flet = project["tool"]["flet"]

        self.assertEqual(project["project"]["requires-python"], ">=3.11,<3.13")
        self.assertIn("cryptography==43.0.1", flet["android"]["dependencies"])
        self.assertIn("cryptography==48.0.0", flet["windows"]["dependencies"])
