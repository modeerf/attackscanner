from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

import discord
from discord.ext import commands

from .db import (
    add_attack,
    add_image_submission,
    connect,
    find_player_by_name,
    get_discord_user_language,
    get_image_submission,
    init_db,
    managed_alliance_tags,
    player_history,
    recent_attacks,
    set_discord_user_language,
    top_alliances,
    top_attackers,
    top_attacked_alliances,
)
from .parsers import ParseError, ParsedAttackEvent, parse_battle_report, parse_caravan_report, parse_ops_report

LOGGER = logging.getLogger("attack_scanner.discord")
logging.basicConfig(level=os.getenv("ATTACK_SCANNER_LOG_LEVEL", "INFO"))

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LANGUAGE = "en-US"
SUPPORTED_LANGUAGES = ("en-US", "en-AU", "fr", "es", "pt", "ru")
LANGUAGE_LABELS = {
    "en-US": "English (US)",
    "en-AU": "English (Australia)",
    "fr": "Francais",
    "es": "Espanol",
    "pt": "Portugues",
    "ru": "Русский",
}

ENGLISH_TEXT = {
    "missing_detail": "I need a little more detail for that command. Try `@Bot stats`, `@Bot recent limit=10`, or `@Bot history PlayerName`.",
    "command_failed": "I could not run that command: {error}",
    "scan_unexpected_error": "I hit an unexpected error while processing that image.",
    "online_hint": "I am online. Try `@Bot stats`, `@Bot recent limit=10`, `@Bot history PlayerName`, or mention me with an image plus `battle`, `ops victim=AVL`, or `caravan`.",
    "pong": "pong",
    "scanhelp": "\n".join(
        [
            "Mention me with one or more image attachments to scan them.",
            "Use `battle` for battle reports, `ops` for covert ops reports, or `caravan` for caravan attacks.",
            "Ops scans can include a victim alliance: `victim=AVL`, `victim_alliance=AVL`, or `defender_alliance=AVL`.",
            "Examples: `@Bot ops victim=AVL server=78 year=2026`, `@Bot caravan server=78`, or `@Bot battle server=78`.",
        ]
    ),
    "language_current": "Your bot language is **{language}**.",
    "language_updated": "Bot language set to **{language}**.",
    "language_usage": "Usage: `@Bot language auto|en-US|en-AU|fr|es|pt|ru`. Languages: {languages}.",
    "top_alliance": "Top alliance: **[{tag}]** with **{attackers}** attacker(s) and **{attacks}** recorded attack(s).",
    "most_attacked": "Most attacked alliance: **[{tag}]** with **{attacks}** attack(s) received.",
    "top_attackers": "Top attackers:",
    "attacker_row": "{idx}. {tag}{name} - {total} total ({battle} battle / {ops} ops)",
    "no_attack_data": "No attack data recorded yet.",
    "no_recent": "No recent attacks found.",
    "history_usage": "Usage: @Bot history <player name> [server=78] [limit=10]",
    "player_not_found": "Player not found: {name}",
    "no_history": "No history recorded for {name}.",
    "history_header": "History for **{name}** (server {server}):",
    "history_attacked": "#{id} ATTACKED {other} [{type}] @ {when}",
    "history_defended": "#{id} DEFENDED vs {other} [{type}] @ {when}",
    "duplicate_image": "{filename}: this image has already been submitted.",
    "saved_line": "{filename}: saved {count} event(s) for {names} (IDs: {ids})",
    "processed_upload": "Processed your image upload.",
    "saved_header": "Saved:",
    "alerts_header": "Alliance alerts:",
    "errors_header": "Errors:",
    "commands_hint": "Commands: `@Bot stats`, `@Bot recent limit=10`, `@Bot history Holash server=78`. Image scans can include `battle`, `ops victim=AVL`, or `caravan`.",
    "violation_recorded": "{target}: violation recorded from {source} (attack ID(s): {ids}).",
    "pending": "pending",
    "image": "image",
}

