# -*- coding: utf-8 -*-
"""Strip query/cookies/tokens before any budget log or ledger field."""
from __future__ import annotations

from urllib.parse import urlparse


def public_target(url: str) -> tuple[str, str, str]:
    """Return (source, host, path) with query/fragment removed."""
    parsed = urlparse(url or "")
    host = (parsed.netloc or "").split("@")[-1].lower()
    path = parsed.path or "/"
    if "netkeiba" in host:
        source = "netkeiba"
    elif host:
        source = "other"
    else:
        source = "unknown"
    return source, host, path


def log_safe(message: str) -> str:
    """Drop common secret-bearing fragments from operator logs."""
    text = message or ""
    for marker in ("?", "cookie", "token", "authorization", "api_key"):
        if marker in text.lower() and marker == "?":
            text = text.split("?", 1)[0]
    return text
