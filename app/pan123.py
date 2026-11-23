"""123 cloud drive open-platform client.

Verified endpoints (123 open platform, base https://open-api.123pan.com):
  POST /api/v1/access_token   {clientID, clientSecret} -> accessToken, expiredAt
  GET  /api/v2/file/list      ?parentFileId=&page=&limit=
  POST /api/v1/direct-link/enable {fileID}  (folder-level)
  GET  /api/v1/direct-link/url?fileID=
All calls send header `Platform: open_platform`; authenticated calls
send `Authorization: Bearer <accessToken>`.

Assumption (user, 2026-11-23): the user has a membership on every
cloud drive, so direct-link / developer privileges are assumed
available. No membership check is done here.

Credentials come from env PAN123_CLIENT_ID / PAN123_CLIENT_SECRET or
from a Source's client_id / client_secret fields. The access token is
cached in data/pan123_token.json (never in git) until expiredAt.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

BASE_URL = "https://open-api.123pan.com"


class Pan123Error(Exception):
    pass


def _headers(token: str | None = None) -> dict:
    h = {"Platform": "open_platform"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _check(resp: dict, what: str) -> dict:
    if resp.get("code") != 0:
        raise Pan123Error(f"{what} failed: {resp.get('message')}")
    return resp.get("data") or {}


class Pan123Client:
    def __init__(self, client_id: str, client_secret: str, data_dir: Path | str = "data", base_url: str = BASE_URL):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self.data_dir = Path(data_dir)
        self._token_file = self.data_dir / "pan123_token.json"

    def _load_cached_token(self) -> str | None:
        try:
            d = json.loads(self._token_file.read_text(encoding="utf-8"))
            if d.get("accessToken") and d.get("expiredAt", 0) > time.time() + 60:
                return d["accessToken"]
        except Exception:
            pass
        return None

    def access_token(self) -> str:
        cached = self._load_cached_token()
        if cached:
            return cached
        with httpx.Client(timeout=30) as c:
            r = c.post(
                f"{self.base_url}/api/v1/access_token",
                headers=_headers(),
                json={"clientID": self.client_id, "clientSecret": self.client_secret},
            )
        data = _check(r.json(), "123 access_token")
        token = data["accessToken"]
        expired = data.get("expiredAt")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._token_file.write_text(
            json.dumps({"accessToken": token, "expiredAt": expired}, ensure_ascii=False),
            encoding="utf-8",
        )
        return token

    def _get(self, path: str, params: dict | None = None) -> dict:
        token = self.access_token()
        with httpx.Client(timeout=30) as c:
            r = c.get(f"{self.base_url}{path}", headers=_headers(token), params=params or {})
        return _check(r.json(), f"123 GET {path}")

    def _post(self, path: str, payload: dict) -> dict:
        token = self.access_token()
        with httpx.Client(timeout=30) as c:
            r = c.post(f"{self.base_url}{path}", headers=_headers(token), json=payload)
        return _check(r.json(), f"123 POST {path}")

    def list_files(self, parent_file_id: int = 0, page: int = 1, limit: int = 100) -> list[dict]:
        data = self._get("/api/v2/file/list", {"parentFileId": parent_file_id, "page": page, "limit": limit})
        return data.get("fileList") or []

    def find_file_id(self, rel_path: str) -> int | None:
        """Resolve a path like 'Movies/Film (2023).mkv' to a 123 fileId."""
        parts = [p for p in Path(rel_path).parts if p not in ("/", ".")]
        parent = 0
        for part in parts:
            found = None
            page = 1
            while True:
                items = self.list_files(parent, page=page)
                if not items:
                    break
                for it in items:
                    if it.get("filename") == part:
                        found = it
                        break
                if found or len(items) < 100:
                    break
                page += 1
            if not found:
                return None
            parent = int(found["fileId"])
        return parent

    def enable_direct_link(self, folder_file_id: int) -> dict:
        return self._post("/api/v1/direct-link/enable", {"fileID": folder_file_id})

    def direct_link_url(self, file_id: int) -> str:
        data = self._get("/api/v1/direct-link/url", {"fileID": file_id})
        url = data.get("url") or data.get("directLink") or ""
        if not url:
            raise Pan123Error("123 direct-link/url returned no url")
        return url

    def direct_link_for_path(self, rel_path: str) -> str:
        """Enable direct link on the file's parent folder, then fetch the URL."""
        file_id = self.find_file_id(rel_path)
        if file_id is None:
            raise Pan123Error(f"123 file not found: {rel_path}")
        parent = self._parent_file_id(rel_path)
        if parent is not None:
            try:
                self.enable_direct_link(parent)
            except Pan123Error:
                pass  # already enabled is fine; url() is the real test
        return self.direct_link_url(file_id)

    def _parent_file_id(self, rel_path: str) -> int | None:
        parts = [p for p in Path(rel_path).parts if p not in ("/", ".")]
        if len(parts) < 2:
            return 0
        parent = 0
        for part in parts[:-1]:
            found = None
            for it in self.list_files(parent):
                if it.get("filename") == part:
                    found = it
                    break
            if not found:
                return None
            parent = int(found["fileId"])
        return parent
