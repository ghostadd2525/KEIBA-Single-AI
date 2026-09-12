# -*- coding: utf-8 -*-
"""FeatureLoader 入力の単一ピン。GET では未設定のため既存 load のまま。"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any, Iterator

_pinned_feature: ContextVar[Any] = ContextVar("pinned_feature", default=None)
_persist_pin_required: ContextVar[bool] = ContextVar("persist_pin_required", default=False)


class FeatureLoadFailed(RuntimeError):
    code = "FEATURE_LOAD_FAILED"


class FeatureLoadReloadForbidden(FeatureLoadFailed):
    code = "FEATURE_LOAD_RELOAD_FORBIDDEN"


@dataclass(frozen=True)
class PinnedFeatureLoad:
    core_race_id: str
    result: Any


def get_pinned_feature() -> PinnedFeatureLoad | None:
    pin = _pinned_feature.get()
    return pin if isinstance(pin, PinnedFeatureLoad) else None


def get_pinned_feature_load() -> Any:
    pin = get_pinned_feature()
    return None if pin is None else pin.result


def persist_pin_required() -> bool:
    return bool(_persist_pin_required.get())


def set_pinned_feature_load(result: Any, *, core_race_id: str) -> Token[Any]:
    return _pinned_feature.set(PinnedFeatureLoad(core_race_id=str(core_race_id), result=result))


def reset_pinned_feature_load(token: Token[Any]) -> None:
    _pinned_feature.reset(token)


@contextmanager
def pin_feature_load(result: Any, *, core_race_id: str, required: bool = True) -> Iterator[None]:
    """POST infer / snapshot が同じ FeatureLoadResult を再利用する。再 load 禁止。"""
    if required and result is None:
        raise FeatureLoadFailed("feature loader result is required for persist POST")
    rid = str(core_race_id or "").strip()
    if not rid:
        raise FeatureLoadFailed("pinned feature load requires core_race_id")
    token = set_pinned_feature_load(result, core_race_id=rid)
    req_token = _persist_pin_required.set(True)
    try:
        yield
    finally:
        _persist_pin_required.reset(req_token)
        reset_pinned_feature_load(token)
