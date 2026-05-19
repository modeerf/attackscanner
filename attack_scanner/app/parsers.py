from __future__ import annotations

import io
import os
import re
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime

import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageOps

ALLIANCE_TAG_RE = re.compile(r"^\[(?P<tag>[^\]\s]+)\]$")
MERGED_NAME_RE = re.compile(r"^\[(?P<tag>[^\]\s]+)\]\s*(?P<name>[^\s\[\]]+)$")
SERVER_TOKEN_RE = re.compile(r"^[S\$]?\d{1,4}$")
NAME_TOKEN_RE = re.compile(r"^[^\W_][^\s\[\]]{1,}$", re.UNICODE)
FULL_DATETIME_RE = re.compile(r"(20\d{2}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{1,2}(?::\d{1,2})?)")
PARTIAL_DATETIME_RE = re.compile(r"(\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{1,2}(?::\d{1,2})?)")
TIME_RE = re.compile(r"(\d{1,2}:\d{1,2}(?::\d{1,2})?)")
COORD_SERVER_RE = re.compile(r"(?:^|\s)[S\$]?(\d{1,4})(?:\s|$)")
OPS_NAME_RE = re.compile(r"(\[[^\]\s]+\]\s*[^\s\[\]]+)")
TAGGED_NAME_RE = re.compile(r"^\[(?P<tag>[^\]\s]+)\]\s*(?P<name>[^\s\[\]]+)$")
OPS_THEFT_WORDS = (
    "stole",
    "rob",
    "robo",
    "robo",
    "ukral",
    "ykpa",
    "украл",
    "украли",
    "украден",
    "recompensa",
    "recompensas",
    "quest reward",
    "quest rewards",
)
OPS_HELP_WORDS = (
    "helped",
    "claim",
    "ayudo",
    "ayudo",
    "reclamar",
)
OPS_CONTEXT_WORDS = (
    "covert",
    "operation",
    "stole",
    "quest",
    "reward",
    "secret operation",
    "ops report",
    "tavhon",
    "onepa",
    "otue",
    "отчет",
    "отчёт",
    "тайн",
    "операц",
    "наград",
    "задан",
    "rob",
    "robo",
    "recompensa",
    "recompensas",
    "mision",
    "misión",
)


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


_OCR_LANG_CACHE: str | None | bool = False


def _preferred_ocr_lang() -> str | None:
    global _OCR_LANG_CACHE
    if _OCR_LANG_CACHE is not False:
        return _OCR_LANG_CACHE
    env_value = os.getenv("ATTACK_SCANNER_TESSERACT_LANGS")
    if env_value:
        _OCR_LANG_CACHE = env_value
        return env_value
    try:
        installed = set(pytesseract.get_languages(config=""))
    except Exception:
        _OCR_LANG_CACHE = None
        return None
    preferred = [lang for lang in ("eng", "rus", "spa") if lang in installed]
    _OCR_LANG_CACHE = "+".join(preferred) if preferred else None
    return _OCR_LANG_CACHE


def ocr_image_to_string(image: Image.Image, config: str) -> str:
    lang = _preferred_ocr_lang()
    try:
        if lang:
            return pytesseract.image_to_string(image, config=config, lang=lang)
        return pytesseract.image_to_string(image, config=config)
    except pytesseract.TesseractError:
        return pytesseract.image_to_string(image, config=config)


def load_image(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def enhance_for_ocr(image: Image.Image, scale: float = 2.0, contrast: float = 2.5) -> Image.Image:
    if scale != 1.0:
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    image = ImageOps.grayscale(image)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    return image


def ocr_words(image: Image.Image, config: str) -> list[dict]:
    lang = _preferred_ocr_lang()
    try:
        if lang:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=config, lang=lang)
        else:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=config)
    except pytesseract.TesseractError:
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


