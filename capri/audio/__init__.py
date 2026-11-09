"""Audio capture, voice activity detection, and speech recognition subsystem."""

from __future__ import annotations

from .recognizer import (
    ModelStatus,
    RecognitionError,
    VoskSpeechService,
    check_available,
    create_recognizer,
    get_model_info,
    get_vosk_model,
    is_model_loading,
    is_model_ready,
    model_load_failed,
    preload_model_async,
    recognize,
    to_mono,
)
from .voice import SileroVAD, VoiceInput

__all__ = [
    "VoiceInput",
    "SileroVAD",
    "ModelStatus",
    "RecognitionError",
    "VoskSpeechService",
    "check_available",
    "create_recognizer",
    "get_model_info",
    "get_vosk_model",
    "is_model_loading",
    "is_model_ready",
    "model_load_failed",
    "preload_model_async",
    "recognize",
    "to_mono",
]
