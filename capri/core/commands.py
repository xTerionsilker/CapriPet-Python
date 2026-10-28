from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..commands.registry import (
    ARGUMENT_PUNCTUATION,
    CommandRegistry as NewCommandRegistry,
    switch_layout,
)
from .fuzzy import MAX_TYPO_DISTANCE, edit_distance, keyword_score, similarity

Handler = Callable[..., str]


@dataclass(frozen=True)
class Command:
    name: str
    description: str
    handler: Handler
    aliases: tuple[str, ...] = ()
    takes_argument: bool = False
    keywords: tuple[str, ...] = ()
    requires_confirmation: bool = False


class CommandRegistry(NewCommandRegistry):
    """Реестр команд, совместимый как с новыми BaseCommand, так и с dataclass Command."""
    pass


__all__ = [
    "Handler",
    "ARGUMENT_PUNCTUATION",
    "switch_layout",
    "Command",
    "CommandRegistry",
    "MAX_TYPO_DISTANCE",
    "edit_distance",
    "keyword_score",
    "similarity",
]
