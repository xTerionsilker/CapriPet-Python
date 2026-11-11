@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM 1. Ensure Python virtual environment exists
call scripts\setup_env.bat
if errorlevel 1 (
    echo [ERROR] Environment initialization failed.
    pause
    exit /b 1
)

REM 2. Ensure dependencies are satisfied
call scripts\install_deps.bat
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

REM 3. Provision and verify models (Silero VAD and Vosk ASR)
".venv\Scripts\python.exe" scripts\download_models.py
if errorlevel 1 (
    echo [WARNING] Model verification finished with warnings.
)

REM 4. Launch application via modular runner (supports --console and pass-through args)
call scripts\run_app.bat %*
if errorlevel 1 (
    echo/
    echo [ERROR] CapriPet launch failed.
    pause
    exit /b 1
)

endlocal
