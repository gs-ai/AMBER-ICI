"""Validation for AMBER services that must remain on the local machine."""

from __future__ import annotations

import urllib.parse


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def require_loopback_http_url(value: str) -> str:
    """Return a validated HTTP(S) loopback URL or raise ``ValueError``."""
    raw = str(value or "").strip()
    try:
        parsed = urllib.parse.urlparse(raw)
        _ = parsed.port
    except ValueError as error:
        raise ValueError("local model URL has an invalid port") from error
    if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() not in LOOPBACK_HOSTS:
        raise ValueError("local model URL must use http(s) on 127.0.0.1, localhost, or ::1")
    if parsed.username or parsed.password:
        raise ValueError("local model URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("local model URL must not contain a query or fragment")
    return raw
