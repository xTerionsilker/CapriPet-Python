# CapriWin.bat Decentralization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decentralize the monolithic 87-line `capriWin.bat` bootstrap script into decoupled, single-responsibility modular scripts under `scripts/` (environment setup, dependency management, Python-native model provisioning, and runtime launching) while preserving 100% backward compatibility.

**Architecture:**
- `capriWin.bat` (Root Facade): Clean orchestrator coordinating sub-scripts, forwarding arguments, and handling exit codes.
- `scripts/setup_env.bat`: Dedicated interpreter discovery (`py` / `python`) and `.venv` initialization.
- `scripts/install_deps.bat`: Fast dependency presence check and `requirements.txt` installation.
- `scripts/download_models.py`: Python-native model downloader with CLI flags (`--all`, `--vad`, `--vosk`, `--check-only`), error handling, and clean reporting (replacing inline `urllib` one-liners).
- `scripts/run_app.bat`: Execution launcher supporting both background/windowless (`pythonw.exe`) and debug console (`python.exe` via `--console` or `--debug`).

**Tech Stack:** Windows Batch (`cmd.exe`), Python 3.10+ standard library (`urllib.request`, `zipfile`, `argparse`, `pathlib`), PySide6 / Vosk environment.

---

## File Structure Map

```text
capriWin.bat                 # Root coordinator delegating to scripts/ (modified)
scripts/
├── setup_env.bat            # Python virtualenv creation and validation (new)
├── install_deps.bat         # Pip dependency installation and check (new)
├── download_models.py       # Python-based model downloader & integrity checker (new)
└── run_app.bat              # App launcher with windowless/console toggle (new)
tests/
└── test_download_models.py  # Unit tests for download_models.py CLI & logic (new)
docs/
└── project_structure.md     # Updated codebase structure (modified)
```

---

## Tasks

### Task 1: Python-Native Model Downloader (`scripts/download_models.py`)

**Files:**
- Create: `scripts/download_models.py`
- Create: `tests/test_download_models.py`

- [ ] **Step 1: Write failing unit test for `download_models.py`**
  Create `tests/test_download_models.py` testing:
  - Model detection logic (detects existing Silero VAD and Vosk directory).
  - CLI parser arguments (`--all`, `--vad`, `--vosk`, `--check-only`, `--models-dir`).
  - Mocked network download & extraction workflow.

- [ ] **Step 2: Run pytest to verify test failure**
  ```cmd
  .\.venv\Scripts\python.exe -m pytest tests/test_download_models.py
  ```

- [ ] **Step 3: Implement `scripts/download_models.py`**
  - Implement `check_vad(models_dir)` and `check_vosk(models_dir)`.
  - Implement `download_vad(models_dir)` and `download_vosk(models_dir)` with download progress indicators and extraction.
  - Implement CLI entry point with `argparse`.

- [ ] **Step 4: Run pytest and compileall to verify Task 1**
  ```cmd
  .\.venv\Scripts\python.exe -m pytest tests/test_download_models.py
  .\.venv\Scripts\python.exe -c "import compileall; compileall.compile_file('scripts/download_models.py')"
  ```

- [ ] **Step 5: Commit Task 1**
  ```cmd
  git add scripts/download_models.py tests/test_download_models.py
  git commit -m "feat(system): add python-native model provisioning script"
  ```

---

### Task 2: Modular Environment & Dependency Scripts (`scripts/setup_env.bat`, `scripts/install_deps.bat`)

**Files:**
- Create: `scripts/setup_env.bat`
- Create: `scripts/install_deps.bat`

- [ ] **Step 1: Implement `scripts/setup_env.bat`**
  - Isolate Python interpreter discovery (`py` -> `python`).
  - Verify Python availability; exit with code 1 and user guidance if missing.
  - Create `.venv` if not present.
  - Return exit code 0 on success.

- [ ] **Step 2: Implement `scripts/install_deps.bat`**
  - Verify `.venv\Scripts\python.exe` exists.
  - Run lightweight import check (`PySide6`, `vosk`).
  - If missing or `--upgrade` flag passed, run `pip install --upgrade pip` and `pip install -r requirements.txt`.
  - Return exit code 0 on success.

- [ ] **Step 3: Verify execution of both batch scripts in standalone mode**
  ```cmd
  cmd /c "scripts\setup_env.bat"
  cmd /c "scripts\install_deps.bat"
  ```

- [ ] **Step 4: Commit Task 2**
  ```cmd
  git add scripts/setup_env.bat scripts/install_deps.bat
  git commit -m "feat(system): add modular environment and dependency setup scripts"
  ```

---

### Task 3: Modular Runner Script (`scripts/run_app.bat`)

**Files:**
- Create: `scripts/run_app.bat`

- [ ] **Step 1: Implement `scripts/run_app.bat`**
  - Check for `--console` or `--debug` flag in command line arguments.
  - If console/debug: launch `.venv\Scripts\python.exe main.py %*` (attached console).
  - If normal run: launch `start "" ".venv\Scripts\pythonw.exe" main.py %*` (windowless GUI).
  - Forward all remaining CLI flags to `main.py`.

- [ ] **Step 2: Verify `scripts/run_app.bat` argument parsing**
  Test with dry-run / `--help` flag via cmd.

- [ ] **Step 3: Commit Task 3**
  ```cmd
  git add scripts/run_app.bat
  git commit -m "feat(system): add modular application runner with console mode toggle"
  ```

---

### Task 4: Refactor Root Orchestrator (`capriWin.bat`)

**Files:**
- Modify: `capriWin.bat`

- [ ] **Step 1: Rewrite `capriWin.bat` as lightweight pipeline coordinator**
  - Call `call scripts\setup_env.bat` (halt on error).
  - Call `call scripts\install_deps.bat` (halt on error).
  - Run `".venv\Scripts\python.exe" scripts\download_models.py` (halt on error).
  - Execute `call scripts\run_app.bat %*`.
  - Keep root script readable (< 30 lines) and strictly structured.

- [ ] **Step 2: Verify root launcher end-to-end**
  ```cmd
  cmd /c "capriWin.bat --help"
  ```

- [ ] **Step 3: Commit Task 4**
  ```cmd
  git add capriWin.bat
  git commit -m "refactor(system): decentralize capriWin.bat into modular scripts"
  ```

---

### Task 5: Documentation & Verification Synchronization

**Files:**
- Modify: `docs/project_structure.md`
- Modify: `README.md`

- [ ] **Step 1: Update `docs/project_structure.md`**
  Document the new `scripts/` directory and its components.

- [ ] **Step 2: Update `README.md`**
  Document the modular scripts, optional `--console` debug mode, and direct model downloader usage.

- [ ] **Step 3: Run comprehensive verification**
  ```cmd
  .\.venv\Scripts\python.exe -m pytest tests/
  .\.venv\Scripts\python.exe -c "import compileall; compileall.compile_dir('capri', force=True); compileall.compile_dir('scripts', force=True); compileall.compile_file('main.py')"
  git status --short
  ```

- [ ] **Step 4: Commit Task 5**
  ```cmd
  git add docs/project_structure.md README.md
  git commit -m "docs(system): document decentralized launcher architecture and scripts"
  ```
