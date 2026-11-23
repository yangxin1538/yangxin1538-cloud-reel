from app.diversion import resolve
from app.sources import Source


def test_smart_picks_cd2():
    sources = [Source(id="cd2", name="CD2", type="clouddrive2", root="/CloudNAS", weight=100)]
    r = resolve("/CloudNAS/电影/片名 (2024).mkv", sources, "smart")
    assert r["ok"] and r["source"] == "cd2"


def test_url_passthrough():
    sources = [Source(id="cd2", name="CD2", type="clouddrive2", root="/CloudNAS")]
    r = resolve("https://example.com/video.mp4", sources, "redirect302")
    assert r["ok"] and r["target"] == "https://example.com/video.mp4"


def test_direct115_requires_115():
    sources = [Source(id="cd2", name="CD2", type="clouddrive2", root="/CloudNAS")]
    r = resolve("/CloudNAS/电影/片名.mkv", sources, "direct115")
    assert not r["ok"]
