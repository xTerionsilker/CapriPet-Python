#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Check for virtual environment
if [ ! -f ".venv/bin/python" ]; then
    if [ -f ".venv/Scripts/python.exe" ]; then
        echo "[WARNING] Detected Windows-based .venv! Remove .venv before running on Linux."
    fi

    echo "[INFO] Virtual environment .venv not found. Creating..."
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD="python"
    else
        echo "[ERROR] Python not found in system! Please install Python 3.10+."
        exit 1
    fi

    "$PYTHON_CMD" -m venv .venv
    echo "[INFO] Environment .venv successfully created."
fi

# 2. Check installed dependencies
if ! ./.venv/bin/python -c "import PySide6; import vosk" >/dev/null 2>&1; then
    echo "[INFO] Required libraries not installed. Installing dependencies from requirements.txt..."
    ./.venv/bin/python -m pip install --upgrade pip
    ./.venv/bin/pip install -r requirements.txt
    echo "[INFO] Dependencies successfully installed."
fi

# 3. Download Silero VAD (ONNX) model if missing
SILERO_URL="https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx"
if [ ! -f "models/silero_vad.onnx" ]; then
    echo "[INFO] Silero VAD model not found. Downloading..."
    mkdir -p models
    if command -v curl >/dev/null 2>&1; then
        curl -L -o "models/silero_vad.onnx" "$SILERO_URL" || true
    elif command -v wget >/dev/null 2>&1; then
        wget -O "models/silero_vad.onnx" "$SILERO_URL" || true
    else
        ./.venv/bin/python -c "import urllib.request; urllib.request.urlretrieve('$SILERO_URL', 'models/silero_vad.onnx')" 2>/dev/null || true
    fi

    if [ -f "models/silero_vad.onnx" ] && [ -s "models/silero_vad.onnx" ]; then
        echo "[INFO] Silero VAD model successfully downloaded."
    else
        echo "[WARNING] Failed to download Silero VAD. VAD will be disabled."
        rm -f "models/silero_vad.onnx"
    fi
fi

# 4. Download Vosk speech recognition model if missing
VOSK_FOUND=false
for dir in models/vosk-model*; do
    if [ -d "$dir" ]; then
        VOSK_FOUND=true
        break
    fi
done

if [ "$VOSK_FOUND" = false ]; then
    echo "[INFO] Vosk model not found in models/. Downloading vosk-model-small-ru-0.22..."
    mkdir -p models
    ./.venv/bin/python -c "
import urllib.request
import zipfile
from pathlib import Path

url = 'https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip'
zip_path = Path('models/vosk-model-small-ru-0.22.zip')
try:
    print('Downloading Vosk model (~45MB)...')
    urllib.request.urlretrieve(url, zip_path)
    print('Extracting model...')
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall('models')
    zip_path.unlink(missing_ok=True)
    print('[INFO] Vosk model successfully installed.')
except Exception as e:
    print(f'[WARNING] Failed to download Vosk model: {e}')
    if zip_path.exists():
        zip_path.unlink()
"
fi

# 5. Generate desktop and application menu shortcuts
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
ICON_PATH="$SCRIPT_DIR/assets/capri_icon.png"

create_desktop_entry() {
    local target_file="$1"
    cat <<EOF > "$target_file"
[Desktop Entry]
Type=Application
Name=CapriPet
Comment=Capri Desktop Pet
Exec=$SCRIPT_DIR/capriLinux.sh
Icon=$ICON_PATH
Path=$SCRIPT_DIR
Terminal=false
Categories=Utility;Game;
StartupNotify=false
EOF
    chmod +x "$target_file"
}

# Desktop shortcut
if [ -d "$DESKTOP_DIR" ] && [ ! -f "$DESKTOP_DIR/CapriPet.desktop" ]; then
    create_desktop_entry "$DESKTOP_DIR/CapriPet.desktop"
    # Allow launching on GNOME desktops if gio is available
    gio set "$DESKTOP_DIR/CapriPet.desktop" metadata::trusted true 2>/dev/null || true
    echo "[INFO] Created desktop shortcut: $DESKTOP_DIR/CapriPet.desktop"
fi

# Applications menu shortcut (~/.local/share/applications)
USER_APPS_DIR="$HOME/.local/share/applications"
if [ ! -f "$USER_APPS_DIR/CapriPet.desktop" ]; then
    mkdir -p "$USER_APPS_DIR"
    create_desktop_entry "$USER_APPS_DIR/CapriPet.desktop"
    echo "[INFO] Created application menu shortcut: $USER_APPS_DIR/CapriPet.desktop"
fi

# 6. Launch CapriPet
set +e
./.venv/bin/python main.py "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo
    echo "[ERROR] CapriPet exited with error (code $EXIT_CODE)."
    if [ -t 0 ] && [ -t 1 ]; then
        read -r -p "Press Enter to exit..." dummy 2>/dev/null || true
    fi
    exit $EXIT_CODE
fi
