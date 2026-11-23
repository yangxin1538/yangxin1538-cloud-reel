"""Direct-link / 302 cache, NextEmby-style: TTL, list, clear."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .config import Settings


def _path(settings: Settings) -> Path:
    return settings.data_dir / "cache.json"


def load_cache(settings: Settings) -> dict:
    p = _path(settings)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    now = time.time()
    ttl = getattr(settings, "cache_ttl_seconds", 3600)
    return {k: v for k, v in data.items() if now - v.get("at", 0) < ttl}


def get_cached(settings: Settings, key: str) -> str | None:
    entry = load_cache(settings).get(key)
    return entry.get("target") if entry else None


def put_cache(settings: Settings, key: str, target: str) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    data = load_cache(settings)
    data[key] = {"target": target, "at": time.time()}
    _path(settings).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_cache(settings: Settings) -> int:
    data = load_cache(settings)
    n = len(data)
    _path(settings).write_text("{}", encoding="utf-8")
    return n
