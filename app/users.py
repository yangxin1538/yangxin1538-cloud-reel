"""User management: bind an Emby user, pick a diversion mode per user."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import Settings

MODES = ("smart", "designated", "direct115", "direct123", "directguangya", "redirect302")


@dataclass
class User:
    id: str
    name: str
    emby_user: str = ""
    mode: str = "smart"
    source_id: str | None = None
    enabled: bool = True


def _path(settings: Settings) -> Path:
    return settings.data_dir / "users.json"


def load_users(settings: Settings) -> list[User]:
    p = _path(settings)
    if p.exists():
        try:
            return [User(**u) for u in json.loads(p.read_text(encoding="utf-8"))]
        except Exception:
            pass
    admin = User(id="admin", name="admin", emby_user="admin", mode="smart")
    save_users(settings, [admin])
    return [admin]


def save_users(settings: Settings, users: list[User]) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    _path(settings).write_text(
        json.dumps([asdict(u) for u in users], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_user(settings: Settings, name: str, emby_user: str = "", mode: str = "smart", source_id: str | None = None) -> User:
    users = load_users(settings)
    user = User(id=uuid.uuid4().hex[:8], name=name, emby_user=emby_user,
                mode=mode if mode in MODES else "smart", source_id=source_id)
    users.append(user)
    save_users(settings, users)
    return user
