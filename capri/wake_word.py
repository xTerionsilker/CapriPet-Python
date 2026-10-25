"""Ключевое слово «Капри» и окно ожидания голосовой команды.

Capri выполняет услышанное только после ключевого слова. Распознавание
иногда выдаёт его с ошибкой: «капри корд», «капри-корд», «Capricorn» и
т. п. — все допустимые варианты перечислены в ``VOICE_TRIGGER_RE``.

Команда может идти сразу за ключевым словом («капри открой гугл») или
звучать отдельной фразой в течение ``VOICE_COMMAND_WINDOW_MS`` после
него. Модуль не зависит от Qt и не хранит состояние: он только разбирает
распознанный текст, а таймер окна ожидания живёт в ``capri.pet_window``.
"""

from __future__ import annotations

import re

VOICE_TRIGGER_RE = re.compile(
    r"(?<!\w)(?:"
    r"капри(?:\s*[-–—]?\s*(?:корд|корт|кард|корн|кор))?"
    r"|кэпри"
    r"|capri(?:\s*[-–—]?\s*(?:corn|kord|cord|card|kor))?"
    r")(?!\w)"
)
# Сколько ждать команду после отдельно произнесённого ключевого слова.
VOICE_COMMAND_WINDOW_MS = 3_000
VOICE_LISTENING_STATUS = "СЛУШАЮ «КАПРИ»…"
VOICE_WAITING_STATUS = "ЖДУ КОМАНДУ…"


def voice_normalized(text: str) -> str:
    """Нормализовать распознанный текст: регистр и лишние пробелы."""
    return " ".join(text.casefold().split())


def command_after_trigger(text: str) -> str | None:
    """Вернуть команду после ключевого слова, либо ``None`` без него.

    Пустая строка означает, что прозвучало только ключевое слово и команду
    нужно ждать отдельной фразой в течение ``VOICE_COMMAND_WINDOW_MS``.
    """
    normalized = voice_normalized(text)
    match = VOICE_TRIGGER_RE.search(normalized)
    if match is None:
        return None
    tokens = text.split()
    consumed = max(1, len(match.group(0).split()))
    before = len(normalized[: match.start()].split())
    # «Дальше уже команда»: всё после ключевого слова.
    return " ".join(tokens[before + consumed:]).strip()
