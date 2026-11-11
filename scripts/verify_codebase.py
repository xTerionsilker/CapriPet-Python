"""Единый детерминированный раннер локальной верификации качества кода CapriPet.

Выполняет последовательную проверку 4 рубежей:
1. Ruff (Linter & PEP 8 Style)
2. Compileall (Синтаксис и компиляция байткода)
3. Mypy (Статический анализ типов и проверка атрибутов)
4. Unittest & Coverage (Юнит-тесты и метрики покрытия)

Возвращает код возврата 0 только при 100% успехе всех проверок.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Цветовые ANSI коды для терминала
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"


def log_step(step_num: int, title: str) -> None:
    print(f"\n{C_CYAN}{C_BOLD}[GATE {step_num}/4] >> {title}...{C_RESET}")


def run_command(cmd: list[str], desc: str) -> bool:
    print(f"{C_YELLOW}Running: {' '.join(cmd)}{C_RESET}")
    res = subprocess.run(cmd, cwd=ROOT)
    if res.returncode != 0:
        print(f"\n{C_RED}{C_BOLD}[FAIL] {desc} завершился с ошибкой (код {res.returncode})!{C_RESET}")
        return False
    print(f"{C_GREEN}[PASS] {desc} успешно пройден.{C_RESET}")
    return True


def main() -> int:
    os.environ["PYTHONUTF8"] = "1"
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    venv_python = (
        ROOT / ".venv" / "Scripts" / "python.exe"
        if sys.platform == "win32"
        else ROOT / ".venv" / "bin" / "python"
    )
    python_bin = str(venv_python) if venv_python.exists() else sys.executable

    print(f"{C_CYAN}{C_BOLD}==================================================={C_RESET}")
    print(f"{C_CYAN}{C_BOLD}   CAPRIPET // PRE-FLIGHT VERIFICATION HARNESS    {C_RESET}")
    print(f"{C_CYAN}{C_BOLD}==================================================={C_RESET}")

    # 1. Ruff check
    log_step(1, "Ruff Linter & Style Check")
    if not run_command([python_bin, "-m", "ruff", "check", "."], "Ruff Linter"):
        return 1

    # 2. Bytecode compileall
    log_step(2, "Bytecode Compilation & Syntax Check")
    compile_cmd = [
        python_bin,
        "-c",
        "import compileall; "
        "compileall.compile_dir('capri', force=True); "
        "compileall.compile_dir('scripts', force=True); "
        "compileall.compile_file('main.py')",
    ]
    if not run_command(compile_cmd, "Compileall Verification"):
        return 2

    # 3. Mypy static type analysis
    log_step(3, "Mypy Static Type & Attribute Analysis")
    if not run_command([python_bin, "-m", "mypy", "capri"], "Mypy Type Analysis"):
        return 3

    # 4. Unittest & Coverage
    log_step(4, "Test Suite Execution & Coverage Report")
    coverage_run = [
        python_bin,
        "-m",
        "coverage",
        "run",
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
    ]
    if not run_command(coverage_run, "Unit Tests Suite"):
        return 4

    coverage_report = [python_bin, "-m", "coverage", "report"]
    run_command(coverage_report, "Coverage Report")

    print(f"\n{C_GREEN}{C_BOLD}==================================================={C_RESET}")
    print(f"{C_GREEN}{C_BOLD}   ALL GATES PASSED! КОД ГОТОВ К ОТПРАВКЕ В РЕПО   {C_RESET}")
    print(f"{C_GREEN}{C_BOLD}==================================================={C_RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
