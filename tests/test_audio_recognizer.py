from __future__ import annotations

import unittest
from unittest.mock import patch

from capri.audio.recognizer import (
    FasterWhisperBackend,
    ModelStatus,
    SpeechRecognitionBackend,
    VoskSpeechService,
)


class TestAudioRecognizer(unittest.TestCase):
    def test_model_status_enum_values(self) -> None:
        self.assertEqual(ModelStatus.UNLOADED.value, "unloaded")
        self.assertEqual(ModelStatus.LOADING.value, "loading")
        self.assertEqual(ModelStatus.READY.value, "ready")
        self.assertEqual(ModelStatus.FAILED.value, "failed")

    def test_abstract_backend_not_implemented(self) -> None:
        backend = SpeechRecognitionBackend()
        with self.assertRaises(NotImplementedError):
            backend.is_available()
        with self.assertRaises(NotImplementedError):
            backend.recognize(b"", channels=1, sample_rate=16000)

    def test_faster_whisper_backend_import_error_handling(self) -> None:
        backend = FasterWhisperBackend()
        with patch.dict("sys.modules", {"faster_whisper": None}):
            backend._available = None
            self.assertFalse(backend.is_available())

    def test_vosk_speech_service_status_initialization(self) -> None:
        service = VoskSpeechService()
        self.assertEqual(service.status, ModelStatus.UNLOADED)
        self.assertFalse(service.is_ready)
