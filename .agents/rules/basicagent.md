# AGENTS.md

## Target Operating Systems & Cross-Platform Support

CapriPet targets **strictly two desktop operating systems: Linux and Windows**. All new features, windowing logic, input capturing, audio playback, file paths, and system integrations must support both platforms seamlessly:

- **Linux:**
  - Handles Wayland (KWin / Mutter) and X11 environments.
  - `main.py` explicitly selects `QT_QPA_PLATFORM=xcb` under Wayland with XWayland to ensure consistent frameless window positioning and coordinate tracking.
  - Configuration files default to `.capri/` inside the project root, falling back to XDG (`$XDG_CONFIG_HOME/capri/config.json` or `~/.config/capri/config.json`).
  - Audio fallbacks use system utilities (`pw-play`, `paplay`, `aplay`) or Qt `QSoundEffect`.
- **Windows:**
  - Works natively with Windows Desktop Window Manager (DWM) and Multi-DPI displays.
  - Frameless click-through overlays use standard Qt tool window flags (`WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW`).
  - Cursor tracking and screen metrics leverage native Win32 APIs (`ctypes.windll.user32`) and Qt virtual screen geometry (`QGuiApplication.screens()`).
  - Configuration files default to `.capri/` inside the project root, falling back to `%APPDATA%/capri/config.json`.
  - Audio uses native `winsound` / `QSoundEffect`.

## Environment & Tooling

- **Python Interpreter:** Always use the local virtual environment (`./.venv/bin/python` on Linux, `.\.venv\Scripts\python.exe` on Windows). System Python lacks dependencies like `PySide6` and `vosk`.
- **Run Application:** `./.venv/bin/python main.py`
- **Headless Testing / Verification:** In terminal sessions without an X/Wayland display server, set `QT_QPA_PLATFORM=offscreen`:
  ```bash
  QT_QPA_PLATFORM=offscreen ./.venv/bin/python -c "from capri.ui.pet_window import CapriWindow; print('OK')"
  ```
- **Syntax & Linter Checks:**
  ```bash
  ./.venv/bin/python -m py_compile capri/**/*.py main.py
  ./.venv/bin/pyflakes capri/ main.py
  ```

## Visual Design & Cyberpunk Style Guide

The entire CapriPet interface must strictly adhere to the **Cyberpunk 2077 Military-Corpo Tech / HUD** aesthetic. Every visual element, overlay, dialog, HUD widget, menu, and effect should feel like an in-universe cyberware display, tactical OS, or neural link overlay:

1. **Geometry & Framing:**
   - **Chamfered / Cut Corners:** Avoid soft rounded corners (`border-radius`). Instead, use 45-degree chamfers, cut-outs (`_CORNER_CUT`), and asymmetrical angular frames.
   - **Corner Brackets & Technical Crosshairs:** Frame containers with corner brackets, caliper ticks, technical notch markers, and micro-grid indicators (e.g. Acid Green / Neon Crimson corner brackets).
   - **Section Separators:** Crisp, thin technical divider lines (`1px`), dotted/dashed guides, or linear gradients fading into transparency.

2. **CRT & Holo Display Elements:**
   - **Scanlines:** Fine horizontal scanlines (`1px` lines every 2–3px with low alpha like `rgba(242, 13, 46, 0.07)`).
   - **Digital Noise & Glitch:** Occasional horizontal line tearing, chromatic shift hints, or momentary flickers during transitions.
   - **Holographic Glow & Glass:** High-contrast solid Obsidian Black (`#0B0B0B`) bases with crisp neon borders; avoid generic translucent blur/aero unless it represents a CRT phosphorescent panel.

3. **Typography & Data Telemetry:**
   - **Font Stack:** Technical / terminal monospace fonts: `"Press Start 2P"`, `"Pixelify Sans"`, `"VT323"`, `"Terminus"`, `"JetBrains Mono"`, `"DejaVu Sans Mono"`, `monospace`.
   - **Technical Headers & Telemetry:** Prefix titles and headers with tactical metadata tags (e.g. `CAPRI//ONLINE`, `[SYS.LOAD: 42%]`, `▶ CAPRI//AWAITING_INPUT // [STATUS]`, `0xDEADBEEF`).
   - **Typewriter Effect & Block Cursors:** Text input and recognition output should appear via rapid typewriter effect accompanied by block cursor pulses (`█`).
   - **Status Indicators:** Micro LED dots, animated audio equalizer bars, and blinking recording / sync markers.

## Character Palette (Strict)

Capri's visual identity uses **only** the following colors:

| Color | Hex | Approx. share |
| --- | --- | --- |
| Neon crimson | `#F20D2E` | 45% |
| Obsidian black | `#0B0B0B` | 35% |
| Acid green | `#3CF12B` | 16% |
| White | `#FFFFFF` | 2% |
| Electric blue | `#1E70F0` | 1.5% |
| Neon violet | `#9922EE` | 0.5% |

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
  - SFX are synthesized on the fly via `capri/ui/speech_sfx.py` into cached WAV files and played via system audio utilities (`pw-play`, `paplay`, `aplay`) or `QSoundEffect`.
- **Configuration Management (`capri/core/settings.py`):**
  - Settings load in priority order: `<repo>/.capri/config.json` -> `$XDG_CONFIG_HOME/capri/config.json` (`~/.config/capri/config.json` on Linux, `%APPDATA%/capri/config.json` on Windows) -> `/tmp/capri_config.json`.
  - Saves are atomic: writes to `.tmp` file and replaces via `os.replace`.
- **Audio & Voice (`capri/audio/`):**
  - Offline STT uses `vosk` with Russian acoustic model located at `models/vosk-model-ru-0.42/`.
  - Wake word detection (`"Капри"`) lives in `capri/core/wake_word.py`.
  - Recognition is fully offline and local; internet dependency has been removed.
  - Missing audio input devices or missing media assets fail gracefully without crashing the app.
