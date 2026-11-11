# CapriPet — AI Agent Guidelines

This document provides strict operational, architectural, and design constraints for AI agents developing the **CapriPet** project.

---

## 1. Environment & Execution

- **Target Platform:** Windows 10 / 11 (DWM-native, Multi-DPI, Win32 APIs).
- **Python Interpreter:** Always use the local virtual environment: `.\.venv\Scripts\python.exe`.
- **Run Application:** `.\.venv\Scripts\python.exe main.py` or `capriWin.bat`.
- **Syntax & Integrity Verification:**
  ```cmd
  .\.venv\Scripts\python.exe -c "import compileall; compileall.compile_dir('capri', force=True); compileall.compile_file('main.py')"
  ```
- **Tool Operation Constraints:**
  - Operate on at most **50 lines per tool call** during edits or reads when necessary to prevent serialization latencies.

---

## 2. Architecture & Subsystems

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

## 3. Character Identity, Lore & Persona

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

## 4. Cyberpunk Design System & Character Palette

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

## 5. Code Quality & Standards

1. **Balanced Typing & Commenting:**
   - **Type Annotations:** All functions and methods must have complete static typing for arguments and return values (e.g. `def handle(query: str) -> CommandResult:`).
   - **Concise Contextual Comments:** Self-documenting code with expressive variable/method names is prioritized. Inline comments (`# ...`) are welcomed to clarify complex Win32 APIs, procedural math/kinematics, or non-obvious algorithms.
   - **PEP 257 Docstrings:** Clear docstrings for public classes and module-level facades.
2. **Anti-Legacy & Direct Refactoring:**
   - No backward-compatibility shims, adapter wrappers, deprecated aliases, or fake arguments.
   - When refactoring a function signature or class, update all callers directly.
   - Rely on established packages (`pydantic`, `psutil`, `rapidfuzz`, `httpx`, `pywin32`) instead of brittle custom workarounds.
3. **Verification Workflow:**
   - Run syntax compilation checks across all modules after modifying code:
     ```cmd
     .\.venv\Scripts\python.exe -c "import compileall; compileall.compile_dir('capri', force=True); compileall.compile_file('main.py')"
     ```

---

## 6. Documentation Synchronization (`docs/`)

Whenever codebase structure, configuration schemas, or subsystems change, update the documentation in the same changeset:
- **`docs/project_structure.md`:** Maintain the canonical ASCII codebase tree and single-line responsibility descriptions.
- **`docs/architecture.md`:** Keep Mermaid C4 and Sequence diagrams synchronized with actual subsystems and control flows.
- **`docs/config_spec.md`:** Keep Pydantic settings models and JSON field specifications up to date.
- **`README.md`:** Reflect updated user-facing features, setup steps, and command lists.

---

## 7. Git Commit Conventions

Strict adherence to **Conventional Commits**: `<type>(<scope>): <short description>`

- **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `chore`.
- **Allowed Scopes:** `audio`, `asr`, `voice`, `ui`, `theme`, `speech`, `menu`, `effects`, `glitch`, `teleport`, `commands`, `input`, `integrations`, `spotify`, `discord`, `system`, `shredder`, `core`, `config`, `morphology`, `rules`, `docs`.
- **Formatting:** Imperative present tense ("add", "fix", "refactor"), lowercase, no trailing period, maximum 72 characters for the subject line.

---

## 8. GitHub Issues & Release Notes Conventions

When authoring GitHub issues or milestone notes for new features, bug fixes, or enhancements, strictly adhere to the project's canonical technical style:

- **Issue Title:** Must match Conventional Commits format: `<type>(<scope>): <short description>` (e.g. `feat(effects): cinematic story-driven power and session transition screens` or `feat(ui): add movable Cyber HUD console for direct command input`).
- **Structure:**
  1. `## Summary`: Concise technical overview (1-2 paragraphs) of the user-facing capability, architectural rationale, and lore integration.
  2. `## What's Changed`: Categorized breakdown by subsystem with bolded component names, technical bullet points (Win32 APIs, Qt flags, audio synthesis signatures, algorithms, shortcuts), and lore quotes/reactions where applicable.
  3. `## Verification & Tests`: Markdown checkbox list (`- [x]`) documenting static compilation (`compileall`), runtime Qt/audio validations, event-loop behavior, and edge-case testing.
