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

## Architecture & Entry Points

- **`main.py`:** Application entry point. Instantiates `CapriWindow` and enters the Qt event loop.
- **Orchestration & Business Logic:**
  - `PetOrchestrator` (`capri/controllers/orchestrator.py`): Central controller decoupling business logic from UI. Owns `CommandRegistry` (`capri/commands/handlers.py`), `InputFlow`, `ActionBridge` (background integrations like AI APIs, Spotify, system and process management), `DiscordRpcManager` (`capri/integrations/discord_rpc.py` for rich status), and `InactivityManager` (which includes `PresenceReminder`).
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

3. **File Chunk Size Limit (Strict):**
   - **Max 50 lines per tool call:** Whenever reading, editing, appending, or writing files, you must operate on at most 50 lines per individual tool call without exception.
