# -*- coding: utf-8 -*-
"""Password hashing — compatible with BFF sha256$<salt>$<hex>."""
from __future__ import annotations

import hashlib
import re

DEFAULT_SALT = "expect-beta-v1"


def hash_password(password: str, salt: str = DEFAULT_SALT) -> str:
    raw = f"{salt}:{password}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return f"sha256${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    if not stored or not isinstance(stored, str):
        return False
    parts = stored.split("$")
    if len(parts) != 3 or parts[0] != "sha256":
        return False
    return hash_password(password, parts[1]) == stored


def is_strong_enough_password(password: str) -> bool:
    return len(str(password or "")) >= 8


def is_valid_login_id(login_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]{4,32}", str(login_id or "").strip()))
