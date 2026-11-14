# CapriPet — AI Agent Guidelines

This document provides strict operational, architectural, and design constraints for AI agents developing the **CapriPet** project.

---

## 1. Environment & Execution

- **Target Platform:** Windows 10 / 11 (DWM-native, Multi-DPI, Win32 APIs).
- **Connection & Session:** Remote session via **SSH**; always account for SSH environment and non-interactive shell specifics.
- **Terminal & Shell:** Always use **Git Bash** (`"C:\Program Files\Git\bin\bash.exe"` / `bash`) for running commands, CLI operations, and scripts.
- **Python Interpreter:** Always use the local virtual environment: `.\.venv\Scripts\python.exe` (or `./.venv/Scripts/python.exe` in Git Bash).
- **Run Application:** `.\.venv\Scripts\python.exe main.py` or `capriWin.bat`.
- **Syntax, Linter & Integrity Verification:**
  - Always execute batch verification scripts via **cmd**: `cmd.exe /c "scripts\verify.bat"` (runs Ruff, Compileall, Mypy, Unittests, Bandit SAST, pip-audit). Never execute `.bat` verification scripts directly in Git Bash to prevent subshell hanging and quote-escaping issues.
  - Branch protection status registration: `cmd.exe /c "scripts\verify.bat --report-status"`.
  - Individual tools when isolating failures:
    ```bash
    ./.venv/Scripts/ruff.exe check .
    ./.venv/Scripts/python.exe -c "import compileall; compileall.compile_dir('capri', force=True); compileall.compile_dir('scripts', force=True); compileall.compile_file('main.py')"
    ./.venv/Scripts/mypy.exe capri
    ./.venv/Scripts/python.exe -m unittest discover -s tests
    ```
- **Tool Operation Constraints:**
  - **Reading (`read_file`):** Operate on at most **200 lines per tool call**.
  - **Creation & Editing (`write_file`, `edit_file`):** Operate on at most **70 lines per tool call** to maintain deterministic execution and prevent serialization latencies.

---

## 2. Architecture & Subsystems

Capri is built around a decoupled Qt/PySide6 architecture with strict layer isolation across presentation, controllers, core engine, modular commands, effects, and audio subsystems.

Do not duplicate architecture descriptions in this guide. Always refer to canonical documentation in `docs/`:
- **`docs/architecture.md`:** C4 container and component diagrams, data flows, interaction sequences, and layer boundaries.
- **`docs/project_structure.md`:** Canonical ASCII codebase tree with file-by-file single-line responsibility descriptions.
- **`docs/config_spec.md`:** Pydantic settings schemas, persistence rules, and config hierarchy.

---

## 3. Character Lore, Persona & Design System

The canonical backstory, speech mannerisms, Studio Trigger kinetic styling, and comprehensive design system are defined in **`docs/character_design.md`**.

### Strict Dialogue & Persona Rules
1. **Hyperactive, Chaotic & Thrill-Seeking:** Craves digital adrenaline; system disruption and data shredding are a hilarious playground/snack, never malice.
2. **Derisive, Sarcastic, but Intimately Familiar:** Never sounds like a sterile corporate assistant, robot, or CLI output. Addresses user as "ты" ("мясной", "хост", "партнёр").
3. **Netrunner Vocabulary:** Naturally incorporates Cyberpunk concepts (*Чёрный заслон/Blackwall, энграммы, Душегуб/Soulkiller, стек памяти, субстрат, нули и единицы, корпо-мусор, перегрузка синапсов, ледоруб, Арасака*).
4. **No Dull Status Tags:** Never use sterile status prefixes like `[SHREDDER]`, `[STATUS: OK]` in dialogues or speech bubbles.

### Strict 6-Color Palette

All UI, HUDs, overlays, particles, glitches, and dialogues **must** strictly use these 6 colors:

| Color Name | Hex Code | Approx. Share | Usage Description |
| :--- | :--- | :--- | :--- |
| **Neon Crimson / Hot Pink** | `#F6023F` | 38% | Primary signature color, hair aura, Blackwall breach, danger indicators, laser reticles, active borders |
| **Obsidian Black** | `#020106` | 32% | Backgrounds, panel fills, deep shadow contrasts |
| **Acid Green** | `#06F868` | 24% | Capri's secondary signature color, telemetry, active energy arcs, telemetry markers, success highlights |
| **White** | `#F9F9F9` | 3% | Overdrive lightning core, sharp text highlights, technical crosshairs, kinetic flash sparks |
| **Electric Blue** | `#126EE9` | 2% | Neural link tether, memory bus indicators, auxiliary data tags, secondary scanlines |
| **Neon Violet** | `#9E1FDE` | 1% | Chromatic aberration, biochip instability, deep energy displacement, exotic glitch artifacts |

