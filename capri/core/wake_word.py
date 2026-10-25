from __future__ import annotations

import re

VOICE_TRIGGER_RE = re.compile(
    r"(?<!\w)(?:"
    r"капри(?:\s*[-–—]?\s*(?:корд|корт|кард|корн|кор))?"
    r"|кэпри"
    r"|capri(?:\s*[-–—]?\s*(?:corn|kord|cord|card|kor))?"
    r")(?!\w)"
)
VOICE_COMMAND_WINDOW_MS = 3_000
VOICE_LISTENING_STATUS = "СЛУШАЮ «КАПРИ»…"
VOICE_WAITING_STATUS = "ЖДУ КОМАНДУ…"


def voice_normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def command_after_trigger(text: str) -> str | None:
    normalized = voice_normalized(text)
    match = VOICE_TRIGGER_RE.search(normalized)
    if match is None:
        return None
    tokens = text.split()
    consumed = max(1, len(match.group(0).split()))
    before = len(normalized[: match.start()].split())
    return " ".join(tokens[before + consumed:]).strip()
