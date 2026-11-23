"""Configuration: environment variables override config.json."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    port: int = 8088
    source_root: Path = Path("/CloudNAS")
    strm_root: Path = Path("/strm/CloudReel")
    strm_mode: str = "file"  # file | url
    strm_base_url: str = ""
    scan_interval_minutes: int = 60
    data_dir: Path = Path("/app/data")
    config_dir: Path = Path("/app/config")

    @property
    def state_path(self) -> Path:
        return self.data_dir / "state.json"

    @property
    def config_path(self) -> Path:
        return self.config_dir / "config.json"


def _from_env() -> dict:
    out: dict = {}
    if os.getenv("PORT"):
        out["port"] = int(os.environ["PORT"])
    if os.getenv("SOURCE_ROOT"):
        out["source_root"] = Path(os.environ["SOURCE_ROOT"])
    if os.getenv("STRM_ROOT"):
        out["strm_root"] = Path(os.environ["STRM_ROOT"])
    if os.getenv("STRM_MODE"):
        out["strm_mode"] = os.environ["STRM_MODE"].strip().lower()
    if os.getenv("STRM_BASE_URL") is not None:
        out["strm_base_url"] = os.environ["STRM_BASE_URL"].strip().rstrip("/")
    if os.getenv("SCAN_INTERVAL_MINUTES"):
        out["scan_interval_minutes"] = int(os.environ["SCAN_INTERVAL_MINUTES"])
    if os.getenv("DATA_DIR"):
        out["data_dir"] = Path(os.environ["DATA_DIR"])
    if os.getenv("CONFIG_DIR"):
        out["config_dir"] = Path(os.environ["CONFIG_DIR"])
    return out


def load_settings() -> Settings:
    settings = Settings()
    # 1. config.json (if present)
    cfg_path = settings.config_path
    # CONFIG_DIR itself can be overridden by env, so re-check first.
    if os.getenv("CONFIG_DIR"):
        cfg_path = Path(os.environ["CONFIG_DIR"]) / "config.json"
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            for key in ("port", "scan_interval_minutes"):
                if key in raw:
                    setattr(settings, key, int(raw[key]))
            for key in ("source_root", "strm_root", "data_dir", "config_dir"):
                if key in raw:
                    setattr(settings, key, Path(raw[key]))
            for key in ("strm_mode", "strm_base_url"):
                if key in raw:
                    setattr(settings, key, str(raw[key]).strip())
        except Exception:
            pass
    # 2. environment variables win
    for key, value in _from_env().items():
        setattr(settings, key, value)
    if settings.strm_mode not in ("file", "url"):
        settings.strm_mode = "file"
    return settings


def save_settings(settings: Settings) -> None:
    settings.config_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "port": settings.port,
        "source_root": str(settings.source_root),
        "strm_root": str(settings.strm_root),
        "strm_mode": settings.strm_mode,
        "strm_base_url": settings.strm_base_url,
        "scan_interval_minutes": settings.scan_interval_minutes,
        "data_dir": str(settings.data_dir),
        "config_dir": str(settings.config_dir),
    }
    settings.config_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
