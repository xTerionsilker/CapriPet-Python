import os
import unittest


class TestArchitectureMetrics(unittest.TestCase):
    def test_audit_report_exists(self) -> None:
        self.assertTrue(os.path.isfile("docs/audit_god_files_report.md"))
