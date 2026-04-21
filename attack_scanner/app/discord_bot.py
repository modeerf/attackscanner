from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from typing import Iterable

import discord
from discord.ext import commands

from .db import (
    add_attack,
    connect,
    find_player_by_name,
    init_db,
    player_history,
    recent_attacks,
    top_alliances,
    top_attackers,
)
from .parsers import ParseError, ParsedAttackEvent, parse_battle_report, parse_ops_report

LOGGER = logging.getLogger("attack_scanner.discord")
logging.basicConfig(level=os.getenv("ATTACK_SCANNER_LOG_LEVEL", "INFO"))

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass(slots=True)
class ScanOptions:
    report_type: str = "auto"
    server_id: int | None = None
    year: int | None = None


def parse_scan_options(content: str) -> ScanOptions:
    lowered = content.lower()
    report_type = "auto"
    if re.search(r"\b(ops|covert)\b", lowered):
        report_type = "covert_ops"
    elif re.search(r"\b(attack|battle)\b", lowered):
        report_type = "battle"

    server_match = re.search(r"(?:server|srv|s)\s*[:=]\s*(\d+)", lowered)
    year_match = re.search(r"(?:year|y)\s*[:=]\s*(\d{4})", lowered)
    return ScanOptions(
        report_type=report_type,
        server_id=int(server_match.group(1)) if server_match else None,
        year=int(year_match.group(1)) if year_match else None,
    )


def build_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.guilds = True
    intents.messages = True
    intents.message_content = True

    bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents, help_command=commands.DefaultHelpCommand())

    @bot.event
    async def on_ready() -> None:
        init_db()
        LOGGER.info("Logged in as %s", bot.user)

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return

        mentioned = bot.user is not None and bot.user in message.mentions
        attachments = [a for a in message.attachments if is_image_attachment(a)]

        if mentioned and attachments:
            try:
                await handle_scan_message(message, attachments)
            except Exception:
                LOGGER.exception("Failed to process scan message")
                await message.reply("I hit an unexpected error while processing that image.")

        await bot.process_commands(message)

    @bot.command(name="stats", help="Show top attackers and top alliance. Example: @Bot stats server=78")
    async def stats_command(ctx: commands.Context, *, args: str = "") -> None:
        server_id = extract_named_int(args, "server")
        with connect() as conn:
            attackers = top_attackers(conn, server_id=server_id, limit=10)
            alliances = top_alliances(conn, server_id=server_id, limit=10)
        lines = []
        if alliances:
            top = alliances[0]
            lines.append(f"Top alliance: **[{top['attacker_alliance_tag']}]** with **{top['unique_attackers']}** attacker(s) and **{top['attack_count']}** recorded attack(s).")
        if attackers:
            lines.append("Top attackers:")
            for idx, row in enumerate(attackers, start=1):
                tag = f"[{row['attacker_alliance_tag']}] " if row['attacker_alliance_tag'] else ""
                lines.append(f"{idx}. {tag}{row['attacker_name']} — {row['attack_count']} total ({row['battle_count']} battle / {row['covert_ops_count']} ops)")
        if not lines:
            lines = ["No attack data recorded yet."]
        await ctx.reply("\n".join(lines))

    @bot.command(name="recent", help="Show recent attacks. Example: @Bot recent limit=10 server=78")
    async def recent_command(ctx: commands.Context, *, args: str = "") -> None:
        server_id = extract_named_int(args, "server")
        limit = extract_named_int(args, "limit") or 10
        with connect() as conn:
            rows = recent_attacks(conn, limit=min(max(limit, 1), 20), server_id=server_id)
        if not rows:
            await ctx.reply("No recent attacks found.")
            return
        lines = []
        for row in rows:
            when = row["occurred_at_text"] or row["occurred_at"] or row["created_at"]
            target = row["defender_name"] or "—"
            lines.append(f"#{row['id']} [{row['attack_type']}] {row['attacker_name']} -> {target} @ {when}")
        await ctx.reply("\n".join(lines))

    @bot.command(name="history", help="Show a player's recent history. Example: @Bot history Holash server=78 limit=10")
    async def history_command(ctx: commands.Context, *, args: str) -> None:
        server_id = extract_named_int(args, "server")
        limit = extract_named_int(args, "limit") or 10
        player_name = strip_named_ints(args, {"server", "limit"}).strip()
        if not player_name:
            await ctx.reply("Usage: @Bot history <player name> [server=78] [limit=10]")
            return
        with connect() as conn:
            player = find_player_by_name(conn, player_name, server_id=server_id)
            if not player:
                await ctx.reply(f"Player not found: {player_name}")
                return
            rows = player_history(conn, player["id"], limit=min(max(limit, 1), 20))
        if not rows:
            await ctx.reply(f"No history recorded for {player['name']}.")
            return
        lines = [f"History for **{player['name']}** (server {player['server_id'] or '—'}):"]
        for row in rows:
            when = row["occurred_at_text"] or row["occurred_at"] or row["created_at"]
            if row["attacker_player_id"] == player["id"]:
                other = row["defender_name"] or "—"
                lines.append(f"#{row['id']} ATTACKED {other} [{row['attack_type']}] @ {when}")
            else:
                lines.append(f"#{row['id']} DEFENDED vs {row['attacker_name']} [{row['attack_type']}] @ {when}")
        await ctx.reply("\n".join(lines))

    @bot.command(name="dashboard", help="Alias for stats")
    async def dashboard_command(ctx: commands.Context, *, args: str = "") -> None:
        await ctx.invoke(stats_command, args=args)

    return bot


