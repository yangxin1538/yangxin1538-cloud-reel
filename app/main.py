"""CloudReel v0.3.1 web service.

v0.1: scan CD2, generate STRM, clean up, Web config, scheduled scan.
v0.2, NextEmby + NextFind integration:
  - Source registry + diversion modes (smart / designated / direct115 / redirect302)
  - /play 302 / file serving, direct-link cache, playback logs
  - User management (bind Emby user, per-user diversion mode)
  - Emby reverse-proxy gateway at /emby/*
  - Discovery ingest + missing-episode diagnosis
  - Plugin system (plugins/*.py)
"""
from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel

from . import cache as cache_mod
from . import discovery as discovery_mod
from . import diversion as diversion_mod
from . import guangya as guangya_mod
from .pan123 import Pan123Client, Pan123Error
from . import gateway as gateway_mod
from . import logs as logs_mod
from . import plugins as plugins_mod
from . import sources as sources_mod
from . import users as users_mod
from .config import Settings, load_settings, save_settings
from .scanner import ScanResult, scan

app = FastAPI(title="CloudReel", version="0.3.2")
settings: Settings = load_settings()
_last_scan: dict = {"status": "never", "result": None, "at": None}
_scan_lock = threading.Lock()
PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


class ConfigIn(BaseModel):
    source_root: str | None = None
    strm_root: str | None = None
    strm_mode: str | None = None
    strm_base_url: str | None = None
    scan_interval_minutes: int | None = None
    emby_upstream: str | None = None


class SourceIn(BaseModel):
    name: str
    type: str = "clouddrive2"
    root: str = ""
    base_url: str = ""
    weight: int = 100
    auth_token: str = ""
    client_id: str = ""
    client_secret: str = ""


class UserIn(BaseModel):
    name: str
    emby_user: str = ""
    mode: str = "smart"
    source_id: str | None = None


class ResolveIn(BaseModel):
    strm: str
    user: str | None = None
    mode: str | None = None
    source_id: str | None = None


class IngestIn(BaseModel):
    text: str
    source: str = "manual"


class DiagnoseIn(BaseModel):
    show: str
    season: int = 1
    total_episodes: int = 1


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
        logs_mod.append_log(settings, "scan", f"scanned={result.scanned} created={result.created} removed={result.removed}")
        return _last_scan


def _user_mode(user_name: str | None, mode: str | None, source_id: str | None):
    if user_name:
        for u in users_mod.load_users(settings):
            if u.name == user_name and u.enabled:
                return u.mode if mode is None else mode, u.source_id if source_id is None else source_id
    return mode or "smart", source_id


@app.get("/health")
def health():
    return {"ok": True, "version": "0.3.2"}


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
        "emby_upstream": settings.emby_upstream,
        "cache_ttl_seconds": settings.cache_ttl_seconds,
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
    if body.emby_upstream is not None:
        settings.emby_upstream = body.emby_upstream.strip().rstrip("/")
    save_settings(settings)
    return get_config()


@app.post("/api/scan")
def trigger_scan():
    return _run_scan()


@app.get("/api/status")
def status():
    return {"config": get_config(), "last_scan": _last_scan,
            "sources": len(sources_mod.load_sources(settings)),
            "users": len(users_mod.load_users(settings)),
            "plugins": len(plugins_mod.list_plugins(PLUGINS_DIR))}


# --- Sources ---
def _mask_source(s):
    d = s.__dict__.copy()
    d["auth_token"] = "***" if d.get("auth_token") else ""
    d["client_secret"] = "***" if d.get("client_secret") else ""
    return d


@app.get("/api/sources")
def list_sources():
    return [_mask_source(s) for s in sources_mod.load_sources(settings)]


@app.post("/api/sources")
def create_source(body: SourceIn):
    src = sources_mod.add_source(settings, body.name, body.type, body.root, body.base_url, body.weight, body.auth_token, body.client_id, body.client_secret)
    return _mask_source(src)


@app.delete("/api/sources/{source_id}")
def delete_source(source_id: str):
    return {"deleted": sources_mod.remove_source(settings, source_id)}


# --- Users ---
@app.get("/api/users")
def list_users():
    return [u.__dict__ for u in users_mod.load_users(settings)]


@app.post("/api/users")
def create_user(body: UserIn):
    user = users_mod.add_user(settings, body.name, body.emby_user, body.mode, body.source_id)
    return user.__dict__


# --- Diversion / play ---
def _pan123_client(source):
    cid = source.client_id or settings.pan123_client_id
    csec = source.client_secret or settings.pan123_client_secret
    if not cid or not csec:
        return None
    return Pan123Client(cid, csec, data_dir=settings.data_dir)