DISCORD_TEXT: dict[str, dict[str, str]] = {
    DEFAULT_LANGUAGE: ENGLISH_TEXT,
    "en-AU": ENGLISH_TEXT,
    "fr": {
        "missing_detail": "Il me faut un peu plus de details pour cette commande. Essayez `@Bot stats`, `@Bot recent limit=10` ou `@Bot history PlayerName`.",
        "command_failed": "Je n'ai pas pu executer cette commande : {error}",
        "scan_unexpected_error": "J'ai rencontre une erreur inattendue pendant le traitement de cette image.",
        "online_hint": "Je suis en ligne. Essayez `@Bot stats`, `@Bot recent limit=10`, `@Bot history PlayerName`, ou mentionnez-moi avec une image et `battle`, `ops victim=AVL` ou `caravan`.",
        "pong": "pong",
        "scanhelp": "\n".join(
            [
                "Mentionnez-moi avec une ou plusieurs images jointes pour les analyser.",
                "Utilisez `battle` pour les rapports de bataille, `ops` pour les operations secretes ou `caravan` pour les attaques de caravane.",
                "Les analyses ops peuvent inclure une alliance victime : `victim=AVL`, `victim_alliance=AVL` ou `defender_alliance=AVL`.",
                "Exemples : `@Bot ops victim=AVL server=78 year=2026`, `@Bot caravan server=78` ou `@Bot battle server=78`.",
            ]
        ),
        "language_current": "Votre langue du bot est **{language}**.",
        "language_updated": "Langue du bot definie sur **{language}**.",
        "language_usage": "Utilisation : `@Bot language auto|en-US|en-AU|fr|es|pt|ru`. Langues : {languages}.",
        "top_alliance": "Meilleure alliance : **[{tag}]** avec **{attackers}** attaquant(s) et **{attacks}** attaque(s) enregistree(s).",
        "most_attacked": "Alliance la plus attaquee : **[{tag}]** avec **{attacks}** attaque(s) recue(s).",
        "top_attackers": "Meilleurs attaquants :",
        "attacker_row": "{idx}. {tag}{name} - {total} total ({battle} bataille / {ops} ops)",
        "no_attack_data": "Aucune donnee d'attaque enregistree pour l'instant.",
        "no_recent": "Aucune attaque recente trouvee.",
        "history_usage": "Utilisation : @Bot history <nom du joueur> [server=78] [limit=10]",
        "player_not_found": "Joueur introuvable : {name}",
        "no_history": "Aucun historique enregistre pour {name}.",
        "history_header": "Historique de **{name}** (serveur {server}) :",
        "history_attacked": "#{id} A ATTAQUE {other} [{type}] @ {when}",
        "history_defended": "#{id} A DEFENDU contre {other} [{type}] @ {when}",
        "duplicate_image": "{filename} : cette image a deja ete soumise.",
        "saved_line": "{filename} : {count} evenement(s) enregistre(s) pour {names} (IDs : {ids})",
        "processed_upload": "Image importee traitee.",
        "saved_header": "Enregistre :",
        "alerts_header": "Alertes d'alliance :",
        "errors_header": "Erreurs :",
        "commands_hint": "Commandes : `@Bot stats`, `@Bot recent limit=10`, `@Bot history Holash server=78`. Les analyses d'image peuvent inclure `battle`, `ops victim=AVL` ou `caravan`.",
        "violation_recorded": "{target} : violation enregistree depuis {source} (ID(s) d'attaque : {ids}).",
        "pending": "en attente",
        "image": "image",
    },
    "es": {
        "missing_detail": "Necesito un poco mas de detalle para ese comando. Prueba `@Bot stats`, `@Bot recent limit=10` o `@Bot history PlayerName`.",
        "command_failed": "No pude ejecutar ese comando: {error}",
        "scan_unexpected_error": "Tuve un error inesperado al procesar esa imagen.",
        "online_hint": "Estoy en linea. Prueba `@Bot stats`, `@Bot recent limit=10`, `@Bot history PlayerName`, o mencioname con una imagen y `battle`, `ops victim=AVL` o `caravan`.",
        "pong": "pong",
        "scanhelp": "\n".join(
            [
                "Mencioname con una o mas imagenes adjuntas para escanearlas.",
                "Usa `battle` para informes de batalla, `ops` para operaciones encubiertas o `caravan` para ataques de caravana.",
                "Los escaneos ops pueden incluir una alianza victima: `victim=AVL`, `victim_alliance=AVL` o `defender_alliance=AVL`.",
                "Ejemplos: `@Bot ops victim=AVL server=78 year=2026`, `@Bot caravan server=78` o `@Bot battle server=78`.",
            ]
        ),
        "language_current": "Tu idioma del bot es **{language}**.",
        "language_updated": "Idioma del bot configurado como **{language}**.",
        "language_usage": "Uso: `@Bot language auto|en-US|en-AU|fr|es|pt|ru`. Idiomas: {languages}.",
        "top_alliance": "Alianza principal: **[{tag}]** con **{attackers}** atacante(s) y **{attacks}** ataque(s) registrado(s).",
        "most_attacked": "Alianza mas atacada: **[{tag}]** con **{attacks}** ataque(s) recibido(s).",
        "top_attackers": "Principales atacantes:",
        "attacker_row": "{idx}. {tag}{name} - {total} total ({battle} batalla / {ops} ops)",
        "no_attack_data": "Aun no hay datos de ataques registrados.",
        "no_recent": "No se encontraron ataques recientes.",
        "history_usage": "Uso: @Bot history <nombre del jugador> [server=78] [limit=10]",
        "player_not_found": "Jugador no encontrado: {name}",
        "no_history": "No hay historial registrado para {name}.",
        "history_header": "Historial de **{name}** (servidor {server}):",
        "history_attacked": "#{id} ATACO a {other} [{type}] @ {when}",
        "history_defended": "#{id} DEFENDIO contra {other} [{type}] @ {when}",
        "duplicate_image": "{filename}: esta imagen ya fue enviada.",
        "saved_line": "{filename}: se guardaron {count} evento(s) para {names} (IDs: {ids})",
        "processed_upload": "Procesada tu carga de imagen.",
        "saved_header": "Guardado:",
        "alerts_header": "Alertas de alianza:",
        "errors_header": "Errores:",
        "commands_hint": "Comandos: `@Bot stats`, `@Bot recent limit=10`, `@Bot history Holash server=78`. Los escaneos de imagen pueden incluir `battle`, `ops victim=AVL` o `caravan`.",
        "violation_recorded": "{target}: violacion registrada desde {source} (ID(s) de ataque: {ids}).",
        "pending": "pendiente",
        "image": "imagen",
    },
    "pt": {
        "missing_detail": "Preciso de um pouco mais de detalhe para esse comando. Tente `@Bot stats`, `@Bot recent limit=10` ou `@Bot history PlayerName`.",
        "command_failed": "Nao consegui executar esse comando: {error}",
        "scan_unexpected_error": "Encontrei um erro inesperado ao processar essa imagem.",
        "online_hint": "Estou online. Tente `@Bot stats`, `@Bot recent limit=10`, `@Bot history PlayerName`, ou me mencione com uma imagem e `battle`, `ops victim=AVL` ou `caravan`.",
        "pong": "pong",
        "scanhelp": "\n".join(
            [
                "Mencione-me com uma ou mais imagens anexadas para escanea-las.",
                "Use `battle` para relatorios de batalha, `ops` para operacoes secretas ou `caravan` para ataques de caravana.",
                "Escaneamentos ops podem incluir uma alianca vitima: `victim=AVL`, `victim_alliance=AVL` ou `defender_alliance=AVL`.",
                "Exemplos: `@Bot ops victim=AVL server=78 year=2026`, `@Bot caravan server=78` ou `@Bot battle server=78`.",
            ]
        ),
        "language_current": "Seu idioma do bot e **{language}**.",
        "language_updated": "Idioma do bot definido como **{language}**.",
        "language_usage": "Uso: `@Bot language auto|en-US|en-AU|fr|es|pt|ru`. Idiomas: {languages}.",
        "top_alliance": "Principal alianca: **[{tag}]** com **{attackers}** atacante(s) e **{attacks}** ataque(s) registrado(s).",
        "most_attacked": "Alianca mais atacada: **[{tag}]** com **{attacks}** ataque(s) recebido(s).",
        "top_attackers": "Principais atacantes:",
        "attacker_row": "{idx}. {tag}{name} - {total} total ({battle} batalha / {ops} ops)",
        "no_attack_data": "Ainda nao ha dados de ataques registrados.",
        "no_recent": "Nenhum ataque recente encontrado.",
        "history_usage": "Uso: @Bot history <nome do jogador> [server=78] [limit=10]",
        "player_not_found": "Jogador nao encontrado: {name}",
        "no_history": "Nenhum historico registrado para {name}.",
        "history_header": "Historico de **{name}** (servidor {server}):",
        "history_attacked": "#{id} ATACOU {other} [{type}] @ {when}",
        "history_defended": "#{id} DEFENDEU contra {other} [{type}] @ {when}",
        "duplicate_image": "{filename}: esta imagem ja foi enviada.",
        "saved_line": "{filename}: {count} evento(s) salvo(s) para {names} (IDs: {ids})",
        "processed_upload": "Upload da imagem processado.",
        "saved_header": "Salvo:",
        "alerts_header": "Alertas de alianca:",
        "errors_header": "Erros:",
        "commands_hint": "Comandos: `@Bot stats`, `@Bot recent limit=10`, `@Bot history Holash server=78`. Escaneamentos de imagem podem incluir `battle`, `ops victim=AVL` ou `caravan`.",
        "violation_recorded": "{target}: violacao registrada de {source} (ID(s) de ataque: {ids}).",
        "pending": "pendente",
        "image": "imagem",
    },
    "ru": {
        "missing_detail": "Мне нужно чуть больше деталей для этой команды. Попробуйте `@Bot stats`, `@Bot recent limit=10` или `@Bot history PlayerName`.",
        "command_failed": "Не удалось выполнить команду: {error}",
        "scan_unexpected_error": "Произошла ошибка при обработке этого изображения.",
        "online_hint": "Я онлайн. Попробуйте `@Bot stats`, `@Bot recent limit=10`, `@Bot history PlayerName`, или упомяните меня с изображением и `battle`, `ops victim=AVL` или `caravan`.",
        "pong": "понг",
        "scanhelp": "\n".join(
            [
                "Упомяните меня и прикрепите одно или несколько изображений для сканирования.",
                "Используйте `battle` для боевых отчетов, `ops` для тайных операций или `caravan` для атак караванов.",
                "Для ops можно указать альянс жертвы: `victim=AVL`, `victim_alliance=AVL` или `defender_alliance=AVL`.",
                "Примеры: `@Bot ops victim=AVL server=78 year=2026`, `@Bot caravan server=78` или `@Bot battle server=78`.",
            ]
        ),
        "language_current": "Ваш язык бота: **{language}**.",
        "language_updated": "Язык бота установлен: **{language}**.",
        "language_usage": "Использование: `@Bot language auto|en-US|en-AU|fr|es|pt|ru`. Языки: {languages}.",
        "top_alliance": "Главный альянс: **[{tag}]** с **{attackers}** атакующим(и) и **{attacks}** записанными атак(ами).",
        "most_attacked": "Самый атакуемый альянс: **[{tag}]** с **{attacks}** полученными атак(ами).",
        "top_attackers": "Главные атакующие:",
        "attacker_row": "{idx}. {tag}{name} - всего {total} ({battle} бой / {ops} ops)",
        "no_attack_data": "Данных атак пока нет.",
        "no_recent": "Недавние атаки не найдены.",
        "history_usage": "Использование: @Bot history <имя игрока> [server=78] [limit=10]",
        "player_not_found": "Игрок не найден: {name}",
        "no_history": "История для {name} не записана.",
        "history_header": "История для **{name}** (сервер {server}):",
        "history_attacked": "#{id} АТАКОВАЛ {other} [{type}] @ {when}",
        "history_defended": "#{id} ЗАЩИЩАЛСЯ против {other} [{type}] @ {when}",
        "duplicate_image": "{filename}: это изображение уже было отправлено.",
        "saved_line": "{filename}: сохранено {count} событ(ий) для {names} (ID: {ids})",
        "processed_upload": "Загрузка изображения обработана.",
        "saved_header": "Сохранено:",
        "alerts_header": "Оповещения альянсов:",
        "errors_header": "Ошибки:",
        "commands_hint": "Команды: `@Bot stats`, `@Bot recent limit=10`, `@Bot history Holash server=78`. Сканирование изображений может включать `battle`, `ops victim=AVL` или `caravan`.",
        "violation_recorded": "{target}: нарушение записано из {source} (ID атак: {ids}).",
        "pending": "ожидает",
        "image": "изображение",
    },
}


