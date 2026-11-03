@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM 1. Check for Windows virtual environment
if not exist ".venv\Scripts\python.exe" (
    if exist ".venv\bin\python" (
        echo [WARNING] Detected Linux-based .venv. Remove it or recreate it for Windows!
    )
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

REM 4. Launch CapriPet without console window via pythonw.exe
start "" ".venv\Scripts\pythonw.exe" main.py %*
if errorlevel 1 (
    echo.
    echo [ERROR] CapriPet exited with error (code !errorlevel!).
    pause
)

endlocal
