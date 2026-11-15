"""Утилиты нормализации текста, раскладки клавиатуры и нечёткого сопоставления."""

from __future__ import annotations

import re

import cyrtranslit
from rapidfuzz import fuzz
from rapidfuzz.distance import DamerauLevenshtein

MAX_TYPO_DISTANCE = 3

_EN_KEYS = "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
_RU_KEYS = "йцукенгшщзхъфывапролджэячсмитьбю.ё"
_LAYOUT_TRANSLATION = str.maketrans(_EN_KEYS + _RU_KEYS, _RU_KEYS + _EN_KEYS)


def switch_layout(text: str) -> str:
    """Переключает раскладку клавиатуры между RU и EN (QWERTY <-> ЙЦУКЕН)."""
    return text.translate(_LAYOUT_TRANSLATION)


def translit_ru_to_en(text: str) -> str:
    """Транслитерирует русский текст в латиницу с заменой 'кс' на 'x'."""
    t = text.lower().replace("кс", "x")
    return cyrtranslit.to_latin(t, "ru")


def phonetic_normalize(text: str) -> str:
    """Упрощённая фонетическая нормализация для нечёткого поиска процессов и ПО."""
    s = text.lower()
    res: list[str] = []
    for i, ch in enumerate(s):
        if ch == "c":
            if i + 1 < len(s) and s[i + 1] in ("e", "i", "y"):
                res.append("s")
            else:
                res.append("k")
        elif ch in ("q", "k"):
            res.append("k")
        elif ch == "x":
            res.extend(["k", "s"])
        elif ch == "w":
            res.append("v")
        else:
            res.append(ch)
    normalized = "".join(res)
    return re.sub(r"([a-z])\1+", r"\1", normalized)


def similarity(text: str, key: str) -> float:
    """Вычисляет коэффициент схожести строк (0.0 .. 1.0) на основе RapidFuzz."""
    if text == key:
        return 1.0
    whole = fuzz.ratio(text, key) / 100.0
    tokens = fuzz.token_set_ratio(text, key) / 100.0
    return max(whole, tokens * 0.95)


def keyword_score(text: str, keywords: tuple[str, ...]) -> float:
    """Оценивает совпадение по ключевым словам."""
    if not keywords:
        return 0.0
    for keyword in keywords:
        for word in re.findall(r"[\w-]+", text):
            if word.startswith(keyword) or keyword in word:
                return 0.95
    return 0.0


def edit_distance(left: str, right: str) -> int:
    """Расстояние Дамерау-Левенштейна между строками."""
    return int(DamerauLevenshtein.distance(left, right))