def normalize_language(raw: object | None) -> str:
    value = str(raw or "").strip().replace("_", "-").lower()
    if value == "en-au":
        return "en-AU"
    if value in {"en", "en-us", "english", "us"}:
        return "en-US"
    if value in {"au", "australian", "australia", "en-australia"}:
        return "en-AU"
    if value.startswith("fr") or value in {"french", "francais"}:
        return "fr"
    if value.startswith("es") or value in {"spanish", "espanol"}:
        return "es"
    if value.startswith("pt") or value in {"portuguese", "portugues"}:
        return "pt"
    if value.startswith("ru") or value in {"russian", "russkiy", "russkii", "русский"}:
        return "ru"
    return DEFAULT_LANGUAGE


def is_supported_language(raw: object | None) -> bool:
    value = str(raw or "").strip().replace("_", "-").lower()
    if value in {"en", "en-us", "english", "us", "en-au", "au", "australian", "australia", "en-australia"}:
        return True
    if value.startswith("fr") or value in {"french", "francais"}:
        return True
    if value.startswith("es") or value in {"spanish", "espanol"}:
        return True
    if value.startswith("pt") or value in {"portuguese", "portugues"}:
        return True
    if value.startswith("ru") or value in {"russian", "russkiy", "russkii", "русский"}:
        return True
    return False


