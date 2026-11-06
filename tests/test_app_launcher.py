from __future__ import annotations

import unittest

from capri.integrations.app_launcher import (
    phonetic_normalize,
    translit_ru_to_en,
)


class TestAppLauncher(unittest.TestCase):
    def test_translit_ru_to_en(self) -> None:
        self.assertEqual(translit_ru_to_en("дискорд"), "diskord")
        self.assertEqual(translit_ru_to_en("хром"), "hrom")

    def test_phonetic_normalize(self) -> None:
        self.assertEqual(phonetic_normalize("cinema"), "sinema")
        self.assertEqual(phonetic_normalize("cat"), "kat")
        self.assertEqual(phonetic_normalize("web"), "veb")
        self.assertEqual(phonetic_normalize("apple"), "aple")
