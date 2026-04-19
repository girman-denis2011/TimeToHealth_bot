# Health Reminder Telegram Bot

A polished Telegram bot that helps users build healthy habits with reminders for stretching, drinking water, walking, and taking screen breaks.

## Features

- Time-based reminders
- Inactivity-based reminders
- English and Russian UI
- Clean inline settings menu
- Adjustable frequency
- Adjustable inactivity threshold
- Active-hours scheduling
- Timezone offset support
- Reminder type toggles
- Snooze, pause, resume, test, and status commands
- Persistent user storage in JSON

## Project structure

```text
.
├── bot.py
├── storage.py
├── content.py
├── user_data.json
└── README.md
```

## Installation

```bash
pip install python-telegram-bot[job-queue]>=21,<22
```

## Setup

Create a Telegram bot with BotFather and export your token.

### Linux / macOS

```bash
export BOT_TOKEN="your_telegram_bot_token"
```

### Windows PowerShell

```powershell
$env:BOT_TOKEN="your_telegram_bot_token"
```

## Run

```bash
python bot.py
```

## Commands

- `/start` — activate the bot
- `/help` — show help
- `/settings` — open settings UI
- `/status` — show current configuration
- `/pause` — pause reminders
- `/resume` — resume reminders
- `/snooze 15` — snooze for 15 minutes
- `/test` — send a test reminder
- `/stop` — deactivate reminders

## Files

### `bot.py`
Main Telegram bot logic, handlers, menus, and reminder engine.

### `storage.py`
User settings models, enums, JSON persistence, and time helpers.

### `content.py`
Localized text, motivational quotes, and reminder activity content.

## Notes

- The inactivity mode is based on inactivity with the bot, not device-level idle detection.
- User settings are saved in `user_data.json`.
- Timezone support uses a UTC hour offset chosen by the user.

## Suggested next improvements

- Docker support
- Admin analytics
- SQLite/PostgreSQL storage
- More languages
- Recurring quiet days
- Better timezone selection via city names

## License

MIT
