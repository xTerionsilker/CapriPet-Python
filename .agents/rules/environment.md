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
