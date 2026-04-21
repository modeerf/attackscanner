from __future__ import annotations

import io
import re
from dataclasses import dataclass, asdict
from datetime import datetime

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageOps

ALLIANCE_TAG_RE = re.compile(r"^\[(?P<tag>[A-Za-z0-9]+)\]$")
MERGED_NAME_RE = re.compile(r"^\[(?P<tag>[A-Za-z0-9]+)\]\s*(?P<name>[A-Za-z0-9_\-]+)$")
SERVER_TOKEN_RE = re.compile(r"^[S\$]?\d{1,4}$")
NAME_TOKEN_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_\-]{2,}$")
FULL_DATETIME_RE = re.compile(r"(20\d{2}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)")
PARTIAL_DATETIME_RE = re.compile(r"(\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)")
TIME_RE = re.compile(r"(\d{1,2}:\d{2}(?::\d{2})?)")
COORD_SERVER_RE = re.compile(r"(?:^|\s)[S\$]?(\d{1,4})(?:\s|$)")
OPS_NAME_RE = re.compile(r"(\[[A-Za-z0-9]+\]\s*[A-Za-z0-9_\-]+)")


@dataclass(slots=True)
class ParsedAttackEvent:
    attack_type: str
    attacker_name: str
    attacker_alliance_tag: str | None = None
    defender_name: str | None = None
    defender_alliance_tag: str | None = None
    server_id: int | None = None
    occurred_at: str | None = None
    occurred_at_text: str | None = None
    notes: str | None = None
    parser_confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class ParseError(Exception):
    pass


