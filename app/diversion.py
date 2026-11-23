"""NextEmby-style diversion: pick a backend for one STRM item.

Modes (same names as NextEmby's user settings):
  smart       - highest-weight enabled source that contains the file
  designated  - the user's fixed source_id, nothing else
  direct115   - only a 115 source; fails otherwise
  redirect302 - return the STRM's own URL, or a /play URL that 302s

Resolution returns a target string. A target starting with '/' and
pointing at a real file is served by /play as a file; any other target
is returned to the client as a 302 redirect.
"""
from __future__ import annotations

from pathlib import Path

from .sources import Source


def _source_for_path(sources: list[Source], path: str) -> Source | None:
    candidates = [
        s for s in sources
        if s.enabled and s.root and str(Path(path)).startswith(s.root.rstrip("/"))
    ]
    return sorted(candidates, key=lambda s: -s.weight)[0] if candidates else None


def resolve(strm_content: str, sources: list[Source], mode: str = "smart", source_id: str | None = None, play_base: str = "") -> dict:
    content = (strm_content or "").strip()
    if not content:
        return {"ok": False, "error": "empty STRM"}

    # A URL in the STRM is already a direct / 302 link.
    if content.startswith("http://") or content.startswith("https://"):
        if mode == "direct115" and "115" not in content:
            return {"ok": False, "error": "direct115 mode requires a 115 link"}
        return {"ok": True, "mode": mode, "source": None, "target": content, "via": "302"}

    # File path: map it to a source.
    source: Source | None = None
    if mode == "designated" and source_id:
        source = next((s for s in sources if s.id == source_id and s.enabled), None)
        if source is None:
            return {"ok": False, "error": f"designated source not found: {source_id}"}
    elif mode == "direct115":
        source = next((s for s in sources if s.type == "115" and s.enabled), None)
        if source is None:
            return {"ok": False, "error": "no enabled 115 source"}
    else:  # smart / redirect302
        source = _source_for_path(sources, content)
        if source is None:
            enabled = [s for s in sources if s.enabled]
            source = sorted(enabled, key=lambda s: -s.weight)[0] if enabled else None

    if source is None:
        return {"ok": False, "error": "no enabled source"}

    # If the source has a base_url, build a direct URL; otherwise the
    # /play endpoint serves / 302s the local file.
    if source.base_url:
        try:
            rel = Path(content).relative_to(source.root) if source.root else Path(content).name
        except ValueError:
            rel = Path(content).name
        target = f"{source.base_url}/{rel}"
        return {"ok": True, "mode": mode, "source": source.id, "target": target, "via": "302"}
    play = f"{play_base}/play?path={content}" if play_base else content
    return {"ok": True, "mode": mode, "source": source.id, "target": play, "via": "file"}
