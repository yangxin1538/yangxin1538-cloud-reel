"""Operation / playback / error logs, capped at 500 lines."""
from __future__ import annotations

import json
import time
from pathlib import Path

from .config import Settings

MAX_LINES = 500


def _path(settings: Settings) -> Path:
    return settings.data_dir / "logs.jsonl"


def append_log(settings: Settings, kind: str, message: str, **extra) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    entry = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "kind": kind, "message": message, **extra}
    with _path(settings).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    # Trim.
    try:
        lines = _path(settings).read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_LINES:
            _path(settings).write_text("\n".join(lines[-MAX_LINES:]) + "\n", encoding="utf-8")
    except Exception:
        pass


def read_logs(settings: Settings, limit: int = 100) -> list[dict]:
    p = _path(settings)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines()[-limit:]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out
