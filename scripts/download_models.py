"""Model provisioning and integrity verification script for CapriPet.

Handles automated downloading, extraction, and validation of:
1. Silero VAD (ONNX model) for neural voice activity detection.
2. Vosk Speech Recognition model (offline Russian acoustic model).
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_SILERO_URL = (
    "https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx"
)
DEFAULT_VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"


def get_default_models_dir() -> Path:
    """Return default models directory relative to project root."""
    return Path(__file__).resolve().parent.parent / "models"


def check_silero_vad(models_dir: Path) -> bool:
    """Return True if silero_vad.onnx exists and has non-zero size."""
    target = models_dir / "silero_vad.onnx"
    return target.is_file() and target.stat().st_size > 0


def check_vosk_model(models_dir: Path) -> bool:
    """Return True if any vosk-model* folder exists in models_dir."""
    if not models_dir.is_dir():
        return False
    return any(p.is_dir() and p.name.startswith("vosk-model") for p in models_dir.iterdir())


def _download_progress(block_num: int, block_size: int, total_size: int) -> None:
    """Print download progress in percentage."""
    if total_size > 0:
        downloaded = block_num * block_size
        pct = min(100.0, downloaded * 100.0 / total_size)
        sys.stdout.write(f"\r  [PROG] {pct:.1f}% ({downloaded / (1024 * 1024):.1f} MB)")
        sys.stdout.flush()


def download_silero_vad(models_dir: Path, url: str = DEFAULT_SILERO_URL) -> bool:
    """Download Silero VAD ONNX model to models_dir."""
    models_dir.mkdir(parents=True, exist_ok=True)
    target = models_dir / "silero_vad.onnx"

    print(f"[INFO] Downloading Silero VAD from {url}...")
    try:
        urllib.request.urlretrieve(url, str(target), reporthook=_download_progress)
        print("\n[INFO] Silero VAD model successfully downloaded.")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"\n[WARNING] Failed to download Silero VAD: {exc}")
        if target.exists():
            target.unlink(missing_ok=True)
        return False


def download_vosk_model(models_dir: Path, url: str = DEFAULT_VOSK_URL) -> bool:
    """Download and extract Vosk speech model zip to models_dir."""
    models_dir.mkdir(parents=True, exist_ok=True)
    zip_path = models_dir / "vosk_temp.zip"

    print(f"[INFO] Downloading Vosk model from {url}...")
    try:
        urllib.request.urlretrieve(url, str(zip_path), reporthook=_download_progress)
        print("\n[INFO] Extracting Vosk model...")
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(models_dir)
        print("[INFO] Vosk model successfully extracted.")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"\n[WARNING] Failed to download or extract Vosk model: {exc}")
        return False
    finally:
        if zip_path.exists():
            try:
                zip_path.unlink()
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for model provisioning."""
    parser = argparse.ArgumentParser(
        description="CapriPet Model Provisioning & Integrity Tool",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=get_default_models_dir(),
        help="Path to models directory (default: <project_root>/models)",
    )
    parser.add_argument(
        "--vad",
        action="store_true",
        help="Target Silero VAD model only",
    )
    parser.add_argument(
        "--vosk",
        action="store_true",
        help="Target Vosk ASR model only",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Target both models (default if neither --vad nor --vosk specified)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify model presence without downloading (exit 0 if present, 1 if missing)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if model is already present",
    )

    args = parser.parse_args(argv)
    models_dir: Path = args.models_dir.resolve()

    target_vad = args.vad or args.all or (not args.vad and not args.vosk)
    target_vosk = args.vosk or args.all or (not args.vad and not args.vosk)

    # 1. Verification mode
    if args.check_only:
        vad_ok = (not target_vad) or check_silero_vad(models_dir)
        vosk_ok = (not target_vosk) or check_vosk_model(models_dir)

        if vad_ok and vosk_ok:
            print("[INFO] All requested models are present.")
            return 0

        if not vad_ok:
            print(f"[MISSING] Silero VAD model not found in {models_dir}")
        if not vosk_ok:
            print(f"[MISSING] Vosk model not found in {models_dir}")
        return 1

    # 2. Provisioning mode
    if target_vad:
        if args.force or not check_silero_vad(models_dir):
            success = download_silero_vad(models_dir)
            if not success and not check_silero_vad(models_dir):
                print("[WARNING] Silero VAD is unavailable. VAD will be disabled.")
        else:
            print("[INFO] Silero VAD model already exists. Skipping.")

    if target_vosk:
        if args.force or not check_vosk_model(models_dir):
            success = download_vosk_model(models_dir)
            if not success and not check_vosk_model(models_dir):
                print("[WARNING] Vosk model is unavailable. Speech recognition may fail.")
        else:
            print("[INFO] Vosk model already exists. Skipping.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
