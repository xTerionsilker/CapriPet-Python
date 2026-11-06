from __future__ import annotations

import unittest

from capri.integrations.system_cleaner import CleanResult, format_bytes
from capri.integrations.web_search import search_google


class TestSystemCleanerAndWeb(unittest.TestCase):
    def test_format_bytes(self) -> None:
        self.assertEqual(format_bytes(0), "0 Б")
        self.assertEqual(format_bytes(512), "512 Б")
        self.assertEqual(format_bytes(1024), "1.0 КБ")
        self.assertEqual(format_bytes(1024 * 1024), "1.0 МБ")
        self.assertEqual(format_bytes(1024 * 1024 * 1024), "1.0 ГБ")

    def test_clean_result_namedtuple(self) -> None:
        res = CleanResult(
            files_deleted=10,
            bytes_freed=2048,
            errors=0,
            recycle_bin_cleared=True,
        )
        self.assertEqual(res.files_deleted, 10)
        self.assertEqual(res.bytes_freed, 2048)
        self.assertEqual(res.errors, 0)
        self.assertTrue(res.recycle_bin_cleared)

    def test_search_google_empty_query(self) -> None:
        msg = search_google("   ")
        self.assertIn("Что искать в Google?", msg)
