from __future__ import annotations

import unittest

from capri.core.input_flow import (
    AFFIRMATIVE_WORDS,
    NEGATIVE_WORDS,
    NUMBER_WORDS_MAP,
    _answer_words,
    _parse_selected_number,
)


class TestInputFlow(unittest.TestCase):
    def test_number_words_map(self) -> None:
        self.assertEqual(NUMBER_WORDS_MAP["1"], 1)
        self.assertEqual(NUMBER_WORDS_MAP["один"], 1)
        self.assertEqual(NUMBER_WORDS_MAP["два"], 2)
        self.assertEqual(NUMBER_WORDS_MAP["три"], 3)
        self.assertEqual(NUMBER_WORDS_MAP["четыре"], 4)
        self.assertEqual(NUMBER_WORDS_MAP["пять"], 5)

    def test_parse_selected_number(self) -> None:
        self.assertEqual(_parse_selected_number("первый"), 1)
        self.assertEqual(_parse_selected_number("три"), 3)
        self.assertEqual(_parse_selected_number("5"), 5)
        self.assertIsNone(_parse_selected_number("десять", max_number=5))
        self.assertIsNone(_parse_selected_number("какой-то текст"))

    def test_affirmative_and_negative_words(self) -> None:
        self.assertIn("да", AFFIRMATIVE_WORDS)
        self.assertIn("yes", AFFIRMATIVE_WORDS)
        self.assertIn("нет", NEGATIVE_WORDS)
        self.assertIn("отмена", NEGATIVE_WORDS)

    def test_answer_words_layout_switch(self) -> None:
        words = _answer_words("lf")
        self.assertIn("lf", words)
        self.assertIn("да", words)
