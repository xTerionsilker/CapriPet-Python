# Agent Operation & Tooling Rules

## Tool Execution Constraints

1. **File Chunk Size Limit (Strict):**
   - **Max 50 lines per tool call:** Whenever reading, editing, appending, or writing files, you must operate on at most 50 lines per individual tool call without exception.
   - **Reason:** Prevents large JSON payload serialization latency, IPC buffer overflows, and RPC timeout crashes during tool responses.

## Environment & Tooling Execution

- **Python Interpreter:** Always use the local virtual environment (`.\.venv\Scripts\python.exe`). System Python lacks dependencies like `PySide6` and `vosk`.
- **Run Application:** `.\.venv\Scripts\python.exe main.py`
- **Launch via batch script:** `capriWin.bat`
- **Syntax & Compilation Checks:**
  ```cmd
  .\.venv\Scripts\python.exe -m py_compile capri/**/*.py main.py
  ```
