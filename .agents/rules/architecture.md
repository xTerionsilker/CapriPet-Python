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
