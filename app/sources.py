"""NextEmby-style source registry: multiple cloud / local backends.

A source is one backend behind the same Emby library:
  clouddrive2 - CD2 mount, e.g. /CloudNAS
  115         - 115 cloud drive, via its direct-link / 302 entry
  123         - 123 cloud drive, via its open-platform direct link
  guangya     - 光鸭 cloud drive (gy), via its temporary direct link
  local       - local disk
  remote      - a remote Emby / WebDAV / HTTP entry

auth_token is optional and lives only in data/sources.json, never in git.

Stored in data/sources.json. The first source is seeded from
Settings.source_root as a clouddrive2 source.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import Settings


@dataclass
class Source:
    id: str
    name: str
    type: str  # clouddrive2 | 115 | 123 | guangya | local | remote
    root: str = ""
    base_url: str = ""
    weight: int = 100
    enabled: bool = True
    auth_token: str = ""
    client_id: str = ""
    client_secret: str = ""


def _path(settings: Settings) -> Path:
    return settings.data_dir / "sources.json"


def load_sources(settings: Settings) -> list[Source]:
    p = _path(settings)
    if p.exists():
        try:
            return [Source(**s) for s in json.loads(p.read_text(encoding="utf-8"))]
        except Exception:
            pass
    default = Source(
        id="cd2",
        name="CloudDrive2",
        type="clouddrive2",
        root=str(settings.source_root),
        base_url="",
        weight=100,
        enabled=True,
    )
    save_sources(settings, [default])
    return [default]


def save_sources(settings: Settings, sources: list[Source]) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _path(settings).write_text(
        json.dumps([asdict(s) for s in sources], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_source(settings: Settings, name: str, type_: str, root: str = "", base_url: str = "", weight: int = 100, auth_token: str = "", client_id: str = "", client_secret: str = "") -> Source:
    sources = load_sources(settings)
    src = Source(id=uuid.uuid4().hex[:8], name=name, type=type_, root=root, base_url=base_url.rstrip("/"), weight=weight, auth_token=auth_token, client_id=client_id, client_secret=client_secret)
    sources.append(src)
    save_sources(settings, sources)
    return src


def remove_source(settings: Settings, source_id: str) -> bool:
    sources = load_sources(settings)
    kept = [s for s in sources if s.id != source_id]
    if len(kept) == len(sources):
        return False
    save_sources(settings, kept)
    return True
