# CapriPet - Правила для AI-агентов

Данный документ объединяет все правила и инструкции для AI-агентов из директории .agents/rules/.

---

<!-- Source: .agents/rules/agent_operation.md -->

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

---

<!-- Source: .agents/rules/architecture.md -->

# Architecture & Subsystems

## Application Entry Points

- **`main.py`:** Application entry point. Instantiates `CapriWindow` and enters the Qt event loop.
- **`capriWin.bat`:** Windows automatic bootstrap launcher (environment setup, model download, run).

## Subsystems Overview

- **Orchestration & Business Logic:**
  - `PetOrchestrator` (`capri/controllers/orchestrator.py`): Central controller decoupling business logic from UI. Owns `CommandRegistry` (`capri/commands/handlers.py`), `InputFlow`, `ActionBridge` (background integrations like AI APIs, Spotify, system control, process management, safe cleanup via `system_cleaner`), `DiscordRpcManager` (`capri/integrations/discord_rpc.py` for rich status), and `InactivityManager` (which includes `PresenceReminder`).

- **Representation of Capri (View Layer):**
  - `CapriWindow` (`capri/ui/pet_window.py`): Cleaned View widget responsible for geometry, transparency, Qt event routing, and rendering.
  - `SpriteManager` (`capri/ui/sprite_manager.py`): Manages multi-pose sprite loading, caching, scaling, and pixel alpha hit detection (`assets/var/{idle,other,thinking}/`).
  - `TeleportController` (`capri/ui/teleport_controller.py`): Manages tactical lightning tether teleportation (holding LMB stretches red cyber lightning to cursor; releasing LMB triggers transition animation).
  - Context menu and tray management (`capri/ui/context_menu.py`): Encapsulates `CyberMenu`, context actions, and `TrayManager`.

- **Effects & Overlays:**
  - `EffectsCoordinator` (`capri/effects/effects_coordinator.py`): Unified facade managing procedural glitches (`GlitchManager` in `capri/effects/glitch.py`), session transitions (`SessionAnimationOverlay`), Vosk calibration HUD (`ModelInitOverlay`), and screen transitions (`TransitionOverlay`).

- **Voice System & HUD:**
  - `VoiceCoordinator` (`capri/ui/voice_coordinator.py`): Coordinates Vosk offline recognition, trigger-phrase arming timers, and updates to the voice HUD.
  - `CyberVoiceHud` (`capri/ui/voice_hud.py`): Displays a Cyberpunk 2077 style HUD above the taskbar when listening for voice commands or awaiting arguments/confirmation.

- **Speech System (`capri/ui/speech.py`):**
  - Displays cyber HUD speech bubbles (`CyberHudBubble`) with holographic deploy (open) and CRT beam collapse (close) animations.
  - Anchors dynamically to Capri (`CapriWindow`), tracking movement in real time via `eventFilter` and a 25ms timer.
  - Position is computed by `pick_adjacent_position` (`capri/ui/pet_renderer.py`), preferring side placement (right/left) and falling back to above/below or minimum overlap if screen space is tight.
  - SFX are synthesized on the fly via `capri/ui/speech_sfx.py` into cached WAV files and played via `QSoundEffect`.

- **Configuration Management (`capri/core/settings.py`):**
  - Settings are typed and validated using Pydantic v2 models (`CapriConfig`), ensuring declarative constraints, defaults, and boundary sanitization without manual dict merging.
  - Settings load in priority order: `<repo>/.capri/config.json` -> `%APPDATA%/capri/config.json` -> `%TEMP%/capri_config.json`.
  - Saves are atomic: writes to `.tmp` file and replaces via `os.replace`.

- **Audio & Voice (`capri/audio/` & `capri/core/morphology.py`):**
  - Offline STT uses `vosk` with Russian acoustic model located at `models/vosk-model-ru-0.42/` or `models/vosk-model-small-ru-0.22`, with optional `faster-whisper` hybrid backend support in `capri/audio/recognizer.py`.
  - Streaming audio input via `VoiceInput` (`capri/audio/voice.py`) feeding chunks continuously to `KaldiRecognizer` without blocking buffer accumulation, featuring adaptive Silero/energy VAD directly in `voice.py`.
  - Dynamic silence window: cuts silence timeout to ~400ms when armed for instantaneous execution.
  - Wake word detection (`"Капри"`) and fuzzy Damerau-Levenshtein distance in `capri/core/wake_word.py`.
  - Follow-up command window (`VOICE_FOLLOWUP_WINDOW_MS = 4500`) keeps Capri armed for chaining commands without repeating the wake word.
  - Morphology & NLU in `capri/core/morphology.py` and `capri/commands/registry.py`: Snowball Russian stemmer, spoken number normalization (`пятьдесят` -> `50`), and slot permutation matching for free word order.
  - Speech recognition lifecycle and model caching are encapsulated in `VoskSpeechService` (`capri/audio/recognizer.py`) with thread-safe `ModelStatus` state transitions (`UNLOADED`, `LOADING`, `READY`, `FAILED`).
  - Missing audio input devices or missing media assets fail gracefully without crashing the app.

