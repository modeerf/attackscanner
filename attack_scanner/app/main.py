from __future__ import annotations

import hashlib
import json
import mimetypes
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from .db import (
    DATA_DIR,
    add_attack,
    add_image_submission,
    add_managed_alliance,
    alliance_matchups,
    alliance_members,
    alliance_opponents,
    alliance_overview,
    attack_type_timeline,
    attacking_alliance_options,
    attacking_player_options,
    connect,
    delete_attack,
    deleted_attacks,
    get_attack,
    get_image_submission,
    get_player,
    init_db,
    is_managed_alliance,
    managed_alliance_tags,
    player_history,
    recent_attacks,
    recent_attacks_for_alliance,
    remove_managed_alliance,
    search_players,
    soft_delete_expired_attacks,
    top_alliances,
    top_attackers,
    top_attacked_alliances,
)
from .parsers import ParseError, parse_battle_report, parse_caravan_report, parse_ops_report, _normalize_datetime_value

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
DELETE_PASSWORD = "mod4life"

app = FastAPI(title="Last Assylum: Plague Violation Tracker")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def alliance_badge(alliance_tag: str | None, server_id: int | None = None, linked: bool = True) -> Markup:
    if not alliance_tag:
        return Markup("")
    with connect() as conn:
        managed = is_managed_alliance(conn, alliance_tag, server_id=78)
    css_class = "alliance-tag alliance-managed" if managed else "alliance-tag alliance-unmanaged"
    label = f"[{escape(alliance_tag)}]"
    if not linked:
        return Markup(f'<span class="{css_class}">{label}</span>')
    href = f"/alliances/{quote(str(alliance_tag))}"
    if server_id:
        href = f"{href}?server_id={int(server_id)}"
    return Markup(f'<a class="{css_class}" href="{href}">{label}</a>')


templates.env.globals["alliance_badge"] = alliance_badge


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    _backfill_upload_hashes()
    _apply_retention_policy()


def _image_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _duplicate_redirect() -> RedirectResponse:
    return RedirectResponse(
        f"/?error={quote('This image has already been submitted.')}",
        status_code=303,
    )


def _redirect_with_error(path: str, message: str) -> RedirectResponse:
    separator = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{separator}error={quote(message)}", status_code=303)


def _backfill_upload_hashes() -> None:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT source_filename, source_kind, MIN(id) AS first_attack_id
            FROM attacks
            WHERE source_filename IS NOT NULL
              AND source_image_hash IS NULL
            GROUP BY source_filename, source_kind
            """
        ).fetchall()
        for row in rows:
            path = UPLOADS_DIR / row["source_filename"]
            if not path.exists():
                continue
            image_hash = _image_hash(path.read_bytes())
            conn.execute(
                "UPDATE attacks SET source_image_hash = ? WHERE source_filename = ? AND source_image_hash IS NULL",
                (image_hash, row["source_filename"]),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO image_submissions (image_hash, source_filename, source_kind, first_attack_id)
                VALUES (?, ?, ?, ?)
                """,
                (image_hash, row["source_filename"], row["source_kind"], row["first_attack_id"]),
            )


def _apply_retention_policy() -> None:
    with connect() as conn:
        soft_delete_expired_attacks(conn, days=30)


def _save_upload(upload: UploadFile, content: bytes) -> Path:
    suffix = Path(upload.filename or "upload.png").suffix or ".png"
    filename = f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex}{suffix}"
    path = UPLOADS_DIR / filename
    path.write_bytes(content)
    return path


def _safe_upload_path(filename: str | None) -> Path | None:
    if not filename:
        return None
    base = UPLOADS_DIR.resolve()
    path = (UPLOADS_DIR / filename).resolve()
    if not path.is_file() or base not in path.parents:
        return None
    return path


def _int_or_none(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _alliance_tag_or_none(raw: str | None) -> str | None:
    value = (raw or "").strip().strip(",.;")
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip()
    return value or None


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, msg: str | None = None, error: str | None = None):
    with connect() as conn:
        attacks = recent_attacks(conn, limit=25)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "attacks": attacks,
            "msg": msg,
            "error": error,
            "now_year": datetime.utcnow().year,
        },
    )


