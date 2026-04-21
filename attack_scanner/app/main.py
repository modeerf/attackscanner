from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import (
    DATA_DIR,
    add_attack,
    connect,
    delete_attack,
    get_player,
    init_db,
    player_history,
    recent_attacks,
    search_players,
    top_alliances,
    top_attackers,
)
from .parsers import ParseError, parse_battle_report, parse_ops_report, _normalize_datetime_value

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Attack Scanner")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _save_upload(upload: UploadFile) -> tuple[bytes, Path]:
    suffix = Path(upload.filename or "upload.png").suffix or ".png"
    filename = f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex}{suffix}"
    path = UPLOADS_DIR / filename
    content = upload.file.read()
    path.write_bytes(content)
    return content, path


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


@app.post("/upload/attack")
def upload_attack(image: UploadFile = File(...), server_id: str | None = Form(None), default_year: str | None = Form(None)):
    content, saved = _save_upload(image)
    server = _int_or_none(server_id)
    year = _int_or_none(default_year)
    try:
        parsed = parse_battle_report(content, default_year=year, fallback_server_id=server)
    except ParseError as exc:
        return RedirectResponse(f"/?error={str(exc)}", status_code=303)

    with connect() as conn:
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
        )
    return RedirectResponse(f"/?msg=Saved battle report as attack #{attack_id}", status_code=303)


@app.post("/upload/ops")
def upload_ops(image: UploadFile = File(...), server_id: str | None = Form(None), default_year: str | None = Form(None)):
    content, saved = _save_upload(image)
    server = _int_or_none(server_id)
    year = _int_or_none(default_year)
    try:
        events = parse_ops_report(content, default_year=year, fallback_server_id=server)
    except ParseError as exc:
        return RedirectResponse(f"/?error={str(exc)}", status_code=303)

    with connect() as conn:
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
                )
            )
    return RedirectResponse(f"/?msg=Saved {len(created)} covert ops event(s)", status_code=303)


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
    with connect() as conn:
        attackers = top_attackers(conn, server_id=server, limit=10)
        alliances = top_alliances(conn, server_id=server, limit=10)
    return templates.TemplateResponse(
        request,
        "stats.html",
        {"request": request, "server_id": server, "attackers": attackers, "alliances": alliances, "top_alliance": alliances[0] if alliances else None},
    )


@app.get("/attacks/new", response_class=HTMLResponse)
def manual_add_page(request: Request, msg: str | None = None, error: str | None = None):
    return templates.TemplateResponse(request, "manual_add.html", {"request": request, "msg": msg, "error": error})


@app.post("/attacks/new")
def manual_add(
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
        return RedirectResponse("/attacks/new?error=Attacker name is required", status_code=303)
    occurred_at, occurred_text = (None, None)
    if (occurred_at_text or "").strip():
        occurred_at, occurred_text = _normalize_datetime_value(occurred_at_text.strip(), default_year=datetime.utcnow().year)
    with connect() as conn:
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
            source_filename=None,
            source_kind="manual",
            notes=(notes or "").strip() or None,
            parser_confidence=1.0,
            raw_parse_json=None,
        )
    return RedirectResponse(f"/attacks/new?msg=Added attack #{attack_id}", status_code=303)


@app.post("/attacks/{attack_id}/delete")
def delete_attack_route(attack_id: int, next_url: str | None = Form(None)):
    with connect() as conn:
        delete_attack(conn, attack_id)
    return RedirectResponse(next_url or "/", status_code=303)


@app.get("/api/attacks")
def api_attacks(limit: int = 50, server_id: int | None = None):
    with connect() as conn:
        items = [dict(row) for row in recent_attacks(conn, limit=min(max(limit, 1), 500), server_id=server_id)]
    return {"items": items}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
