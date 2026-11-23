"""光鸭云盘 (Guangya) direct-link handling.

Assumption (user, 2026-11-23): the user has a membership on every
cloud drive, so Guangya direct-link privilege and traffic are assumed
available. No membership / traffic check is done here.

Honest limit: no stable public official Guangya open-platform API
endpoint was found. So CloudReel does NOT invent one. The workable
paths, in order, are:
  1. CD2 / local mount (root path): scan + file serving, no token.
  2. A configured direct-link entry (source.base_url) + Bearer
     auth_token captured from a logged-in web session or obtained
     by QR / device-code login: CloudReel 302s to that entry.
     The Bearer token is needed by the player / downloader when
     the link itself does not carry it; CloudReel returns it in
     the resolve result as `auth_hint`, never in logs.
"""
from __future__ import annotations

from pathlib import Path


def direct_url(base_url: str, root: str, content: str) -> dict:
    if not base_url:
        return {
            "ok": False,
            "error": "光鸭 source needs a direct-link entry (base_url) or a CD2/local root. Membership is assumed; supply the direct link from a logged-in Guangya session (Bearer auth_token) and CloudReel will 302 to it.",
        }
    try:
        rel = Path(content).relative_to(root) if root else Path(content).name
    except ValueError:
        rel = Path(content).name
    return {"ok": True, "target": f"{base_url.rstrip('/')}/{rel}", "via": "302"}
