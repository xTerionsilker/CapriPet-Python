"""Нечёткое сопоставление строк: опечатки и смысловые подсказки.

Чистые функции без состояния, отделяющие «математику» распознавания
команд от самого реестра в ``capri.commands``. Пунктуация, регистр и
лишние пробелы сюда не входят — их снимает ``CommandRegistry._normalize``.

Три оценки работают вместе:

- :func:`edit_distance` решает, можно ли считать ввод опечаткой;
- :func:`similarity` измеряет похожесть фразы на имя или псевдоним;
- :func:`keyword_score` ловит смысловые основы («цвет» → «глитч»).
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# Длинный ввод может содержать больше опечаток: одна правка до 5 символов,
# затем ещё одна на каждые 5 символов, с ограничением, чтобы посторонние
# фразы никогда не совпадали с командой.
MAX_TYPO_DISTANCE = 3


def similarity(text: str, key: str) -> float:
    """Насколько фраза похожа на команду или её псевдоним."""
    if text == key:
        return 1.0

    whole = SequenceMatcher(None, text, key).ratio()
    text_tokens = text.split()
    key_tokens = key.split()
    if not text_tokens or not key_tokens:
        return whole

    # Средняя похожесть каждого слова фразы на ближайшее слово команды:
    # так «выруби глюки» уверенно тянется к «выключить глюки».
    token_score = sum(
        max(
            SequenceMatcher(None, token, key_token).ratio()
            for key_token in key_tokens
        )
        for token in text_tokens
    ) / len(text_tokens)
    return max(whole, token_score * 0.9)


def keyword_score(text: str, keywords: tuple[str, ...]) -> float:
    """Оценка по смысловым основам слов (``цвет`` → глитч и т. п.)."""
    if not keywords:
        return 0.0
    words = re.findall(r"[\w-]+", text)
    for keyword in keywords:
        for word in words:
            if word.startswith(keyword) or keyword in word:
                return 0.95
    return 0.0


def edit_distance(left: str, right: str) -> int:
    """Расстояние оптимального выравнивания (Левенштейн + перестановки)."""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    # Три скользящих ряда: [i-2], [i-1], [i].
    prev_prev = [0] * (len(right) + 1)
    prev = list(range(len(right) + 1))

    for i, left_char in enumerate(left, start=1):
        current = [i] + [0] * len(right)
        for j, right_char in enumerate(right, start=1):
            cost = 0 if left_char == right_char else 1
            current[j] = min(
                prev[j] + 1,          # удаление
                current[j - 1] + 1,   # вставка
                prev[j - 1] + cost,   # замена
            )
            if (
                i > 1
                and j > 1
                and left_char == right[j - 2]
                and left[i - 2] == right_char
            ):
                current[j] = min(current[j], prev_prev[j - 2] + 1)
        prev_prev, prev = prev, current

    return prev[-1]
