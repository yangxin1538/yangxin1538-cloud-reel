from app.diversion import resolve
from app.drives import build_direct_url, detect_share_drive
from app.sources import Source


def test_detect_123_share():
    assert detect_share_drive("https://www.123pan.com/s/abc") == "123"
    assert detect_share_drive("https://yun.123pan.com/s/abc") == "123"


def test_123_needs_base_url():
    r = build_direct_url("123", "", "/CloudNAS/123", "/CloudNAS/123/a.mkv")
    assert not r["ok"] and "RequestAccessToken" in r["error"]


def test_guangya_needs_base_url():
    r = build_direct_url("guangya", "", "/CloudNAS/gy", "/CloudNAS/gy/a.mkv")
    assert not r["ok"] and "Authorization" in r["error"]


def test_123_direct_url_with_base():
    r = build_direct_url("123", "https://direct.example.com", "/CloudNAS/123", "/CloudNAS/123/a.mkv")
    assert r["ok"] and r["target"].endswith("/a.mkv")


def test_direct123_mode():
    sources = [
        Source(id="s123", name="123", type="123", root="/CloudNAS/123", base_url="https://direct.example.com"),
        Source(id="cd2", name="CD2", type="clouddrive2", root="/CloudNAS"),
    ]
    r = resolve("/CloudNAS/123/a.mkv", sources, "direct123")
    assert r["ok"] and r["source"] == "s123"


def test_directguangya_requires_source():
    sources = [Source(id="cd2", name="CD2", type="clouddrive2", root="/CloudNAS")]
    r = resolve("/CloudNAS/a.mkv", sources, "directguangya")
    assert not r["ok"]
