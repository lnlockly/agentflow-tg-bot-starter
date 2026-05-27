# agentflow-tg-bot-starter

Minimal Python + aiogram 3 starter used by AgentFlow when the user brief implies a Telegram bot (`kind=tg_bot`).

## Local

```bash
cp .env.example .env
# fill BOT_TOKEN + BOT_USERNAME from @BotFather
pip install -r requirements.txt
python bot.py
```

## On the platform

The platform registers a bot via @BotFather using the owner's TG account, writes `BOT_TOKEN` to `.env`, then starts `python bot.py` inside the daemon pod. The coder agent edits `bot.py` to fit the brief — fills in `/start`, adds custom commands, wires SQLite if needed.

## Slot markers

- `<!-- SLOT:brief.start_greeting -->` — coder MUST replace the body of `cmd_start` with brief-specific copy. Gate fails if the marker is left in place after coder runs.
