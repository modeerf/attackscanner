# Last Assylum: Plague Violation Tracker + Discord Bot

This project now has **two entry points** that share the same parser and SQLite database:

- a FastAPI web dashboard
- a Discord bot that can be tagged with an image or tagged with commands

## Features

### Web app

- Upload battle screenshots and parse attacker, defender, server, and date/time.
- Upload covert ops screenshots and parse the red attacker names, with an optional victim alliance.
- Upload caravan attack screenshots and parse the top caravan owner as the victim and battle-history entries as attackers.
- Search players and view their history.
- View top 10 attackers.
- View the alliance with the most distinct attackers.
- View alliance stats, including top attacking alliances, most attacked alliances, alliance-vs-alliance matchups, and alliance member activity.
- Click an attack ID to view its details and submitted image.
- Read the in-app user manual at `/manual`.
- Manually add attacks.
- Delete attacks with the moderator password. Deleted records are soft-deleted and can be reviewed at `/admin/deleted`.
- Manage the hidden server 78 alliance list at `/admin/server78-alliances`; listed alliances display green, all others display red.
- Automatically soft-delete records older than 30 days using the parsed event time, or creation time if no event time was parsed.

### Discord bot

- Tag the bot **with an image attachment** and it will process the image.
- Tag the bot with commands such as:
  - `@Bot stats server=78`
  - `@Bot recent limit=10 server=78`
  - `@Bot history Holash server=78 limit=10`
- Add `server=78` to override the default server for a Discord message.
- Add `year=2026` to override the current calendar year if OCR cannot infer the year.
- Include `ops`, `battle`, or `caravan` in the post text to force the parser type, otherwise the bot auto-detects.
- For ops screenshots, add `victim=AVL`, `victim_alliance=AVL`, or `defender_alliance=AVL` to record the victim alliance.
- After a successful Server 78 image scan, the bot alerts each offending attacker alliance that is on the managed Server 78 alliance list. If the Discord server has a role named `AVL` or `[AVL]`, the bot mentions that role; otherwise it prints the alliance tag.

## Setup

1. Create a virtual environment.
2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install **Tesseract OCR** on the host machine and make sure `tesseract` is on your `PATH`. For non-English screenshots, install the matching Tesseract language packs. The parser will use installed `eng`, `rus`, and `spa` language data when available.
4. In the Discord Developer Portal, enable the **Message Content Intent** for your bot, because mention-prefix commands and mention + image posts rely on message content.

## Run the web app

```bash
uvicorn app.main:app --reload --app-dir .
```

## Run the Discord bot

Set your token:

```bash
export DISCORD_BOT_TOKEN=your-token-here
export ATTACK_SCANNER_DEFAULT_SERVER=78
```

Then start it:

```bash
python -m app.discord_bot
```

## Discord usage examples

### Scan an image

Post a message like:

```text
@LastAssylumTracker ops server=78 year=2026
```

and attach the screenshot.

For a covert ops report where the victim alliance is AVL:

```text
@LastAssylumTracker ops server=78 victim=AVL
```

Or:

```text
@LastAssylumTracker battle server=78
```

with an attack screenshot attached.

For a caravan attack report:

```text
@LastAssylumTracker caravan server=78
```

with a caravan screenshot attached. The top player is stored as the victim, and the battle-history entries are stored as attackers.

### Query data

```text
@LastAssylumTracker stats server=78
@LastAssylumTracker recent limit=10 server=78
@LastAssylumTracker history GrumblyFeline server=78 limit=10
```

If `ATTACK_SCANNER_DEFAULT_SERVER` is set, you can omit `server=78` from Discord scans and commands. Discord image scans default `year` to the current calendar year unless you include `year=YYYY`.

## Notes

- The Discord bot uses the same database as the web app, so anything scanned in Discord appears on the dashboard.
- Records older than 30 days are hidden from normal views by a startup retention pass. Their database rows and images are retained for review at `/admin/deleted`.
- Ops screenshots usually do not visibly show the defender, so those entries are stored with a blank defender.
- If OCR added a stray leading `J` to attacker names, preview repairs with `python -m app.cleanup_j_prefixes`, then apply them with `python -m app.cleanup_j_prefixes --apply`.
- SQLite is fine for a starter deployment. For heavier multi-user usage, moving to PostgreSQL would be the next upgrade.