def detected_discord_language(source: commands.Context | discord.Message) -> str:
    locale = None
    interaction = getattr(source, "interaction", None)
    if interaction is not None:
        locale = getattr(interaction, "locale", None)
    if locale is None:
        guild = getattr(source, "guild", None)
        if guild is not None:
            locale = getattr(guild, "preferred_locale", None)
    return normalize_language(locale)


def language_for_user(conn: sqlite3.Connection, user_id: int | str, source: commands.Context | discord.Message) -> str:
    stored = get_discord_user_language(conn, user_id)
    if stored:
        return normalize_language(stored)
    detected = detected_discord_language(source)
    set_discord_user_language(conn, user_id, detected)
    return detected


def t(lang_code: str, key: str, **values: object) -> str:
    template = DISCORD_TEXT.get(lang_code, {}).get(key) or DISCORD_TEXT.get(DEFAULT_LANGUAGE, {}).get(key) or ENGLISH_TEXT[key]
    return template.format(**values)


def language_list() -> str:
    return "`auto` (Discord), " + ", ".join(f"`{code}` ({label})" for code, label in LANGUAGE_LABELS.items())


@dataclass(slots=True)
class ScanOptions:
    report_type: str = "auto"
    server_id: int | None = None
    year: int | None = None
    victim_alliance_tag: str | None = None