def is_image_attachment(attachment: discord.Attachment) -> bool:
    content_type = (attachment.content_type or "").lower()
    if content_type.startswith("image/"):
        return True
    filename = (attachment.filename or "").lower()
    return any(filename.endswith(ext) for ext in IMAGE_EXTENSIONS)


def extract_named_int(text: str, key: str) -> int | None:
    match = re.search(rf"(?:^|\s){re.escape(key)}\s*=\s*(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def strip_named_ints(text: str, keys: set[str]) -> str:
    for key in keys:
        text = re.sub(rf"(?:^|\s){re.escape(key)}\s*=\s*\d+", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text)


def classify_report(data: bytes, options: ScanOptions) -> list[ParsedAttackEvent]:
    if options.report_type == "battle":
        return [parse_battle_report(data, default_year=options.year, fallback_server_id=options.server_id)]
    if options.report_type == "covert_ops":
        return parse_ops_report(data, default_year=options.year, fallback_server_id=options.server_id)

    # auto-detect
    try:
        return [parse_battle_report(data, default_year=options.year, fallback_server_id=options.server_id)]
    except ParseError:
        return parse_ops_report(data, default_year=options.year, fallback_server_id=options.server_id)


async def handle_scan_message(message: discord.Message, attachments: list[discord.Attachment]) -> None:
    options = parse_scan_options(message.content)
    saved_lines: list[str] = []
    error_lines: list[str] = []

    with connect() as conn:
        for attachment in attachments:
            try:
                raw = await attachment.read()
                events = await asyncio.to_thread(classify_report, raw, options)
                created_ids: list[int] = []
                for event in events:
                    attack_id = add_attack(
                        conn,
                        attack_type=event.attack_type,
                        attacker_name=event.attacker_name,
                        attacker_alliance_tag=event.attacker_alliance_tag,
                        defender_name=event.defender_name,
                        defender_alliance_tag=event.defender_alliance_tag,
                        server_id=event.server_id,
                        occurred_at=event.occurred_at,
                        occurred_at_text=event.occurred_at_text,
                        source_filename=attachment.filename,
                        source_kind="discord",
                        notes=event.notes,
                        parser_confidence=event.parser_confidence,
                        raw_parse_json=event.to_dict(),
                    )
                    created_ids.append(attack_id)
                names = ", ".join(event.attacker_name for event in events)
                saved_lines.append(f"{attachment.filename}: saved {len(created_ids)} event(s) for {names} (IDs: {', '.join(map(str, created_ids))})")
            except Exception as exc:
                error_lines.append(f"{attachment.filename}: {exc}")

    chunks = ["Processed your image upload."]
    if saved_lines:
        chunks.append("Saved:\n" + "\n".join(f"- {line}" for line in saved_lines))
    if error_lines:
        chunks.append("Errors:\n" + "\n".join(f"- {line}" for line in error_lines))
    chunks.append("Commands: `@Bot stats`, `@Bot recent limit=10`, `@Bot history Holash server=78`")
    await message.reply("\n\n".join(chunks))


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")
    init_db()
    build_bot().run(token)


if __name__ == "__main__":
    main()
