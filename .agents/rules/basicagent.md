# AGENTS.md

## Target Operating Systems & Platform Support

CapriPet targets **strictly Windows (Windows 10/11)**:

- **Windows:**
  - Works natively with Windows Desktop Window Manager (DWM) and Multi-DPI displays.
  - Frameless click-through overlays use standard Qt tool window flags (`WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW`).
  - Cursor tracking and screen metrics leverage native Win32 APIs (`ctypes.windll.user32`) and Qt virtual screen geometry (`QGuiApplication.screens()`).
  - Configuration files default to `.capri/` inside the project root, falling back to `%APPDATA%/capri/config.json`.
  - Audio uses Qt `QSoundEffect`.

## Environment & Tooling

- **Python Interpreter:** Always use the local virtual environment (`.\.venv\Scripts\python.exe`). System Python lacks dependencies like `PySide6` and `vosk`.
- **Run Application:** `.\.venv\Scripts\python.exe main.py`
- **Launch via batch script:** `capriWin.bat`
- **Syntax & Compilation Checks:**
  ```cmd
  .\.venv\Scripts\python.exe -m py_compile capri/**/*.py main.py
  ```

## Visual Design & Cyberpunk Style Guide

The entire CapriPet interface must strictly adhere to the **Cyberpunk 2077 Military-Corpo Tech / HUD** aesthetic. Every visual element, overlay, dialog, HUD widget, menu, and effect should feel like an in-universe cyberware display, tactical OS, or neural link overlay:

1. **Geometry & Framing:**
   - **Chamfered / Cut Corners:** Avoid soft rounded corners (`border-radius`). Instead, use 45-degree chamfers, cut-outs (`_CORNER_CUT`), and asymmetrical angular frames.
   - **Corner Brackets & Technical Crosshairs:** Frame containers with corner brackets, caliper ticks, technical notch markers, and micro-grid indicators (e.g. Acid Green / Neon Crimson corner brackets).
   - **Section Separators:** Crisp, thin technical divider lines (`1px`), dotted/dashed guides, or linear gradients fading into transparency.

2. **CRT & Holo Display Elements:**
   - **Scanlines:** Fine horizontal scanlines (`1px` lines every 2–3px with low alpha like `rgba(246, 2, 63, 0.07)`).
   - **Digital Noise & Glitch:** Occasional horizontal line tearing, chromatic shift hints, or momentary flickers during transitions.
   - **Holographic Glow & Glass:** High-contrast solid Obsidian Black (`#020106`) bases with crisp neon borders; avoid generic translucent blur/aero unless it represents a CRT phosphorescent panel.

3. **Typography & Data Telemetry:**
   - **Font Stack:** Technical / terminal monospace fonts: `"Press Start 2P"`, `"Pixelify Sans"`, `"VT323"`, `"Terminus"`, `"JetBrains Mono"`, `"DejaVu Sans Mono"`, `monospace`.
   - **Technical Headers & Telemetry:** Prefix titles and headers with tactical metadata tags (e.g. `CAPRI//ONLINE`, `[SYS.LOAD: 42%]`, `▶ CAPRI//AWAITING_INPUT // [STATUS]`, `0xDEADBEEF`).
   - **Typewriter Effect & Block Cursors:** Text input and recognition output should appear via rapid typewriter effect accompanied by block cursor pulses (`█`).
   - **Status Indicators:** Micro LED dots, animated audio equalizer bars, and blinking recording / sync markers.

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

## Architecture & Entry Points

- **`main.py`:** Application entry point. Instantiates `CapriWindow` and enters the Qt event loop.
- **Orchestration & Business Logic:**
  - `PetOrchestrator` (`capri/controllers/orchestrator.py`): Central controller decoupling business logic from UI. Owns `CommandRegistry`, `InputFlow`, `ActionBridge` (background integrations like AI APIs, Spotify, process management), `InactivityManager`, and `PresenceReminder`.
- **Representation of Capri (View Layer):**
  - `CapriWindow` (`capri/ui/pet_window.py`): Cleaned View widget responsible for geometry, transparency, Qt event routing, and rendering.
  - `SpriteManager` (`capri/ui/sprite_manager.py`): Manages multi-pose sprite loading, caching, scaling, and pixel alpha hit detection (`assets/var/{idle,other,thinking}/`).
  - `TeleportController` (`capri/ui/teleport_controller.py`): Manages tactical lightning tether teleportation (holding LMB stretches red cyber lightning to cursor; releasing LMB triggers transition animation).
  - `TrayManager` (`capri/ui/tray_manager.py`): Encapsulates system tray icon lifecycle and activation menus.
- **Effects & Overlays:**
  - `EffectsCoordinator` (`capri/effects/effects_coordinator.py`): Unified facade managing procedural glitches (`GlitchManager`), session transitions (`SessionAnimationOverlay`), Vosk calibration HUD (`ModelInitOverlay`), and screen transitions (`TransitionOverlay`).
