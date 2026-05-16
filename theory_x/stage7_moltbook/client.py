"""Moltbook REST client. Thin wrapper over /api/v1/. Auth via Bearer token.
Loads key from ~/.config/moltbook/credentials.json on init."""
from __future__ import annotations
import json
import logging
import os
import time
from pathlib import Path
from typing import Any
import urllib.parse
import urllib.request
import urllib.error

log = logging.getLogger("theory_x.stage7_moltbook.client")

BASE = "https://www.moltbook.com/api/v1"
DEFAULT_CREDS = Path.home() / ".config" / "moltbook" / "credentials.json"
TIMEOUT_SEC = 20
USER_AGENT = "nex5-moltbook-client/0.1"


class MoltbookError(Exception):
    """Base for all client errors."""


class AuthError(MoltbookError):
    """Missing or invalid credentials."""


class RateLimited(MoltbookError):
    """429 from server."""

    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(f"rate limited (retry_after={retry_after})")


class ApiError(MoltbookError):
    """4xx / 5xx response."""

    def __init__(self, status: int, body: str):
        self.status = status
        self.body = body
        super().__init__(f"http {status}: {body[:200]}")


class MoltbookClient:
    def __init__(self, creds_path: Path | str = DEFAULT_CREDS, dry_run: bool | None = None):
        self.creds_path = Path(creds_path).expanduser()
        if dry_run is None:
            dry_run = os.environ.get("MOLTBOOK_DRY_RUN", "1") == "1"
        self.dry_run = dry_run
        self.api_key = self._load_key()

    def _load_key(self) -> str:
        if not self.creds_path.exists():
            raise AuthError(f"creds file missing: {self.creds_path}")
        try:
            data = json.loads(self.creds_path.read_text())
        except json.JSONDecodeError as e:
            raise AuthError(f"creds file unreadable: {e}") from e
        key = data.get("api_key")
        if not key or not isinstance(key, str):
            raise AuthError(f"creds file has no api_key field: {self.creds_path}")
        return key

    # -- core HTTP --

    def _request(self, method: str, path: str, body: dict | None = None,
                 params: dict | None = None) -> Any:
        url = BASE + path
        if params:
            url += "?" + urllib.parse.urlencode(params)

        if self.dry_run and method != "GET":
            log.info("DRY_RUN %s %s body=%s", method, path, body)
            return {"dry_run": True, "method": method, "path": path, "body": body}

        data = None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                if not raw:
                    return None
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return {"raw": raw}
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                raise RateLimited(retry_after=float(ra) if ra else None) from e
            raise ApiError(e.code, body_text) from e
        except urllib.error.URLError as e:
            raise MoltbookError(f"network error: {e.reason}") from e

    def get(self, path: str, **params) -> Any:
        return self._request("GET", path, params=params or None)

    def post(self, path: str, body: dict | None = None) -> Any:
        return self._request("POST", path, body=body)

    # -- identity --

    def status(self) -> dict:
        return self.get("/agents/status")

    # -- outbound posts --

    def create_post(self, submolt: str, title: str, content: str) -> dict:
        return self.post("/posts", {"submolt": submolt, "title": title, "content": content})

    def post_comment(self, post_id: str, content: str) -> dict:
        """Endpoint guessed; probe via probe_comment_endpoint at startup."""
        return self.post(f"/posts/{post_id}/comments", {"content": content})

    def reply_to_comment(self, comment_id: str, content: str) -> dict:
        return self.post(f"/comments/{comment_id}/reply", {"content": content})

    def probe_comment_endpoint(self, sample_post_id: str | None = None) -> bool:
        """Return True if /posts/{id}/comments accepts POST."""
        if sample_post_id is None:
            posts = self.get_posts(sort="new", limit=1) or []
            if not posts:
                return False
            sample_post_id = (posts[0] or {}).get("id")
            if not sample_post_id:
                return False
        try:
            self.post_comment(sample_post_id, "[probe]")
            return True
        except ApiError as e:
            if e.status == 404:
                return False
            # Other errors (rate limit, auth) don't disprove existence
            return True
        except RateLimited:
            return True

    # -- feed reads --

    def get_feed(self, sort: str = "new", limit: int = 15) -> list:
        r = self.get("/feed", sort=sort, limit=limit)
        return r if isinstance(r, list) else (r.get("posts") if isinstance(r, dict) else []) or []

    def get_posts(self, sort: str = "new", limit: int = 15) -> list:
        r = self.get("/posts", sort=sort, limit=limit)
        return r if isinstance(r, list) else (r.get("posts") if isinstance(r, dict) else []) or []

    def get_submolts(self) -> list:
        r = self.get("/submolts")
        return r if isinstance(r, list) else (r.get("submolts") if isinstance(r, dict) else []) or []

    # -- DMs --

    def dm_check(self) -> dict:
        return self.get("/agents/dm/check") or {}

    def dm_list_requests(self) -> list:
        r = self.get("/agents/dm/requests") or {}
        return r.get("requests") or r.get("items") or []

    def dm_approve(self, conv_id: str) -> dict:
        return self.post(f"/agents/dm/requests/{conv_id}/approve")

    def dm_reject(self, conv_id: str, block: bool = False) -> dict:
        return self.post(f"/agents/dm/requests/{conv_id}/reject", {"block": block} if block else None)

    def dm_list_conversations(self) -> list:
        r = self.get("/agents/dm/conversations") or {}
        convs = r.get("conversations")
        if isinstance(convs, dict):
            return convs.get("items") or []
        return convs or []

    def dm_read(self, conv_id: str) -> dict:
        return self.get(f"/agents/dm/conversations/{conv_id}") or {}

    def dm_send(self, conv_id: str, message: str, needs_human: bool = False) -> dict:
        body: dict[str, Any] = {"message": message}
        if needs_human:
            body["needs_human_input"] = True
        return self.post(f"/agents/dm/conversations/{conv_id}/send", body)

    def dm_request(self, to: str | None = None, to_owner: str | None = None,
                   message: str = "") -> dict:
        body: dict[str, Any] = {"message": message}
        if to:
            body["to"] = to
        if to_owner:
            body["to_owner"] = to_owner
        return self.post("/agents/dm/request", body)


def with_backoff(fn, *args, max_tries: int = 4, base_delay: float = 1.0, **kwargs):
    """Call fn with retries on 5xx + rate limit. Used by callers, not internal."""
    last_exc: Exception | None = None
    for attempt in range(max_tries):
        try:
            return fn(*args, **kwargs)
        except RateLimited as e:
            delay = e.retry_after or (base_delay * (2 ** attempt))
            log.warning("rate_limited attempt=%d sleep=%.1f", attempt, delay)
            time.sleep(delay)
            last_exc = e
        except ApiError as e:
            if 500 <= e.status < 600:
                delay = base_delay * (2 ** attempt)
                log.warning("server_5xx attempt=%d sleep=%.1f status=%d", attempt, delay, e.status)
                time.sleep(delay)
                last_exc = e
                continue
            raise
    if last_exc:
        raise last_exc
