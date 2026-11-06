from __future__ import annotations

import importlib
import pkgutil
import unittest

import capri


class TestImports(unittest.TestCase):
    def test_import_all_submodules(self) -> None:
        failed: list[tuple[str, str]] = []
        for module_info in pkgutil.walk_packages(capri.__path__, prefix="capri."):
            try:
                importlib.import_module(module_info.name)
            except Exception as exc:
                failed.append((module_info.name, str(exc)))
        self.assertEqual(failed, [])

    def test_import_top_level_modules(self) -> None:
        top_level = [
            "capri.core",
            "capri.commands",
            "capri.controllers",
            "capri.effects",
            "capri.integrations",
            "capri.ui",
        ]
        for name in top_level:
            mod = importlib.import_module(name)
            self.assertIsNotNone(mod)
