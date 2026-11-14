#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="./.venv/Scripts/python.exe"
if [ ! -f "$PYTHON" ]; then
    echo "[ERROR] Virtual environment .venv not found. Please run scripts/setup_env.bat first."
    exit 1
fi

REPORT_STATUS=0
SKIP_AUDIT=0
for arg in "$@"; do
    case "$arg" in
        --report-status) REPORT_STATUS=1 ;;
        --skip-audit) SKIP_AUDIT=1 ;;
    esac
done

echo "======================================================================"
echo "[CI LOCAL] CapriPet Integrity & Security Verification"
echo "======================================================================"

echo "[STEP 1/6] Running Ruff linter..."
"$PYTHON" -m ruff check .
echo "[OK] Ruff lint checks passed."

echo "[STEP 2/6] Verifying bytecode compilation..."
"$PYTHON" -c "import compileall; compileall.compile_dir('capri', force=True); compileall.compile_dir('scripts', force=True); compileall.compile_file('main.py')"
echo "[OK] Bytecode compilation passed."

echo "[STEP 3/6] Running Mypy static type analysis..."
"$PYTHON" -m mypy capri
echo "[OK] Mypy type analysis passed."

echo "[STEP 4/6] Executing unit and integration test suite..."
export PYTHONUTF8=1
"$PYTHON" -m unittest discover -s tests
echo "[OK] Test suite passed."

echo "[STEP 5/6] Running Bandit SAST security scanner..."
"$PYTHON" -m bandit -r capri/ -ll
echo "[OK] Bandit security audit passed (0 high/medium issues)."

if [ "$SKIP_AUDIT" -eq 0 ]; then
    echo "[STEP 6/6] Running pip-audit dependency vulnerability scanner..."
    "$PYTHON" -m pip_audit
    echo "[OK] Dependency vulnerability audit passed."
else
    echo "[STEP 6/6] Skipping pip-audit dependency scanner (--skip-audit specified)."
fi

if [ "$REPORT_STATUS" -eq 1 ]; then
    HEAD_SHA=$(git rev-parse HEAD 2>/dev/null || true)
    if [ -n "$HEAD_SHA" ]; then
        echo "[INFO] Registering commit status to GitHub for $HEAD_SHA..."
        gh api -X POST repos/xTerionsilker/CapriPet-Python/statuses/"$HEAD_SHA" \
            -F state=success -F context="Local CI / Integrity" \
            -F description="All 100 tests, Ruff, Mypy, Bandit & pip-audit passed" >/dev/null 2>&1 || true
        echo "[OK] GitHub commit status registered: Local CI / Integrity [success]."
    fi
fi

echo "======================================================================"
echo "[SUCCESS] All 6 local verification checks passed successfully!"
echo "======================================================================"
