# -*- coding: utf-8 -*-
"""
Version18 Research Knowledge Base

Transform V17 Evidence Discovery into structured Knowledge entries
for Version19+ improvement candidate input.

FORBIDDEN to mutate:
  Prediction / PE / CE / AI / Challenge / Resolver /
  ResultAutomation / Shadow / Production
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..data.db import connect, migrate
from .config import evidence_root, repo_root
from .evidence_discovery import (
    CONFIDENT_MIN_N,
    FEATURE_LABELS,
    wilson_ci,
)
from .young_horse_intelligence import _pct, _safe_div

SCHEMA_VERSION = "expect-knowledge-base/1.0"

CONFIDENCE_LEVELS = ("High", "Medium", "Low", "Exploratory")
ACTIONS = ("Research", "Shadow", "Candidate", "Reject", "Watch")
LIMITATION_TAGS = (
    "insufficient_n",
    "coverage_gap",
    "selection_bias",
    "missing_metadata",
    "roi_unavailable",
    "exploratory_corpus",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _week_id(dt: datetime | None = None) -> str:
    d = dt or datetime.now(timezone.utc)
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _kid(*parts: str) -> str:
    raw = "|".join(str(p) for p in parts if p)
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"kb-{h}"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _limitations(
    *,
    n: int | None = None,
    coverage: float | None = None,
    gate: dict[str, Any] | None = None,
    exploratory_corpus: bool = False,
    roi_available: bool = True,
    extra: list[str] | None = None,
) -> list[str]:
    out: list[str] = []
    if n is not None and n < CONFIDENT_MIN_N:
        out.append("insufficient_n")
    if coverage is not None and coverage < 0.5:
        out.append("coverage_gap")
    if exploratory_corpus:
        out.append("exploratory_corpus")
    if not roi_available:
        out.append("roi_unavailable")
    g = gate or {}
    if g.get("gate_reason") == "ci95_low_not_above_baseline":
        out.append("selection_bias")
    if extra:
        for x in extra:
            if x in LIMITATION_TAGS and x not in out:
                out.append(x)
    if not out and n == 0:
        out.append("missing_metadata")
    return out


def _confidence_level(
    *,
    gate: dict[str, Any] | None,
    n: int,
    reliability: float | None = None,
    exploratory_corpus: bool = False,
) -> str:
    g = gate or {}
    if exploratory_corpus and n < CONFIDENT_MIN_N:
        return "Exploratory"
    if g.get("confident") and n >= CONFIDENT_MIN_N:
        if reliability is None or reliability >= 65:
            return "High"
        return "Medium"
    if n >= 10:
        return "Medium"
    if n >= 5:
        return "Low"
    return "Exploratory"


def _recommended_action(
    *,
    confidence: str,
    knowledge_type: str,
    rate: float | None = None,
    baseline: float | None = None,
    reliability: float | None = None,
) -> str:
    if confidence == "Exploratory":
        return "Research"
    if reliability is not None and reliability < 50:
        return "Watch"
    if rate is not None and baseline is not None and rate < baseline * 0.8:
        return "Reject"
    if confidence == "High":
        if knowledge_type in {"interaction", "feature"}:
            return "Candidate"
        if knowledge_type == "segment":
            return "Watch"
        return "Shadow"
    if confidence == "Medium":
        return "Watch"
    if confidence == "Low":
        return "Research"
    return "Research"


def _hypothesis_text(
    knowledge_type: str,
    *,
    feature: str | None = None,
    segment: str | None = None,
    pattern: str | None = None,
    direction: str = "positive",
) -> str:
    """Non-definitive hypothesis language only."""
    if knowledge_type == "feature" and feature:
        if direction == "positive":
            return (
                f"{feature} may correlate with winner selection in this segment; "
                "causation is not established."
            )
        return (
            f"{feature} may be weak or noisy in this segment; "
            "further Evidence collection is needed before any product use."
        )
    if knowledge_type == "interaction" and pattern:
        return (
            f"The combination `{pattern}` may indicate a recurring winner profile; "
            "this is a research pattern, not a proven rule."
        )
    if knowledge_type == "segment" and segment:
        return (
            f"Category `{segment}` may behave differently from the global baseline; "
            "segment-specific factors could include class, field, or market effects."
        )
    if knowledge_type == "failure":
        return (
            "Prediction misses may cluster under these conditions; "
            "root cause could be market shift, sparse Evidence, or segment mismatch."
        )
    if knowledge_type == "winner":
        return (
            "Prediction hits may cluster under these conditions; "
            "repeatability across future samples is not guaranteed."
        )
    return "Observed pattern may warrant further research; no causal claim is made."


def _parse_pattern_features(pattern: str | None) -> list[str]:
    if not pattern:
        return []
    feats = []
    for part in str(pattern).split("|"):
        if "=" in part:
            feats.append(part.split("=", 1)[0].strip())
    return feats


class KnowledgeBaseBuilder:
    def __init__(self) -> None:
        migrate()
        self.root = repo_root()
        self.evidence = evidence_root()

    def _load_v17(self) -> dict[str, Any]:
        path = self.evidence / "reports" / "v17-evidence-discovery.json"
        data = _load_json(path)
        if data:
            return data
        from .evidence_discovery import EvidenceDiscoveryResearch

        research = EvidenceDiscoveryResearch()
        return research.analyze()

    def _load_reliability(self) -> dict[str, float]:
        path = self.evidence / "reports" / "v14-evidence-reliability.json"
        data = _load_json(path)
        out: dict[str, float] = {}
        for f in data.get("features") or []:
            fid = str(f.get("feature_id") or "")
            if fid:
                out[fid] = float(f.get("reliability_score") or 50.0)
        return out

    def _load_weakness_roi(self) -> dict[str, float]:
        """segment key -> roi from V15/V16 atlas if available."""
        out: dict[str, float] = {}
        for name in ("v16-weakness-atlas.json", "v15-weakness-atlas.json"):
            data = _load_json(self.evidence / "reports" / name)
            for axis, rows in (data.get("by_axis") or {}).items():
                for r in rows:
                    seg = str(r.get("segment") or "")
                    if r.get("roi") is not None:
                        out[f"{axis}:{seg}"] = float(r["roi"])
        return out

    def build_entries(self, v17: dict[str, Any]) -> list[dict[str, Any]]:
        sample = v17.get("sample") or {}
        exploratory_corpus = bool(sample.get("exploratory"))
        global_strict = float(sample.get("global_strict") or 0.0)
        global_soft = float(sample.get("global_soft") or 0.0)
        reliability_map = self._load_reliability()
        roi_map = self._load_weakness_roi()
        entries: list[dict[str, Any]] = []

        # --- Feature importance ---
        for cat, rows in (
            v17.get("feature_importance") or {}
        ).get("by_category_horse_features", {}).items():
            for row in rows:
                fid = str(row.get("feature_id") or "")
                gate = row.get("gate") or {}
                n = int(gate.get("n") or row.get("field_resolved") or 0)
                hits = int(gate.get("successes") or row.get("field_correct") or 0)
                cov = float(row.get("coverage") or 0.0)
                rel = reliability_map.get(fid)
                conf = _confidence_level(
                    gate=gate,
                    n=n,
                    reliability=rel,
                    exploratory_corpus=exploratory_corpus,
                )
                lo, hi = wilson_ci(hits, n) if n else (0.0, 1.0)
                limitations = _limitations(
                    n=n,
                    coverage=cov,
                    gate=gate,
                    exploratory_corpus=exploratory_corpus,
                    roi_available=False,
                )
                action = _recommended_action(
                    confidence=conf,
                    knowledge_type="feature",
                    rate=row.get("field_hit_rate"),
                    baseline=gate.get("baseline"),
                    reliability=rel,
                )
                source_key = f"feature:{cat}:{fid}"
                entries.append(
                    {
                        "knowledge_id": _kid("feature", cat, fid),
                        "knowledge_type": "feature",
                        "observation": (
                            f"In category `{cat}`, {row.get('label')} resolved {n} field picks "
                            f"with hit rate {_pct(row.get('field_hit_rate'))} "
                            f"(tie hit {_pct(row.get('tie_hit_rate'))}, "
                            f"importance={row.get('importance_score')})."
                        ),
                        "evidence": {
                            "n": n,
                            "hit": hits,
                            "hit_rate": row.get("field_hit_rate"),
                            "soft": row.get("tie_hit_rate"),
                            "roi": None,
                            "wilson_ci": {"low": round(lo, 4), "high": round(hi, 4)},
                            "coverage": cov,
                            "reliability": rel,
                        },
                        "hypothesis": _hypothesis_text(
                            "feature",
                            feature=row.get("label"),
                            segment=cat,
                            direction="positive"
                            if (row.get("field_hit_rate") or 0) >= (gate.get("baseline") or 0)
                            else "negative",
                        ),
                        "confidence": conf,
                        "limitations": limitations,
                        "recommended_action": action,
                        "graph": {
                            "features": [fid],
                            "segments": [cat] if cat != "ALL" else [],
                            "interactions": [],
                            "evidence_ids": [source_key],
                        },
                        "source_key": source_key,
                        "meta": {
                            "rank": row.get("rank"),
                            "avg_ig": row.get("avg_ig"),
                            "gate": gate,
                        },
                    }
                )

        # --- Race-axis segments from importance ---
        for axis, rows in (
            v17.get("feature_importance") or {}
        ).get("race_axis_segments", {}).items():
            for row in rows:
                seg = str(row.get("segment") or "")
                n = int(row.get("n") or 0)
                hits = int(round((row.get("strict_rate") or 0) * n))
                gate = row.get("gate") or {}
                lo, hi = wilson_ci(hits, n) if n else (0.0, 1.0)
                roi = roi_map.get(f"{axis}:{seg}")
                conf = _confidence_level(gate=gate, n=n, exploratory_corpus=exploratory_corpus)
                limitations = _limitations(
                    n=n,
                    gate=gate,
                    exploratory_corpus=exploratory_corpus,
                    roi_available=roi is not None,
                )
                action = _recommended_action(
                    confidence=conf,
                    knowledge_type="segment",
                    rate=row.get("strict_rate"),
                    baseline=global_strict,
                )
                source_key = f"race_axis:{axis}:{seg}"
                entries.append(
                    {
                        "knowledge_id": _kid("race_axis", axis, seg),
                        "knowledge_type": "segment",
                        "observation": (
                            f"Race axis `{axis}={seg}` shows Strict {_pct(row.get('strict_rate'))} "
                            f"on n={n} (lift vs global {row.get('lift_vs_global')})."
                        ),
                        "evidence": {
                            "n": n,
                            "hit": hits,
                            "hit_rate": row.get("strict_rate"),
                            "soft": None,
                            "roi": roi,
                            "wilson_ci": {"low": round(lo, 4), "high": round(hi, 4)},
                            "coverage": None,
                            "reliability": None,
                        },
                        "hypothesis": _hypothesis_text("segment", segment=f"{axis}={seg}"),
                        "confidence": conf,
                        "limitations": limitations,
                        "recommended_action": action,
                        "graph": {
                            "features": [axis],
                            "segments": [seg],
                            "interactions": [],
                            "evidence_ids": [source_key],
                        },
                        "source_key": source_key,
                        "meta": {"axis": axis, "segment": seg, "gate": gate},
                    }
                )

        # --- Category segments ---
        for row in (v17.get("segment_comparison") or {}).get("categories") or []:
            cat = str(row.get("category") or "")
            n = int(row.get("n") or 0)
            if not n:
                continue
            hits = int(round((row.get("strict_rate") or 0) * n))
            soft_hits = int(round((row.get("soft_rate") or 0) * n))
            gate = row.get("gate") or {}
            lo, hi = wilson_ci(hits, n)
            conf = _confidence_level(gate=gate, n=n, exploratory_corpus=exploratory_corpus)
            limitations = _limitations(
                n=n,
                coverage=_safe_div(row.get("evidence_n"), n),
                gate=gate,
                exploratory_corpus=exploratory_corpus,
                roi_available=False,
            )
            action = _recommended_action(
                confidence=conf,
                knowledge_type="segment",
                rate=row.get("strict_rate"),
                baseline=global_strict,
            )
            source_key = f"category:{cat}"
            entries.append(
                {
                    "knowledge_id": _kid("category", cat),
                    "knowledge_type": "segment",
                    "observation": (
                        f"Category `{cat}`: Strict {_pct(row.get('strict_rate'))}, "
                        f"Soft {_pct(row.get('soft_rate'))}, Tie {_pct(row.get('tie_rate'))} "
                        f"on n={n} (evidence snapshots={row.get('evidence_n')})."
                    ),
                    "evidence": {
                        "n": n,
                        "hit": hits,
                        "hit_rate": row.get("strict_rate"),
                        "soft": row.get("soft_rate"),
                        "soft_hits": soft_hits,
                        "roi": None,
                        "wilson_ci": {"low": round(lo, 4), "high": round(hi, 4)},
                        "coverage": _safe_div(row.get("evidence_n"), n),
                        "reliability": None,
                    },
                    "hypothesis": _hypothesis_text("segment", segment=cat),
                    "confidence": conf,
                    "limitations": limitations,
                    "recommended_action": action,
                    "graph": {
                        "features": [],
                        "segments": [cat],
                        "interactions": [],
                        "evidence_ids": [source_key],
                    },
                    "source_key": source_key,
                    "meta": {
                        "research_notes": row.get("research_notes"),
                        "surface_mix": row.get("surface_mix"),
                        "gate": gate,
                    },
                }
            )

        # --- Interactions ---
        inter = v17.get("interactions") or {}
        for kind, rows, itype in (
            ("cascade_2way", inter.get("cascade_2way") or [], "cascade"),
            ("mined_2way", inter.get("mined_2way") or [], "mined_2way"),
            ("mined_3way", inter.get("mined_3way") or [], "mined_3way"),
        ):
            for row in rows:
                if kind == "cascade_2way":
                    key = row.get("key") or "×".join(row.get("features") or [])
                    pattern = key
                    n = int(row.get("cascade_resolved") or 0)
                    hits = int(row.get("cascade_correct") or 0)
                    rate = row.get("cascade_hit_rate")
                else:
                    pattern = str(row.get("pattern") or "")
                    n = int(row.get("n_horses") or 0)
                    hits = int(row.get("wins") or 0)
                    rate = row.get("win_rate")
                gate = row.get("gate") or {}
                feats = (
                    list(row.get("features") or [])
                    if kind == "cascade_2way"
                    else _parse_pattern_features(pattern)
                )
                rel_vals = [reliability_map.get(f) for f in feats if f in reliability_map]
                rel = sum(rel_vals) / len(rel_vals) if rel_vals else None
                lo, hi = wilson_ci(hits, n) if n else (0.0, 1.0)
                conf = _confidence_level(
                    gate=gate, n=n, reliability=rel, exploratory_corpus=exploratory_corpus
                )
                limitations = _limitations(
                    n=n,
                    gate=gate,
                    exploratory_corpus=exploratory_corpus,
                    roi_available=False,
                )
                action = _recommended_action(
                    confidence=conf,
                    knowledge_type="interaction",
                    rate=rate,
                    baseline=gate.get("baseline"),
                    reliability=rel,
                )
                source_key = f"interaction:{itype}:{pattern}"
                entries.append(
                    {
                        "knowledge_id": _kid("interaction", itype, pattern),
                        "knowledge_type": "interaction",
                        "observation": (
                            f"Interaction `{pattern}` ({itype}): "
                            f"rate={_pct(rate)} on n={n}."
                        ),
                        "evidence": {
                            "n": n,
                            "hit": hits,
                            "hit_rate": rate,
                            "soft": None,
                            "roi": None,
                            "wilson_ci": {"low": round(lo, 4), "high": round(hi, 4)},
                            "coverage": None,
                            "reliability": rel,
                        },
                        "hypothesis": _hypothesis_text(
                            "interaction", pattern=pattern
                        ),
                        "confidence": conf,
                        "limitations": limitations,
                        "recommended_action": action,
                        "graph": {
                            "features": feats,
                            "segments": [],
                            "interactions": [pattern],
                            "evidence_ids": [source_key],
                        },
                        "source_key": source_key,
                        "meta": {"interaction_type": itype, "gate": gate},
                    }
                )

        # --- Failure / Winner slices ---
        for label, block in (
            ("failure", v17.get("failure_analysis") or {}),
            ("winner", v17.get("winner_analysis") or {}),
        ):
            for cond in block.get("conditions") or []:
                axis = str(cond.get("axis") or "")
                seg = str(cond.get("segment") or "")
                cnt = int(cond.get("count") or 0)
                n_slice = int(block.get("n") or 0)
                gate = cond.get("gate") or {}
                lo, hi = wilson_ci(cnt, n_slice) if n_slice else (0.0, 1.0)
                conf = _confidence_level(
                    gate=gate, n=n_slice, exploratory_corpus=exploratory_corpus
                )
                limitations = _limitations(
                    n=n_slice,
                    gate=gate,
                    exploratory_corpus=exploratory_corpus,
                    roi_available=False,
                    extra=["selection_bias"] if label == "failure" else None,
                )
                action = "Research" if label == "failure" else "Watch"
                if conf == "High" and label == "winner":
                    action = "Candidate"
                source_key = f"{label}:{axis}:{seg}"
                entries.append(
                    {
                        "knowledge_id": _kid(label, axis, seg),
                        "knowledge_type": label,
                        "observation": (
                            f"{'Miss' if label == 'failure' else 'Hit'} slice: "
                            f"`{axis}={seg}` appears in {cnt}/{n_slice} "
                            f"({_pct(cond.get('share'))} share)."
                        ),
                        "evidence": {
                            "n": n_slice,
                            "hit": cnt if label == "winner" else n_slice - cnt,
                            "hit_rate": cond.get("share"),
                            "soft": global_soft if label == "winner" else None,
                            "roi": None,
                            "wilson_ci": {"low": round(lo, 4), "high": round(hi, 4)},
                            "coverage": _safe_div(block.get("evidence_n"), n_slice),
                            "reliability": None,
                        },
                        "hypothesis": _hypothesis_text(label, segment=f"{axis}={seg}"),
                        "confidence": conf,
                        "limitations": limitations,
                        "recommended_action": action,
                        "graph": {
                            "features": [axis] if axis in FEATURE_LABELS or axis in {
                                "popularity", "win_odds", "trainer"
                            } else [],
                            "segments": [seg],
                            "interactions": [],
                            "evidence_ids": [source_key],
                        },
                        "source_key": source_key,
                        "meta": {"axis": axis, "segment": seg, "gate": gate},
                    }
                )

        # Deduplicate by source_key (keep first)
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for e in entries:
            sk = str(e.get("source_key") or e["knowledge_id"])
            if sk in seen:
                continue
            seen.add(sk)
            unique.append(e)
        return unique

    def build_graph(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, str]] = []

        def _node(nid: str, ntype: str, label: str) -> None:
            if nid not in nodes:
                nodes[nid] = {"id": nid, "type": ntype, "label": label}

        for e in entries:
            kid = e["knowledge_id"]
            _node(kid, "evidence", e["source_key"])
            g = e.get("graph") or {}
            for fid in g.get("features") or []:
                fn = f"feature:{fid}"
                _node(fn, "feature", FEATURE_LABELS.get(fid, fid))
                edges.append({"from": fn, "to": kid, "rel": "supports"})
            for seg in g.get("segments") or []:
                sn = f"segment:{seg}"
                _node(sn, "segment", seg)
                edges.append({"from": sn, "to": kid, "rel": "context"})
                for fid in g.get("features") or []:
                    edges.append(
                        {
                            "from": f"feature:{fid}",
                            "to": sn,
                            "rel": "conditions",
                        }
                    )
            for pat in g.get("interactions") or []:
                pn = f"interaction:{pat}"
                _node(pn, "interaction", pat)
                edges.append({"from": pn, "to": kid, "rel": "instantiates"})
                for fid in _parse_pattern_features(pat):
                    edges.append(
                        {"from": f"feature:{fid}", "to": pn, "rel": "combines"}
                    )

        # dedupe edges
        edge_set = {json.dumps(x, sort_keys=True) for x in edges}
        edges = [json.loads(x) for x in sorted(edge_set)]
        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "counts": {
                "nodes": len(nodes),
                "edges": len(edges),
                "evidence": sum(1 for n in nodes.values() if n["type"] == "evidence"),
                "features": sum(1 for n in nodes.values() if n["type"] == "feature"),
                "segments": sum(1 for n in nodes.values() if n["type"] == "segment"),
                "interactions": sum(
                    1 for n in nodes.values() if n["type"] == "interaction"
                ),
            },
        }

    def _persist_entries(
        self, conn, entries: list[dict[str, Any]], week_id: str, now: str
    ) -> None:
        conn.execute(
            "DELETE FROM research_knowledge_entries WHERE week_id=?",
            (week_id,),
        )
        for e in entries:
            conn.execute(
                """
                INSERT INTO research_knowledge_entries(
                  knowledge_id, knowledge_type, week_id, observation, evidence_json,
                  hypothesis, confidence, limitations_json, recommended_action,
                  graph_json, source_key, meta_json, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    e["knowledge_id"],
                    e["knowledge_type"],
                    week_id,
                    e["observation"],
                    json.dumps(e.get("evidence") or {}, ensure_ascii=False),
                    e["hypothesis"],
                    e["confidence"],
                    json.dumps(e.get("limitations") or [], ensure_ascii=False),
                    e["recommended_action"],
                    json.dumps(e.get("graph") or {}, ensure_ascii=False),
                    e.get("source_key"),
                    json.dumps(e.get("meta") or {}, ensure_ascii=False),
                    now,
                    now,
                ),
            )

    def _load_prev_snapshot(self) -> dict[str, Any]:
        snap_dir = self.evidence / "knowledge" / "snapshots"
        if not snap_dir.is_dir():
            return {}
        files = sorted(snap_dir.glob("*.json"))
        if len(files) < 2:
            if len(files) == 1:
                # only current — treat as first run
                return {}
            return {}
        # second-to-last is previous (last may be current being written)
        prev = files[-2] if len(files) >= 2 else files[-1]
        return _load_json(prev)

    def compute_diff(
        self,
        current: list[dict[str, Any]],
        previous: list[dict[str, Any]],
    ) -> dict[str, Any]:
        prev_by_key = {str(e.get("source_key")): e for e in previous}
        curr_by_key = {str(e.get("source_key")): e for e in current}
        added = [curr_by_key[k] for k in curr_by_key if k not in prev_by_key]
        removed = [prev_by_key[k] for k in prev_by_key if k not in curr_by_key]
        changed = []
        for k in curr_by_key:
            if k not in prev_by_key:
                continue
            c, p = curr_by_key[k], prev_by_key[k]
            deltas = {}
            if c.get("confidence") != p.get("confidence"):
                deltas["confidence"] = {
                    "before": p.get("confidence"),
                    "after": c.get("confidence"),
                }
            if c.get("recommended_action") != p.get("recommended_action"):
                deltas["recommended_action"] = {
                    "before": p.get("recommended_action"),
                    "after": c.get("recommended_action"),
                }
            ce = c.get("evidence") or {}
            pe = p.get("evidence") or {}
            if ce.get("hit_rate") != pe.get("hit_rate"):
                deltas["hit_rate"] = {
                    "before": pe.get("hit_rate"),
                    "after": ce.get("hit_rate"),
                }
            if deltas:
                changed.append(
                    {
                        "source_key": k,
                        "knowledge_id": c.get("knowledge_id"),
                        "deltas": deltas,
                    }
                )
        return {
            "added": [
                {
                    "source_key": e.get("source_key"),
                    "confidence": e.get("confidence"),
                    "action": e.get("recommended_action"),
                    "observation": e.get("observation"),
                }
                for e in added[:50]
            ],
            "removed": [
                {
                    "source_key": e.get("source_key"),
                    "confidence": e.get("confidence"),
                }
                for e in removed[:50]
            ],
            "changed": changed[:50],
            "counts": {
                "added": len(added),
                "removed": len(removed),
                "changed": len(changed),
            },
        }

    def build(self) -> dict[str, Any]:
        now = _now()
        week = _week_id()
        v17 = self._load_v17()
        entries = self.build_entries(v17)
        graph = self.build_graph(entries)

        # snapshot path
        snap_dir = self.evidence / "knowledge" / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        snap_path = snap_dir / f"{week}.json"
        others = sorted(p for p in snap_dir.glob("*.json") if p.name != f"{week}.json")

        # diff vs previous snapshot file (before overwrite)
        prev_snap = _load_json(snap_path) if snap_path.exists() else {}
        prev_entries = prev_snap.get("entries") or []
        if not prev_entries and others:
            prev_entries = _load_json(others[-1]).get("entries") or []

        diff = self.compute_diff(entries, prev_entries)
        snapshot_payload = {
            "schema_version": SCHEMA_VERSION,
            "week_id": week,
            "generated_at": now,
            "entries": entries,
            "graph_summary": graph.get("counts"),
        }
        snap_path.write_text(
            json.dumps(snapshot_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        prev_week = prev_snap.get("week_id") or (others[-1].stem if others else None)

        conn = connect()
        try:
            self._persist_entries(conn, entries, week, now)
            snap_id = f"snap-{uuid.uuid4().hex[:12]}"
            summary = {
                "week_id": week,
                "entry_count": len(entries),
                "by_confidence": dict(Counter(e["confidence"] for e in entries)),
                "by_action": dict(Counter(e["recommended_action"] for e in entries)),
                "by_type": dict(Counter(e["knowledge_type"] for e in entries)),
                "v17_generated_at": v17.get("generated_at"),
            }
            conn.execute(
                """
                INSERT INTO research_knowledge_snapshots(
                  snapshot_id, week_id, schema_version, generated_at,
                  entry_count, snapshot_path, summary_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(week_id) DO UPDATE SET
                  generated_at=excluded.generated_at,
                  entry_count=excluded.entry_count,
                  snapshot_path=excluded.snapshot_path,
                  summary_json=excluded.summary_json
                """,
                (
                    snap_id,
                    week,
                    SCHEMA_VERSION,
                    now,
                    len(entries),
                    str(snap_path),
                    json.dumps(summary, ensure_ascii=False),
                    now,
                ),
            )
            diff_id = f"diff-{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO research_knowledge_diffs(
                  diff_id, week_id, prev_week_id, added_count, removed_count,
                  changed_count, diff_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    diff_id,
                    week,
                    prev_week,
                    diff["counts"]["added"],
                    diff["counts"]["removed"],
                    diff["counts"]["changed"],
                    json.dumps(diff, ensure_ascii=False),
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": now,
            "week_id": week,
            "prediction_mutation": "FORBIDDEN",
            "shadow_mutation": "FORBIDDEN",
            "sample": v17.get("sample"),
            "summary": summary,
            "entries": entries,
            "graph": graph,
            "weekly_diff": diff,
            "prev_week_id": prev_week,
        }


def write_knowledge_base_md(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = report.get("summary") or {}
    lines = [
        "# Version18 Research - Knowledge Base",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Week:** `{report.get('week_id')}`  ",
        "**Scope:** Research Knowledge / Prediction FORBIDDEN  ",
        "",
        "## Summary",
        "",
        f"- Entries: `{s.get('entry_count')}`",
        f"- By confidence: `{json.dumps(s.get('by_confidence') or {}, ensure_ascii=False)}`",
        f"- By action: `{json.dumps(s.get('by_action') or {}, ensure_ascii=False)}`",
        f"- By type: `{json.dumps(s.get('by_type') or {}, ensure_ascii=False)}`",
        f"- Source V17: `{s.get('v17_generated_at')}`",
        "",
        "## Knowledge entries (sample)",
        "",
        "| ID | Type | Confidence | Action | Observation |",
        "|----|------|------------|--------|-------------|",
    ]
    for e in (report.get("entries") or [])[:30]:
        obs = str(e.get("observation") or "")[:80].replace("|", "/")
        lines.append(
            f"| `{e.get('knowledge_id')}` | {e.get('knowledge_type')} | "
            f"{e.get('confidence')} | {e.get('recommended_action')} | {obs}… |"
        )
    lines.extend(
        [
            "",
            "## Entry schema",
            "",
            "Each Knowledge item includes:",
            "",
            "- **Observation** — what was measured",
            "- **Evidence** — N, Hit, Soft, ROI, Wilson CI, Coverage, Reliability",
            "- **Hypothesis** — plausible reason (non-definitive)",
            "- **Confidence** — High / Medium / Low / Exploratory",
            "- **Limitations** — insufficient_n, coverage_gap, selection_bias, missing",
            "- **Recommended Action** — Research / Shadow / Candidate / Reject / Watch",
            "",
            "## Guardrails",
            "",
            "- Knowledge is input for Version19+ candidate review only",
            "- No Prediction / PE / CE / AI / Resolver / Shadow implementation",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_knowledge_graph_md(report: dict[str, Any], path: Path) -> None:
    g = report.get("graph") or {}
    counts = g.get("counts") or {}
    lines = [
        "# Version18 Research - Knowledge Graph",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Week:** `{report.get('week_id')}`  ",
        "",
        "## Graph summary",
        "",
        f"- Nodes: `{counts.get('nodes')}`",
        f"- Edges: `{counts.get('edges')}`",
        f"- Features: `{counts.get('features')}`",
        f"- Segments: `{counts.get('segments')}`",
        f"- Interactions: `{counts.get('interactions')}`",
        f"- Evidence nodes: `{counts.get('evidence')}`",
        "",
        "## Structure",
        "",
        "```",
        "Feature → Segment → Interaction → Evidence",
        "```",
        "",
        "## Feature nodes",
        "",
    ]
    for n in sorted(
        [x for x in g.get("nodes") or [] if x.get("type") == "feature"],
        key=lambda x: x.get("label", ""),
    )[:25]:
        lines.append(f"- `{n.get('id')}` — {n.get('label')}")
    lines.extend(["", "## Segment nodes", ""])
    for n in sorted(
        [x for x in g.get("nodes") or [] if x.get("type") == "segment"],
        key=lambda x: x.get("label", ""),
    )[:25]:
        lines.append(f"- `{n.get('id')}` — {n.get('label')}")
    lines.extend(["", "## Interaction nodes (top)", ""])
    for n in [x for x in g.get("nodes") or [] if x.get("type") == "interaction"][:20]:
        lines.append(f"- `{n.get('id')}`")
    lines.extend(
        [
            "",
            "## Edge relations",
            "",
            "| From | To | Relation |",
            "|------|----|----------|",
        ]
    )
    for e in (g.get("edges") or [])[:40]:
        lines.append(f"| `{e.get('from')}` | `{e.get('to')}` | {e.get('rel')} |")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_weekly_knowledge_md(report: dict[str, Any], path: Path) -> None:
    diff = report.get("weekly_diff") or {}
    counts = diff.get("counts") or {}
    lines = [
        "# Version18 Research - Weekly Knowledge Diff",
        "",
        f"**Date:** {report.get('generated_at')}  ",
        f"**Week:** `{report.get('week_id')}`  ",
        f"**Previous:** `{report.get('prev_week_id') or 'none (first run)'}`  ",
        "",
        "## Diff summary",
        "",
        f"- Added: `{counts.get('added', 0)}`",
        f"- Removed: `{counts.get('removed', 0)}`",
        f"- Changed: `{counts.get('changed', 0)}`",
        "",
    ]
    if counts.get("added", 0) == 0 and counts.get("changed", 0) == 0:
        lines.append(
            "_First run or no prior snapshot — weekly diff will populate on next run._"
        )
        lines.append("")
    if diff.get("added"):
        lines.extend(["## Added", ""])
        for a in diff["added"][:20]:
            lines.append(
                f"- `{a.get('source_key')}` [{a.get('confidence')}/{a.get('action')}] "
                f"{str(a.get('observation') or '')[:100]}"
            )
        lines.append("")
    if diff.get("changed"):
        lines.extend(["## Changed", ""])
        for c in diff["changed"][:20]:
            lines.append(
                f"- `{c.get('source_key')}` — "
                f"{json.dumps(c.get('deltas') or {}, ensure_ascii=False)}"
            )
        lines.append("")
    if diff.get("removed"):
        lines.extend(["## Removed", ""])
        for r in diff["removed"][:15]:
            lines.append(f"- `{r.get('source_key')}` (was {r.get('confidence')})")
        lines.append("")
    lines.extend(
        [
            "## Decision",
            "",
            "```",
            "Action Type: Knowledge Base (Research)",
            "Prediction Mutation: FORBIDDEN",
            "Use: Version19+ improvement candidate input only",
            "```",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_and_write() -> dict[str, Any]:
    report = KnowledgeBaseBuilder().build()
    docs = repo_root() / "docs" / "research"
    docs.mkdir(parents=True, exist_ok=True)
    write_knowledge_base_md(report, docs / "v18-knowledge-base.md")
    write_knowledge_graph_md(report, docs / "v18-knowledge-graph.md")
    write_weekly_knowledge_md(report, docs / "v18-weekly-knowledge.md")
    json_path = evidence_root() / "reports" / "v18-knowledge-base.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    # trim entries in json for size — full in snapshot
    export = dict(report)
    export["entries"] = report.get("entries") or []
    json_path.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    report["_outputs"] = {
        "knowledge_base": str(docs / "v18-knowledge-base.md"),
        "graph": str(docs / "v18-knowledge-graph.md"),
        "weekly": str(docs / "v18-weekly-knowledge.md"),
        "json": str(json_path),
        "snapshot": str(
            evidence_root() / "knowledge" / "snapshots" / f"{report.get('week_id')}.json"
        ),
    }
    return report
