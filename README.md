# CapriPet

CapriPet is a small desktop pet in the style of a tamagotchi. Capri lives in a
looping video, listens to text and voice input, and answers in a floating speech
bubble with a typewriter effect. The UI is a pixel-terminal frameless window, and
the whole desktop gets a light CRT glitch overlay while Capri is running.

## Features

- Frameless 800×540 window; drag it by the video area.
- Text input and continuous offline voice input (Vosk) with the wake word “Капри”.
- Random startup greeting and a goodbye sequence on exit.
- Auto-hide after 10 seconds of inactivity: the main window disappears with a
  fast red-pink lightning transition; speaking a command brings it back. The
  glitch overlay stays visible the whole time.
- Floating speech bubbles that appear away from the main window.
- Built-in commands: screen glitches, voice input, Google/YouTube search, Spotify,
  screen lock, power actions, local Ollama chat, desktop overlay mode, and cursor locator.
- Typo-tolerant and keyboard layout-tolerant (QWERTY / ЙЦУКЕН) command matching.
- Optional Spotify, Ollama, and Google Speech integrations.

## Requirements

- Python 3.10+
- PySide6 6.12+
- `vosk` (local offline voice recognition, default)
- `SpeechRecognition` (optional fallback for Google Web Speech: `CAPRI_VOICE_BACKEND=google`)
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
| `помощь` | `что ты умеешь?`, `что ты можешь`, `команды`, `хелп` и др. | Show all commands |
| `комплимент` | `ты красивая`, `ты прекрасна`, `ты лучшая`, `ты супер` и др. | Trigger wild glitches for 5 seconds |
| `глитч` | `глюки`, `эффекты`, `переключить глитч` и др. | Toggle glitch overlay |
| `голос` | `микрофон`, `слушать`, `запись` и др. | Toggle voice input |
| `гугл <запрос>` | `загугли`, `погугли`, `google` и др. | Search Google |
| `ютуб <запрос>` | `youtube`, `найди на ютубе` и др. | Search YouTube |
| `спотифай <запрос>` | `spotify`, `спотик`, `включи музыку` и др. | Play a Spotify track |
| `пауза` | `поставь на паузу`, `стоп`, `заткнись`, `тихо`, `pause` и др. | Pause Spotify |
| `продолжить` | `плей`, `играй`, `продолжай`, `play` и др. | Resume Spotify |
| `следующий трек` | `следующий`, `некст`, `скип`, `дальше`, `next` и др. | Next Spotify track |
| `предыдущий трек` | `предыдущий`, `прев`, `назад`, `прошлый трек`, `prev` и др. | Previous Spotify track |
| `блокировка` | `заблокировать`, `лок`, `залочь`, `lock` и др. | Lock the screen |
| `я спать` | `выключи пк`, `шатдаун`, `shutdown` и др. | Power off |
| `я гулять` | `спящий режим`, `слип`, `отдохни`, `sleep` и др. | Suspend |
| `перезагрузка` | `перезагрузи`, `рестарт`, `ребут`, `restart` и др. | Reboot |
| `слушай <запрос>` | `спроси модель`, `нейросеть`, `оллама`, `квен` и др. | Ask the local Ollama model |
| `Нормальный облик` | `нормальный вид`, `оверлей`, `убери окно`, `капри оверлей` и др. | Toggle between window and Capri overlay image (transparent, on top) |
| `где мышь` | `где курсор`, `найди мышь`, `поймай мышь`, `потерял курсор` и др. | Teleport cursor and pet to screen center |

Use `Ctrl+Q` to quit.

## Configuration

| Variable | Description |
| --- | --- |
| `CAPRI_VOICE_BACKEND` | Voice backend: `vosk` (default, offline) or `google` (online) |
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
├── controllers/
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
- Voice recognition defaults to offline local recognition with Vosk (`models/vosk-model-ru-0.42`). Google Web Speech is available via `CAPRI_VOICE_BACKEND=google` and requires internet access.
- Commands accept speech in Russian phonetics and auto-correct accidental English/Russian keyboard layout mismatches.
- If a microphone or dependency is unavailable, text input still works.
