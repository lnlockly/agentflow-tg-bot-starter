# agentflow-tg-bot-starter

Python + aiogram 3 starter used by AgentFlow when the user brief implies a Telegram bot (`kind=tg_bot`). Ships with SQLite-backed user tracking and a creator-only admin panel.

## Local

```bash
cp .env.example .env
# fill BOT_TOKEN + BOT_USERNAME from @BotFather, OWNER_TG_ID from your Telegram account
pip install -r requirements.txt
python bot.py
```

## On the platform

The platform registers a bot via @BotFather using the owner's TG account, writes `BOT_TOKEN` + `OWNER_TG_ID` to `.env`, then starts `python bot.py` inside the daemon pod. The coder agent edits `bot.py` (and adds extra handlers / tables) to fit the brief — fills in `/start`, customises `/book` capture, adds domain commands.

## Env vars

| Var | Who sets it | Purpose |
|---|---|---|
| `BOT_TOKEN` | Platform (`auto-bot.ts`) | aiogram authentication |
| `BOT_USERNAME` | Platform | Cosmetic — used in startup log |
| `OWNER_TG_ID` | Platform (lookup `tg_links` for the project owner) | Gate for `/admin` — only this Telegram user ID can open the panel |
| `BOT_DB_PATH` | Optional (defaults to `bot.db`) | SQLite path; the supervisor mounts `/workspace/bot.db` |

## Files

| Path | Role |
|---|---|
| `bot.py` | Dispatcher + user-facing handlers (`/start`, `/help`, `/book`) |
| `admin.py` | Owner-only `/admin` panel router (stats, recent leads, broadcast) |
| `db.py` | SQLite schema + helpers (`users`, `bookings`, `broadcasts`) |
| `middleware.py` | Outer middleware that upserts every interacting user |
| `tests/` | pytest cases — `OWNER_TG_ID` gate, broadcast, stats |

## Admin panel (`/admin`)

Available only to the Telegram account whose ID matches `OWNER_TG_ID`. Anyone else gets `Доступ только для владельца.` and no menu. The panel is an inline-keyboard with four entries:

- **📊 Статистика** — aggregate counts: users total, bookings total / 24h / 7d.
- **📋 Последние 10 заявок** — most recent rows from `bookings` with timestamps and the originating user.
- **📣 Рассылка** — collects one message of text, fans it out to every row in `users` (skips the owner to avoid echo), records the broadcast in the `broadcasts` table.
- **❌ Закрыть** — deletes the menu message.

The broadcast worker rate-limits at ~25 msg/s, well below Telegram's 30 msg/s ceiling, and silently skips users who blocked the bot (TelegramForbiddenError) or have stale records (TelegramBadRequest).

## What AgentFlow's coder will generate on top

- Brief-derived `/start` body replacing the `SLOT:brief.start_greeting` placeholder.
- Brief-specific `/book` capture flow (multi-step FSM for date + slot + contact, instead of the one-shot stub).
- Extra commands (`/menu`, `/price`, `/contact`, …) matching the business vertical.
- Optional extra columns on `bookings` for domain payload.

## Slot markers

- `<!-- SLOT:brief.start_greeting -->` — coder MUST replace the body of `cmd_start` with brief-specific copy. Gate fails if the marker is left in place after the coder runs.

## Tests

```bash
pip install -r requirements.txt pytest pytest-asyncio
pytest -q
```

Tests cover the `/admin` gate (non-owner blocked, owner served), broadcast fan-out, and stats counters. They run against an in-memory SQLite file (overridden via `BOT_DB_PATH`).
