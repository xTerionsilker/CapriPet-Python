# CapriPet

A small Tamagotchi-style desktop pet. Capri lives in a looping video, listens
to whatever you type, and answers through a typewriter speech bubble that
appears somewhere else on the screen. The interface is styled like a blocky pixel-art terminal, and the whole
desktop is covered by a subtle CRT glitch layer that occasionally goes haywire.

```
+--------------------------------------------------+
|                                                  |
|                 looping capri.mp4                |
|                                                  |
+--------------------------------------------------+
| // CAPRI ONLINE                                  |
| > Say something to Capri…                [SEND]  |
+--------------------------------------------------+
```

## Features

- Loop the character video forever with QtMultimedia at 1.5× speed.
- Text input with Enter or the **SEND** button.
- Replies are typed out character by character in a frameless neon bubble.
- The speech bubble appears at a random spot on screen and avoids the main
  window, then closes itself after the text has been read.
- Random startup greetings, including one that uses your OS username.
- Built-in commands: `help` / `what u can?` lists everything Capri understands,
  `glitch` / `turn glitch` toggles the glitch overlay, and `noise` toggles the
  background hiss on and off.
- Commands are forgiving: casing, punctuation and small typos (like `gltich`
  or `quie`) are still matched to the right command.
- Constant subtle scanlines/static with periodic, much stronger glitch spikes.
- A quiet looping hiss under everything that swells with the visual glitch.
- Glitch overlays are click-through, focus-less and cover every monitor.
- Quit with `Ctrl+Q`.

## Requirements

- Python 3.10+ (tested with 3.14)
- PySide6 6.12+ (QtMultimedia and its FFmpeg backend ship with the wheel)

Everything is pinned in `requirements.txt`.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

Or directly with the virtualenv interpreter:

```bash
.venv/bin/python main.py
```

The video is loaded from `capri.mp4` next to `main.py`; it loops indefinitely.
You can replace it with another clip, though the window is sized for an
800×450 video. Playback speed is set by `PLAYBACK_RATE` at the top of
`capri/pet_window.py` (default `1.5`; use `1.0` for normal speed).

## Starting with the system

On Linux desktops that follow the XDG autostart specification (KDE Plasma,
GNOME, Xfce, …), create `~/.config/autostart/capripet.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=CapriPet
Comment=Tamagotchi-style desktop pet
Exec=/absolute/path/to/CapriPet/.venv/bin/python /absolute/path/to/CapriPet/main.py
Path=/absolute/path/to/CapriPet
Icon=video-television
Terminal=false
StartupNotify=false
X-GNOME-Autostart-enabled=true
```

Replace the paths with the project's real location and make sure the
virtualenv is already set up. The entry starts Capri at login and can be
enabled or disabled under *Autostart* in the desktop's system settings.
`main.py` still switches to XWayland when needed, so this also works on
Wayland sessions.

## Using Capri

1. Type a message into the input field.
2. Press **Enter** or click **SEND**.
3. Capri's answer appears in a speech bubble somewhere on the screen. Click
   the bubble to skip the typing animation; click again to close it early.
4. `Ctrl+Q` closes the application and removes the glitch overlays.

### Commands

| Command | Aliases | Action |
| --- | --- | --- |
| `help` | `what u can?`, `commands` | List every available command. |
| `glitch` | `turn glitch` | Toggle the full-screen glitch overlay. |
| `noise` | `toggle noise` | Toggle the background static noise on/off. |

Anything else is passed through `process_input()` and echoed back by the demo.

Command matching ignores case, surrounding punctuation and repeated spaces,
and tolerates a few typos. The allowed edit distance grows with the command
length (one edit up to five characters, up to three for long aliases), and
transposed letters count as a single typo. The matching logic lives in
`CommandRegistry.find()` / `_closest()` in `capri/commands.py`.

## Project structure

```
main.py                 # application entry point
capri/
├── __init__.py         # public exports
├── pet_window.py       # main window: video, input, greeting, wiring
├── speech.py           # reusable typewriter speech bubble
├── glitch.py           # full-screen click-through glitch overlays
├── static_noise.py     # looping white noise that follows the glitch
├── commands.py         # command registry and help listing
└── theme.py            # cyberpunk stylesheet
requirements.txt
capri.mp4
```

