# -*- coding: utf-8 -*-
"""Strip query/cookies/tokens before any budget log or ledger field."""
from __future__ import annotations

from urllib.parse import urlparse


def public_target(url: str) -> tuple[str, str, str]:
    """Return (source, host, path) with userinfo/query/fragment removed."""
    parsed = urlparse(url or "")
    host = (parsed.hostname or "").lower()
    if not host:
        host = (parsed.netloc or "").split("@")[-1].lower()
        if ":" in host and host.rsplit(":", 1)[-1].isdigit():
            host = host.rsplit(":", 1)[0]
    path = parsed.path or "/"
    if "netkeiba" in host:
        source = "netkeiba"
    elif host:
        source = "other"
    else:
        source = "unknown"
    return source, host, path


def public_url(url: str) -> str:
    """Public scheme://host/path only. No userinfo, query, or fragment."""
    parsed = urlparse(url or "")
    _source, host, path = public_target(url)
    scheme = (parsed.scheme or "").lower()
    if host and scheme:
        return f"{scheme}://{host}{path}"
    if host:
        return f"{host}{path}"
    return path


def log_safe(message: str) -> str:
    """Drop query/fragment and common secret-bearing fragments from operator logs."""
    text = message or ""
    if "?" in text:
        text = text.split("?", 1)[0]
    if "#" in text:
        text = text.split("#", 1)[0]
    if "://" in text and "@" in text.split("://", 1)[1].split("/", 1)[0]:
        scheme, rest = text.split("://", 1)
        after_at = rest.split("@", 1)[1]
        text = f"{scheme}://{after_at}"
    return text
