"""CapriPet package initialization and core interface exports."""

from .audio.voice import VoiceInput
from .ui.pet_window import CapriWindow
from .ui.speech import SpeechWindow, show_text

__all__ = ["CapriWindow", "SpeechWindow", "VoiceInput", "show_text"]
