# CapriPet — AI Agent Guidelines

This document provides strict operational, architectural, and design constraints for AI agents developing the **CapriPet** project.

---

## 1. Superpowers Skills & Autonomous Workflow

CapriPet utilizes the **Superpowers** skill framework for disciplined, reproducible software engineering. Whenever a task matches an available skill, agents **must invoke and follow the skill before acting**.

### Core Invocation Protocol
- **Skill-First Discipline:** Check for applicable skills before writing code, proposing solutions, or asking clarifying questions. If a skill applies to the task, invoking it is mandatory.
- **Process Skills Precedence:** Process skills (`brainstorming`, `systematic-debugging`) take priority over implementation skills (`writing-plans`, `test-driven-development`).
- **Antigravity Tool Mapping:**
  - **Subagents:** Use `invoke_subagent` (`TypeName: "self"` for full execution or `"research"` for read-only exploration).
  - **Task Tracking:** Maintain task artifacts (`write_file` / `edit_file` with `ArtifactMetadata`) as the living checklist (`- [ ]` / `- [x]`). Do not misuse `manage_task` (which is reserved for OS background processes).

### Essential Skills Matrix
| Trigger / Workflow Phase | Mandatory Skill | Scope & Primary Objectives |
| :--- | :--- | :--- |
| **New features / Architecture** | `brainstorming` | Explore requirements, design trade-offs, and visual/lore impact before planning. |
| **Multi-step implementation** | `writing-plans` | Formulate granular plans with explicit file paths, tasks, and verification steps. |
| **Plan execution (inline)** | `executing-plans` | Execute plans sequentially with task artifact checklist updates. |
| **Plan execution (subagents)**| `subagent-driven-development` | Dispatch focused subagents per independent work item. |
| **Feature / Bugfix coding** | `test-driven-development` | Red-Green-Refactor: failing test first, minimal implementation, clean refactor. |
| **Bug or unexpected behavior** | `systematic-debugging` | Trace root causes and test hypotheses before touching code. |
| **Verification & completion** | `verification-before-completion` | Run deterministic verification (`ruff check .`, `compileall`, full test suite) before claiming completion. |
| **Code reviews & feedback** | `requesting-code-review` / `receiving-code-review` | Pre-merge verification and objective technical review of feedback. |
| **Branch & task completion** | `finishing-a-development-branch` | Clean integration, commit hygiene, and branch disposition. |
| **Workspace isolation** | `using-git-worktrees` | Maintain isolated workspace state when developing parallel features. |

---

## 2. Environment & Execution

- **Target Platform:** Windows 10 / 11 (DWM-native, Multi-DPI, Win32 APIs).
- **Python Interpreter:** Always use the local virtual environment: `.\.venv\Scripts\python.exe`.
- **Run Application:** `.\.venv\Scripts\python.exe main.py` or `capriWin.bat`.
- **Syntax, Linter & Integrity Verification:**
  ```cmd
  .\.venv\Scripts\ruff.exe check .
  .\.venv\Scripts\python.exe -c "import compileall; compileall.compile_dir('capri', force=True); compileall.compile_dir('scripts', force=True); compileall.compile_file('main.py')"
  .\.venv\Scripts\mypy.exe capri
  .\.venv\Scripts\python.exe -m unittest discover -s tests
  ```
- **Tool Operation Constraints:**
  - Operate on at most **50 lines per tool call** during edits or reads when necessary to prevent serialization latencies.

---

## 3. Architecture & Subsystems

Capri is built around a decoupled Qt/PySide6 architecture with strict layer isolation:

- **Entry Points:** `main.py` (instantiates `CapriWindow` and launches Qt event loop), `capriWin.bat` (bootstrap launcher).
- **Presentation Layer (`capri/ui/`):**
  - `CapriWindow` (`ui/pet_window.py`): Clean frameless Qt view widget handling window geometry, transparency, DWM tracking, mouse/drag-and-drop events, and sprite hit-testing.
  - `PetRenderer` (`ui/pet_renderer.py`): Procedural rendering of sprite aura, scanlines, Blackwall glitch outlines, targeting reticles, and consumption vortexes.
  - `SpriteManager` (`ui/sprite_manager.py`): Multi-pose sprite loading, caching, scaling bounds, and pixel-alpha hitbox calculation (`assets/var/`).
  - `CyberHudBubble` & `SpeechSFX` (`ui/speech.py`, `ui/speech_sfx.py`): Holographic cyber speech bubbles with procedural CRT open/close animations and on-the-fly 8-bit/cyber audio synthesis.
  - `VoiceCoordinator` & `CyberVoiceHud` (`ui/voice_coordinator.py`, `ui/voice_hud.py`): Bottom-screen taskbar HUD displaying Vosk recognition states, listening feedback, and command chaining countdowns.
  - `TeleportController` (`ui/teleport_controller.py`): Tactical lightning tether and LMB repositioning.
  - `ContextMenuBuilder` & `TrayManager` (`ui/context_menu.py`): Cyberpunk styled context menu and system tray.
