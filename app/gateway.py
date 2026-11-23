"""Emby reverse-proxy gateway, NextEmby-style (single-port version).

CloudReel keeps one port (8088) instead of NextEmby's 8091/8097/8098:
  /emby/*  -> upstream Emby (EMBY_UPSTREAM, e.g. http://127.0.0.1:8096)
  /play    -> diversion / 302 / file serving for STRM items

Only GET is proxied in v0.2; other methods return 501.
"""
from __future__ import annotations

import urllib.error
import urllib.request


def proxy_get(upstream: str, path: str, query: str = "") -> tuple[int, bytes, str]:
    url = f"{upstream.rstrip('/')}/{path.lstrip('/')}"
    if query:
        url += f"?{query}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read(), resp.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), "text/plain"
    except Exception as exc:  # noqa: BLE001
        return 502, str(exc).encode(), "text/plain"