def parse_scan_options(content: str) -> ScanOptions:
    lowered = content.lower()
    report_type = "auto"
    if re.search(r"\b(caravan|trade|merchant)\b", lowered):
        report_type = "caravan"
    elif re.search(r"\b(ops|covert)\b", lowered):
        report_type = "covert_ops"
    elif re.search(r"\b(attack|battle)\b", lowered):
        report_type = "battle"

    server_match = re.search(r"(?:server|srv|s)\s*[:=]\s*(\d+)", lowered)
    year_match = re.search(r"(?:year|y)\s*[:=]\s*(\d{4})", lowered)
    victim_match = re.search(
        r"(?:victim_alliance|victim|defender_alliance)\s*[:=]\s*(\[[^\]\s]+\]|[^\s]+)",
        content,
        re.IGNORECASE,
    )
    return ScanOptions(
        report_type=report_type,
        server_id=int(server_match.group(1)) if server_match else default_server_id(),
        year=int(year_match.group(1)) if year_match else datetime.now().year,
        victim_alliance_tag=normalize_alliance_option(victim_match.group(1)) if victim_match else None,
    )


def default_server_id() -> int | None:
    raw = os.getenv("ATTACK_SCANNER_DEFAULT_SERVER")
    if not raw:
        return None
    try:
        return int(raw.strip())
    except ValueError:
        LOGGER.warning("Ignoring invalid ATTACK_SCANNER_DEFAULT_SERVER=%r", raw)
        return None


