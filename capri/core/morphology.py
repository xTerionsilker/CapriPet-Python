"""Морфологический анализ русской речи и нормализация числительных."""

from __future__ import annotations

import re

from pymorphy3 import MorphAnalyzer
from words2numsrus import NumberExtractor

_MORPH = MorphAnalyzer()
_EXTRACTOR = NumberExtractor()
_PUNCTUATION = ".,!?:;-–—\"'«»"
MAX_INPUT_LENGTH = 500


def stem_russian_word(word: str) -> str:
    clean = word.strip(_PUNCTUATION).casefold()
    if not clean:
        return word
    return _MORPH.parse(clean)[0].normal_form


def stem_text(text: str) -> str:
    return " ".join(
        stem_russian_word(token) for token in text.lower().split()
    )


def normalize_spoken_numbers(text: str) -> str:
    """Нормализует русские числительные в цифры с защитой от DoS/ReDoS."""
    if not text:
        return ""
    trimmed = text[:MAX_INPUT_LENGTH] if len(text) > MAX_INPUT_LENGTH else text
    try:
        replaced = _EXTRACTOR.replace_groups(trimmed.lower())
        replaced = re.sub(r"\bплюс\s+(\d+)\b", r"+\1", replaced)
        replaced = re.sub(r"\bминус\s+(\d+)\b", r"-\1", replaced)
        return replaced
    except Exception:
        return text
