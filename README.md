# FRIDAY AI — Your JARVIS-grade Personal Assistant for macOS

FRIDAY is a fully local, always-available AI companion for your Mac. It speaks
(real neural TTS via the Hermes voice), listens (push-to-talk or wake word),
remembers, schedules, controls your system, and answers intelligently through a
unified AI gateway.

## Features

- **Voice-first interaction** — Push-to-Talk (hold **⌥ Option + Space**), wake-word
  ("Hey Friday"), or type. Voice output via edge-tts neural voices (Hermes voice by default).
- **Real AI brain** — routes to the OmniRoute gateway (200+ models incl. free tiers)
  with a JARVIS-grade persona, memory recall, and system-aware context.
- **Proactive engine** — task nagging, agenda reminders, context-aware suggestions,
  and morning greetings.
- **System control** — open apps, scenes (focus/relax/coding/movie), volume,
  brightness, screen lock, window tiling, timers, dark mode.
- **Integration modules** — Calendar (Apple + Google), Music (Spotify/Apple Music),
  Notes (Apple Notes + local), Email (Apple Mail/Gmail), Files, Clipboard history,
  Web agent, Vision agent, Git agent, Memory (Obsidian-compatible), Smart Scheduler.
- **Holographic HUD** — animated hologram core with 6 presets (core/arc/radar/nebula/
  matrix/pulse) and 7 color themes.

## Quick Start

```bash
open "/Applications/FridayAI.app"
```

Or from source:

```bash
pip install -r requirements.txt
python3 main_app.py          # GUI window (pywebview)
python3 friday_server.py     # headless REST + SocketIO on :5050
```

## Push-to-Talk

Hold **Right Option + Space** while speaking. FRIDAY listens while you hold, then
transcribes, thinks, and replies — all hands-free. The hotkey helper lives in
`ptt_hotkey.c` and auto-launches with the server.

## Directory Layout

```
FridayAI.app/Contents/Resources/
├── main_app.py          # pywebview GUI launcher + JS bridge (60+ methods)
├── friday_server.py     # Flask + SocketIO backend (REST + realtime, port 5050)
├── brain.py             # Multi-LLM brain with routing (OmniRoute, Gemini, GPT, Claude, Grok)
├── omniroute.py         # OmniRoute gateway client
├── context_engine.py    # system context + persona for prompts
├── proactive_engine.py  # proactive suggestions & reminders
├── ptt_hotkey.c         # Carbon global-hotkey helper (push-to-talk)
├── static/              # frontend (modular HUD, 9 module views, 6 hologram presets)
└── data/                # local memory, DBs, config (git-ignored)
```

## Privacy

Everything runs locally. Your API key lives in `data/omniroute_config.json`
(git-ignored). Memory stays on-disk in `data/`. No telemetry.
