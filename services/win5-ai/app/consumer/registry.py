# -*- coding: utf-8 -*-
"""Decision Registry — Policy table only (V109 C1).

Holds policy_id / strategy refs. MUST NOT hold Prediction ranks/scores.
MUST NOT rewrite Core / CEW / world_id.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

REGISTRY_VERSIONS = (
    "v88-decision-policy",
    "v95-residual-policy",
    "v75-expected-strategy",
    "decision-registry/v1",
)

# Ready / Partial worlds (V88)
_WORLD_POLICIES: dict[str, str] = {
    "rank7_world": "policy_rank7_ready",
    "midhole_world": "policy_midhole_partial",
    "unsatisfied": "policy_unsatisfied_conservative",
    "core_world": "policy_blocked_provisional",
    "midupper_world": "policy_blocked",
    "mixed_world": "policy_blocked",
    "bug_world": "policy_blocked_exception",
}

# Near Miss: conservative per near_world (V95) — never copies Ready Ticket strategy
_NEAR_MISS_POLICIES: dict[str, str] = {
    "core_world": "policy_near_miss_core_conservative",
    "midupper_world": "policy_near_miss_midupper_conservative",
    "midhole_world": "policy_near_miss_midhole_conservative",
    "rank7_world": "policy_near_miss_rank7_conservative",
}

FALLBACK_POLICY = "policy_legacy_fallback"
PURE_RESIDUAL_POLICY = "policy_pure_residual_conservative"

# Strategy registry keys mirror world_id (V75 KEEP_DERIVED) — not prediction
_STRATEGY_BY_WORLD: dict[str, str] = {
    "rank7_world": "rank7_world",
    "midhole_world": "midhole_world",
    "unsatisfied": "unsatisfied",
    "core_world": "core_world",
    "midupper_world": "midupper_world",
    "mixed_world": "mixed_world",
    "bug_world": "bug_world",
}


@dataclass(frozen=True)
class RegistryResolution:
    policy_id: str
    strategy_id: str
    registry_versions: tuple[str, ...] = REGISTRY_VERSIONS
    world_id: str | None = None
    residual_class: str | None = None
    near_world: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _world_id_from_core(core: Mapping[str, Any]) -> str | None:
    w = core.get("world_id")
    if w is not None and str(w) != "":
        return str(w)
    return None


def _near_miss_meta(core: Mapping[str, Any]) -> tuple[str | None, str | None]:
    nm = core.get("near_miss")
    if not isinstance(nm, Mapping):
        return None, None
    residual = nm.get("residual_class")
    near = nm.get("near_world")
    return (
        str(residual) if residual is not None else None,
        str(near) if near is not None else None,
    )


def resolve_policy(core: Mapping[str, Any]) -> RegistryResolution:
    """Map Core semantic selectors → policy_id.

    Reads world_id / near_miss only. Ignores prediction entirely.
    Does not mutate ``core``.
    """
    world_id = _world_id_from_core(core)
    residual, near_world = _near_miss_meta(core)
    notes: list[str] = []

    if world_id is None:
        notes.append("missing_world_id_fallback")
        return RegistryResolution(
            policy_id=FALLBACK_POLICY,
            strategy_id="unknown",
            world_id=None,
            residual_class=residual,
            near_world=near_world,
            notes=tuple(notes),
        )

    strategy_id = _STRATEGY_BY_WORLD.get(world_id, world_id)

    if world_id == "unsatisfied":
        if residual == "NEAR_MISS":
            if near_world and near_world in _NEAR_MISS_POLICIES:
                return RegistryResolution(
                    policy_id=_NEAR_MISS_POLICIES[near_world],
                    strategy_id=strategy_id,
                    world_id=world_id,
                    residual_class=residual,
                    near_world=near_world,
                    notes=("near_miss_conservative",),
                )
            notes.append("near_miss_missing_near_world")
            return RegistryResolution(
                policy_id=PURE_RESIDUAL_POLICY,
                strategy_id=strategy_id,
                world_id=world_id,
                residual_class=residual,
                near_world=near_world,
                notes=tuple(notes),
            )
        # PURE_RESIDUAL or unspecified
        return RegistryResolution(
            policy_id=PURE_RESIDUAL_POLICY if residual == "PURE_RESIDUAL" else _WORLD_POLICIES["unsatisfied"],
            strategy_id=strategy_id,
            world_id=world_id,
            residual_class=residual,
            near_world=near_world,
            notes=("unsatisfied_conservative",),
        )

    policy = _WORLD_POLICIES.get(world_id)
    if policy is None:
        notes.append("unknown_world_fallback")
        return RegistryResolution(
            policy_id=FALLBACK_POLICY,
            strategy_id=strategy_id,
            world_id=world_id,
            residual_class=residual,
            near_world=near_world,
            notes=tuple(notes),
        )

    return RegistryResolution(
        policy_id=policy,
        strategy_id=strategy_id,
        world_id=world_id,
        residual_class=residual,
        near_world=near_world,
        notes=tuple(notes),
    )


def registry_holds_prediction(resolution: RegistryResolution) -> bool:
    """Contract guard helper — Registry output must never embed ranks/scores."""
    blob = resolution.to_dict()
    forbidden = ("ranks", "scores", "prediction", "win_prob", "model_rank")
    return any(k in blob for k in forbidden)
