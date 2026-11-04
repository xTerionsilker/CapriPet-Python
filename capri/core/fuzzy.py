from __future__ import annotations

import re
from rapidfuzz import fuzz
from rapidfuzz.distance import DamerauLevenshtein

MAX_TYPO_DISTANCE = 3


def similarity(text: str, key: str) -> float:
    if text == key:
        return 1.0

    whole = fuzz.ratio(text, key) / 100.0
    tokens = fuzz.token_set_ratio(text, key) / 100.0
    return max(whole, tokens * 0.95)


def keyword_score(text: str, keywords: tuple[str, ...]) -> float:
    if not keywords:
        return 0.0
    for keyword in keywords:
        for word in re.findall(r"[\w-]+", text):
            if word.startswith(keyword) or keyword in word:
                return 0.95
    return 0.0


def edit_distance(left: str, right: str) -> int:
    return int(DamerauLevenshtein.distance(left, right))
