from __future__ import annotations

import re
from rapidfuzz import fuzz
from rapidfuzz.distance import DamerauLevenshtein

MAX_TYPO_DISTANCE = 3


def similarity(text: str, key: str) -> float:
    if text == key:
        return 1.0

    whole = fuzz.ratio(text, key) / 100.0
    text_tokens = text.split()
    key_tokens = key.split()
    if not text_tokens or not key_tokens:
        return whole

    token_score = sum(
        max(
            fuzz.ratio(token, key_token) / 100.0
            for key_token in key_tokens
        )
        for token in text_tokens
    ) / len(text_tokens)
    return max(whole, token_score * 0.9)


def keyword_score(text: str, keywords: tuple[str, ...]) -> float:
    if not keywords:
        return 0.0
    words = re.findall(r"[\w-]+", text)
    for keyword in keywords:
        for word in words:
            if word.startswith(keyword) or keyword in word:
                return 0.95
    return 0.0


def edit_distance(left: str, right: str) -> int:
    return int(DamerauLevenshtein.distance(left, right))