## Customizing

### Replies

`CapriWindow.process_input()` in `capri/pet_window.py` receives the raw text
and returns the reply string. Replace or extend it with your own logic — a
state machine, an API call, a local model, etc.

```python
def process_input(self, text: str) -> str:
    reply = self.commands.dispatch(text)
    if reply is not None:
        return reply
    return f"You said: {text}"
```

Commands are kept in `capri/commands.py` (`CommandRegistry`). Register your
own in `CapriWindow.__init__`:

```python
self.commands.register(
    "dance",
    "make Capri dance.",
    lambda: "Capri wiggles!",
    aliases=("start dance",),
)
```

Registered commands appear automatically in `help` / `what u can?`.

### Startup lines

Edit `STARTUP_LINES` in `capri/pet_window.py`. `{user}` is replaced with
`getpass.getuser()`:

```python
STARTUP_LINES = (
    "Good boy, {user}",
    "just call me Capri!!!",
    "...",
)
```

### Speech bubble

`capri.speech.show_text()` can be reused anywhere:

```python
from capri.speech import show_text

show_text(
    "Hello there!",
    parent=window,          # window to avoid overlapping
    chars_per_second=40,    # reveal speed
    hold_ms=1200,           # pause after the text is fully shown
    max_width=420,          # wrapping width in pixels
)
```

Placement uses the parent window's screen. A random free rectangle is chosen
with a 24 px gap from the parent; if the parent fills the whole screen, the
least-overlapping spot is used instead.

### Glitches

Tune `_BASE_INTERVAL_MS` and `_SPIKE_INTERVAL_MS` at the top of
`capri/glitch.py`. The spike duration and frequency live in `_start_spike()`
and `_tick()`; colours are in `_COLORS` / `_NOISE`. The overlay only draws —
it never intercepts clicks or keyboard input.

Every overlay also reports an amplitude between 0 and 1 each frame, which
`GlitchManager.amplitude_changed` forwards to the sound layer.

### Static noise

`capri/static_noise.py` plays looping white noise for as long as Capri runs.
`_BASE_LEVEL` and `_PEAK_LEVEL` at the top of the file control the idle and
maximum volume; the rest is shaped automatically by the glitch amplitude, so
the hiss swells during a spike and settles back to its quiet baseline
afterwards. Volume changes are smoothed in `StaticNoise._smooth()` to avoid
zipper noise. If no audio output is available the noise is skipped silently.

The noise can be muted without releasing the audio device via
`set_enabled(False)`; `toggle()` flips it and returns the new state. Muting
jumps straight to zero volume instead of fading down to the idle level, so it
is fully silent. The `noise` command uses these methods.

```python
from capri.static_noise import StaticNoise

noise = StaticNoise(window)
glitch_manager.amplitude_changed.connect(noise.set_amplitude)
```

### Theme

All colours, fonts and widget styles for the main window are in
`capri/theme.py`; the speech bubble keeps its own small matching stylesheet in
`capri/speech.py` so it stays self-contained and reusable. The theme uses
square corners, chunky 3 px bevels and stepped gradients to mimic pixel art.
For a true bitmap look, install a pixel font such as *Press Start 2P* or
*VT323* — `PIXEL_FONT` already lists them ahead of the monospace fallbacks.

## Platform notes

- Wayland does not allow applications to position their own top-level windows.
  To make the random speech placement work, `main.py` automatically switches
  to XWayland (`QT_QPA_PLATFORM=xcb`) when both a Wayland session and an X11
  display are available. Set `QT_QPA_PLATFORM=wayland` explicitly to override
  this; the speech bubble will then be placed by the compositor instead.
- XWayland is also the most reliable backend for the always-on-top glitch
  overlays. Some compositors may still restrict coverage across native Wayland
  windows.
- The glitch overlay is decorative and renders above other applications while
  Capri is running.
