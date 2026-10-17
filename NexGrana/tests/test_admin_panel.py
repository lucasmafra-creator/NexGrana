import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from admin.achados_admin import field_values, main


class FakePage:
    def __init__(self):
        self.width = 390
        self.height = 780
        self.controls = []
        self.dialogs = []

    def add(self, *controls):
        self.controls.extend(controls)

    def clean(self):
        self.controls.clear()

    def update(self):
        pass

    def show_dialog(self, control):
        self.dialogs.append(control)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()


def descendants(control):
    yield control
    content = getattr(control, "content", None)
    if content is not None:
        yield from descendants(content)
    for child in getattr(control, "controls", []) or []:
        yield from descendants(child)


class AdminPanelTests(unittest.TestCase):
    def test_login_shell_renders_without_network_or_service_role(self):
        page = FakePage()
        with patch("admin.achados_admin.create_client", return_value=object()):
            asyncio.run(main(page))
        controls = [item for root in page.controls for item in descendants(root)]
        fields = [item for item in controls if isinstance(item, ft.TextField)]
        buttons = [item for item in controls if isinstance(item, ft.Button)]
        self.assertEqual([field.label for field in fields], ["E-mail administrativo", "Senha"])
        labels = [button.content if isinstance(button.content, str) else button.content.value for button in buttons]
        self.assertIn("Entrar no painel", labels)

    def test_field_values_only_reads_declared_controls(self):
        controls = {"title": ft.TextField(value="Produto"), "enabled": ft.Switch(value=True)}
        self.assertEqual(field_values(controls), {"title": "Produto", "enabled": True})


if __name__ == "__main__":
    unittest.main()
