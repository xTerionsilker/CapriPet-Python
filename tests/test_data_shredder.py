"""Unit tests for DataShredder module."""

import os
import stat
import tempfile
from pathlib import Path
import unittest

from capri.integrations.data_shredder import (
    _is_critical_path,
    analyze_paths,
    shred_paths,
    generate_shred_dialogue,
)


class TestDataShredder(unittest.TestCase):
    def test_critical_path_detection(self):
        # Windows directory
        self.assertTrue(_is_critical_path(Path(r"C:\Windows")))
        self.assertTrue(_is_critical_path(Path(r"C:\Windows\System32")))
        self.assertTrue(_is_critical_path(Path(r"C:\Program Files")))
        self.assertTrue(_is_critical_path(Path("C:\\")))
        self.assertTrue(_is_critical_path(Path.home()))

        # Non-critical paths
        temp_dir = Path(tempfile.gettempdir())
        self.assertFalse(_is_critical_path(temp_dir / "my_random_file.tmp"))

    def test_shred_files_and_directories(self):
        with tempfile.TemporaryDirectory() as base_tmp:
            base_path = Path(base_tmp)
            # Create subfolder with files, including readonly file
            sub_dir = base_path / "victim_folder"
            sub_dir.mkdir()
            normal_file = sub_dir / "normal.txt"
            normal_file.write_text("hello world")

            ro_file = sub_dir / "readonly.log"
            ro_file.write_text("log content " * 100)
            os.chmod(ro_file, stat.S_IREAD)

            single_file = base_path / "standalone.py"
            single_file.write_text("print('test')")

            # Analyze before shredding
            safe_paths, metrics = analyze_paths([sub_dir, single_file])
            self.assertEqual(len(safe_paths), 2)
            self.assertEqual(metrics.total_files, 3)
            self.assertEqual(metrics.total_dirs, 1)

            # Shred
            final_metrics = shred_paths([sub_dir, single_file])
            self.assertFalse(sub_dir.exists())
            self.assertFalse(single_file.exists())
            self.assertFalse(final_metrics.had_errors)

            # Check dialogue generation
            dialogue = generate_shred_dialogue(final_metrics)
            self.assertIn("[SHREDDER]", dialogue)


if __name__ == "__main__":
    unittest.main()