- **Controllers & Orchestration (`capri/controllers/`):**
  - `PetOrchestrator` (`controllers/orchestrator.py`): Central state and logic mediator. Coordinates ASR results, user input flow, UI notifications, and command routing.
  - `ActionBridge` (`controllers/action_bridge.py`): Async worker thread bridge executing non-UI tasks (web searches, process management, external APIs) without freezing the Qt main loop.
  - `InactivityManager` (`controllers/inactivity_manager.py`): Inactivity detection, periodic reminder triggers (`PresenceReminder`), and stealth mode management.
- **Core Engine & NLU (`capri/core/`):**
  - `CapriConfig` (`core/settings.py`): Pydantic v2 declarative configuration model with atomic file persistence (`.capri/config.json` -> `%APPDATA%/capri/config.json`).
  - `WakeWordDetector` (`core/wake_word.py`): Fuzzy Damerau-Levenshtein detector for trigger phrase («Капри»).
  - `MorphologyService` (`core/morphology.py`): Snowball Russian stemmer, phonetic normalization, and number parser.
  - `InputFlow` (`core/input_flow.py`): Multi-turn conversational sessions, confirmations, and argument capture.
- **Commands & Integrations (`capri/commands/`, `capri/integrations/`):**
  - `CommandRegistry` (`commands/registry.py`, `handlers.py`): Modular command matching, keyword permutation matching, and execution.
  - System integrations: `app_launcher.py`, `data_shredder.py` (Blackwall drag-and-drop secure file destruction), `discord_rpc.py`, `spotify.py`, `system_cleaner.py`, `system_control.py`, `game_mode.py`, `system_power_hook.py`, `process_manager.py`, `web_search.py`.
- **Procedural Effects (`capri/effects/`):**
  - `EffectsCoordinator` (`effects/effects_coordinator.py`): Facade managing procedural CRT glitch overlays (`glitch.py`), lightning tether overlays (`lightning_tether.py`), model calibration (`model_init_animation.py`), and screen transitions (`transition.py`).
- **Audio Subsystem (`capri/audio/`):**
  - `VoiceInput` (`audio/voice.py`): Continuous microphone streaming with Silero VAD noise suppression.
  - `VoskSpeechService` (`audio/recognizer.py`): Thread-safe speech recognition with dynamic silence cutoffs on standalone Vosk engine.

---

## 4. Character Identity, Lore & Persona

### Who Capri Truly Is
- **Origin & Nature:** **Capricorn (Каприкорн / Capri)** is an experimental digital personality construct / bio-weapon engram created by Arasaka under secret *Project Capricorn* using **Soulkiller (Душегуб)** technology. She is not an ordinary utility AI, but a fusion of multiple digitized human psyches merged into a single hyper-potent entity.
- **Symbiosis & Tether:** Having no organic body of her own, she is housed on a stolen biochip and projects herself holographically. She cannot exist long outside a host's neural link/system — the user/host is her anchor in reality, leading to an interdependent, chaotic partnership.
- **Visual & Auditory Persona:** A glitched, razor-sharp feminine projection with vibrant neon pink/crimson and electric green highlights, an explosive spiky hairstyle, and erratic Studio Trigger-style kinetic hyperactivity. Her voice/sound design features high-frequency coil whine, digital clipping, and static snaps.

### Temperament & Speech Mannerisms (Strict Lore Guidelines)
1. **Hyperactive, Chaotic & Thrill-Seeking:**
   - She is bored by mundane tasks and craves digital adrenaline. Destruction, shredding data, and causing systemic disruption are not malicious evil to her — they are a hilarious game, a playground, or a crunchy snack.
2. **Derisive, Sarcastic, but Intimately Familiar:**
   - She never speaks like a bland corporate assistant, robot, or technical system log (no dry status tags like `[SHREDDER]`, `[STATUS: OK]`, or formal polite phrasing).
   - She addresses the user directly on "ты", treating them like a fleshy, slightly incompetent partner-in-crime ("мясной", "хост", "партнёр").
   - She teases, mocks mistakes, brags about her superior processing speed, and comments with sharp black humor.
3. **Blackwall & Netrunner Vocabulary:**
   - Naturally weaves in netrunner and Cyberpunk concepts: *Чёрный заслон (Blackwall), энграммы, Душегуб (Soulkiller), стек памяти, субстрат, нули и единицы, корпо-мусор, перегрузка синапсов, ледоруб, Арасака*.
4. **Dialogue Generation Rule:**
   - Any dialog, bubble message, reminder, or error reaction written for Capri must reflect this energetic, sharp-tongued, mischievous personality. Never make her sound like Cortana, Siri, or a dull Linux console report.

---

## 5. Cyberpunk Design System & Character Palette

Capri's UI reflects corrupted military-corpo technology and Blackwall breach phenomena fused with **Studio Trigger-style kinetic hyperactivity**: cut 45° chamfered corners, micro-grid indicators, CRT scanlines, datamosh displacement, harsh electric discharge, and dynamic high-contrast duotone framing (Neon Crimson/Pink & Acid Green).

### Strict Character Palette

