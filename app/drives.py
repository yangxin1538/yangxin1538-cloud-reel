"""123网盘 and 光鸭云盘 direct-link handling.

What is verified from public sources:
  - 123 has an open platform: RequestAccessToken(client_id, client_secret),
    then GetDirectLinkUrl(fileId) / EnableDirectLink(fileId). Large files
    (>100MB) usually need a logged-in Authorization, otherwise the
    download API returns 5112 / "please log in".
  - 光鸭 (gy, Xunlei) offers an open platform and third-party direct
    connection. Its single-file direct link is a temporary link that
    needs a Bearer Authorization captured from a logged-in web session;
    no stable public endpoint was found, so CloudReel does not invent one.

So both drives work in CloudReel in two honest ways:
  1. Via a CD2 / local mount (root path): scan + file serving, no API.
  2. Via a configured base_url + auth_token: build a 302 direct URL.
     For 123 that base_url is normally its direct-link entry; for 光鸭
     it is the temporary direct link's host/prefix.

Auth tokens live only in data/sources.json on the user's machine,
never in git and never in logs.
"""
from __future__ import annotations

import re
from pathlib import Path

SHARE_123_RE = re.compile(r"(?:yun\.123pan\.com|www\.123pan\.com|[\w-]+\.share\.123pan\.cn)", re.IGNORECASE)
SHARE_GUANGYA_RE = re.compile(r"guangya", re.IGNORECASE)


def detect_share_drive(url: str) -> str | None:
    """Return '123' or 'guangya' for a known share URL, else None."""
    if SHARE_123_RE.search(url):
        return "123"
    if SHARE_GUANGYA_RE.search(url):
        return "guangya"
    return None


def build_direct_url(source_type: str, base_url: str, root: str, content: str) -> dict:
    """Build a 302 direct URL from a configured source, or explain why not."""
    if not base_url:
        if source_type == "123":
            return {
                "ok": False,
                "error": "123 source needs base_url (its direct-link entry) or a CD2/local root. 123 open platform: RequestAccessToken(client_id, client_secret), then EnableDirectLink(fileId) + GetDirectLinkUrl(fileId). Large files need a logged-in Authorization.",
            }
        if source_type == "guangya":
            return {
                "ok": False,
                "error": "光鸭 source needs base_url or a CD2/local root. 光鸭 direct links are temporary and need a Bearer Authorization from a logged-in web session.",
            }
        return {"ok": False, "error": f"{source_type} source needs base_url"}
    try:
        rel = Path(content).relative_to(root) if root else Path(content).name
    except ValueError:
        rel = Path(content).name
    return {"ok": True, "target": f"{base_url.rstrip('/')}/{rel}", "via": "302"}
