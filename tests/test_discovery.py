import tempfile
from pathlib import Path

from app.config import Settings
from app.discovery import diagnose, ingest


def test_ingest_and_diagnose(tmp_path):
    tmp_path = Path(tmp_path)
    s = Settings(data_dir=tmp_path, strm_root=tmp_path / "strm")
    (tmp_path / "strm" / "TV" / "三体" / "Season 01").mkdir(parents=True)
    (tmp_path / "strm" / "TV" / "三体" / "Season 01" / "三体 - S01E01.strm").write_text("x")
    items = ingest(s, "三体.S01E02 https://example.com/abc", "manual")
    assert items and items[0]["episode"] == 2
    d = diagnose(s, "三体", 1, 3)
    assert d["present"] == [1] and d["missing"] == [2, 3] and not d["complete"]
