from __future__ import annotations

from nltk.stem.snowball import SnowballStemmer

_STEMMER = SnowballStemmer("russian")

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
    "двести": 200,
    "триста": 300,
    "четыреста": 400,
    "пятьсот": 500,
}


def stem_russian_word(word: str) -> str:
    """Выполняет стемминг русского слова с использованием официального NLTK SnowballStemmer."""
    clean = word.strip(".,!?:;-–—\"'«»").casefold()
    if not clean:
        return word
    return _STEMMER.stem(clean)


def stem_text(text: str) -> str:
    """Возвращает нормализованную стеммированную строку через NLTK Snowball."""
    tokens = text.lower().split()
    return " ".join(stem_russian_word(tok) for tok in tokens)


def normalize_spoken_numbers(text: str) -> str:
    """Заменяет слова-числительные ('пятьдесят', 'плюс десять') на числовые эквиваленты ('50', '+10')."""
    tokens = text.lower().split()
    res: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i].strip(".,!?«»\"'")
        sign = ""
        if tok in ("плюс", "+"):
            sign = "+"
            i += 1
            tok = tokens[i].strip(".,!?«»\"'") if i < len(tokens) else ""
        elif tok in ("минус", "-"):
            sign = "-"
            i += 1
            tok = tokens[i].strip(".,!?«»\"'") if i < len(tokens) else ""

        if tok in NUM_WORDS:
            val = NUM_WORDS[tok]
            if i + 1 < len(tokens):
                next_tok = tokens[i + 1].strip(".,!?«»\"'")
                if next_tok in NUM_WORDS:
                    next_val = NUM_WORDS[next_tok]
                    if val in (20, 30, 40, 50, 60, 70, 80, 90, 100, 200) and next_val < 10:
                        val += next_val
                        i += 1
            res.append(f"{sign}{val}")
        else:
            if sign:
                res.append(sign)
            if tok:
                res.append(tok)
        i += 1
    return " ".join(res)
