# Testing & Verification Rules

## Testing Framework & Execution

1. **Standard Library Testing:**
   - All tests must use Python's built-in `unittest` module.
   - Do not require or add external test runners (like `pytest`) unless explicitly requested.

2. **Test Execution Command:**
   - Always run the test suite using the project virtual environment:
     ```cmd
     .\.venv\Scripts\python.exe -m unittest discover -s tests -v
     ```
   - Individual test files can be executed via:
     ```cmd
     .\.venv\Scripts\python.exe -m unittest tests/test_imports.py
     ```

## Test Suite Structure (`tests/`)

- **`tests/test_imports.py`**:
  - Validates dynamic import of all submodules in `capri` using `pkgutil.walk_packages`.
  - Ensures clean dependency resolution and catches broken import paths or missing modules early.
- **`tests/test_core.py`**:
  - Tests configuration schema validation (`settings.py`), morphology stemming, spoken number parsing, and wake word triggers.
- **`tests/test_commands.py`**:
  - Tests keyboard layout switching (`switch_layout`), command registry population, and command matching/dispatch logic.
- **`tests/test_integrations.py`**:
  - Tests command line specifications for system integrations (power management, screen locking).
- **`tests/test_input_flow.py`**:
  - Tests conversational flow parsing, spoken selection numbers, affirmation/negation sets, and layout switching.
- **`tests/test_system_cleaner.py`**:
  - Tests byte formatting conversions, data structures, and URL query handling.
- **`tests/test_theme.py`**:
  - Tests strict cyberpunk hex palette compliance and typography stack specifications.
- **`tests/test_command_handlers.py`**:
  - Tests command execution with mocked CommandContext and duration formatting.
- **`tests/test_audio_recognizer.py`**:
  - Tests ModelStatus state machine and speech backend isolation.
- **`tests/test_process_manager.py`**:
  - Tests fuzzy process matching and process iteration via psutil mocks.
- **`tests/test_app_launcher.py`**:
  - Tests transliteration and phonetic normalization algorithms.
- **`tests/test_sprite_manager.py`**:
  - Tests sprite scaling bounds and pixel alpha hit detection.

## Rules for Writing Tests

1. **Strict Code Quality Compliance:**
   - No comments (`#`) or docstrings in test code.
   - Strict static typing with explicit return types (`-> None`) on test methods.
2. **Deterministic & Isolated:**
   - Unit tests must not trigger actual OS destructive operations (e.g. do not invoke `run_lock` or `run_power` without mocking).
3. **Mandatory Test Verification:**
   - When modifying core modules, commands, or imports, run both `py_compile` and `unittest` to ensure zero regressions before completing tasks.