@app.get("/manual", response_class=HTMLResponse)
def user_manual(request: Request):
    return templates.TemplateResponse(request, "manual.html", {"request": request})


@app.post("/upload/attack")
def upload_attack(image: UploadFile = File(...), server_id: str | None = Form(None), default_year: str | None = Form(None)):
    content = image.file.read()
    image_hash = _image_hash(content)
    with connect() as conn:
        if get_image_submission(conn, image_hash):
            return _duplicate_redirect()

    server = _int_or_none(server_id)
    year = _int_or_none(default_year)
    try:
        parsed = parse_battle_report(content, default_year=year, fallback_server_id=server)
    except ParseError as exc:
        return RedirectResponse(f"/?error={quote(str(exc))}", status_code=303)

    saved = _save_upload(image, content)
    with connect() as conn:
        try:
            add_image_submission(conn, image_hash=image_hash, source_filename=saved.name, source_kind="upload", first_attack_id=None)
        except sqlite3.IntegrityError:
            return _duplicate_redirect()
        attack_id = add_attack(
            conn,
            attack_type=parsed.attack_type,
            attacker_name=parsed.attacker_name,
            attacker_alliance_tag=parsed.attacker_alliance_tag,
            defender_name=parsed.defender_name,
            defender_alliance_tag=parsed.defender_alliance_tag,
            server_id=parsed.server_id,
            occurred_at=parsed.occurred_at,
            occurred_at_text=parsed.occurred_at_text,
            source_filename=saved.name,
            source_kind="upload",
            notes=parsed.notes,
            parser_confidence=parsed.parser_confidence,
            raw_parse_json=parsed.to_dict(),
            source_image_hash=image_hash,
        )
        conn.execute("UPDATE image_submissions SET first_attack_id = ? WHERE image_hash = ?", (attack_id, image_hash))
    return RedirectResponse(f"/?msg=Saved battle report as attack #{attack_id}", status_code=303)


@app.post("/upload/ops")
def upload_ops(
    image: UploadFile = File(...),
    server_id: str | None = Form(None),
    default_year: str | None = Form(None),
    victim_alliance_tag: str | None = Form(None),
):
    content = image.file.read()
    image_hash = _image_hash(content)
    with connect() as conn:
        if get_image_submission(conn, image_hash):
            return _duplicate_redirect()

    server = _int_or_none(server_id)
    year = _int_or_none(default_year)
    try:
        events = parse_ops_report(content, default_year=year, fallback_server_id=server)
    except ParseError as exc:
        return RedirectResponse(f"/?error={quote(str(exc))}", status_code=303)

    victim_alliance = _alliance_tag_or_none(victim_alliance_tag)
    if victim_alliance:
        for event in events:
            event.defender_alliance_tag = victim_alliance

    saved = _save_upload(image, content)
    with connect() as conn:
        try:
            add_image_submission(conn, image_hash=image_hash, source_filename=saved.name, source_kind="upload", first_attack_id=None)
        except sqlite3.IntegrityError:
            return _duplicate_redirect()
        created = []
        for event in events:
            created.append(
                add_attack(
                    conn,
                    attack_type=event.attack_type,
                    attacker_name=event.attacker_name,
                    attacker_alliance_tag=event.attacker_alliance_tag,
                    defender_name=event.defender_name,
                    defender_alliance_tag=event.defender_alliance_tag,
                    server_id=event.server_id,
                    occurred_at=event.occurred_at,
                    occurred_at_text=event.occurred_at_text,
                    source_filename=saved.name,
                    source_kind="upload",
                    notes=event.notes,
                    parser_confidence=event.parser_confidence,
                    raw_parse_json=event.to_dict(),
                    source_image_hash=image_hash,
                )
            )
        if created:
            conn.execute("UPDATE image_submissions SET first_attack_id = ? WHERE image_hash = ?", (created[0], image_hash))
    return RedirectResponse(f"/?msg=Saved {len(created)} covert ops event(s)", status_code=303)