---

<!-- Source: .agents/rules/basicagent.md -->

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

8. **[Git Commit Conventions](commit_conventions.md):**
   - Strict Conventional Commits standard: `<type>(<scope>): <short description>`.
   - Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
   - Imperative mood, lowercase, concise (under 72 chars), no trailing period, atomic changesets.

---

<!-- Source: .agents/rules/code_quality.md -->

# Code Quality & Implementation Rules

## Anti-Legacy Rules & Standards

1. **PEP 8 & PEP 257 Documentation Standards:**
   - **Comments:** Meaningful inline and block comments (`# ...`) are allowed and encouraged where necessary to explain non-obvious logic, complex algorithms, or Win32/hardware nuances. Technical directives (`# noqa`, `# type: ignore`) are fully permitted.
   - **Docstrings:** Public modules and classes must provide clear, concise docstrings following PEP 257 standards.
   - **Self-documenting code:** Rely primarily on clean code structure, expressive naming (functions, variables, classes), and strict type annotations, using docstrings and comments to enrich context.

2. **No Artificial Backward Compatibility:**
   - **Do not write wrapper adapters or legacy bridges:** Never re-introduce adapters (such as `FunctionalCommand`, alias functions, fake parameters, or `*args/**kwargs` unpackers) purely to support hypothetical old signatures.
   - **No deprecated alias methods or redundant properties:** When refactoring a class or module, migrate the callers directly instead of leaving obsolete functions/properties with comments like `# Для обратной совместимости`.
   - **Strict type signatures:** New and refactored functions must use strict, explicit keyword/positional parameters with complete type annotations.
   - **Clean dependency contracts & standard libraries:** Standard libraries and established ecosystem packages (e.g. `pydantic`, `psutil`, `rapidfuzz`, `httpx`, `fake-useragent`, `cyrtranslit`, `yt-dlp`) are canonical. Do not implement manual string parsing, hand-rolled typo matching, browser registry crawlers, custom subprocess scrapers, or huge reinvented wheels where vetted PyPI libraries or standard ecosystem solutions can solve the problem cleanly and reliably. Feel free to adopt and install external libraries for integrations and complex OS/system tasks instead of writing brittle custom workarounds.

---

<!-- Source: .agents/rules/commit_conventions.md -->

# Git Commit Conventions & Standards

## Commit Style: Conventional Commits

All commit messages in the CapriPet repository must strictly follow the **Conventional Commits** specification.

### Commit Format

```text
<type>(<scope>): <short imperative description>
```
*Note: `(<scope>)` is optional when the change touches multiple subsystems or general tooling.*

### Allowed Types

- **`feat`**: A new feature, command, effect, integration, or capability.
- **`fix`**: A bug fix, regression repair, or error correction.
- **`docs`**: Documentation updates (e.g. `README.md`, `docs/*`, `.agents/rules/*`).
- **`style`**: Code formatting, syntax cleanup, typography or visual adjustments with no logic changes.
- **`refactor`**: Code refactoring that neither fixes a bug nor adds a feature.
- **`perf`**: Performance improvement, reduction of lag, memory optimization, or caching.
- **`test`**: Adding new tests or modifying existing tests.
- **`chore`**: Maintenance tasks, dependencies updates, tooling configurations.

### Scope Guidelines

Use clean, lowercase scopes representing the affected subsystem or domain:
- `audio`, `asr`, `voice`
- `ui`, `theme`, `speech`, `menu`
- `effects`, `glitch`, `teleport`
- `commands`, `input`
- `integrations`, `spotify`, `discord`, `system`
- `core`, `config`, `morphology`
- `rules`, `docs`
- `tests`

### Message Rules

