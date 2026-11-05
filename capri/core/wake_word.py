from __future__ import annotations

import re
from rapidfuzz.distance import DamerauLevenshtein

VOICE_TRIGGER_RE = re.compile(
    r"(?<!\w)(?:"
    r"капри[зс]?(?:\s*[-–—]?\s*(?:корд|корт|кард|корн|кор))?"
    r"|capri(?:[sz]|corn|cord)?"
    r"|к[эео]при[зс]?"
    r"|ка[кп]\s+при"
    r")(?!\w)",
    re.IGNORECASE,
)

VOICE_COMMAND_WINDOW_MS = 5_000
VOICE_FOLLOWUP_WINDOW_MS = 4_500
VOICE_LISTENING_STATUS = "СЛУШАЮ «КАПРИ»…"
VOICE_WAITING_STATUS = "ЖДУ КОМАНДУ…"

_WAKE_TARGETS = (
    "капри",
    "каприз",
    "кэпри",
    "каприс",
    "каприк",
    "каприкорд",
    "каприкорн",
    "capri",
    "capris",
    "capriz",
    "capricorn",
    "capricord",
)


def voice_normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def _is_fuzzy_wake_word(word: str) -> bool:
    cleaned = word.strip(".,!?:;-–—\"'«»").casefold()
    if not cleaned or len(cleaned) < 4:
        return False

    for target in _WAKE_TARGETS:
        dist = DamerauLevenshtein.distance(cleaned, target)
        if len(target) <= 6:
            if dist <= 1:
                return True
        else:
            if dist <= 2:
                return True
    return False


def command_after_trigger(text: str) -> str | None:
\
\
\
\

    normalized = voice_normalized(text)
    if not normalized:
        return None


    match = VOICE_TRIGGER_RE.search(normalized)
    if match is not None:
        tokens = text.split()
        consumed = max(1, len(match.group(0).split()))
        before = len(normalized[: match.start()].split())
        return " ".join(tokens[before + consumed:]).strip()


    tokens = text.split()
    if not tokens:
        return None

    first = tokens[0]
    if _is_fuzzy_wake_word(first):
        return " ".join(tokens[1:]).strip()


    if len(tokens) >= 2:
        combined = (tokens[0] + tokens[1]).casefold()
        if _is_fuzzy_wake_word(combined):
            return " ".join(tokens[2:]).strip()

    return None