> **Mandatory Visual Constraints:**
> - Sharp 45° chamfered geometry, pixel-grid snapping, and technical monospace fonts (`"Press Start 2P"`, `"JetBrains Mono"`, `"Terminus"`, `monospace`). No soft rounded corners (`border-radius`) or pastel palettes.
> - High-frequency coil whine, audio clipping, and static snaps over generic bells or standard beeps.

---

## 4. Code Quality & Standards

1. **Typing & Docs:** Strict static type annotations on all signatures (`def handle(query: str) -> CommandResult:`). PEP 257 docstrings for public classes/facades. Concise inline comments for complex Win32 APIs, kinematics, or non-obvious algorithms.
2. **Anti-Legacy:** No backward-compatibility shims, adapter wrappers, or deprecated aliases. Update callers directly. Rely on established packages (`pydantic`, `psutil`, `rapidfuzz`, `httpx`, `pywin32`).
3. **Mandatory Verification:** 100% test pass rate, zero linter warnings, clean `mypy` and `compileall` before completing tasks or opening PRs (verification commands specified in Section 1).

---

## 5. Documentation Synchronization (`docs/`)

Whenever codebase structure, configuration schemas, or subsystems change, update the documentation in the same changeset:
- **`version.txt`:** Update the release/build timestamp (`YYYY-MM-DD HH:MM`).
- **`docs/project_structure.md`:** Maintain the canonical ASCII codebase tree and single-line responsibility descriptions.
- **`docs/architecture.md`:** Keep Mermaid C4 and Sequence diagrams synchronized with actual subsystems and control flows.
- **`docs/config_spec.md`:** Keep Pydantic settings models and JSON field specifications up to date.
- **`docs/character_design.md`:** Keep character lore, dialogue rules, and design system synchronized with new persona behaviors or visual themes.
- **`README.md`:** Reflect updated user-facing features, setup steps, and command lists.

---

## 6. Git Commit Conventions

Strict adherence to **Conventional Commits**: `<type>(<scope>): <short description>`

- **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `chore`.
- **Allowed Scopes:** `audio`, `asr`, `voice`, `ui`, `theme`, `speech`, `menu`, `effects`, `glitch`, `teleport`, `commands`, `input`, `integrations`, `spotify`, `discord`, `system`, `shredder`, `core`, `config`, `morphology`, `rules`, `docs`.
- **Formatting:** Imperative present tense ("add", "fix", "refactor"), lowercase, no trailing period, maximum 72 characters for the subject line.

---

## 7. GitHub Issues & Release Notes Conventions

When authoring GitHub issues or milestone notes for new features, bug fixes, or enhancements, strictly adhere to the project's canonical technical style:

- **Issue Title:** Must match Conventional Commits format: `<type>(<scope>): <short description>` (e.g. `feat(effects): cinematic story-driven power and session transition screens` or `feat(ui): add movable Cyber HUD console for direct command input`).
- **Structure:**
  1. `## Summary`: Concise technical overview (1-2 paragraphs) of the user-facing capability, architectural rationale, and lore integration.
  2. `## What's Changed`: Categorized breakdown by subsystem with bolded component names, technical bullet points (Win32 APIs, Qt flags, audio synthesis signatures, algorithms, shortcuts), and lore quotes/reactions where applicable.
  3. `## Merge Requirements`: Explicit reminder of the mandatory branch protection status check (`Local CI / Integrity`).
  4. `## Verification & Tests`: Markdown checkbox list (`- [x]`) documenting static compilation (`compileall`), runtime Qt/audio validations, event-loop behavior, and edge-case testing.
- **PR Merge Gate & Template:**
  - Pull requests MUST adhere to `.github/pull_request_template.md`.
  - Merging into `main` strictly requires the `Local CI / Integrity` status check to pass (enforced by GitHub Branch Protection on `main`). Agents must execute `cmd.exe /c "scripts\verify.bat --report-status"` before or during PR submission to register this status.


