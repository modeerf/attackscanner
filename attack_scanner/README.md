# Attack Scanner + Discord Bot

This project now has **two entry points** that share the same parser and SQLite database:

- a FastAPI web dashboard
- a Discord bot that can be tagged with an image or tagged with commands

## Features

### Web app

- Upload battle screenshots and parse attacker, defender, server, and date/time.
- Upload covert ops screenshots and parse the red attacker names.
- Search players and view their history.
- View top 10 attackers.
- View the alliance with the most distinct attackers.
- Manually add attacks.
- Delete attacks.

### Discord bot

- Tag the bot **with an image attachment** and it will process the image.
- Tag the bot with commands such as:
  - `@Bot stats server=78`
  - `@Bot recent limit=10 server=78`
  - `@Bot history Holash server=78 limit=10`
- Add `server=78` and `year=2026` to image posts when OCR cannot infer them.
- Include `ops` or `battle` in the post text to force the parser type, otherwise the bot auto-detects.

## Setup

1. Create a virtual environment.
2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install **Tesseract OCR** on the host machine and make sure `tesseract` is on your `PATH`.
4. In the Discord Developer Portal, enable the **Message Content Intent** for your bot, because mention-prefix commands and mention + image posts rely on message content.

## Run the web app

```bash
uvicorn app.main:app --reload --app-dir .
```

## Run the Discord bot

Set your token:

```bash
export DISCORD_BOT_TOKEN=your-token-here
```

Then start it:

```bash
python -m app.discord_bot
```

## Discord usage examples

### Scan an image

Post a message like:

```text
@AttackScanner ops server=78 year=2026
```

and attach the screenshot.

Or:

```text
@AttackScanner battle server=78
```

with an attack screenshot attached.

### Query data

```text
@AttackScanner stats server=78
@AttackScanner recent limit=10 server=78
@AttackScanner history GrumblyFeline server=78 limit=10
```

## Notes

- The Discord bot uses the same database as the web app, so anything scanned in Discord appears on the dashboard.
- Ops screenshots usually do not visibly show the defender, so those entries are stored with a blank defender.
- SQLite is fine for a starter deployment. For heavier multi-user usage, moving to PostgreSQL would be the next upgrade.
