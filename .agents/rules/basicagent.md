# CapriPet Agent Rules Index

This file serves as the root dispatch guide for AI agents working on CapriPet. Individual domains and operational constraints are partitioned into modular rules below:

## Modular Rule Modules

1. **[Agent Operation & Tooling Rules](agent_operation.md):**
   - File chunk size limits (max 50 lines per tool call to prevent serialization lag and JSON parser crashes).
   - Execution constraints: virtual environment (`.venv`), Python scripts, py_compile checks.

2. **[Code Quality & Anti-Legacy Standards](code_quality.md):**
   - Strict ban on comments and docstrings (clean self-documenting code with full type annotations).
   - Ban on artificial backward compatibility, legacy shims, and redundant adapters.
   - Requirement to prefer established standard/ecosystem packages over custom reinvented wheels.

3. **[Cyberpunk Visual Design & Palette Guide](design_system.md):**
   - Military-Corpo Tech / Rogue AI aesthetic, Blackwall themes, cut corners, CRT scanlines, datamosh.
   - Strict 6-color character palette with exact hex codes and proportion shares.
   - Audio soundscapes and monospace font stacks.

4. **[Platform & Environment Specifications](environment.md):**
   - Windows 10/11 platform requirements, Desktop Window Manager (DWM) integration, Multi-DPI, Win32 APIs.
   - Storage priority paths (`.capri/` -> `%APPDATA%/capri/`).

5. **[Architecture & Subsystems Reference](architecture.md):**
   - Application entry points (`main.py`, `capriWin.bat`).
   - Core submodules: `controllers`, `ui`, `effects`, `core`, `commands`, `integrations`, `audio`.

6. **[Mandatory Documentation Synchronization](docs_sync.md):**
   - Architectural documentation in `docs/`: system schemas & C4/sequence diagrams (`architecture.md`), Pydantic settings specification (`config_spec.md`), and codebase tree index (`project_structure.md`).
   - Strict requirement to proactively update `README.md`, `docs/`, and agent rules concurrently with any code or structural change.

7. **[Testing & Verification Rules](testing.md):**
   - Standard `unittest` framework, execution via `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`.
   - Pipeline discipline: execute tests only once at the very end of work, never iteratively during editing.
   - Coverage of imports, core settings, morphology, commands, and system integration specs.