def image_text_candidates(image: Image.Image, configs: tuple[str, ...] = ("--psm 6", "--psm 11")) -> list[str]:
    images = [
        image,
        enhance_for_ocr(image, scale=1.6, contrast=2.4),
        enhance_for_ocr(image, scale=2.2, contrast=2.8),
    ]
    texts: list[str] = []
    for candidate in images:
        for config in configs:
            try:
                texts.append(ocr_image_to_string(candidate, config=config))
            except pytesseract.TesseractError:
                continue
    return texts


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
    time_match = re.search(r"(?P<hour>\d{1,2}):(?P<minute>\d{1,2})(?::(?P<second>\d{1,2}))?$", raw)
    if time_match:
        hour = int(time_match.group("hour"))
        minute = int(time_match.group("minute"))
        second = int(time_match.group("second") or 0)
        raw = re.sub(
            r"\d{1,2}:\d{1,2}(?::\d{1,2})?$",
            f"{hour:02d}:{minute:02d}:{second:02d}",
            raw,
        )
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
        time_text = ocr_image_to_string(sub, config="--psm 13 -c tessedit_char_whitelist=0123456789:")
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
        raw = ocr_image_to_string(sub, config="--psm 13 -c tessedit_char_whitelist=0123456789:- ")
        candidate = _parse_lenient_attack_datetime(raw)
        if candidate[0]:
            return candidate

    if best_guess:
        return best_guess

    crop_text = ocr_image_to_string(prepared, config="--psm 11")
    match = FULL_DATETIME_RE.search(crop_text)
    if match:
        return _normalize_datetime_value(match.group(1), default_year)

    candidate = _parse_lenient_attack_datetime(crop_text)
    if candidate[0]:
        return candidate

    full_text = ocr_image_to_string(enhance_for_ocr(image, scale=1.75, contrast=2.5), config="--psm 6")
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
    attacker = candidates[0]
    defender = candidates[-1]
    occurred_at, occurred_at_text = extract_attack_datetime(image, default_year=default_year)
    server_id = attacker.get("server_id") or defender.get("server_id") or fallback_server_id
    if server_id is None:
        server_match = COORD_SERVER_RE.search(ocr_image_to_string(image, config="--psm 6"))
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


def red_text_mask(image_arr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image_arr, cv2.COLOR_RGB2HSV)
    h = hsv[:, :, 0].astype(np.int32)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    return ((((h <= 12) | (h >= 168)) & (s > 45) & (v > 95))).astype(np.uint8) * 255


def _ops_datetime_from_text(text: str, default_year: int | None = None) -> tuple[str | None, str | None]:
    match = FULL_DATETIME_RE.search(text) or PARTIAL_DATETIME_RE.search(text)
    if match:
        return _normalize_datetime_value(match.group(1), default_year=default_year)
    return None, None


def _fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_text.lower()


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    folded = _fold_text(text)
    return any(needle in folded for needle in needles)


def _is_ops_theft_text(text: str) -> bool:
    return _contains_any(text, OPS_THEFT_WORDS) and not _contains_any(text, OPS_HELP_WORDS)


def _is_ops_context_text(text: str) -> bool:
    return _contains_any(text, OPS_CONTEXT_WORDS)


def _event_from_ops_match(
    raw_name: str,
    *,
    occurred_at: str | None,
    occurred_at_text: str | None,
    fallback_server_id: int | None,
    confidence: float,
) -> ParsedAttackEvent:
    alliance_tag, name = _parse_name_fragment(raw_name)
    return ParsedAttackEvent(
        attack_type="covert_ops",
        attacker_name=name,
        attacker_alliance_tag=alliance_tag,
        server_id=fallback_server_id,
        occurred_at=occurred_at,
        occurred_at_text=occurred_at_text,
        notes="Parsed from covert ops report",
        parser_confidence=min(1.0, round(confidence, 3)),
    )


