# AGENTS.md

## Environment & Tooling

- **Python Interpreter:** Always use the local virtual environment at `./.venv/bin/python`. System Python lacks dependencies like `PySide6` and `vosk`.
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
- **Wayland / X11 Quirk:** `main.py` explicitly selects `QT_QPA_PLATFORM=xcb` when running under Wayland with XWayland to ensure frameless window positioning and movement behave consistently across Linux compositors.

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
- **Representation of Capri:**
  - `CapriWindow` (`capri/ui/pet_window.py`): Floating translucent sprite (`assets/var/{idle,other,thinking}/`) rendered with custom pixel glitch passes.
  - Position is saved to configuration and restored automatically; dragging moves Capri across monitors.
  - Automatically hides during inactivity and reappears via `InactivityManager` (`capri/controllers/inactivity_manager.py`).
- **Speech System (`capri/ui/speech.py`):**
  - Displays cyber HUD speech bubbles (`CyberHudBubble`) with holographic deploy (open) and CRT beam collapse (close) animations.
  - Anchors dynamically to Capri (`CapriWindow`), tracking movement in real time via `eventFilter` and a 25ms timer.
  - Position is computed by `pick_adjacent_position` (`capri/ui/placement.py`), preferring side placement (right/left) and falling back to above/below or minimum overlap if screen space is tight.
  - SFX are synthesized on the fly via `capri/ui/speech_sfx.py` into cached WAV files and played via system audio utilities (`pw-play`, `paplay`, `aplay`) or `QSoundEffect`.
- **Configuration Management (`capri/core/settings.py`):**
  - Settings load in priority order: `$XDG_CONFIG_HOME/capri/config.json` (`~/.config/capri/config.json`) -> `<repo>/.capri/config.json` -> `/tmp/capri_config.json`.
  - Saves are atomic: writes to `.tmp` file and replaces via `os.replace`.
- **Audio & Voice (`capri/audio/`):**
  - Offline STT uses `vosk` with Russian acoustic model located at `models/vosk-model-ru-0.42/`.
  - Wake word detection (`"Капри"`) lives in `capri/core/wake_word.py`.
  - Recognition is fully offline and local; internet dependency has been removed.
  - Missing audio input devices or missing media assets fail gracefully without crashing the app.
