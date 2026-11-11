@echo off
setlocal
cd /d "%~dp0\.."

set "PYTHONUTF8=1"
set "QT_QPA_PLATFORM=offscreen"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" scripts\verify_codebase.py
exit /b %ERRORLEVEL%
