# -*- coding: utf-8 -*-
"""P1 refresh lock — W2 reads; P1 writes. Missing file = IDLE."""
from __future__ import annotations

import json
import os
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

P1LockState = Literal["IDLE", "STARTING", "ACTIVE"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


@dataclass
class P1Lock:
    owner: str = "p1_race_refresh"
    state: P1LockState = "IDLE"
    acquired_at: str | None = None
    expires_at: str | None = None
    heartbeat_at: str | None = None
    process_identity: str | None = None
    race_date: str | None = None

    def to_dict(self) -> dict:
        return {
            "owner": self.owner,
            "state": self.state,
            "acquired_at": self.acquired_at,
            "expires_at": self.expires_at,
            "heartbeat_at": self.heartbeat_at,
            "process_identity": self.process_identity,
            "race_date": self.race_date,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "P1Lock":
        state = d.get("state") or "IDLE"
        if state not in ("IDLE", "STARTING", "ACTIVE"):
            state = "IDLE"
        return cls(
            owner=str(d.get("owner") or "p1_race_refresh"),
            state=state,  # type: ignore[arg-type]
            acquired_at=d.get("acquired_at"),
            expires_at=d.get("expires_at"),
            heartbeat_at=d.get("heartbeat_at"),
            process_identity=d.get("process_identity"),
            race_date=d.get("race_date"),
        )


def process_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{os.environ.get('W2_RUN_ID', 'p1')}"


def read_p1_lock(path: Path, *, now: datetime | None = None) -> P1Lock:
    """Read lock; apply stale → IDLE. Missing file = IDLE."""
    now = now or _utc_now()
    if not path.exists():
        return P1Lock(state="IDLE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        lock = P1Lock.from_dict(data if isinstance(data, dict) else {})
    except (OSError, json.JSONDecodeError):
        return P1Lock(state="IDLE")

    if lock.state == "IDLE":
        return lock

    expires = _parse_iso(lock.expires_at)
    heartbeat = _parse_iso(lock.heartbeat_at) or _parse_iso(lock.acquired_at)
    stale = False
    if expires is not None and now > expires:
        stale = True
    elif heartbeat is not None and now - heartbeat > timedelta(minutes=30):
        # Safety: long silence without refresh → stale
        stale = True
    if stale:
        return P1Lock(
            owner=lock.owner,
            state="IDLE",
            acquired_at=lock.acquired_at,
            expires_at=lock.expires_at,
            heartbeat_at=lock.heartbeat_at,
            process_identity=lock.process_identity,
            race_date=lock.race_date,
        )
    return lock


def write_p1_lock(path: Path, lock: P1Lock) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(lock.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def acquire_p1_lock(
    path: Path,
    *,
    race_date: str | None = None,
    ttl_sec: float = 3600.0,
    state: P1LockState = "ACTIVE",
) -> P1Lock:
    now = _utc_now()
    lock = P1Lock(
        state=state,
        acquired_at=_iso(now),
        expires_at=_iso(now + timedelta(seconds=ttl_sec)),
        heartbeat_at=_iso(now),
        process_identity=process_identity(),
        race_date=race_date,
    )
    write_p1_lock(path, lock)
    return lock


def heartbeat_p1_lock(path: Path, *, ttl_sec: float = 3600.0) -> None:
    lock = read_p1_lock(path)
    if lock.state == "IDLE":
        return
    now = _utc_now()
    lock.heartbeat_at = _iso(now)
    lock.expires_at = _iso(now + timedelta(seconds=ttl_sec))
    write_p1_lock(path, lock)


def release_p1_lock(path: Path) -> None:
    now = _utc_now()
    write_p1_lock(
        path,
        P1Lock(
            state="IDLE",
            acquired_at=_iso(now),
            expires_at=_iso(now),
            heartbeat_at=_iso(now),
            process_identity=process_identity(),
        ),
    )


def p1_allows_w2(path: Path, *, now: datetime | None = None) -> bool:
    return read_p1_lock(path, now=now).state == "IDLE"


@contextmanager
def p1_lock_session(
    path: Path,
    *,
    race_date: str | None = None,
    ttl_sec: float = 3600.0,
) -> Iterator[P1Lock]:
    """P1 exclusive session: STARTING → ACTIVE → IDLE (always release)."""
    acquire_p1_lock(path, race_date=race_date, ttl_sec=ttl_sec, state="STARTING")
    lock = acquire_p1_lock(path, race_date=race_date, ttl_sec=ttl_sec, state="ACTIVE")
    try:
        yield lock
    finally:
        release_p1_lock(path)