def normalize_alliance_option(raw: str | None) -> str | None:
    value = (raw or "").strip().strip(",.;")
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip()
    return value or None


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
    async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
        with connect() as conn:
            lang = language_for_user(conn, ctx.author.id, ctx)
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(t(lang, "missing_detail"))
            return
        LOGGER.exception("Discord command failed", exc_info=error)
        await ctx.reply(t(lang, "command_failed", error=error))

    @bot.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot:
            return

        mentioned = bot.user is not None and bot.user in message.mentions
        attachments = [a for a in message.attachments if is_image_attachment(a)]
        context = await bot.get_context(message)

        if mentioned and attachments:
            try:
                await handle_scan_message(message, attachments)
            except Exception:
                LOGGER.exception("Failed to process scan message")
                with connect() as conn:
                    lang = language_for_user(conn, message.author.id, message)
                await message.reply(t(lang, "scan_unexpected_error"))

        if mentioned and not attachments and not context.valid:
            with connect() as conn:
                lang = language_for_user(conn, message.author.id, message)
            await message.reply(t(lang, "online_hint"))
            return

        await bot.process_commands(message)

    @bot.command(name="ping", help="Check whether the bot is online.")
    async def ping_command(ctx: commands.Context) -> None:
        with connect() as conn:
            lang = language_for_user(conn, ctx.author.id, ctx)
        await ctx.reply(t(lang, "pong"))

    @bot.command(name="scanhelp", help="Show image scan options, including ops victim alliance.")
    async def scanhelp_command(ctx: commands.Context) -> None:
        with connect() as conn:
            lang = language_for_user(conn, ctx.author.id, ctx)
        await ctx.reply(t(lang, "scanhelp"))

    @bot.command(name="language", aliases=["lang", "locale", "langue", "idioma", "yazyk", "язык"], help="Set your bot language. Example: @Bot language ru")
    async def language_command(ctx: commands.Context, language: str | None = None) -> None:
        with connect() as conn:
            current = language_for_user(conn, ctx.author.id, ctx)
            if language is None:
                await ctx.reply(t(current, "language_current", language=LANGUAGE_LABELS[current]))
                return
            if language.strip().casefold() == "auto":
                lang = detected_discord_language(ctx)
                set_discord_user_language(conn, ctx.author.id, lang)
                await ctx.reply(t(lang, "language_updated", language=LANGUAGE_LABELS[lang]))
                return
            if not is_supported_language(language):
                await ctx.reply(t(current, "language_usage", languages=language_list()))
                return
            lang = normalize_language(language)
            set_discord_user_language(conn, ctx.author.id, lang)
        await ctx.reply(t(lang, "language_updated", language=LANGUAGE_LABELS[lang]))

    @bot.command(name="stats", help="Show top attackers and top alliance. Example: @Bot stats server=78")
    async def stats_command(ctx: commands.Context, *, args: str = "") -> None:
        server_id = extract_named_int(args, "server", default=default_server_id())
        with connect() as conn:
            lang = language_for_user(conn, ctx.author.id, ctx)
            attackers = top_attackers(conn, server_id=server_id, limit=10)
            alliances = top_alliances(conn, server_id=server_id, limit=10)
            attacked_alliances = top_attacked_alliances(conn, server_id=server_id, limit=3)
        lines = []
        if alliances:
            top = alliances[0]
            lines.append(t(lang, "top_alliance", tag=top["attacker_alliance_tag"], attackers=top["unique_attackers"], attacks=top["attack_count"]))
        if attacked_alliances:
            top_target = attacked_alliances[0]
            lines.append(t(lang, "most_attacked", tag=top_target["defender_alliance_tag"], attacks=top_target["attack_count"]))
        if attackers:
            lines.append(t(lang, "top_attackers"))
            for idx, row in enumerate(attackers, start=1):
                tag = f"[{row['attacker_alliance_tag']}] " if row['attacker_alliance_tag'] else ""
                lines.append(t(lang, "attacker_row", idx=idx, tag=tag, name=row["attacker_name"], total=row["attack_count"], battle=row["battle_count"], ops=row["covert_ops_count"]))
        if not lines:
            lines = [t(lang, "no_attack_data")]
        await ctx.reply("\n".join(lines))

    @bot.command(name="recent", help="Show recent attacks. Example: @Bot recent limit=10 server=78")
    async def recent_command(ctx: commands.Context, *, args: str = "") -> None:
        server_id = extract_named_int(args, "server", default=default_server_id())
        limit = extract_named_int(args, "limit") or 10
        with connect() as conn:
            lang = language_for_user(conn, ctx.author.id, ctx)
            rows = recent_attacks(conn, limit=min(max(limit, 1), 20), server_id=server_id)
        if not rows:
            await ctx.reply(t(lang, "no_recent"))
            return
        lines = []
        for row in rows:
            when = row["occurred_at_text"] or row["occurred_at"] or row["created_at"]
            target = row["defender_name"] or "-"
            lines.append(f"#{row['id']} [{row['attack_type']}] {row['attacker_name']} -> {target} @ {when}")
        await ctx.reply("\n".join(lines))

    @bot.command(name="history", help="Show a player's recent history. Example: @Bot history Holash server=78 limit=10")
    async def history_command(ctx: commands.Context, *, args: str) -> None:
        server_id = extract_named_int(args, "server", default=default_server_id())
        limit = extract_named_int(args, "limit") or 10
        player_name = strip_named_ints(args, {"server", "limit"}).strip()
        with connect() as conn:
            lang = language_for_user(conn, ctx.author.id, ctx)
        if not player_name:
            await ctx.reply(t(lang, "history_usage"))
            return
        with connect() as conn:
            player = find_player_by_name(conn, player_name, server_id=server_id)
            if not player:
                await ctx.reply(t(lang, "player_not_found", name=player_name))
                return
            rows = player_history(conn, player["id"], limit=min(max(limit, 1), 20))
        if not rows:
            await ctx.reply(t(lang, "no_history", name=player["name"]))
            return
        lines = [t(lang, "history_header", name=player["name"], server=player["server_id"] or "-")]
        for row in rows:
            when = row["occurred_at_text"] or row["occurred_at"] or row["created_at"]
            if row["attacker_player_id"] == player["id"]:
                other = row["defender_name"] or "-"
                lines.append(t(lang, "history_attacked", id=row["id"], other=other, type=row["attack_type"], when=when))
            else:
                lines.append(t(lang, "history_defended", id=row["id"], other=row["attacker_name"], type=row["attack_type"], when=when))
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