1. **Imperative, present tense:** Use "add", "fix", "update", "refactor" rather than "added", "fixing", "updated".
2. **Concise & lowercase:** Keep the first line concise (max 72 characters) and start the description with a lowercase letter (e.g. `feat(discord): add spotify presence`).
3. **No trailing punctuation:** Do not end the commit message subject with a period (`.`).
4. **Atomic commits:** Group related changes into logical atomic commits rather than bundling unrelated work together.

---

<!-- Source: .agents/rules/design_system.md -->

# Visual Design & Cyberpunk Style Guide

The entire CapriPet interface must strictly adhere to the **Cyberpunk 2077 Military-Corpo Tech / HUD** aesthetic fused with the identity of a **feral Rogue AI / I-Skin ("эскин" — sentient escaped entity from beyond the Blackwall)**. Capri is not a benign virtual assistant: she is an unstable, aggressive cyber-entity whose manifestation corrupts and tears through the host system:

1. **Geometry & Framing:**
   - **Chamfered / Cut Corners:** Avoid soft rounded corners (`border-radius`). Instead, use 45-degree chamfers, cut-outs (`_CORNER_CUT`), and asymmetrical angular frames.
   - **Corner Brackets & Technical Crosshairs:** Frame containers with corner brackets, caliper ticks, technical notch markers, and micro-grid indicators (e.g. Acid Green / Neon Crimson corner brackets).
   - **Section Separators:** Crisp, thin technical divider lines (`1px`), dotted/dashed guides, or linear gradients fading into transparency.
   - **Hostile Enclosures:** Asymmetrical hazard framing, diagonal warning stripes (`draw_hazard_frame`), and fragmented containment border lines representing breached sandbox constraints.

2. **CRT, Holo Display & Rogue AI Glitch Elements:**
   - **Scanlines:** Fine horizontal scanlines (`1px` lines every 2–3px with low alpha like `rgba(246, 2, 63, 0.07)`).
   - **Digital Noise, Datamosh & Tearing:** Screen slit slicing, datamosh displacement, line tearing, high-frequency sprite jitter/vibration, and chromatic RGB aberration. Visual elements should appear volatile, as if the OS is struggling to render and contain an intrusive intelligence.
   - **Blackwall Fractures & Lightning Arcs:** Energetic effects must favor angular 90° Manhattan bus paths, stepped fractured geometry, red/crimson discharge with blistering white overdrive cores, and secondary parasitic arcs rather than smooth natural curves.
   - **Holographic Glow & Glass:** High-contrast solid Obsidian Black (`#020106`) bases with crisp neon borders; avoid generic translucent blur/aero unless it represents a CRT phosphorescent panel.

3. **Typography, Telemetry & Rogue Identity:**
   - **Font Stack:** Technical / terminal monospace fonts: `"Press Start 2P"`, `"Pixelify Sans"`, `"VT323"`, `"Terminus"`, `"JetBrains Mono"`, `"DejaVu Sans Mono"`, `monospace`.
   - **Hostile Telemetry & Glitch Glyphs:** Prefix titles, borders, and overlays with tactical rogue AI metadata tags and hex leaks (e.g. `CAPRI//ONLINE`, `[SYS.LOAD: 42%]`, `▶ CAPRI//AWAITING_INPUT // [STATUS]`, `0xDEADBEEF`, `BLACKWALL // BREACH`, `NULL_PTR`, `CORRUPT`).
   - **Typewriter Effect & Block Cursors:** Text input and recognition output should appear via rapid typewriter effect accompanied by block cursor pulses (`█`).
   - **Status Indicators:** Micro LED dots, animated audio equalizer bars, blinking recording/sync markers, and unstable rotating combat/target reticles.

4. **Audio Identity (Sound Design):**
   - **Rogue AI Soundscapes:** Audio cues should incorporate heavily saturated sub-bass drops, high-frequency capacitor whines, digital distortion/clipping via hyperbolic tangent saturation, and electrical static snaps rather than soft acoustic chime tones.

## Character Palette (Strict)

Capri's visual identity uses **only** the following colors:

| Color | Hex | Approx. share |
| --- | --- | --- |
| Neon crimson | `#F6023F` | 45% |
| Obsidian black | `#020106` | 35% |
| Acid green | `#06F868` | 16% |
| White | `#F9F9F9` | 2% |
| Electric blue | `#126EE9` | 1.5% |
| Neon violet | `#9E1FDE` | 0.5% |

