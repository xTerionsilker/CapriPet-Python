from __future__ import annotations

import os
import py_compile
import subprocess
import sys
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
                        py_compile.compile(full_path, doraise=True)
                    except py_compile.PyCompileError as exc:
                        failed_files.append((full_path, str(exc)))
        self.assertEqual(failed_files, [])

    def test_pylint_checks(self) -> None:
        root_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        venv_python = sys.executable
        res = subprocess.run(
            [
                venv_python,
                "-m",
                "pylint",
                "capri",
                "main.py",
            ],
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            res.returncode,
            0,
            f"Pylint detected issues:\n{res.stdout}\n{res.stderr}",
        )