@app.post("/upload/caravan")
def upload_caravan(image: UploadFile = File(...), server_id: str | None = Form(None), default_year: str | None = Form(None)):
    content = image.file.read()
    image_hash = _image_hash(content)
    with connect() as conn:
        if get_image_submission(conn, image_hash):
            return _duplicate_redirect()

    server = _int_or_none(server_id)
    year = _int_or_none(default_year)
    try:
        events = parse_caravan_report(content, default_year=year, fallback_server_id=server)
    except ParseError as exc:
        return RedirectResponse(f"/?error={quote(str(exc))}", status_code=303)

    saved = _save_upload(image, content)
    with connect() as conn:
        try:
            add_image_submission(conn, image_hash=image_hash, source_filename=saved.name, source_kind="upload", first_attack_id=None)
        except sqlite3.IntegrityError:
            return _duplicate_redirect()
        created = []
        for event in events:
            created.append(
                add_attack(
                    conn,
                    attack_type=event.attack_type,
                    attacker_name=event.attacker_name,
                    attacker_alliance_tag=event.attacker_alliance_tag,
                    defender_name=event.defender_name,
                    defender_alliance_tag=event.defender_alliance_tag,
                    server_id=event.server_id,
                    occurred_at=event.occurred_at,
                    occurred_at_text=event.occurred_at_text,
                    source_filename=saved.name,
                    source_kind="upload",
                    notes=event.notes,
                    parser_confidence=event.parser_confidence,
                    raw_parse_json=event.to_dict(),
                    source_image_hash=image_hash,
                )
            )
        if created:
            conn.execute("UPDATE image_submissions SET first_attack_id = ? WHERE image_hash = ?", (created[0], image_hash))
    return RedirectResponse(f"/?msg=Saved {len(created)} caravan attack event(s)", status_code=303)


@app.get("/players", response_class=HTMLResponse)
def players_page(request: Request, q: str = "", server_id: str | None = None):
    server = _int_or_none(server_id)
    with connect() as conn:
        players = search_players(conn, query=q, server_id=server)
    return templates.TemplateResponse(request, "players.html", {"request": request, "players": players, "q": q, "server_id": server})


@app.get("/players/{player_id}", response_class=HTMLResponse)
def player_detail(request: Request, player_id: int):
    with connect() as conn:
        player = get_player(conn, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        history = player_history(conn, player_id)
    return templates.TemplateResponse(request, "player_detail.html", {"request": request, "player": player, "history": history})


@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, server_id: str | None = None):
    server = _int_or_none(server_id)
    alliance_filter = _alliance_tag_or_none(request.query_params.get("attacker_alliance"))
    attacker_player_id = _int_or_none(request.query_params.get("attacker_player_id"))
    chart_error = None
    with connect() as conn:
        attackers = top_attackers(conn, server_id=server, limit=10)
        alliances = top_alliances(conn, server_id=server, limit=10)
        attacked_alliances = top_attacked_alliances(conn, server_id=server, limit=10)
        matchups = alliance_matchups(conn, server_id=server, limit=15)
        try:
            # Keep filter menus populated from all active data. The selected filters still
            # constrain the chart query, but the menu choices should not disappear just
            # because the current server filter is narrow or older rows have no server_id.
            alliance_filters = attacking_alliance_options(conn)
            player_filters = attacking_player_options(conn, attacker_alliance_tag=alliance_filter)
            if alliance_filter and not player_filters:
                player_filters = attacking_player_options(conn)
            timeline_rows = attack_type_timeline(
                conn,
                server_id=server,
                attacker_alliance_tag=alliance_filter,
                attacker_player_id=attacker_player_id,
            )
        except sqlite3.Error as exc:
            alliance_filters = []
            player_filters = []
            timeline_rows = []
            chart_error = str(exc)
    return templates.TemplateResponse(
        request,
        "stats.html",
        {
            "request": request,
            "server_id": server,
            "attacker_alliance": alliance_filter,
            "attacker_player_id": attacker_player_id,
            "attackers": attackers,
            "alliances": alliances,
            "attacked_alliances": attacked_alliances,
            "matchups": matchups,
            "alliance_filters": [dict(row) for row in alliance_filters],
            "player_filters": [dict(row) for row in player_filters],
            "timeline_json": json.dumps(
                [
                    {
                        "day": row["attack_day"],
                        "attack_type": row["attack_type"],
                        "attack_count": row["attack_count"],
                    }
                    for row in timeline_rows
                ]
            ),
            "chart_error": chart_error,
            "top_alliance": alliances[0] if alliances else None,
            "most_attacked_alliance": attacked_alliances[0] if attacked_alliances else None,
        },
    )


