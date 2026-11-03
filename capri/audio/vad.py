from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SileroVAD:
\
\
\
\


    def __init__(self, sample_rate: int = 16_000, threshold: float = 0.5) -> None:
        self.sample_rate = sample_rate
        self.threshold = threshold
        self._session: Any = None
        self._state: Any = None
        self._available: bool | None = None
        self._init_session()

    def _find_model_path(self) -> Path | None:
        project_root = Path(__file__).resolve().parents[2]
        candidate = project_root / "models" / "silero_vad.onnx"
        if candidate.exists():
            return candidate
        return None

    def _init_session(self) -> None:
        model_path = self._find_model_path()
        if not model_path:
            self._available = False
            return

        try:
            import onnxruntime as ort
            import numpy as np

            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = ort.InferenceSession(str(model_path), sess_options=opts)
            self._state = np.zeros((2, 1, 128), dtype=np.float32)
            self._available = True
        except Exception as error:
            logger.warning("Не удалось загрузить Silero VAD ONNX: %s", error)
            self._available = False

    @property
    def is_available(self) -> bool:
        return bool(self._available and self._session is not None)

    def reset(self) -> None:
        if self.is_available:
            import numpy as np

            self._state = np.zeros((2, 1, 128), dtype=np.float32)

    def is_speech(self, chunk: bytes) -> tuple[bool, float]:
        """Возвращает (is_speech, probability)."""
        if not self.is_available:
            return False, 0.0

        try:
            import numpy as np


            audio_data = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            if len(audio_data) == 0:
                return False, 0.0


            chunk_size = 512
            total_samples = len(audio_data)
            max_prob = 0.0

            sr_tensor = np.array(self.sample_rate, dtype=np.int64)

            for i in range(0, total_samples, chunk_size):
                sub_chunk = audio_data[i : i + chunk_size]
                if len(sub_chunk) < chunk_size:

                    padded = np.zeros(chunk_size, dtype=np.float32)
                    padded[: len(sub_chunk)] = sub_chunk
                    sub_chunk = padded

                input_tensor = np.expand_dims(sub_chunk, axis=0)
                out, self._state = self._session.run(
                    None,
                    {"input": input_tensor, "state": self._state, "sr": sr_tensor},
                )
                prob = float(out[0][0])
                if prob > max_prob:
                    max_prob = prob

            return max_prob >= self.threshold, max_prob
        except Exception as error:
            logger.debug("Ошибка инференса Silero VAD: %s", error)
            return False, 0.0
