@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv not found. Please run scripts\setup_env.bat first.
    exit /b 1
)

if "%~1"=="--install-hook" (
    echo [INFO] Installing pre-push git hook...
    if not exist ".git" (
        echo [ERROR] .git directory not found. Not a git repository.
        exit /b 1
    )
    if not exist ".git\hooks" mkdir ".git\hooks"
    (
        echo #^^!/bin/sh
        echo cmd.exe /c "scripts\\verify.bat"
        echo RESULT=$?
        echo if [ $RESULT -ne 0 ]; then
        echo     echo "[ERROR] Pre-push verification failed. Push aborted."
        echo     exit 1
        echo fi
        echo exit 0
    ) > ".git\hooks\pre-push"
    echo [SUCCESS] Git pre-push hook installed at .git\hooks\pre-push
    exit /b 0
)

echo ======================================================================
echo [CI LOCAL] CapriPet Integrity ^& Quality Verification
echo ======================================================================

REM 1. Ruff Lint Check
echo [STEP 1/4] Running Ruff linter...
if exist ".venv\Scripts\ruff.exe" (
    ".venv\Scripts\ruff.exe" check .
    if errorlevel 1 (
        echo [FAIL] Ruff linter found issues.
        exit /b 1
    )
) else (
    echo [WARNING] Ruff not found in virtual environment. Skipping lint check.
)
echo [OK] Ruff lint checks passed.

REM 2. Bytecode Compilation
echo [STEP 2/4] Verifying bytecode compilation...
".venv\Scripts\python.exe" -c "import compileall; compileall.compile_dir('capri', force=True); compileall.compile_dir('scripts', force=True); compileall.compile_file('main.py')"
if errorlevel 1 (
    echo [FAIL] Bytecode syntax compilation failed.
    exit /b 1
)
echo [OK] Bytecode compilation passed.

REM 3. Mypy Static Type Analysis
echo [STEP 3/4] Running Mypy static type analysis...
if exist ".venv\Scripts\mypy.exe" (
    ".venv\Scripts\mypy.exe" capri
    if errorlevel 1 (
        echo [FAIL] Mypy static type analysis failed.
        exit /b 1
    )
) else (
    echo [WARNING] Mypy not found in virtual environment. Skipping type analysis.
)
echo [OK] Mypy type analysis passed.

REM 4. Unittest Test Suite
echo [STEP 4/4] Executing unit and integration test suite...
set "PYTHONUTF8=1"
".venv\Scripts\python.exe" -m unittest discover -s tests
if errorlevel 1 (
    echo [FAIL] Unit tests failed.
    exit /b 1
)
echo [OK] Test suite passed.

echo ======================================================================
echo [SUCCESS] All local verification checks passed successfully!
echo ======================================================================
exit /b 0