def load_image(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def enhance_for_ocr(image: Image.Image, scale: float = 2.0, contrast: float = 2.5) -> Image.Image:
    if scale != 1.0:
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    image = ImageOps.grayscale(image)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    return image


def ocr_words(image: Image.Image, config: str) -> list[dict]:
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=config)
    words: list[dict] = []
    for i, raw in enumerate(data["text"]):
        text = (raw or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = -1.0
        words.append(
            {
                "text": text,
                "conf": conf,
                "left": int(data["left"][i]),
                "top": int(data["top"][i]),
                "width": int(data["width"][i]),
                "height": int(data["height"][i]),
                "block_num": int(data.get("block_num", [0] * len(data["text"]))[i]),
                "par_num": int(data.get("par_num", [0] * len(data["text"]))[i]),
                "line_num": int(data.get("line_num", [0] * len(data["text"]))[i]),
            }
        )
    return words


def group_words_into_lines(words: list[dict], tolerance: int = 18) -> list[list[dict]]:
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"] + w["height"] / 2, w["left"])):
        cy = word["top"] + word["height"] / 2
        placed = False
        for line in lines:
            avg = sum(item["top"] + item["height"] / 2 for item in line) / len(line)
            if abs(cy - avg) <= tolerance:
                line.append(word)
                placed = True
                break
        if not placed:
            lines.append([word])
    return [sorted(line, key=lambda w: w["left"]) for line in lines]


def normalize_server_id(raw: str | None) -> int | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return int(digits) if digits else None


def _normalize_datetime_value(raw: str, default_year: int | None = None) -> tuple[str | None, str | None]:
    raw = raw.strip().replace("/", "-")
    raw = re.sub(r"\s+", " ", raw)
    patterns = [
        ("%Y-%m-%d %H:%M:%S", True),
        ("%Y-%m-%d %H:%M", True),
        ("%m-%d %H:%M:%S", False),
        ("%m-%d %H:%M", False),
    ]
    for fmt, has_year in patterns:
        try:
            dt = datetime.strptime(raw, fmt)
            if not has_year:
                dt = dt.replace(year=default_year or datetime.utcnow().year)
            return dt.isoformat(sep=" "), raw
        except ValueError:
            continue
    return None, raw if raw else None


def _normalize_year_token(token: str) -> str | None:
    token = re.sub(r"\D", "", token)
    if len(token) == 4 and token.startswith("20"):
        return token
    if len(token) == 3:
        if token.startswith("0"):
            return f"2{token}"
        if token.startswith("2"):
            return f"20{token[1:]}"
    if len(token) == 2:
        return f"20{token}"
    return None


def _parse_lenient_attack_datetime(raw: str) -> tuple[str | None, str | None]:
    compact = re.sub(r"[^0-9:-]", "", raw)
    patterns = [
        re.compile(r"(?P<year>\d{3,4})[:\-]?(?P<month>\d{2})[:\-]?(?P<day>\d{2})(?P<hour>\d{1,2})[:\-]?(?P<minute>\d{2})[:\-]?(?P<second>\d{2})"),
        re.compile(r"(?P<year>\d{3,4})[:\-]?(?P<month>\d{2})[:\-]?(?P<day>\d{2})(?P<hour>\d{1,2})[:\-]?(?P<minute>\d{2})"),
    ]
    for pattern in patterns:
        match = pattern.search(compact)
        if not match:
            continue
        year = _normalize_year_token(match.group("year"))
        if not year:
            continue
        month = int(match.group("month"))
        day = int(match.group("day"))
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        second = int(match.groupdict().get("second") or 0)
        if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            continue
        clean = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
        return clean, clean
    return None, None


def extract_attack_datetime(image: Image.Image, default_year: int | None = None) -> tuple[str | None, str | None]:
    crop = image.crop((int(image.width * 0.41), 0, image.width, int(image.height * 0.115)))
    prepared = enhance_for_ocr(crop, scale=3.0, contrast=3.0)

    best_guess: tuple[str | None, str | None] | None = None
    words = ocr_words(prepared, "--psm 11")
    for word in words:
        date_match = re.search(r"(\d{3,4}[-/]\d{2}[-/]\d{2})", word["text"])
        if not date_match:
            continue
        parts = date_match.group(1).replace("/", "-").split("-")
        if len(parts) != 3:
            continue
        year = _normalize_year_token(parts[0])
        if not year:
            continue
        try:
            month = int(parts[1])
            day = int(parts[2])
        except ValueError:
            continue
        if not (1 <= month <= 12 and 1 <= day <= 31):
            continue
        sub = prepared.crop((
            max(0, word["left"] + word["width"] - 10),
            max(0, word["top"] - 10),
            min(prepared.width, word["left"] + word["width"] + 280),
            min(prepared.height, word["top"] + word["height"] + 25),
        ))
        time_text = pytesseract.image_to_string(sub, config="--psm 13 -c tessedit_char_whitelist=0123456789:")
        time_match = TIME_RE.search(time_text)
        if time_match:
            candidate = _normalize_datetime_value(f"{year}-{month:02d}-{day:02d} {time_match.group(1)}", default_year)
            if time_match.group(1).count(":") == 2:
                return candidate
            best_guess = candidate

    candidate_boxes = [
        (0.40, 0.72, 0.90, 0.98),
        (0.42, 0.70, 0.97, 0.98),
        (0.45, 0.74, 0.96, 0.98),
    ]
    for x1r, y1r, x2r, y2r in candidate_boxes:
        sub = prepared.crop((
            int(prepared.width * x1r),
            int(prepared.height * y1r),
            int(prepared.width * x2r),
            int(prepared.height * y2r),
        ))
        raw = pytesseract.image_to_string(sub, config="--psm 13 -c tessedit_char_whitelist=0123456789:- ")
        candidate = _parse_lenient_attack_datetime(raw)
        if candidate[0]:
            return candidate

    if best_guess:
        return best_guess

    crop_text = pytesseract.image_to_string(prepared, config="--psm 11")
    match = FULL_DATETIME_RE.search(crop_text)
    if match:
        return _normalize_datetime_value(match.group(1), default_year)

    candidate = _parse_lenient_attack_datetime(crop_text)
    if candidate[0]:
        return candidate

    full_text = pytesseract.image_to_string(enhance_for_ocr(image, scale=1.75, contrast=2.5), config="--psm 6")
    match = FULL_DATETIME_RE.search(full_text) or PARTIAL_DATETIME_RE.search(full_text)
    if match:
        return _normalize_datetime_value(match.group(1), default_year)

    return None, None


def _candidate_from_merged(word: dict) -> dict | None:
    match = MERGED_NAME_RE.match(word["text"])
    if not match:
        return None
    return {
        "alliance_tag": match.group("tag"),
        "name": match.group("name"),
        "server_id": None,
        "x_center": word["left"] + word["width"] / 2,
        "confidence": max(0.0, min(1.0, word["conf"] / 100.0)),
    }


def _extract_battle_candidates(words: list[dict]) -> list[dict]:
    candidates: list[dict] = []
    for word in words:
        merged = _candidate_from_merged(word)
        if merged:
            candidates.append(merged)

    by_line: dict[tuple[int, int, int], list[dict]] = {}
    for word in words:
        by_line.setdefault((word["block_num"], word["par_num"], word["line_num"]), []).append(word)

    for line_words in by_line.values():
        line_words.sort(key=lambda item: item["left"])
        for idx, word in enumerate(line_words):
            tag = ALLIANCE_TAG_RE.match(word["text"])
            if not tag:
                continue
            server_id = None
            if idx > 0 and SERVER_TOKEN_RE.match(line_words[idx - 1]["text"]):
                server_id = normalize_server_id(line_words[idx - 1]["text"])
            name = None
            conf = word["conf"]
            if idx + 1 < len(line_words) and NAME_TOKEN_RE.match(line_words[idx + 1]["text"]):
                name = line_words[idx + 1]["text"]
                conf = min(conf, line_words[idx + 1]["conf"])
            if not name:
                continue
            candidates.append(
                {
                    "alliance_tag": tag.group("tag"),
                    "name": name,
                    "server_id": server_id,
                    "x_center": word["left"] + word["width"] / 2,
                    "confidence": max(0.0, min(1.0, conf / 100.0)),
                }
            )

    deduped: dict[tuple[str | None, str], dict] = {}
    for item in candidates:
        key = (item["alliance_tag"], item["name"])
        if key not in deduped or item["confidence"] > deduped[key]["confidence"]:
            deduped[key] = item
    return list(deduped.values())


def parse_battle_report(image_bytes: bytes, default_year: int | None = None, fallback_server_id: int | None = None) -> ParsedAttackEvent:
    image = load_image(image_bytes)
    words = ocr_words(image, "--psm 6")
    candidates = _extract_battle_candidates(words)
    if len(candidates) < 2:
        enlarged = enhance_for_ocr(image, scale=2.0, contrast=2.8)
        enlarged_words = ocr_words(enlarged, "--psm 6")
        candidates = _extract_battle_candidates(enlarged_words)
        for c in candidates:
            c["x_center"] /= 2.0
    if len(candidates) < 2:
        raise ParseError("Could not find both attacker and defender in the battle image.")

    candidates.sort(key=lambda item: item["x_center"])
    defender = candidates[0]
    attacker = candidates[-1]
    occurred_at, occurred_at_text = extract_attack_datetime(image, default_year=default_year)
    server_id = attacker.get("server_id") or defender.get("server_id") or fallback_server_id
    if server_id is None:
        server_match = COORD_SERVER_RE.search(pytesseract.image_to_string(image, config="--psm 6"))
        if server_match:
            server_id = normalize_server_id(server_match.group(1))

    confidence = round((attacker["confidence"] + defender["confidence"]) / 2, 3)
    if occurred_at_text:
        confidence = min(1.0, confidence + 0.08)

    return ParsedAttackEvent(
        attack_type="battle",
        attacker_name=attacker["name"],
        attacker_alliance_tag=attacker.get("alliance_tag"),
        defender_name=defender["name"],
        defender_alliance_tag=defender.get("alliance_tag"),
        server_id=server_id,
        occurred_at=occurred_at,
        occurred_at_text=occurred_at_text,
        parser_confidence=confidence,
    )


def red_score(image_arr: np.ndarray, x: int, y: int, w: int, h: int) -> float:
    roi = image_arr[max(0, y): max(0, y + h), max(0, x): max(0, x + w)]
    if roi.size == 0:
        return 0.0
    hsv = cv2.cvtColor(roi, cv2.COLOR_RGB2HSV)
    h = hsv[:, :, 0].astype(np.int32)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    mask = (((h <= 10) | (h >= 170)) & (s > 80) & (v > 80))
    return float(mask.mean())


def _parse_name_fragment(fragment: str) -> tuple[str | None, str]:
    fragment = fragment.strip()
    match = MERGED_NAME_RE.match(fragment)
    if match:
        return match.group("tag"), match.group("name")
    match = re.match(r"^\[(?P<tag>[A-Za-z0-9]+)\]\s+(?P<name>[A-Za-z0-9_\-]+)$", fragment)
    if match:
        return match.group("tag"), match.group("name")
    return None, fragment


def parse_ops_report(image_bytes: bytes, default_year: int | None = None, fallback_server_id: int | None = None) -> list[ParsedAttackEvent]:
    image = load_image(image_bytes)
    arr = np.array(image)
    words = ocr_words(image, "--psm 11")
    if not words:
        raise ParseError("No text could be read from the covert ops image.")
    for word in words:
        word["red_score"] = red_score(arr, word["left"], word["top"], word["width"], word["height"])

    events: list[ParsedAttackEvent] = []
    seen: set[tuple[str, str | None]] = set()
    for line in group_words_into_lines(words, tolerance=20):
        text = " ".join(item["text"] for item in line)
        matches = OPS_NAME_RE.findall(text)
        if not matches:
            continue
        max_red = max(item["red_score"] for item in line)
        avg_red = sum(item["red_score"] for item in line) / len(line)
        if max_red < 0.12 and avg_red < 0.05:
            continue
        dt_match = FULL_DATETIME_RE.search(text) or PARTIAL_DATETIME_RE.search(text)
        occurred_at, occurred_at_text = (None, None)
        if dt_match:
            occurred_at, occurred_at_text = _normalize_datetime_value(dt_match.group(1), default_year=default_year)
        for raw_name in matches:
            alliance_tag, name = _parse_name_fragment(raw_name)
            key = (name.lower(), occurred_at_text)
            if key in seen:
                continue
            seen.add(key)
            confidence = 0.75 + (0.12 if max_red > 0.25 else 0.0) + (0.08 if occurred_at_text else 0.0)
            events.append(
                ParsedAttackEvent(
                    attack_type="covert_ops",
                    attacker_name=name,
                    attacker_alliance_tag=alliance_tag,
                    server_id=fallback_server_id,
                    occurred_at=occurred_at,
                    occurred_at_text=occurred_at_text,
                    notes="Parsed from covert ops report",
                    parser_confidence=min(1.0, round(confidence, 3)),
                )
            )
    if not events:
        raise ParseError("Could not find any red attacker names in the covert ops image.")
    return events