@app.get("/alliances", response_class=HTMLResponse)
def alliances_page(request: Request, server_id: str | None = None):
    server = _int_or_none(server_id)
    with connect() as conn:
        alliances = alliance_overview(conn, server_id=server, limit=100)
        matchups = alliance_matchups(conn, server_id=server, limit=25)
    return templates.TemplateResponse(
        request,
        "alliances.html",
        {"request": request, "server_id": server, "alliances": alliances, "matchups": matchups},
    )


@app.get("/alliances/{alliance_tag}", response_class=HTMLResponse)
def alliance_detail(request: Request, alliance_tag: str, server_id: str | None = None):
    server = _int_or_none(server_id)
    with connect() as conn:
        members = alliance_members(conn, alliance_tag, server_id=server, limit=100)
        outgoing = alliance_opponents(conn, alliance_tag, direction="outgoing", server_id=server, limit=20)
        incoming = alliance_opponents(conn, alliance_tag, direction="incoming", server_id=server, limit=20)
        history = recent_attacks_for_alliance(conn, alliance_tag, server_id=server, limit=50)
    if not members and not outgoing and not incoming and not history:
        raise HTTPException(status_code=404, detail="Alliance not found")
    return templates.TemplateResponse(
        request,
        "alliance_detail.html",
        {
            "request": request,
            "alliance_tag": alliance_tag,
            "server_id": server,
            "members": members,
            "outgoing": outgoing,
            "incoming": incoming,
            "history": history,
        },
    )