def _fallback_ops_events_from_red_regions(
    image: Image.Image,
    image_arr: np.ndarray,
    *,
    default_year: int | None,
    fallback_server_id: int | None,
) -> list[ParsedAttackEvent]:
    mask = red_text_mask(image_arr)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (26, 7))
    merged = cv2.dilate(mask, kernel, iterations=2)
    contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    events: list[ParsedAttackEvent] = []
    seen: set[tuple[str, str | None]] = set()
    for contour in sorted(contours, key=lambda c: cv2.boundingRect(c)[1]):
        x, y, w, h = cv2.boundingRect(contour)
        if w < image.width * 0.08 or h < 14:
            continue
        if y < image.height * 0.15:
            continue

        crop_box = (
            max(0, x - 20),
            max(0, y - 18),
            min(image.width, x + w + 40),
            min(image.height, y + h + 24),
        )
        crop = image.crop(crop_box)
        prepared = enhance_for_ocr(crop, scale=2.5, contrast=2.8)
        text_candidates = [
            ocr_image_to_string(crop, config="--psm 7"),
            ocr_image_to_string(prepared, config="--psm 7"),
        ]
        row_crop = image.crop(
            (
                0,
                max(0, y - 70),
                image.width,
                min(image.height, y + max(h, 38) + 100),
            )
        )
        row_text = ocr_image_to_string(row_crop, config="--psm 6")
        occurred_at, occurred_at_text = _ops_datetime_from_text(row_text, default_year=default_year)

        for text in text_candidates:
            for raw_name in find_tagged_names(text):
                alliance_tag, name = _parse_name_fragment(raw_name)
                key = (name.lower(), occurred_at_text)
                if key in seen:
                    continue
                seen.add(key)
                events.append(
                    ParsedAttackEvent(
                        attack_type="covert_ops",
                        attacker_name=name,
                        attacker_alliance_tag=alliance_tag,
                        server_id=fallback_server_id,
                        occurred_at=occurred_at,
                        occurred_at_text=occurred_at_text,
                        notes="Parsed from covert ops report red-text fallback",
                        parser_confidence=0.72,
                    )
                )
    return events


def _fallback_ops_events_from_report_text(
    image: Image.Image,
    *,
    default_year: int | None,
    fallback_server_id: int | None,
) -> list[ParsedAttackEvent]:
    crop_boxes = [
        (0, int(image.height * 0.38), image.width, int(image.height * 0.72)),
        (0, int(image.height * 0.42), image.width, int(image.height * 0.82)),
        (0, int(image.height * 0.30), image.width, image.height),
    ]
    texts: list[str] = []
    for box in crop_boxes:
        crop = image.crop(box)
        prepared = enhance_for_ocr(crop, scale=2.6, contrast=2.6)
        texts.extend(
            [
                ocr_image_to_string(crop, config="--psm 6"),
                ocr_image_to_string(prepared, config="--psm 6"),
                ocr_image_to_string(prepared, config="--psm 11"),
            ]
        )

    events: list[ParsedAttackEvent] = []
    seen: set[tuple[str, str | None]] = set()
    for text in texts:
        if not _is_ops_context_text(text):
            continue
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            window = " ".join(lines[max(0, idx - 1): min(len(lines), idx + 3)])
            if not _is_ops_theft_text(window):
                continue
            occurred_at, occurred_at_text = _ops_datetime_from_text(window, default_year=default_year)
            for raw_name in find_tagged_names(window):
                alliance_tag, name = _parse_name_fragment(raw_name)
                key = (name.lower(), occurred_at_text)
                if key in seen:
                    continue
                seen.add(key)
                events.append(
                    ParsedAttackEvent(
                        attack_type="covert_ops",
                        attacker_name=name,
                        attacker_alliance_tag=alliance_tag,
                        server_id=fallback_server_id,
                        occurred_at=occurred_at,
                        occurred_at_text=occurred_at_text,
                        notes="Parsed from covert ops report text fallback",
                        parser_confidence=0.74 + (0.06 if occurred_at_text else 0.0),
                    )
                )
    return events


def _events_from_ops_text(
    text: str,
    *,
    default_year: int | None,
    fallback_server_id: int | None,
    confidence: float,
    note: str,
) -> list[ParsedAttackEvent]:
    events: list[ParsedAttackEvent] = []
    seen: set[tuple[str, str | None]] = set()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for idx, line in enumerate(lines):
        line_names = find_tagged_names(line)
        if not line_names:
            continue
        end_idx = len(lines)
        for next_idx in range(idx + 1, len(lines)):
            if find_tagged_names(lines[next_idx]):
                end_idx = next_idx
                break
        window = " ".join(lines[idx:end_idx])
        if not _is_ops_theft_text(window):
            continue
        occurred_at, occurred_at_text = _ops_datetime_from_text(window, default_year=default_year)
        for raw_name in line_names:
            alliance_tag, name = _parse_name_fragment(raw_name)
            key = (name.lower(), occurred_at_text)
            if key in seen:
                continue
            seen.add(key)
            events.append(
                ParsedAttackEvent(
                    attack_type="covert_ops",
                    attacker_name=name,
                    attacker_alliance_tag=alliance_tag,
                    server_id=fallback_server_id,
                    occurred_at=occurred_at,
                    occurred_at_text=occurred_at_text,
                    notes=note,
                    parser_confidence=confidence + (0.06 if occurred_at_text else 0.0),
                )
            )
    return events