def extract_named_int(text: str, key: str, default: int | None = None) -> int | None:
    match = re.search(rf"(?:^|\s){re.escape(key)}\s*=\s*(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else default


def strip_named_ints(text: str, keys: set[str]) -> str:
    for key in keys:
        text = re.sub(rf"(?:^|\s){re.escape(key)}\s*=\s*\d+", " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text)


def apply_victim_alliance(events: list[ParsedAttackEvent], options: ScanOptions) -> list[ParsedAttackEvent]:
    if options.victim_alliance_tag:
        for event in events:
            if event.attack_type == "covert_ops":
                event.defender_alliance_tag = options.victim_alliance_tag
    return events


def classify_report(data: bytes, options: ScanOptions) -> list[ParsedAttackEvent]:
    if options.report_type == "battle":
        return [parse_battle_report(data, default_year=options.year, fallback_server_id=options.server_id)]
    if options.report_type == "caravan":
        return parse_caravan_report(data, default_year=options.year, fallback_server_id=options.server_id)
    if options.report_type == "covert_ops":
        return apply_victim_alliance(
            parse_ops_report(data, default_year=options.year, fallback_server_id=options.server_id),
            options,
        )

    # auto-detect
    try:
        return [parse_battle_report(data, default_year=options.year, fallback_server_id=options.server_id)]
    except ParseError:
        try:
            return apply_victim_alliance(
                parse_ops_report(data, default_year=options.year, fallback_server_id=options.server_id),
                options,
            )
        except ParseError:
            return parse_caravan_report(data, default_year=options.year, fallback_server_id=options.server_id)


def image_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_discord_attachment(filename: str | None, data: bytes) -> str:
    suffix = Path(filename or "discord-upload.png").suffix or ".png"
    saved_name = f"{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex}{suffix}"
    path = UPLOADS_DIR / saved_name
    path.write_bytes(data)
    return saved_name


async def handle_scan_message(message: discord.Message, attachments: list[discord.Attachment]) -> None:
    options = parse_scan_options(message.content)
    saved_lines: list[str] = []
    error_lines: list[str] = []
    alert_lines: list[str] = []
    alert_roles: list[discord.Role] = []

    with connect() as conn:
        lang = language_for_user(conn, message.author.id, message)
        server78_alliances = set(managed_alliance_tags(conn, server_id=78))
        for attachment in attachments:
            try:
                raw = await attachment.read()
                attachment_hash = image_hash(raw)
                if get_image_submission(conn, attachment_hash):
                    error_lines.append(t(lang, "duplicate_image", filename=attachment.filename))
                    continue
                events = await asyncio.to_thread(classify_report, raw, options)
                created_ids: list[int] = []
                saved_filename = save_discord_attachment(attachment.filename, raw)
                try:
                    add_image_submission(conn, image_hash=attachment_hash, source_filename=saved_filename, source_kind="discord", first_attack_id=None)
                except sqlite3.IntegrityError:
                    error_lines.append(t(lang, "duplicate_image", filename=attachment.filename))
                    continue
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
                        source_filename=saved_filename,
                        source_kind="discord",
                        notes=event.notes,
                        parser_confidence=event.parser_confidence,
                        raw_parse_json=event.to_dict(),
                        source_image_hash=attachment_hash,
                    )
                    created_ids.append(attack_id)
                if created_ids:
                    conn.execute("UPDATE image_submissions SET first_attack_id = ? WHERE image_hash = ?", (created_ids[0], attachment_hash))
                names = ", ".join(event.attacker_name for event in events)
                saved_lines.append(t(lang, "saved_line", filename=attachment.filename, count=len(created_ids), names=names, ids=", ".join(map(str, created_ids))))
                attachment_alerts, attachment_roles = build_alliance_alerts(message.guild, attachment.filename, events, created_ids, server78_alliances, lang)
                alert_lines.extend(attachment_alerts)
                alert_roles.extend(role for role in attachment_roles if role not in alert_roles)
            except Exception as exc:
                error_lines.append(f"{attachment.filename}: {exc}")

    chunks = [t(lang, "processed_upload")]
    if saved_lines:
        chunks.append(t(lang, "saved_header") + "\n" + "\n".join(f"- {line}" for line in saved_lines))
    if alert_lines:
        chunks.append(t(lang, "alerts_header") + "\n" + "\n".join(f"- {line}" for line in alert_lines))
    if error_lines:
        chunks.append(t(lang, "errors_header") + "\n" + "\n".join(f"- {line}" for line in error_lines))
    chunks.append(t(lang, "commands_hint"))
    await message.reply(
        "\n\n".join(chunks),
        allowed_mentions=discord.AllowedMentions(
            everyone=False,
            users=False,
            roles=alert_roles,
            replied_user=False,
        ),
        mention_author=False,
    )


def build_alliance_alerts(
    guild: discord.Guild | None,
    filename: str | None,
    events: Iterable[ParsedAttackEvent],
    attack_ids: list[int],
    server78_alliances: set[str],
    lang: str = DEFAULT_LANGUAGE,
) -> tuple[list[str], list[discord.Role]]:
    alliance_tags = sorted(
        {
            event.attacker_alliance_tag
            for event in events
            if event.server_id == 78 and event.attacker_alliance_tag in server78_alliances
        }
    )
    if not alliance_tags:
        return [], []

    roles = {role_key(role.name): role for role in guild.roles} if guild else {}
    lines: list[str] = []
    mentioned_roles: list[discord.Role] = []
    ids = ", ".join(map(str, attack_ids)) or t(lang, "pending")
    source = filename or t(lang, "image")

    for alliance_tag in alliance_tags:
        role = roles.get(role_key(alliance_tag))
        target = f"{role.mention} ([{alliance_tag}])" if role else f"**[{alliance_tag}]**"
        if role:
            mentioned_roles.append(role)
        lines.append(t(lang, "violation_recorded", target=target, source=source, ids=ids))

    return lines, mentioned_roles


def role_key(value: str) -> str:
    normalized = value.strip()
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1].strip()
    return normalized.casefold()


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")
    init_db()
    build_bot().run(token)


if __name__ == "__main__":
    main()