def _resolve_123(strm: str, sources) -> dict | None:
    """Try the real 123 open-platform API. Returns None to fall back."""
    src = next((s for s in sources if s.type == "123" and s.enabled), None)
    if src is None:
        return {"ok": False, "error": "no enabled 123 source"}
    client = _pan123_client(src)
    if client is None:
        return None  # no credentials: fall back to base_url / file
    try:
        rel = str(Path(strm).relative_to(src.root)) if src.root and strm.startswith(src.root.rstrip("/")) else Path(strm).name
        url = client.direct_link_for_path(rel)
        return {"ok": True, "mode": "direct123", "source": src.id, "target": url, "via": "302", "api": "123-open-platform"}
    except Pan123Error as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"123 API error: {e}"}


@app.get("/api/drives/123/status")
def pan123_status():
    sources = sources_mod.load_sources(settings)
    src = next((s for s in sources if s.type == "123" and s.enabled), None)
    return {
        "configured": src is not None,
        "credentials": bool(src and (src.client_id or settings.pan123_client_id) and (src.client_secret or settings.pan123_client_secret)),
        "membership_assumed": True,
        "base_url": "https://open-api.123pan.com",
    }


@app.post("/api/resolve")
def resolve(body: ResolveIn):
    mode, source_id = _user_mode(body.user, body.mode, body.source_id)
    cached = cache_mod.get_cached(settings, body.strm)
    if cached:
        return {"ok": True, "mode": mode, "target": cached, "via": "cache", "cached": True}
    sources = sources_mod.load_sources(settings)
    if mode == "direct123":
        real = _resolve_123(body.strm, sources)
        if real is not None:
            if real.get("ok"):
                cache_mod.put_cache(settings, body.strm, real["target"])
            return real
    if mode == "directguangya":
        src = next((s for s in sources if s.type == "guangya" and s.enabled), None)
        if src is None:
            return {"ok": False, "error": "no enabled guangya source"}
        if src.root and Path(body.strm).is_file():
            return {"ok": True, "mode": mode, "source": src.id, "target": body.strm, "via": "file"}
        r = guangya_mod.direct_url(src.base_url, src.root, body.strm)
        if r.get("ok"):
            out = {"ok": True, "mode": mode, "source": src.id, "target": r["target"], "via": "302"}
            if src.auth_token:
                out["auth_hint"] = "Bearer token required by player"
            cache_mod.put_cache(settings, body.strm, r["target"])
            return out
        return {"ok": False, "error": r["error"]}
    result = diversion_mod.resolve(body.strm, sources, mode, source_id, play_base="")
    if result.get("ok"):
        cache_mod.put_cache(settings, body.strm, result["target"])
    return result


@app.get("/play")
def play(path: str, user: str | None = None):
    # path is a file path or a URL stored in a STRM.
    mode, source_id = _user_mode(user, None, None)
    cached = cache_mod.get_cached(settings, path)
    if cached:
        target = cached
    else:
        result = diversion_mod.resolve(path, sources_mod.load_sources(settings), mode, source_id, play_base="")
        if not result.get("ok"):
            logs_mod.append_log(settings, "playback_error", result.get("error", "resolve failed"), path=path)
            return JSONResponse(result, status_code=404)
        target = result["target"]
        cache_mod.put_cache(settings, path, target)
    logs_mod.append_log(settings, "playback", target, path=path, user=user or "")
    if target.startswith("http://") or target.startswith("https://"):
        return RedirectResponse(target, status_code=302)
    if Path(target).is_file():
        return FileResponse(target)
    # /play?path=<file> where resolve returned the file itself
    if Path(path).is_file():
        return FileResponse(path)
    return JSONResponse({"ok": False, "error": "target not found", "target": target}, status_code=404)


# --- Cache / logs ---
@app.get("/api/cache")
def list_cache():
    return cache_mod.load_cache(settings)


@app.post("/api/cache/clear")
def clear_cache():
    return {"cleared": cache_mod.clear_cache(settings)}


@app.get("/api/logs")
def list_logs(limit: int = 100):
    return logs_mod.read_logs(settings, limit)


# --- Discovery (NextFind) ---
@app.post("/api/discovery/ingest")
def ingest(body: IngestIn):
    return discovery_mod.ingest(settings, body.text, body.source)


@app.get("/api/discovery")
def list_discovery():
    return discovery_mod.load_items(settings)


@app.post("/api/discovery/diagnose")
def diagnose(body: DiagnoseIn):
    return discovery_mod.diagnose(settings, body.show, body.season, body.total_episodes)


# --- Plugins ---
@app.get("/api/plugins")
def list_plugins():
    return plugins_mod.list_plugins(PLUGINS_DIR)


@app.post("/api/plugins/{name}/run")
def run_plugin(name: str, body: dict | None = None):
    query = (body or {}).get("query", "")
    return plugins_mod.run_plugin(PLUGINS_DIR, name, query, settings)


# --- Emby gateway ---
@app.get("/emby/{path:path}")
def emby_proxy(path: str, request: Request):
    if not settings.emby_upstream:
        return JSONResponse({"ok": False, "error": "EMBY_UPSTREAM not configured"}, status_code=501)
    status, body, ctype = gateway_mod.proxy_get(settings.emby_upstream, path, str(request.query_params))
    return Response(content=body, status_code=status, media_type=ctype)


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
