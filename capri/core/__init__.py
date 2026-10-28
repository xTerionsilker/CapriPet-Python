from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .command_catalog import Handlers, register_commands
    from .commands import Command, CommandRegistry
    from .input_flow import InputFlow


def __getattr__(name: str):
    if name in ("Command", "CommandRegistry"):
        from . import commands
        return getattr(commands, name)
    if name in ("Handlers", "register_commands"):
        from . import command_catalog
        return getattr(command_catalog, name)
    if name == "InputFlow":
        from . import input_flow
        return getattr(input_flow, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["Command", "CommandRegistry", "Handlers", "register_commands", "InputFlow"]