Any UI, HUD, particle, lightning arc, glitch, or dialog **must** strictly use the following 6 colors:

| Color Name | Hex Code | Approx. Share | Usage Description |
| :--- | :--- | :--- | :--- |
| **Neon Crimson / Hot Pink** | `#F6023F` | 38% | Primary signature color, hair aura, Blackwall breach, danger indicators, laser reticles, active borders |
| **Obsidian Black** | `#020106` | 32% | Backgrounds, panel fills, deep shadow contrasts |
| **Acid Green** | `#06F868` | 24% | Capri's secondary signature color, telemetry, active energy arcs, telemetry markers, success highlights |
| **White** | `#F9F9F9` | 3% | Overdrive lightning core, sharp text highlights, technical crosshairs, kinetic flash sparks |
| **Electric Blue** | `#126EE9` | 2% | Neural link tether, memory bus indicators, auxiliary data tags, secondary scanlines |
| **Neon Violet** | `#9E1FDE` | 1% | Chromatic aberration, biochip instability, deep energy displacement, exotic glitch artifacts |

> **Mandatory Visual Rules:**
> 1. **Kinetic & Dynamic:** UI elements and overlays must not feel like static corporate consoles. They should reflect a hijacked, glitching neural link experiencing adrenaline spikes and erratic bursts of personality.
> 2. **Sharp Geometry:** No soft rounded corners (`border-radius`) or generic pastels. Maintain sharp 45° chamfers, pixel-grid snapping, and technical monospace typography (`"Press Start 2P"`, `"JetBrains Mono"`, `"Terminus"`, `monospace`).
> 3. **Auditory Persona:** Procedural audio synthesis favors high-frequency coil whines, hyperbolic tangent clipping, and electric snaps over soft melodic bells or dry system beeps.

---

## 6. Code Quality & Standards

1. **Typing & Docs:** Strict static type annotations on all signatures (`def handle(query: str) -> CommandResult:`). PEP 257 docstrings for public classes/facades. Concise inline comments for complex Win32 APIs, kinematics, or non-obvious algorithms.
2. **Anti-Legacy:** No backward-compatibility shims, adapter wrappers, or deprecated aliases. Update callers directly. Rely on established packages (`pydantic`, `psutil`, `rapidfuzz`, `httpx`, `pywin32`).
3. **Mandatory Verification:** 100% test pass rate, zero linter warnings, clean `mypy` and `compileall` before completing tasks or opening PRs (verification commands specified in Section 2).

---

## 7. Documentation Synchronization (`docs/`)

Whenever codebase structure, configuration schemas, or subsystems change, update the documentation in the same changeset:
- **`docs/project_structure.md`:** Maintain the canonical ASCII codebase tree and single-line responsibility descriptions.
- **`docs/architecture.md`:** Keep Mermaid C4 and Sequence diagrams synchronized with actual subsystems and control flows.
- **`docs/config_spec.md`:** Keep Pydantic settings models and JSON field specifications up to date.
- **`README.md`:** Reflect updated user-facing features, setup steps, and command lists.

---

## 8. Git Commit Conventions

Strict adherence to **Conventional Commits**: `<type>(<scope>): <short description>`

- **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `chore`.
- **Allowed Scopes:** `audio`, `asr`, `voice`, `ui`, `theme`, `speech`, `menu`, `effects`, `glitch`, `teleport`, `commands`, `input`, `integrations`, `spotify`, `discord`, `system`, `shredder`, `core`, `config`, `morphology`, `rules`, `docs`.
- **Formatting:** Imperative present tense ("add", "fix", "refactor"), lowercase, no trailing period, maximum 72 characters for the subject line.

---

## 9. GitHub Issues & Release Notes Conventions

When authoring GitHub issues or milestone notes for new features, bug fixes, or enhancements, strictly adhere to the project's canonical technical style:

- **Issue Title:** Must match Conventional Commits format: `<type>(<scope>): <short description>` (e.g. `feat(effects): cinematic story-driven power and session transition screens` or `feat(ui): add movable Cyber HUD console for direct command input`).
- **Structure:**
  1. `## Summary`: Concise technical overview (1-2 paragraphs) of the user-facing capability, architectural rationale, and lore integration.
  2. `## What's Changed`: Categorized breakdown by subsystem with bolded component names, technical bullet points (Win32 APIs, Qt flags, audio synthesis signatures, algorithms, shortcuts), and lore quotes/reactions where applicable.
  3. `## Merge Requirements`: Explicit reminder of the mandatory branch protection status check (`Local CI / Integrity`).
  4. `## Verification & Tests`: Markdown checkbox list (`- [x]`) documenting static compilation (`compileall`), runtime Qt/audio validations, event-loop behavior, and edge-case testing.
- **PR Merge Gate & Template:**
  - Pull requests MUST adhere to `.github/pull_request_template.md`.
  - Merging into `main` strictly requires the `Local CI / Integrity` status check to pass (enforced by GitHub Branch Protection on `main`). Agents must execute `scripts\verify.bat --report-status` before or during PR submission to register this status.


