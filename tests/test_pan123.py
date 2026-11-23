import json

import httpx

from app.guangya import direct_url
from app.pan123 import Pan123Client


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _Client:
    """Fake httpx.Client: token, file list, enable, direct url."""
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def post(self, url, headers=None, json=None):
        if url.endswith("/api/v1/access_token"):
            return _Resp({"code": 0, "data": {"accessToken": "tok123", "expiredAt": 9999999999}})
        if url.endswith("/api/v1/direct-link/enable"):
            return _Resp({"code": 0, "data": {"filename": "Movies"}})
        raise AssertionError(url)

    def get(self, url, headers=None, params=None):
        if "/api/v2/file/list" in url:
            parent = params.get("parentFileId", 0)
            if parent == 0:
                return _Resp({"code": 0, "data": {"fileList": [{"filename": "Movies", "fileId": 10}]}})
            return _Resp({"code": 0, "data": {"fileList": [{"filename": "a.mkv", "fileId": 11}]}})
        if "/api/v1/direct-link/url" in url:
            return _Resp({"code": 0, "data": {"url": "https://direct.123pan.com/a.mkv"}})
        raise AssertionError(url)


def test_pan123_direct_link_for_path(monkeypatch, tmp_path):
    monkeypatch.setattr(httpx, "Client", _Client)
    c = Pan123Client("id", "secret", data_dir=tmp_path)
    assert c.direct_link_for_path("Movies/a.mkv") == "https://direct.123pan.com/a.mkv"
    assert json.loads((tmp_path / "pan123_token.json").read_text())["accessToken"] == "tok123"


def test_guangya_member_assumed_no_base_url():
    r = direct_url("", "/CloudNAS/gy", "/CloudNAS/gy/a.mkv")
    assert not r["ok"] and "Membership is assumed" in r["error"]


def test_guangya_direct_url():
    r = direct_url("https://gy.example.com", "/CloudNAS/gy", "/CloudNAS/gy/a.mkv")
    assert r["ok"] and r["target"].endswith("/a.mkv")