- **Voice System & HUD:**
  - `VoiceCoordinator` (`capri/ui/voice_coordinator.py`): Coordinates Vosk offline recognition, trigger-phrase arming timers, and updates to the voice HUD.
  - `CyberVoiceHud` (`capri/ui/voice_hud.py`): Displays a Cyberpunk 2077 style HUD above the taskbar when listening for voice commands or awaiting arguments/confirmation.
- **Speech System (`capri/ui/speech.py`):**
  - Displays cyber HUD speech bubbles (`CyberHudBubble`) with holographic deploy (open) and CRT beam collapse (close) animations.
  - Anchors dynamically to Capri (`CapriWindow`), tracking movement in real time via `eventFilter` and a 25ms timer.
  - Position is computed by `pick_adjacent_position` (`capri/ui/placement.py`), preferring side placement (right/left) and falling back to above/below or minimum overlap if screen space is tight.
  - SFX are synthesized on the fly via `capri/ui/speech_sfx.py` into cached WAV files and played via `QSoundEffect`.
- **Configuration Management (`capri/core/settings.py` & `capri/core/ai_config.py`):**
  - Settings are typed and validated using Pydantic v2 models (`CapriConfig`, `AIConfigModel`), ensuring declarative constraints, defaults, and boundary sanitization without manual dict merging.
  - Settings load in priority order: `<repo>/.capri/config.json` -> `%APPDATA%/capri/config.json` -> `%TEMP%/capri_config.json`.
  - Saves are atomic: writes to `.tmp` file and replaces via `os.replace`.
- **Audio & Voice (`capri/audio/` & `capri/core/morphology.py`):**
  - Offline STT uses `vosk` with Russian acoustic model located at `models/vosk-model-ru-0.42/` or `models/vosk-model-small-ru-0.22`, with optional `faster-whisper` hybrid backend support.
  - Streaming audio input via `VoiceInput` (`capri/audio/voice.py`) feeding chunks continuously to `KaldiRecognizer` without blocking buffer accumulation.
  - Adaptive noise-floor `EnergyVAD` (`capri/audio/vad.py`) eliminates false triggers from mouse clicks, keyboard presses, and background noise.
  - Dynamic silence window: cuts silence timeout to ~400ms when armed for instantaneous execution.
  - Wake word detection (`"Капри"`) in `capri/core/wake_word.py` uses hybrid regex + Damerau-Levenshtein fuzzy matching.
  - Follow-up command window (`VOICE_FOLLOWUP_WINDOW_MS = 4500`) keeps Capri armed for chaining commands without repeating the wake word.
  - Morphology & NLU in `capri/core/morphology.py` and `capri/commands/registry.py`: Snowball Russian stemmer, spoken number normalization (`пятьдесят` -> `50`), and slot permutation matching for free word order.
  - Speech recognition lifecycle and model caching are encapsulated in `VoskSpeechService` (`capri/audio/recognizer.py`) with thread-safe `ModelStatus` state transitions (`UNLOADED`, `LOADING`, `READY`, `FAILED`).
  - Missing audio input devices or missing media assets fail gracefully without crashing the app.

## Code Quality & Anti-Legacy Rules

1. **No Code Comments or Docstrings (Strict):**
   - **Do not write comments:** Do not add inline or block comments (`# ...`) in code under any circumstances (except mandatory shebangs `#!/usr/bin/env ...` when applicable).
   - **Do not write docstrings:** Do not add triple-quoted docstrings (`"""..."""` or `'''...'''`) to modules, classes, or functions.
   - **Self-documenting code:** Rely entirely on clean code structure, expressive naming (functions, variables, classes), and strict type annotations to make logic self-evident.

2. **No Artificial Backward Compatibility:**
   - **Do not write wrapper adapters or legacy bridges:** Never re-introduce adapters (such as `FunctionalCommand`, alias functions, fake parameters, or `*args/**kwargs` unpackers) purely to support hypothetical old signatures.
   - **No deprecated alias methods or redundant properties:** When refactoring a class or module, migrate the callers directly instead of leaving obsolete functions/properties with comments like `# Для обратной совместимости`.
   - **Strict type signatures:** New and refactored functions must use strict, explicit keyword/positional parameters with complete type annotations.
   - **Clean dependency contracts & standard libraries:** Standard libraries and established ecosystem packages (e.g. `pydantic`, `psutil`, `rapidfuzz`, `httpx`, `fake-useragent`, `cyrtranslit`, `yt-dlp`) are canonical. Do not implement manual string parsing, hand-rolled typo matching, browser registry crawlers, custom subprocess scrapers, or huge reinvented wheels where vetted PyPI libraries or standard ecosystem solutions can solve the problem cleanly and reliably. Feel free to adopt and install external libraries for integrations and complex OS/system tasks instead of writing brittle custom workarounds.