def _fallback_ops_events_from_all_text(
    image: Image.Image,
    *,
    default_year: int | None,
    fallback_server_id: int | None,
) -> list[ParsedAttackEvent]:
    events: list[ParsedAttackEvent] = []
    seen: set[tuple[str, str | None]] = set()
    for text in image_text_candidates(image, configs=("--psm 6", "--psm 11", "--psm 12")):
        for event in _events_from_ops_text(
            text,
            default_year=default_year,
            fallback_server_id=fallback_server_id,
            confidence=0.70,
            note="Parsed from covert ops full-text fallback",
        ):
            key = (event.attacker_name.lower(), event.occurred_at_text)
            if key in seen:
                continue
            seen.add(key)
            events.append(event)
    return events


def _parse_name_fragment(fragment: str) -> tuple[str | None, str]:
    fragment = fragment.strip()
    match = TAGGED_NAME_RE.match(fragment)
    if match:
        return match.group("tag"), normalize_ocr_player_name(match.group("name"))
    match = MERGED_NAME_RE.match(fragment)
    if match:
        return match.group("tag"), normalize_ocr_player_name(match.group("name"))
    match = re.match(r"^\[(?P<tag>[A-Za-z0-9]+)[\]\|Il1]\s*(?P<name>[A-Za-z0-9_\-]+)$", fragment)
    if match:
        return match.group("tag"), normalize_ocr_player_name(match.group("name"))
    match = re.match(r"^\[(?P<tag>[A-Za-z0-9]+)\]\s+(?P<name>[A-Za-z0-9_\-]+)$", fragment)
    if match:
        return match.group("tag"), normalize_ocr_player_name(match.group("name"))
    return None, normalize_ocr_player_name(fragment)


def normalize_ocr_player_name(name: str) -> str:
    name = name.strip()
    if len(name) >= 4 and name.startswith("J") and name[1].isupper() and name[2].islower():
        return name[1:]
    return name


def _event_key(event: ParsedAttackEvent) -> tuple[str, str | None, str | None]:
    return (event.attacker_name.lower(), event.attacker_alliance_tag, event.occurred_at_text)


def _dedupe_ops_events(events: list[ParsedAttackEvent]) -> list[ParsedAttackEvent]:
    best: dict[tuple[str, str | None], ParsedAttackEvent] = {}
    for event in events:
        key = (event.attacker_name.lower(), event.attacker_alliance_tag)
        current = best.get(key)
        if current is None:
            best[key] = event
            continue
        current_has_time = bool(current.occurred_at_text)
        event_has_time = bool(event.occurred_at_text)
        if event_has_time and not current_has_time:
            best[key] = event
            continue
        if event_has_time == current_has_time and event.parser_confidence > current.parser_confidence:
            best[key] = event
    return list(best.values())