@app.get("/attacks/{attack_id:int}", response_class=HTMLResponse)
def attack_detail(request: Request, attack_id: int):
    with connect() as conn:
        attack = get_attack(conn, attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")
    image_path = _safe_upload_path(attack["source_filename"])
    return templates.TemplateResponse(
        request,
        "attack_detail.html",
        {"request": request, "attack": attack, "image_available": image_path is not None},
    )


@app.get("/attacks/{attack_id:int}/image")
def attack_image(attack_id: int):
    with connect() as conn:
        attack = get_attack(conn, attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")
    path = _safe_upload_path(attack["source_filename"])
    if not path:
        raise HTTPException(status_code=404, detail="Submitted image not found")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)


@app.get("/attacks/new", response_class=HTMLResponse)
def manual_add_page(request: Request, msg: str | None = None, error: str | None = None):
    return templates.TemplateResponse(request, "manual_add.html", {"request": request, "msg": msg, "error": error})


@app.post("/attacks/new")
def manual_add(
    image: UploadFile = File(...),
    attack_type: str = Form(...),
    attacker_name: str = Form(...),
    attacker_alliance_tag: str | None = Form(None),
    defender_name: str | None = Form(None),
    defender_alliance_tag: str | None = Form(None),
    server_id: str | None = Form(None),
    occurred_at_text: str | None = Form(None),
    notes: str | None = Form(None),
):
    if not attacker_name.strip():
        return _redirect_with_error("/attacks/new", "Attacker name is required")
    content = image.file.read()
    if not content:
        return _redirect_with_error("/attacks/new", "Submitted image is required")
    image_hash = _image_hash(content)
    with connect() as conn:
        if get_image_submission(conn, image_hash):
            return _redirect_with_error("/attacks/new", "This image has already been submitted.")

    occurred_at, occurred_text = (None, None)
    if (occurred_at_text or "").strip():
        occurred_at, occurred_text = _normalize_datetime_value(occurred_at_text.strip(), default_year=datetime.utcnow().year)
    saved = _save_upload(image, content)
    with connect() as conn:
        try:
            add_image_submission(conn, image_hash=image_hash, source_filename=saved.name, source_kind="manual", first_attack_id=None)
        except sqlite3.IntegrityError:
            return _redirect_with_error("/attacks/new", "This image has already been submitted.")
        attack_id = add_attack(
            conn,
            attack_type=attack_type,
            attacker_name=attacker_name.strip(),
            attacker_alliance_tag=(attacker_alliance_tag or "").strip() or None,
            defender_name=(defender_name or "").strip() or None,
            defender_alliance_tag=(defender_alliance_tag or "").strip() or None,
            server_id=_int_or_none(server_id),
            occurred_at=occurred_at,
            occurred_at_text=occurred_text,
            source_filename=saved.name,
            source_kind="manual",
            notes=(notes or "").strip() or None,
            parser_confidence=1.0,
            raw_parse_json=None,
            source_image_hash=image_hash,
        )
        conn.execute("UPDATE image_submissions SET first_attack_id = ? WHERE image_hash = ?", (attack_id, image_hash))
    return RedirectResponse(f"/attacks/new?msg=Added attack #{attack_id}", status_code=303)


@app.post("/attacks/{attack_id}/delete")
def delete_attack_route(attack_id: int, next_url: str | None = Form(None), delete_password: str = Form("")):
    redirect_to = next_url or "/"
    if delete_password != DELETE_PASSWORD:
        return _redirect_with_error(redirect_to, "Delete password is incorrect.")
    with connect() as conn:
        delete_attack(conn, attack_id, delete_reason="Deleted from web UI")
    return RedirectResponse(redirect_to, status_code=303)


@app.get("/admin/deleted", response_class=HTMLResponse)
def deleted_records_page(request: Request, password: str | None = None):
    if password != DELETE_PASSWORD:
        return templates.TemplateResponse(
            request,
            "deleted_records.html",
            {"request": request, "authorized": False, "records": []},
        )
    with connect() as conn:
        records = deleted_attacks(conn, limit=500)
    return templates.TemplateResponse(
        request,
        "deleted_records.html",
        {"request": request, "authorized": True, "records": records},
    )


@app.get("/admin/server78-alliances", response_class=HTMLResponse)
def server78_alliances_page(request: Request, password: str | None = None, msg: str | None = None, error: str | None = None):
    if password != DELETE_PASSWORD:
        return templates.TemplateResponse(
            request,
            "server78_alliances.html",
            {"request": request, "authorized": False, "alliances": [], "password": "", "msg": msg, "error": error},
        )
    with connect() as conn:
        alliances = managed_alliance_tags(conn, server_id=78)
    return templates.TemplateResponse(
        request,
        "server78_alliances.html",
        {"request": request, "authorized": True, "alliances": alliances, "password": password, "msg": msg, "error": error},
    )


@app.post("/admin/server78-alliances/add")
def add_server78_alliance(password: str = Form(""), alliance_tag: str = Form("")):
    if password != DELETE_PASSWORD:
        return _redirect_with_error("/admin/server78-alliances", "Password is incorrect.")
    tag = alliance_tag.strip()
    if not tag:
        return _redirect_with_error(f"/admin/server78-alliances?password={quote(password)}", "Alliance tag is required.")
    with connect() as conn:
        add_managed_alliance(conn, tag, server_id=78)
    return RedirectResponse(f"/admin/server78-alliances?password={quote(password)}&msg={quote('Alliance added.')}", status_code=303)


@app.post("/admin/server78-alliances/remove")
def remove_server78_alliance(password: str = Form(""), alliance_tag: str = Form("")):
    if password != DELETE_PASSWORD:
        return _redirect_with_error("/admin/server78-alliances", "Password is incorrect.")
    with connect() as conn:
        remove_managed_alliance(conn, alliance_tag, server_id=78)
    return RedirectResponse(f"/admin/server78-alliances?password={quote(password)}&msg={quote('Alliance removed.')}", status_code=303)


@app.get("/api/attacks")
def api_attacks(limit: int = 50, server_id: int | None = None):
    with connect() as conn:
        items = [dict(row) for row in recent_attacks(conn, limit=min(max(limit, 1), 500), server_id=server_id)]
    return {"items": items}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
