"""NextFind-style discovery: ingest cloud links, diagnose missing episodes.

Ingest accepts pasted text (Telegram channel exports, share links, ...),
extracts video titles / SxxEyy and URLs, and stores them in
data/discovery.json. Diagnose compares a show's expected episode list
with the STRM files already in STRM_ROOT and reports the missing ones.
Only path-mode STRM is used here, matching NextFind v3.7.7.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .config import Settings
from .parser import parse_filename

URL_RE = re.compile(r"https?://\S+")


def _path(settings: Settings) -> Path:
    return settings.data_dir / "discovery.json"


def load_items(settings: Settings) -> list[dict]:
    p = _path(settings)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def ingest(settings: Settings, text: str, source: str = "manual") -> list[dict]:
    items = load_items(settings)
    found: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        urls = URL_RE.findall(line)
        # Parse only the text before any URL; a URL breaks Path().stem.
        parsed = parse_filename(URL_RE.split(line, maxsplit=1)[0].strip() or line)
        item = {
            "title": parsed.title,
            "kind": parsed.kind,
            "year": parsed.year,
            "season": parsed.season,
            "episode": parsed.episode,
            "urls": urls,
            "text": line,
            "source": source,
        }
        if item not in items:
            items.append(item)
        found.append(item)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _path(settings).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    return found


def diagnose(settings: Settings, show: str, season: int, total_episodes: int) -> dict:
    present: set[int] = set()
    tv_root = settings.strm_root / "TV"
    if tv_root.exists():
        for p in tv_root.rglob("*.strm"):
            parsed = parse_filename(p.name)
            if parsed.kind == "tv" and parsed.season == season and show in parsed.title:
                if parsed.episode:
                    present.add(parsed.episode)
    expected = set(range(1, total_episodes + 1))
    missing = sorted(expected - present)
    return {
        "show": show,
        "season": season,
        "total_episodes": total_episodes,
        "present": sorted(present),
        "missing": missing,
        "complete": not missing,
    }
