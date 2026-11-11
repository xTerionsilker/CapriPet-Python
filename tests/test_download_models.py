"""Unit tests for the Python-native model provisioning script."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root and scripts dir to path for testing
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "scripts"))

import download_models  # type: ignore[import-not-found]


class TestDownloadModels(unittest.TestCase):
    """Test model detection, CLI options, and download orchestration."""

    def test_check_silero_vad_presence(self) -> None:
        """Check detection of silero_vad.onnx presence."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            models_dir = Path(tmp_dir)
            self.assertFalse(download_models.check_silero_vad(models_dir))

            vad_file = models_dir / "silero_vad.onnx"
            vad_file.write_bytes(b"dummy_vad_bytes")
            self.assertTrue(download_models.check_silero_vad(models_dir))

    def test_check_vosk_model_presence(self) -> None:
        """Check detection of vosk model folder presence."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            models_dir = Path(tmp_dir)
            self.assertFalse(download_models.check_vosk_model(models_dir))

            vosk_dir = models_dir / "vosk-model-small-ru-0.22"
            vosk_dir.mkdir(parents=True)
            self.assertTrue(download_models.check_vosk_model(models_dir))

    def test_cli_check_only_missing(self) -> None:
        """CLI with --check-only exits 1 when models are missing."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            ret = download_models.main(["--models-dir", tmp_dir, "--check-only"])
            self.assertEqual(ret, 1)

    def test_cli_check_only_present(self) -> None:
        """CLI with --check-only exits 0 when required models are present."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            models_dir = Path(tmp_dir)
            (models_dir / "silero_vad.onnx").write_bytes(b"vad")
            (models_dir / "vosk-model-small-ru-0.22").mkdir(parents=True)

            ret = download_models.main(["--models-dir", tmp_dir, "--check-only"])
            self.assertEqual(ret, 0)

    @patch("urllib.request.urlretrieve")
    def test_download_silero_vad_success(self, mock_retrieve: MagicMock) -> None:
        """Test download_silero_vad writes file and returns True."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            models_dir = Path(tmp_dir)
            target = models_dir / "silero_vad.onnx"

            def fake_retrieve(url: str, filename: str, reporthook: object = None) -> None:
                Path(filename).write_bytes(b"downloaded_vad")

            mock_retrieve.side_effect = fake_retrieve

            result = download_models.download_silero_vad(models_dir)
            self.assertTrue(result)
            self.assertTrue(target.exists())
            self.assertEqual(target.read_bytes(), b"downloaded_vad")


if __name__ == "__main__":
    unittest.main()
