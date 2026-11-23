"""Scan SOURCE_ROOT, generate .strm files, clean up orphans.

State is kept in data/state.json:
  { "<strm relative path>": "<source absolute path>" }
so a deleted / renamed source can be cleaned up on the next scan.
"""
from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings
from .parser import is_video, parse_filename


@dataclass
class ScanResult:
    scanned: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    errors: list[str] = field(default_factory=list)


def _safe(name: str) -> str:
    return "".join(c for c in name if c not in '/\\:*?"<>|').strip() or "Unknown"


def strm_rel_path(parsed, source: Path) -> Path:
    if parsed.kind == "tv":
        season = f"Season {parsed.season:02d}"
        ep = f"{_safe(parsed.title)} - S{parsed.season:02d}E{parsed.episode:02d}"
        return Path("TV") / _safe(parsed.title) / season / f"{ep}.strm"
    return Path("Movies") / _safe(parsed.display_title) / f"{_safe(parsed.display_title)}.strm"


def strm_content(settings: Settings, source: Path) -> str:
    if settings.strm_mode == "url" and settings.strm_base_url:
        try:
            rel = source.relative_to(settings.source_root)
        except ValueError:
            rel = Path(source.name)
        quoted = "/".join(urllib.parse.quote(p) for p in rel.parts)
        return f"{settings.strm_base_url}/{quoted}\n"
    return f"{source}\n"


def _load_state(settings: Settings) -> dict:
    if not settings.state_path.exists():
        return {}
    try:
        return json.loads(settings.state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(settings: Settings, state: dict) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def scan(settings: Settings) -> ScanResult:
    result = ScanResult()
    if not settings.source_root.exists():
        result.errors.append(f"源目录不存在: {settings.source_root}")
        return result

    settings.strm_root.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    state = _load_state(settings)
    seen: set[str] = set()

    for source in sorted(settings.source_root.rglob("*")):
        if not source.is_file() or not is_video(source):
            continue
        result.scanned += 1
        try:
            parsed = parse_filename(source.name)
            rel = strm_rel_path(parsed, source)
            dest = settings.strm_root / rel
            seen.add(str(rel))
            content = strm_content(settings, source)
            if dest.exists() and dest.read_text(encoding="utf-8", errors="ignore") == content:
                result.unchanged += 1
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                existed = dest.exists()
                dest.write_text(content, encoding="utf-8")
                result.updated += 1 if existed else 0
                result.created += 0 if existed else 1
            state[str(rel)] = str(source)
        except Exception as exc:  # noqa: BLE001 - keep scanning other files
            result.errors.append(f"{source}: {exc}")

    # Cleanup: strm files whose source is gone.
    for rel, _src in list(state.items()):
        if rel not in seen:
            dest = settings.strm_root / rel
            try:
                if dest.exists():
                    dest.unlink()
                result.removed += 1
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"清理 {rel} 失败: {exc}")
            del state[rel]

    _save_state(settings, state)
    return result
