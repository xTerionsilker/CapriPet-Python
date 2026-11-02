from __future__ import annotations

import re

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

_PERFECTIVE_GERUND = re.compile(
    r"(?:[ая](?:в|вши|вшись))$|(?:ив|ивши|ившись|ыв|ывши|ывшись)$"
)
_ADJECTIVE = re.compile(
    r"(?:ее|ие|ые|ое|ими|ыми|ей|ий|ый|ой|ем|им|ым|ом|его|ого|ему|ому|их|ых|ую|юю|ая|яя|ою|ею)$"
)
_PARTICIPLE = re.compile(r"(?:[ая](?:ем|нн|вш|ющ|щ))$|(?:ивш|ывш|ующ)$")
_REFLEXIVE = re.compile(r"(?:ся|сь)$")
_VERB = re.compile(
    r"(?:[ая](?:ла|на|ете|йте|ли|й|л|ем|н|ло|но|ет|ют|ны|ть|ешь|нно))$|(?:ила|ыла|ена|ейте|уйте|ите|или|ыли|ей|уй|ил|ыл|им|ым|ен|ило|ыло|ено|ят|ует|уют|ит|ыт|ены|ить|ыть|ишь|ую|ю)$"
)
_NOUN = re.compile(
    r"(?:а|ев|ов|ие|ье|е|иями|ями|ами|еи|ии|и|ией|ей|ой|ий|й|иям|ям|ием|ем|ам|ом|о|у|ах|иях|ях|ы|ь|ию|ью|ю|ия|ья|я)$"
)
_SUPERLATIVE = re.compile(r"(?:ейш|ейше)$")
_DERIVATIONAL = re.compile(r"(?:ост|ость)$")


def stem_russian_word(word: str) -> str:
    """Выполняет стемминг русского слова по алгоритму Snowball."""
    word = word.lower().replace("ё", "е")
    m = re.search(r"[аеиоуыэюя]", word)
    if not m:
        return word
    rv_pos = m.start() + 1
    rv = word[rv_pos:]
    head = word[:rv_pos]

    # Шаг 1: Гернундий / Возвратный / Прилагательное / Глагол / Существительное
    m_pg = _PERFECTIVE_GERUND.search(rv)
    if m_pg:
        rv = rv[: m_pg.start()]
    else:
        m_ref = _REFLEXIVE.search(rv)
        if m_ref:
            rv = rv[: m_ref.start()]
        m_adj = _ADJECTIVE.search(rv)
        if m_adj:
            rv = rv[: m_adj.start()]
            m_part = _PARTICIPLE.search(rv)
            if m_part:
                rv = rv[: m_part.start()]
        else:
            m_verb = _VERB.search(rv)
            if m_verb:
                rv = rv[: m_verb.start()]
            else:
                m_noun = _NOUN.search(rv)
                if m_noun:
                    rv = rv[: m_noun.start()]

    # Шаг 2: Удаление 'и'
    if rv.endswith("и"):
        rv = rv[:-1]

    # Шаг 3: Производные суффиксы
    m_der = _DERIVATIONAL.search(rv)
    if m_der:
        rv = rv[: m_der.start()]

    # Шаг 4: Суперлатив, 'нн', 'ь'
    m_sup = _SUPERLATIVE.search(rv)
    if m_sup:
        rv = rv[: m_sup.start()]
    if rv.endswith("нн"):
        rv = rv[:-1]
    if rv.endswith("ь"):
        rv = rv[:-1]

    return head + rv


def stem_text(text: str) -> str:
    """Возвращает нормализованную стеммированную строку."""
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
