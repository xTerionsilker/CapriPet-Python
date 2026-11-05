@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM 1. Check for Windows virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment .venv not found. Creating...
    
    set "PY_CMD="
    where py >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=py"
    ) else (
        where python >nul 2>&1
        if !errorlevel! equ 0 (
            set "PY_CMD=python"
        )
    )

    if not defined PY_CMD (
        echo [ERROR] Python not found in system! Please install Python 3.10+ and add it to PATH.
        pause
        exit /b 1
    )

    "!PY_CMD!" -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment .venv.
        pause
        exit /b 1
    )
    echo [INFO] Environment .venv successfully created.
)

REM 2. Check installed dependencies
".venv\Scripts\python.exe" -c "import PySide6; import vosk" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Required libraries not installed. Installing dependencies from requirements.txt...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\pip.exe" install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [INFO] Dependencies successfully installed.
)

REM 3. Download Silero VAD (ONNX) model if missing
if not exist "models\silero_vad.onnx" (
    echo [INFO] Silero VAD model not found. Downloading...
    if not exist "models" mkdir "models"
    set "SILERO_URL=https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx"
    curl.exe -L -o "models\silero_vad.onnx" "!SILERO_URL!" >nul 2>&1
    if not exist "models\silero_vad.onnx" (
        ".venv\Scripts\python.exe" -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx', 'models/silero_vad.onnx')" >nul 2>&1
    )
    if exist "models\silero_vad.onnx" (
        echo [INFO] Silero VAD model successfully downloaded.
    ) else (
        echo [WARNING] Failed to download Silero VAD. VAD will be disabled.
    )
)

REM 4. Download Vosk speech recognition model if missing
set "VOSK_FOUND=0"
for /d %%D in (models\vosk-model*) do (
    set "VOSK_FOUND=1"
)
if "!VOSK_FOUND!"=="0" (
    echo [INFO] Vosk model not found in models\. Downloading vosk-model-small-ru-0.22...
    if not exist "models" mkdir "models"
    ".venv\Scripts\python.exe" -c "import urllib.request, zipfile, os; zip_p='models/vosk-model-small-ru-0.22.zip'; print('Downloading Vosk model (~45MB)...'); urllib.request.urlretrieve('https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip', zip_p); print('Extracting model...'); zipfile.ZipFile(zip_p, 'r').extractall('models'); os.remove(zip_p); print('[INFO] Vosk model successfully installed.')"
    if errorlevel 1 (
        echo [WARNING] Failed to download Vosk model. Speech recognition might require manual setup.
    )
)

REM 5. Download Faster-Whisper base model if missing
if not exist "models\whisper-base\model.bin" (
    echo [INFO] Faster-Whisper base model not found in models\whisper-base\. Downloading...
    if not exist "models" mkdir "models"
    ".venv\Scripts\python.exe" -c "from faster_whisper import WhisperModel; import shutil, os; from pathlib import Path; print('Downloading Whisper base model (~140MB)...'); WhisperModel('base', device='cpu', compute_type='int8', download_root='models/whisper-base'); snap=list(Path('models/whisper-base').glob('**/snapshots/*')); [shutil.copy2(f, 'models/whisper-base/' + f.name) for f in snap[0].iterdir()] if snap else None; [shutil.rmtree(p, ignore_errors=True) for p in [Path('models/whisper-base/.locks'), Path('models/whisper-base/models--Systran--faster-whisper-base')]]; Path('models/whisper-base/CACHEDIR.TAG').unlink(missing_ok=True); print('[INFO] Faster-Whisper model successfully installed.')"
    if errorlevel 1 (
        echo [WARNING] Failed to download Faster-Whisper model.
    )
)

REM 6. Launch CapriPet without console window via pythonw.exe
start "" ".venv\Scripts\pythonw.exe" main.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] CapriPet exited with error (code !errorlevel!).
    pause
)

endlocal
