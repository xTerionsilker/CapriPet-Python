from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .recognizer import (
    FasterWhisperBackend,
    ModelStatus,
    RecognitionError,
    SpeechRecognitionBackend,
    VoskSpeechService,
    check_available,
    create_recognizer,
    get_backend,
    get_model_info,
    get_vosk_model,
    is_model_loading,
    is_model_ready,
    model_load_failed,
    preload_model_async,
    recognize,
    set_backend,
    to_mono,
)
from .voice import SileroVAD, VoiceInput

__all__ = [
    "VoiceInput",
    "SileroVAD",
    "ModelStatus",
    "RecognitionError",
    "SpeechRecognitionBackend",
    "FasterWhisperBackend",
    "VoskSpeechService",
    "check_available",
    "create_recognizer",
    "get_backend",
    "get_model_info",
    "get_vosk_model",
    "is_model_loading",
    "is_model_ready",
    "model_load_failed",
    "preload_model_async",
    "recognize",
    "set_backend",
    "to_mono",
]