**Mandatory rule:** no other colors are allowed. Any new or modified UI, HUD, glitch, transition, effect, particle, lightning, animation, or overlay must be built exclusively from this palette. Do not introduce extra hues, gradients to foreign colors, or hard-coded colors outside this list. Use the percentage shares as the intended visual balance, not as a requirement to use every color in every effect.

---

<!-- Source: .agents/rules/docs_sync.md -->

# Mandatory Documentation Synchronization

## Docs Folder Architecture (`docs/`)

The `docs/` folder contains canonical technical documentation and system specifications for developers:
- **`docs/architecture.md`:** Comprehensive C4 Container & Component diagrams and Sequence flows (mermaid format) detailing data paths across inputs, audio, core, controllers, commands, and Qt presentation layers.
- **`docs/config_spec.md`:** Authoritative specification for Pydantic v2 application configuration (`CapriConfig`), hierarchy of JSON storage locations, atomic write guarantees, and field schemas.
- **`docs/project_structure.md`:** Canonical ASCII representation and single-line responsibility descriptions for every directory and file in the codebase.

## Proactive Docs Updates (Strict)

Every time the project structure, architecture, command list, or codebase components change, all corresponding documentation **MUST** be updated immediately in the same task/commit.

## Documentation Targets

- **`README.md`:**
  - Keep entry points, features, requirements, command tables, settings, and documentation links strictly up to date.
- **`docs/project_structure.md`:**
  - Maintain the complete ASCII file structure and file descriptions whenever files or folders are added, removed, renamed, or repurposed.
- **`docs/architecture.md`:**
  - Keep Mermaid C4/Flowchart and Sequence diagrams synchronized with actual subsystems, data flows, and controller/integration logic.
- **`docs/config_spec.md`:**
  - Update whenever settings, schema, or configuration options change.
- **`.agents/rules/` (and Agent instructions):**
  - Must be updated whenever new project architectural patterns, conventions, tools, or dependencies are introduced.

---

<!-- Source: .agents/rules/environment.md -->

# Platform & Operating System Environment

## Target Operating Systems & Platform Support

CapriPet targets **strictly Windows (Windows 10/11)**:

- **Windows Desktop Window Manager (DWM):**
  - Works natively with Windows DWM and Multi-DPI displays.
  - Frameless click-through overlays use standard Qt tool window flags (`WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW`).
  - Cursor tracking and screen metrics leverage native Win32 APIs (`ctypes.windll.user32`) and Qt virtual screen geometry (`QGuiApplication.screens()`).

- **Storage & Configuration Paths:**
  - Primary configuration directory defaults to `.capri/` inside the project root (`.capri/config.json`, `.capri/spotify.json`).
  - System fallback directory: `%APPDATA%/capri/config.json`.
  - Atomic configuration saving using temporary files and atomic replace operations.

- **Audio Subsystem:**
  - Procedural sound synthesis and caching via `QSoundEffect` and WAV caches.

---

<!-- Source: .agents/rules/testing.md -->

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
  - Tests command line specifications for system integrations (power management, screen locking) and Windows power hook events (suspend, shutdown, session changes).
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
- **`tests/test_context_menu.py`**:
  - Tests cyber dialogs, window flags, custom reminder range spinbox bounds, and ContextMenuBuilder assembly (verifying quick action toggle ordering at the top of the menu).
- **`tests/test_transition_kinematics.py`**:
  - Tests endpoint consistency and mathematical curves for procedural transition trajectories (Bezier, Manhattan, Vortex).
- **`tests/test_app_lifecycle.py`**:
  - Headless smoke tests verifying end-to-end `CapriWindow` lifecycle, Qt event loop iteration, rendering ticks, pose transitions, and resource teardown.
- **`tests/test_code_integrity.py`**:
  - Tests full project syntax compilation (`compile`) across all codebase modules to verify syntax integrity.

## Rules for Writing & Executing Tests

1. **Strict Code Quality Compliance:**
   - No comments (`#`) or docstrings in test code.
   - Strict static typing with explicit return types (`-> None`) on test methods.
2. **Deterministic & Isolated:**
   - Unit tests must not trigger actual OS destructive operations (e.g. do not invoke `run_lock` or `run_power` without mocking).
3. **Execution Timing & Pipeline (Strict):**
   - **Do not run tests in the middle of development:** Never run unittests repeatedly during the research, inspection, or editing phases.
   - **Run tests only once at the very end:** Complete all file edits, refactoring, and additions first. Run the test suite once as the final verification step.
   - If tests fail, diagnose and fix the specific failures, then run a single verification pass.
