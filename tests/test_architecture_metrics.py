import os
import unittest


class TestArchitectureMetrics(unittest.TestCase):
    def test_canonical_docs_exist(self) -> None:
        canonical_docs = [
            "docs/architecture.md",
            "docs/character_design.md",
            "docs/config_spec.md",
            "docs/project_structure.md",
        ]
        for doc in canonical_docs:
            with self.subTest(doc=doc):
                self.assertTrue(os.path.isfile(doc), f"Missing canonical doc: {doc}")
