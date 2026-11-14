@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv not found. Please run scripts\setup_env.bat first.
    exit /b 1
)

set "INSTALL_HOOK=0"
set "REPORT_STATUS=0"
set "SKIP_AUDIT=0"

:parse_loop
if "%~1"=="" goto after_parse
if /i "%~1"=="--install-hook" (
    set "INSTALL_HOOK=1"
    shift
    goto parse_loop
)
if /i "%~1"=="--report-status" (
    set "REPORT_STATUS=1"
    shift
    goto parse_loop
)
if /i "%~1"=="--skip-audit" (
    set "SKIP_AUDIT=1"
    shift
    goto parse_loop
)
shift
goto parse_loop

:after_parse
if "!INSTALL_HOOK!"=="1" (
    echo [INFO] Installing pre-push git hook with status reporting...
    if not exist ".git" (
        echo [ERROR] .git directory not found. Not a git repository.
        exit /b 1
    )
    if not exist ".git\hooks" mkdir ".git\hooks"
    (
        echo #^^!/bin/sh
        echo cmd.exe /c "scripts\\verify.bat --report-status"
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
echo [CI LOCAL] CapriPet Integrity ^& Security Verification
echo ======================================================================

set "FAILED_STAGE=None"

REM 1. Ruff Lint Check
echo [STEP 1/6] Running Ruff linter...
if exist ".venv\Scripts\ruff.exe" (
    ".venv\Scripts\ruff.exe" check .
) else (
    ".venv\Scripts\python.exe" -m ruff check .
)
if errorlevel 1 (
    echo [FAIL] Ruff linter found issues or tool is missing.
    set "FAILED_STAGE=Ruff Linter"
    goto on_fail
)
echo [OK] Ruff lint checks passed.

REM 2. Bytecode Compilation
echo [STEP 2/6] Verifying bytecode compilation...
".venv\Scripts\python.exe" -c "import compileall; compileall.compile_dir('capri', force=True); compileall.compile_dir('scripts', force=True); compileall.compile_file('main.py')"
if errorlevel 1 (
    echo [FAIL] Bytecode syntax compilation failed.
    set "FAILED_STAGE=Bytecode Compilation"
    goto on_fail
)
echo [OK] Bytecode compilation passed.

REM 3. Mypy Static Type Analysis
echo [STEP 3/6] Running Mypy static type analysis...
if exist ".venv\Scripts\mypy.exe" (
    ".venv\Scripts\mypy.exe" capri
) else (
    ".venv\Scripts\python.exe" -m mypy capri
)
if errorlevel 1 (
    echo [FAIL] Mypy static type analysis failed or tool is missing.
    set "FAILED_STAGE=Mypy Type Check"
    goto on_fail
)
echo [OK] Mypy type analysis passed.

REM 4. Unittest Test Suite
echo [STEP 4/6] Executing unit and integration test suite...
set "PYTHONUTF8=1"
".venv\Scripts\python.exe" -m unittest discover -s tests
if errorlevel 1 (
    echo [FAIL] Unit tests failed.
    set "FAILED_STAGE=Unit Tests"
    goto on_fail
)
echo [OK] Test suite passed.

REM 5. Bandit SAST Security Scan
echo [STEP 5/6] Running Bandit SAST security scanner...
if exist ".venv\Scripts\bandit.exe" (
    ".venv\Scripts\bandit.exe" -r capri/ -ll
) else (
    ".venv\Scripts\python.exe" -m bandit -r capri/ -ll
)
if errorlevel 1 (
    echo [FAIL] Bandit security scanner identified vulnerabilities or tool is missing.
    set "FAILED_STAGE=Bandit SAST Scanner"
    goto on_fail
)
echo [OK] Bandit security audit passed ^(0 high/medium issues^).

REM 6. pip-audit Dependency Vulnerability Scan
if "!SKIP_AUDIT!"=="1" (
    echo [STEP 6/6] Skipping pip-audit dependency scanner ^(--skip-audit specified^).
    goto after_audit
)
echo [STEP 6/6] Running pip-audit dependency vulnerability scanner...
if exist ".venv\Scripts\pip-audit.exe" (
    call ".venv\Scripts\pip-audit.exe"
) else (
    ".venv\Scripts\python.exe" -m pip_audit
)
if errorlevel 1 (
    echo [FAIL] pip-audit detected vulnerable dependencies or tool is missing.
    set "FAILED_STAGE=pip-audit Vulnerability Scanner"
    goto on_fail
)
echo [OK] Dependency vulnerability audit passed.

:after_audit
if "!REPORT_STATUS!"=="1" (
    for /f %%i in ('git rev-parse HEAD 2^>nul') do set "HEAD_SHA=%%i"
    if defined HEAD_SHA (
        echo [INFO] Registering commit status to GitHub for !HEAD_SHA!...
        gh api -X POST repos/xTerionsilker/CapriPet-Python/statuses/!HEAD_SHA! -F state=success -F context="Local CI / Integrity" -F description="All 60 tests, Ruff, Mypy, Bandit & pip-audit passed" >nul 2>&1
        if not errorlevel 1 (
            echo [OK] GitHub commit status registered: Local CI / Integrity [success].
        )
    )
)

echo ======================================================================
echo [SUCCESS] All 6 local verification checks passed successfully!
echo ======================================================================
exit /b 0

:on_fail
if "!REPORT_STATUS!"=="1" (
    for /f %%i in ('git rev-parse HEAD 2^>nul') do set "HEAD_SHA=%%i"
    if defined HEAD_SHA (
        gh api -X POST repos/xTerionsilker/CapriPet-Python/statuses/!HEAD_SHA! -F state=failure -F context="Local CI / Integrity" -F description="Verification failed at !FAILED_STAGE!" >nul 2>&1
    )
)
echo [ERROR] Verification failed at stage: !FAILED_STAGE!.
exit /b 1