def parse_caravan_report(image_bytes: bytes, default_year: int | None = None, fallback_server_id: int | None = None) -> list[ParsedAttackEvent]:
    image = load_image(image_bytes)
    texts = image_text_candidates(image, configs=("--psm 6", "--psm 11"))

    all_names: list[tuple[str | None, str]] = []
    for text in texts:
        for raw_name in find_tagged_names(text):
            parsed = _parse_name_fragment(raw_name)
            if parsed not in all_names:
                all_names.append(parsed)
    if len(all_names) < 2:
        raise ParseError("Could not find victim and attackers in the caravan image.")

    victim_alliance, victim_name = all_names[0]
    events: list[ParsedAttackEvent] = []
    seen: set[tuple[str, str | None, str | None]] = set()

    for text in texts:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            occurred_at, occurred_at_text = _ops_datetime_from_text(line, default_year=default_year)
            if not occurred_at_text:
                continue
            end_idx = len(lines)
            for next_idx in range(idx + 1, len(lines)):
                if _ops_datetime_from_text(lines[next_idx], default_year=default_year)[1]:
                    end_idx = next_idx
                    break
            window = " ".join(lines[idx:end_idx])
            for raw_name in find_tagged_names(window):
                attacker_alliance, attacker_name = _parse_name_fragment(raw_name)
                if attacker_name == victim_name and attacker_alliance == victim_alliance:
                    continue
                event = ParsedAttackEvent(
                    attack_type="caravan",
                    attacker_name=attacker_name,
                    attacker_alliance_tag=attacker_alliance,
                    defender_name=victim_name,
                    defender_alliance_tag=victim_alliance,
                    server_id=fallback_server_id,
                    occurred_at=occurred_at,
                    occurred_at_text=occurred_at_text,
                    notes="Parsed from caravan attack report",
                    parser_confidence=0.74,
                )
                key = _event_key(event)
                if key in seen:
                    continue
                seen.add(key)
                events.append(event)

    if not events:
        for attacker_alliance, attacker_name in all_names[1:]:
            event = ParsedAttackEvent(
                attack_type="caravan",
                attacker_name=attacker_name,
                attacker_alliance_tag=attacker_alliance,
                defender_name=victim_name,
                defender_alliance_tag=victim_alliance,
                server_id=fallback_server_id,
                notes="Parsed from caravan attack report",
                parser_confidence=0.58,
            )
            key = _event_key(event)
            if key not in seen:
                seen.add(key)
                events.append(event)

    if not events:
        raise ParseError("Could not find caravan attackers in the image.")
    return events


def parse_ops_report(image_bytes: bytes, default_year: int | None = None, fallback_server_id: int | None = None) -> list[ParsedAttackEvent]:
    image = load_image(image_bytes)
    arr = np.array(image)
    words = ocr_words(image, "--psm 11")
    if not words:
        raise ParseError("No text could be read from the covert ops image.")
    for word in words:
        word["red_score"] = red_score(arr, word["left"], word["top"], word["width"], word["height"])

    events: list[ParsedAttackEvent] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for line in group_words_into_lines(words, tolerance=20):
        text = " ".join(item["text"] for item in line)
        matches = find_tagged_names(text)
        if not matches:
            continue
        max_red = max(item["red_score"] for item in line)
        avg_red = sum(item["red_score"] for item in line) / len(line)
        is_theft_row = _is_ops_theft_text(text)
        if not is_theft_row and max_red < 0.035 and avg_red < 0.012:
            continue
        occurred_at, occurred_at_text = _ops_datetime_from_text(text, default_year=default_year)
        for raw_name in matches:
            event = _event_from_ops_match(
                raw_name,
                occurred_at=occurred_at,
                occurred_at_text=occurred_at_text,
                fallback_server_id=fallback_server_id,
                confidence=0.75 + (0.12 if max_red > 0.25 else 0.0) + (0.08 if occurred_at_text else 0.0) + (0.06 if is_theft_row else 0.0),
            )
            key = _event_key(event)
            if key in seen:
                continue
            seen.add(key)
            events.append(event)

    fallback_batches = [
        _fallback_ops_events_from_red_regions(
            image,
            arr,
            default_year=default_year,
            fallback_server_id=fallback_server_id,
        ),
        _fallback_ops_events_from_report_text(
            image,
            default_year=default_year,
            fallback_server_id=fallback_server_id,
        ),
        _fallback_ops_events_from_all_text(
            image,
            default_year=default_year,
            fallback_server_id=fallback_server_id,
        ),
    ]
    for batch in fallback_batches:
        for event in batch:
            key = _event_key(event)
            if key in seen:
                continue
            seen.add(key)
            events.append(event)
    events = _dedupe_ops_events(events)
    if not events:
        raise ParseError("Could not find any red attacker names in the covert ops image.")
    return events


def find_tagged_names(text: str) -> list[str]:
    matches: list[str] = []
    for match in re.finditer(r"\[(?P<tag>[A-Za-z0-9]{2,12})[\]\|Il1]\s*(?P<name>[^\s\[\]]+)", text):
        name = match.group("name").strip().strip(".,;:!?)")
        if not name:
            continue
        if re.fullmatch(r"\d{1,2}[-/]\d{1,2}", name) or TIME_RE.fullmatch(name):
            continue
        matches.append(f"[{match.group('tag')}]{name}")
    return matches
