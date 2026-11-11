@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv not found. Please run scripts\setup_env.bat first.
    exit /b 1
)

set "UPGRADE_REQUESTED=0"
if "%~1"=="--upgrade" set "UPGRADE_REQUESTED=1"
if "%~1"=="-u" set "UPGRADE_REQUESTED=1"

REM Check key runtime dependencies
".venv\Scripts\python.exe" -c "import PySide6; import vosk" >nul 2>&1
if errorlevel 1 (
    set "DEPS_MISSING=1"
) else (
    set "DEPS_MISSING=0"
)

if "%DEPS_MISSING%"=="1" (
    echo [INFO] Required dependencies missing. Installing from requirements.txt...
) else if "%UPGRADE_REQUESTED%"=="1" (
    echo [INFO] Dependency upgrade requested. Updating from requirements.txt...
) else (
    echo [INFO] Dependencies are satisfied.
    exit /b 0
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo [WARNING] Failed to upgrade pip. Proceeding with package installation...
)

".venv\Scripts\pip.exe" install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies from requirements.txt.
    exit /b 1
)

echo [INFO] Dependencies successfully installed.
exit /b 0
