"""CloudReel web service: config, manual scan, status, scheduled scan."""
from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from .config import Settings, load_settings, save_settings
from .scanner import ScanResult, scan

app = FastAPI(title="CloudReel", version="0.1.0")
settings: Settings = load_settings()
_last_scan: dict = {"status": "never", "result": None, "at": None}
_scan_lock = threading.Lock()


class ConfigIn(BaseModel):
    source_root: str | None = None
    strm_root: str | None = None
    strm_mode: str | None = None
    strm_base_url: str | None = None
    scan_interval_minutes: int | None = None


def _run_scan() -> dict:
    global _last_scan
    with _scan_lock:
        started = time.strftime("%Y-%m-%d %H:%M:%S")
        result: ScanResult = scan(settings)
        _last_scan = {
            "status": "ok" if not result.errors else "partial",
            "result": result.__dict__,
            "at": started,
        }
        return _last_scan


@app.get("/health")
def health():
    return {"ok": True, "version": "0.1.0"}


@app.get("/")
def index():
    return FileResponse(Path(__file__).resolve().parent.parent / "web" / "index.html")


@app.get("/api/config")
def get_config():
    return {
        "port": settings.port,
        "source_root": str(settings.source_root),
        "strm_root": str(settings.strm_root),
        "strm_mode": settings.strm_mode,
        "strm_base_url": settings.strm_base_url,
        "scan_interval_minutes": settings.scan_interval_minutes,
        "source_exists": settings.source_root.exists(),
        "strm_exists": settings.strm_root.exists(),
    }


@app.post("/api/config")
def update_config(body: ConfigIn):
    global settings
    if body.source_root:
        settings.source_root = Path(body.source_root)
    if body.strm_root:
        settings.strm_root = Path(body.strm_root)
    if body.strm_mode in ("file", "url"):
        settings.strm_mode = body.strm_mode
    if body.strm_base_url is not None:
        settings.strm_base_url = body.strm_base_url.strip().rstrip("/")
    if body.scan_interval_minutes is not None:
        settings.scan_interval_minutes = int(body.scan_interval_minutes)
    save_settings(settings)
    return get_config()


@app.post("/api/scan")
def trigger_scan():
    return _run_scan()


@app.get("/api/status")
def status():
    return {"config": get_config(), "last_scan": _last_scan}


async def _scheduler() -> None:
    while True:
        interval = max(0, settings.scan_interval_minutes)
        if interval <= 0:
            await asyncio.sleep(60)
            continue
        await asyncio.sleep(interval * 60)
        try:
            _run_scan()
        except Exception:
            pass


@app.on_event("startup")
async def startup():
    asyncio.create_task(_scheduler())


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
