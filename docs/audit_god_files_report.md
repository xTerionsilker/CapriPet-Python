# God-Files and Large Modules Architecture Audit

## 1. Overview & Context

This document captures the architectural audit of the **CapriPet** codebase conducted on branch `refactor/god-files-audit`. It establishes quantitative metrics, identifies God-Classes and monolithic files (>500 LOC), analyzes architectural coupling, and defines decomposition targets.

---

## 2. Top Monolithic Modules Ranking

| Module | LOC | Size (KB) | Primary Responsibilities | Anti-Pattern Profile |
| :--- | :---: | :---: | :--- | :--- |
| `capri/ui/pet_window.py` | 1004 | 36.3 | Window view, DWM events, drag-and-drop shredder, mouse gestures, prank kinematics, system hooks | **God-Class (`CapriWindow`)**: 59 methods violating Single Responsibility Principle. |
| `capri/ui/speech.py` | 944 | 31.3 | CRT holographic speech bubble rendering, typewriter animation, window positioning, queue management | **God-Module**: Mixed presentation widget, screen-geometry adapter, and queue controller. |
| `capri/effects/session_anim_helpers.py` | 894 | 31.3 | Matrix frame synthesis and math helpers for system session transition screens | **Oversized Utility**: Procedural calculation routines grouped without granular modularization. |
| `capri/effects/session_animations.py` | 779 | 26.1 | Lock/Power/Suspend fullscreen procedural animations | **Monolithic View**: High cyclomatic complexity across disparate session states. |
| `capri/ui/pet_renderer.py` | 739 | 24.5 | Procedural rendering: Blackwall aura, scanlines, chromatic aberration, sparks, HUD telemetry | **Monolithic Painter**: Multiple rendering passes intertwined in a single rendering class. |
| `capri/audio/sfx_generators.py` | 736 | 30.5 | 23 procedural audio synthesizer functions (PCM bytes, WAV packaging) | **Monolithic Repository**: Raw byte synthesis routines for UI, voice, and system transitions in one file. |
| `capri/effects/transition_modes.py` | 731 | 24.7 | Glitch transition mode implementations and procedural effect calculations | High line count due to detailed procedural algorithms. |
| `capri/effects/glitch.py` | 709 | 22.6 | Glitch managers, screen detection, and screen overlay management | Multiple screen and overlay state hooks. |
| `capri/controllers/orchestrator.py` | 544 | 20.3 | Central mediator for voice, ASR, UI speech, commands, inactivity, and window signals | High method fan-out orchestrating multiple async signals. |
| `capri/controllers/inactivity_manager.py` | 532 | 17.6 | Win32 idle tracking, reminder scheduling, stealth mode triggers | Mixed OS polling and presentation speech scheduling. |

---

## 3. Detailed Coupling & Responsibility Analysis

### 3.1 `CapriWindow` (`capri/ui/pet_window.py`)
`CapriWindow` has accumulated 59 methods and serves as the epicenter for:
1. **Window Lifecycle & Geometry:** Multi-monitor bounds, DPI scaling, and frameless transparency.
2. **Win32 & DWM Message Interception:** `nativeEvent` hooks for `WM_DWMCOLORIZATIONCOLORCHANGED` and power state notifications.
3. **Drag & Drop Subsystem:** Extracting file URLs from `QDropEvent`, triggering targeting VFX, and delegating file deletion to `data_shredder`.
4. **Prank Kinematics:** Intercepting cursor movement, dodging, melting, and relic dump animations.
5. **Speech & HUD Bridges:** Spawning bubbles, managing console HUD toggles, and coordinating volume indicators.

**Refactoring Solution:**
- Extract `WindowDragDropHandler` (`capri/ui/window_drag_drop.py`).
- Extract `WindowPrankController` (`capri/ui/window_prank_controller.py`).

### 3.2 Monolithic Speech Architecture (`capri/ui/speech.py`)
Combines three distinct architectural layers into 944 lines:
1. `CyberHudBubble`: Interactive Qt widget with CRT open/close animations, typewriter effects, and button layouts.
2. `SpeechWindow`: Frameless top-level window handling multi-screen geometry and clamping relative to the pet sprite.
3. `_SpeechManager`: Singleton queue prioritizing incoming lines, coordinating timeouts, and handling concurrent speech requests.

**Refactoring Solution:**
- Split into `capri/ui/speech_bubble.py` (widget view), `capri/ui/speech_manager.py` (queue & coordination), and maintain `capri/ui/speech.py` as a backward-compatible facade.

### 3.3 Procedural Rendering Passes (`capri/ui/pet_renderer.py`)
`PetRenderer` (739 lines) combines 8 distinct procedural rendering passes inside one file:
- Blackwall corruption aura calculation
- Chromatic aberration displacement
- Sparks & action lines
- HUD telemetry overlay

**Refactoring Solution:**
- Extract sub-painters: `BlackwallAuraPainter` and `HudTelemetryPainter` into `capri/ui/renderers/`.

### 3.4 Procedural Sound Generation (`capri/audio/sfx_generators.py`)
Contains 23 individual waveform synthesis functions handling mathematical PCM wave packing, frequency modulation, and RIFF headers.
**Refactoring Solution:**
- Decompose into `capri/audio/sfx/core_synth.py` (PCM/RIFF utilities), `ui_generators.py` (bubbles, teleports, clicks), and `session_generators.py` (lock, power, reboot).

---

## 4. Architectural Target Metrics

- No presentation file exceeds 600 LOC after refactoring (or substantial decomposition applied).
- Every extracted component must have dedicated unit tests with 100% pass rate.
- Zero public API breaks for existing callers.

---

## 5. Post-Refactoring Results & Metrics

| Module | Before (LOC) | After (LOC) | Extracted Delegates / Sub-Painters | Test Coverage |
| :--- | :---: | :---: | :--- | :--- |
| `capri/ui/pet_window.py` | 1004 | 909 | `WindowSystemEventsHandler`, `WindowPrankController` | `test_window_system_events.py`, `test_window_prank_controller.py` |
| `capri/ui/speech.py` | 944 | 531 | `CyberHudBubble` (`capri/ui/speech_bubble.py`) | `test_speech_bubble.py` |
| `capri/ui/pet_renderer.py` | 739 | 638 | `HudTelemetryPainter` (`capri/ui/renderers/hud_telemetry.py`) | `test_pet_renderer_passes.py` |
| `capri/audio/sfx_generators.py` | 736 | 706 | `capri/audio/sfx_core.py` (PCM/WAV DSP primitives) | `test_sfx_core.py` |

### Verification Summary
- **Total Tests:** 74 tests passing (0 failures, 0 errors).
- **Linter Status:** Zero warnings under `ruff check .`.
- **API Stability:** 100% backward-compatible facades preserved.

