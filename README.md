# CapriPet

CapriPet is a small desktop pet in the style of a tamagotchi. Capri lives in a
looping video, listens to text and voice input, and answers in a floating speech
bubble with a typewriter effect. The UI is a pixel-terminal frameless window, and
the whole desktop gets a light CRT glitch overlay while Capri is running.

## Features

- Frameless 800×540 window; drag it by the video area.
- Text input and continuous voice input with the wake word “Капри”.
- Random startup greeting and a goodbye sequence on exit.
- Auto-hide after 10 seconds of inactivity: the main window disappears with a
  fast red-pink lightning transition; speaking a command brings it back. The
  glitch overlay stays visible the whole time.
- Floating speech bubbles that appear away from the main window.
- Built-in commands: glitch, noise, voice, Google/YouTube search, Spotify,
  screen lock, power actions, and local Ollama chat.
- Typo-tolerant command matching.
- Optional Spotify and Ollama integrations.

## Requirements

- Python 3.10+
- PySide6 6.12+
- `SpeechRecognition`
- Working microphone for voice input
- Spotify client and `dbus-send` for music commands
- Ollama for the `слушай` command

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Or with the virtual environment interpreter:

```bash
.venv/bin/python main.py
```

Media files live in `faces/` and `voices/` next to `main.py`. Missing files are
skipped, so the app still starts.

## Commands

| Command | Aliases | Action |
| --- | --- | --- |
| `помощь` | `что ты умеешь?`, `команды`, `справка` и др. | Show all commands |
| `комплимент` | `ты красивая`, `ты самая лучшая`, `ты прекрасна` и др. | Trigger wild glitches for 5 seconds |
| `глитч` | `глюки`, `эффекты`, `переключить глитч` и др. | Toggle glitch overlay |
| `голос` | `микрофон`, `слушать`, `запись` и др. | Toggle voice input |
| `гугл <запрос>` | `загугли`, `погугли`, `google` и др. | Search Google |
| `ютуб <запрос>` | `youtube`, `найди на ютубе` и др. | Search YouTube |
| `спотифай <запрос>` | `spotify`, `спотик`, `включи музыку` и др. | Play a Spotify track |
| `пауза` | `поставь на паузу`, `приостанови` и др. | Pause Spotify |
| `продолжить` | `плей`, `играй`, `возобнови` и др. | Resume Spotify |
| `следующий трек` | `следующий`, `next` и др. | Next Spotify track |
| `предыдущий трек` | `предыдущий`, `prev` и др. | Previous Spotify track |
| `блокировка` | `заблокировать`, `я отойду`, `lock` и др. | Lock the screen |
| `я спать` | `выключи пк`, `shutdown` и др. | Power off |
| `я гулять` | `спящий режим`, `sleep` и др. | Suspend |
| `я заебался` | `перезагрузи`, `restart` и др. | Reboot |
| `слушай <запрос>` | `спроси модель`, `ollama`, `qwen` и др. | Ask the local Ollama model |
| `Нормальный облик` | `нормальный вид`, `капри оверлей`, `покажи капри` и др. | Toggle between window and Capri overlay image (transparent, on top) |

Use `Ctrl+Q` to quit.

## Configuration

| Variable | Description |
| --- | --- |
| `CAPRI_OLLAMA_URL` / `OLLAMA_HOST` | Ollama server URL |
| `CAPRI_OLLAMA_MODEL` / `OLLAMA_MODEL` | Ollama model name |
| `CAPRI_OLLAMA_THINK` | Set to `0` to disable thinking |
| `SPOTIFY_CLIENT_ID` | Spotify client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify client secret |
| `QT_QPA_PLATFORM` | Override Qt platform backend |

Spotify keys can also be stored in `~/.config/capri/spotify.json`.

## Project structure

```text
main.py
capri/
├── __init__.py
├── ui/
├── core/
├── effects/
├── audio/
└── integrations/
faces/
voices/
requirements.txt
```

## Notes

- Wayland sessions are switched to XWayland automatically when possible.
- Voice recognition uses Google Web Speech and requires internet access.
- If a microphone or dependency is unavailable, text input still works.
