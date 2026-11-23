"""Filename parsing: movies and TV episodes.

Examples:
  流浪地球2 (2023).mkv
  Dune.Part.Two.2024.2160p.mkv
  三体.S01E01.2023.mkv
  Breaking.Bad.S01E01.Pilot.mkv
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

VIDEO_EXTS = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".ts", ".m2ts", ".webm", ".rmvb"}
IGNORE_RE = re.compile(r"sample|trailer|预告|样片", re.IGNORECASE)
EP_RE = re.compile(r"[Ss](\d{1,2})[Ee](\d{1,3})")
YEAR_RE = re.compile(r"(19\d{2}|20\d{2})")


@dataclass
class Parsed:
    kind: str  # "movie" | "tv"
    title: str
    year: str | None = None
    season: int | None = None
    episode: int | None = None

    @property
    def display_title(self) -> str:
        return f"{self.title} ({self.year})" if self.year else self.title


def _clean_title(raw: str) -> str:
    raw = raw.replace(".", " ").replace("_", " ").replace("-", " ")
    raw = re.sub(r"\s+", " ", raw).strip()
    # Drop a dangling opening bracket left by "Title (2023)" -> "Title ("
    raw = re.sub(r"[\(\[\{]\s*$", "", raw).strip()
    raw = re.sub(r"\s*[\)\]\}]\s*$", "", raw).strip()
    # Drop common quality / source tags at the end.
    raw = re.sub(
        r"\b(2160p|1080p|720p|4K|HDR|BluRay|WEB-DL|WEBRip|HDTV|x264|x265|HEVC|AAC|DTS|TrueHD)\b.*$",
        "",
        raw,
        flags=re.IGNORECASE,
    ).strip()
    return raw or "Unknown"


def is_video(path: Path) -> bool:
    if path.suffix.lower() not in VIDEO_EXTS:
        return False
    if IGNORE_RE.search(path.stem):
        return False
    return True


def parse_filename(name: str) -> Parsed:
    stem = Path(name).stem
    ep = EP_RE.search(stem)
    year_match = YEAR_RE.search(stem)
    year = year_match.group(1) if year_match else None

    if ep:
        season, episode = int(ep.group(1)), int(ep.group(2))
        title_raw = stem[: ep.start()]
        # A year before S01E01 belongs to the show, keep it out of the title.
        title_raw = YEAR_RE.sub("", title_raw)
        return Parsed(kind="tv", title=_clean_title(title_raw), year=year,
                      season=season, episode=episode)

    title_raw = stem
    if year_match:
        title_raw = stem[: year_match.start()]
    return Parsed(kind="movie", title=_clean_title(title_raw), year=year)
