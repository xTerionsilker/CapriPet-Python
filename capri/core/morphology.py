"""Морфологический анализ русской речи и нормализация числительных."""

from __future__ import annotations

from pymorphy3 import MorphAnalyzer

_MORPH = MorphAnalyzer()
_PUNCTUATION = ".,!?:;-–—\"'«»"

NUM_WORDS: dict[str, int] = {
    "ноль": 0,
    "нуль": 0,
    "один": 1,
    "одна": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "одиннадцать": 11,
    "двенадцать": 12,
    "тринадцать": 13,
    "четырнадцать": 14,
    "пятнадцать": 15,
    "шестнадцать": 16,
    "семнадцать": 17,
    "восемнадцать": 18,
    "девятнадцать": 19,
    "двадцать": 20,
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50,
    "шестьдесят": 60,
    "семьдесят": 70,
    "восемьдесят": 80,
    "девяносто": 90,
    "сто": 100,
    "сотка": 100,
    "двести": 200,
    "триста": 300,
    "четыреста": 400,
    "пятьсот": 500,
}

_TENS = frozenset((20, 30, 40, 50, 60, 70, 80, 90, 100, 200))


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
    tokens = text.lower().split()
    result: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index].strip(_PUNCTUATION)
        sign = ""
        if token in ("плюс", "+"):
            sign = "+"
            index += 1
            token = (
                tokens[index].strip(_PUNCTUATION)
                if index < len(tokens)
                else ""
            )
        elif token in ("минус", "-"):
            sign = "-"
            index += 1
            token = (
                tokens[index].strip(_PUNCTUATION)
                if index < len(tokens)
                else ""
            )

        if token in NUM_WORDS:
            value = NUM_WORDS[token]
            if index + 1 < len(tokens):
                following = tokens[index + 1].strip(_PUNCTUATION)
                if following in NUM_WORDS:
                    following_value = NUM_WORDS[following]
                    if value in _TENS and following_value < 10:
                        value += following_value
                        index += 1
            result.append(f"{sign}{value}")
        else:
            if sign:
                result.append(sign)
            if token:
                result.append(token)
        index += 1
    return " ".join(result)
