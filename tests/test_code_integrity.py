from __future__ import annotations

import os
import unittest


class TestCodeIntegrity(unittest.TestCase):
    def test_all_python_files_compile(self) -> None:
        root_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        failed_files: list[tuple[str, str]] = []
        for root, _, files in os.walk(root_dir):
            if ".venv" in root or ".git" in root or "__pycache__" in root:
                continue
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, "rb") as f:
                            compile(f.read(), full_path, "exec")
                    except Exception as exc:
                        failed_files.append((full_path, str(exc)))
        self.assertEqual(failed_files, [])

