"""Capri — маленький видео-питомец с ответами печатной машинкой."""

from .pet_window import CapriWindow
from .speech import SpeechWindow, show_text
from .voice import VoiceInput

__all__ = ["CapriWindow", "SpeechWindow", "VoiceInput", "show_text"]
