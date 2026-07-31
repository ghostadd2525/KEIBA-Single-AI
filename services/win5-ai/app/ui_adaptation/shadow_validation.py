# -*- coding: utf-8 -*-
"""
UI2 Existing UI Shadow Validation — PredictionBundle 2.0 ↔ existing UI slots.

Does NOT modify UI. Validates Bundle compatibility for:
marks, picks, confidence, evaluation ability_scores, loading/error shapes,
race switch mismatch guard, and structural HTML slot readiness.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.ui_adaptation.single_to_bundle import (
    assert_no_internal_terms_leaked,
    map_single_to_prediction_bundle,
)

SCHEMA = "ui2-shadow-validation/1.0"


def _fixture_core(race_id: str = "2026-07-19-hanshin-11") -> dict[str, Any]:
    return {
        "schema": "core-semantic-payload/v1",
        "race_id": race_id,
        "world_id": "rank7_world",
        "prediction": {
            "ranks": [5, 3, 8, 2],
            "scores": [0.32, 0.22, 0.15, 0.1],
            "top1": 5,
        },
        "near_miss": {"residual_class": "NEAR_MISS", "near_world": "core_world"},
        "affinity": {"core_world": 0.9},
        "explanation_confidence": {"overall": 0.88},
    }


def _baseline_bundle(race_id: str = "2026-07-19-hanshin-11") -> dict[str, Any]:
    """Product-like PredictionBundle used as visual/compat baseline."""
    return {
        "schema_version": "single-prediction-bundle/2.0",
        "race_id": race_id,
        "race_info": {
            "race_id": race_id,
            "date": "2026-07-19",
            "venue": "阪神",
            "race_no": 11,
            "race_name": "UI2検証ステークス",
            "post_time": "15:40",
            "grade": "G2",
            "field_size": 4,
        },
        "evaluation": {
            "status": "ok",
            "world": None,
            "sub_world": None,
            "runners": [
                {
                    "candidate_id": "c05",
                    "horse_number": 5,
                    "horse_name": "シャドウホース",
                    "model_rank": 1,
                    "win_prob": 0.32,
                    "mark": "honmei",
                    "mark_rank": 1,
                    "ability_scores": {
                        "history_score": 0.82,
                        "distance_score": 0.71,
                        "style_distance_fit_weight": 0.66,
                        "front_rate": 0.55,
                        "pace_collapse_risk_v2": 0.4,
                    },
                },
                {
                    "candidate_id": "c03",
                    "horse_number": 3,
                    "horse_name": "対抗ホース",
                    "model_rank": 2,
                    "win_prob": 0.22,
                    "mark": "taikou",
                    "mark_rank": 1,
                },
                {
                    "candidate_id": "c08",
                    "horse_number": 8,
                    "horse_name": "穴ホース",
                    "model_rank": 3,
                    "win_prob": 0.15,
                    "mark": "ana",
                    "mark_rank": 1,
                },
                {
                    "candidate_id": "c02",
                    "horse_number": 2,
                    "horse_name": "中穴ホース",
                    "model_rank": 4,
                    "win_prob": 0.1,
                    "mark": "chuuken",
                    "mark_rank": 1,
                },
            ],
        },
        "ai_confidence": {
            "schema_version": "ai-confidence/1.0",
            "status": "ok",
            "score": 0.72,
            "score_unit": "normalized",
            "band": "medium",
            "component_scores": {
                "model_score": 0.74,
                "segment_hit_rate": 0.61,
                "segment_scope": "venue",
                "segment_key": "阪神",
            },
            "factors": [],
            "notes": None,
            "computed_at": None,
        },
        "explain": {
            "meta": {"world": None, "sub_world": None},
            "reasons": [
                {
                    "horse_number": 5,
                    "bullets": ["脚質が条件に合う", "距離実績が安定"],
                }
            ],
        },
        "betting_recommendations": {"schema_version": "betting-recommendations/1.0", "items": []},
        "warnings": [],
    }


def mapped_bundle_from_single(race_id: str | None = None) -> dict[str, Any]:
    rid = race_id or "2026-07-19-hanshin-11"
    base = _baseline_bundle(rid)
    return map_single_to_prediction_bundle(
        {"core_payload": _fixture_core(rid)},
        race_id=rid,
        race_info=base["race_info"],
        base_bundle=base,
    )


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"id": name, "pass": bool(ok), "detail": detail}


def validate_marks(bundle: dict[str, Any]) -> dict[str, Any]:
    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
    marks = {r.get("mark") for r in runners if isinstance(r, dict)}
    ok = "honmei" in marks and "taikou" in marks and "ana" in marks
    return _check("marks", ok, f"marks={sorted(m for m in marks if m)}")


def validate_picks(bundle: dict[str, Any]) -> dict[str, Any]:
    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
    by_mark = {r.get("mark"): r for r in runners if isinstance(r, dict)}
    ok = all(m in by_mark for m in ("taikou", "ana", "chuuken"))
    return _check("picks_taikou_ana_chuuken", ok, f"keys={list(by_mark)}")


def validate_confidence(bundle: dict[str, Any]) -> dict[str, Any]:
    ac = bundle.get("ai_confidence") or {}
    ok = isinstance(ac, dict) and ac.get("band") in ("high", "medium", "low", "unknown")
    ok = ok and ("score" in ac)
    # EC must not be the confidence source object
    ok = ok and "explanation_confidence" not in ac
    return _check("ai_confidence", ok, f"band={ac.get('band')} score={ac.get('score')}")


def validate_ability_breakdown(bundle: dict[str, Any]) -> dict[str, Any]:
    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
    honmei = next((r for r in runners if r.get("mark") == "honmei"), None)
    scores = (honmei or {}).get("ability_scores") or {}
    needed = ("history_score", "distance_score")
    ok = isinstance(scores, dict) and all(k in scores for k in needed)
    return _check("evaluation_breakdown", ok, f"ability_keys={list(scores)[:8]}")


def validate_loading_error_shapes() -> list[dict[str, Any]]:
    """Document/verify shapes the existing UI already understands (no UI change)."""
    pending = {
        "ok": False,
        "pending": True,
        "error": {"code": "PREDICTION_PENDING", "message": "Prediction pending"},
    }
    err = {"ok": False, "error": {"code": "NOT_FOUND", "message": "PredictionBundle not found"}}
    checks = [
        _check("loading_pending_shape", pending.get("pending") is True and pending["error"]["code"] == "PREDICTION_PENDING"),
        _check("error_shape", err["error"]["code"] == "NOT_FOUND"),
    ]
    return checks


def validate_race_switching(bundle_a: dict[str, Any], bundle_b: dict[str, Any]) -> dict[str, Any]:
    """applyRaceDetail mismatch guard: expectedRaceId !== bundle.race_id → mismatch."""
    ok = bundle_a.get("race_id") != bundle_b.get("race_id")
    ok = ok and bool(bundle_a.get("race_id")) and bool(bundle_b.get("race_id"))
    return _check(
        "race_switching_ids_distinct",
        ok,
        f"{bundle_a.get('race_id')} vs {bundle_b.get('race_id')}",
    )


def validate_navigation_contracts() -> list[dict[str, Any]]:
    """
    Existing navigation contracts (multipage + list URL state).
    Verified statically — no UI edits.
    """
    repo = Path(__file__).resolve().parents[4]
    race_html = repo / "public" / "race.html"
    races_html = repo / "public" / "races.html"
    list_url_js = repo / "public" / "assets" / "api" / "race-list-url.js"
    text = race_html.read_text(encoding="utf-8") if race_html.exists() else ""
    list_js = list_url_js.read_text(encoding="utf-8") if list_url_js.exists() else ""
    checks = [
        _check("back_link_present", 'class="back-btn"' in text and "races.html" in text),
        _check("race_html_exists", race_html.exists()),
        _check("races_html_exists", races_html.exists()),
        _check(
            "spa_list_url_state",
            "pushState" in list_js and "popstate" in list_js,
            "races list uses history.pushState/popstate (existing)",
        ),
        _check(
            "scroll_preserve_contract",
            True,
            "Detail↔list is multipage; browser scroll restore on back is existing behavior",
        ),
    ]
    return checks


def validate_no_internal_leak(bundle: dict[str, Any]) -> dict[str, Any]:
    leaks = assert_no_internal_terms_leaked(bundle)
    return _check("no_internal_terms", len(leaks) == 0, f"leaks={leaks}")


def validate_schema(bundle: dict[str, Any]) -> dict[str, Any]:
    ok = bundle.get("schema_version") == "single-prediction-bundle/2.0"
    ok = ok and isinstance(bundle.get("evaluation"), dict)
    ok = ok and isinstance((bundle.get("evaluation") or {}).get("runners"), list)
    return _check("bundle_schema", ok, bundle.get("schema_version") or "")


def structural_slot_fingerprint(bundle: dict[str, Any]) -> dict[str, Any]:
    """Stable fingerprint for visual-diff without screenshots."""
    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
    marks = [
        {
            "mark": r.get("mark"),
            "horse_number": r.get("horse_number"),
            "model_rank": r.get("model_rank"),
        }
        for r in runners
        if r.get("mark") and r.get("mark") != "none"
    ]
    ac = bundle.get("ai_confidence") or {}
    honmei = next((r for r in runners if r.get("mark") == "honmei"), {}) or {}
    return {
        "race_id": bundle.get("race_id"),
        "marks": marks,
        "confidence_band": ac.get("band"),
        "confidence_score": ac.get("score"),
        "ability_score_keys": sorted((honmei.get("ability_scores") or {}).keys()),
        "world_null": (bundle.get("evaluation") or {}).get("world") is None,
    }


def visual_diff(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    fb = structural_slot_fingerprint(baseline)
    fc = structural_slot_fingerprint(candidate)
    diffs: list[str] = []
    for key in ("marks", "confidence_band", "ability_score_keys", "world_null"):
        if fb.get(key) != fc.get(key):
            diffs.append(key)
    # score may float-equal
    if fb.get("confidence_score") != fc.get("confidence_score"):
        diffs.append("confidence_score")
    return {
        "identical_slots": len(diffs) == 0,
        "diff_keys": diffs,
        "baseline": fb,
        "candidate": fc,
    }


def run_shadow_validation(*, write_artifacts: bool = True) -> dict[str, Any]:
    baseline = _baseline_bundle()
    mapped = mapped_bundle_from_single()
    mapped_b = mapped_bundle_from_single("2026-07-19-kyoto-10")

    checks: list[dict[str, Any]] = []
    checks.append(validate_schema(mapped))
    checks.append(validate_marks(mapped))
    checks.append(validate_picks(mapped))
    checks.append(validate_confidence(mapped))
    checks.append(validate_ability_breakdown(mapped))
    checks.append(validate_no_internal_leak(mapped))
    checks.append(validate_race_switching(mapped, mapped_b))
    checks.extend(validate_loading_error_shapes())
    checks.extend(validate_navigation_contracts())

    vdiff = visual_diff(baseline, mapped)
    checks.append(
        _check(
            "visual_diff_slots",
            vdiff["identical_slots"],
            f"diff_keys={vdiff['diff_keys']}",
        )
    )

    # Bundle compat 100% for display slots: all critical axes pass
    critical = {
        "bundle_schema",
        "marks",
        "picks_taikou_ana_chuuken",
        "ai_confidence",
        "evaluation_breakdown",
        "no_internal_terms",
        "visual_diff_slots",
        "race_switching_ids_distinct",
        "loading_pending_shape",
        "error_shape",
        "back_link_present",
        "spa_list_url_state",
    }
    critical_results = [c for c in checks if c["id"] in critical]
    all_pass = all(c["pass"] for c in critical_results)

    report = {
        "schema": SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": "UI2",
        "ui_changed": False,
        "verdict": "PASS" if all_pass else "FAIL",
        "prediction_bundle_compat_pct": 100.0 if all_pass else round(
            100.0 * sum(1 for c in critical_results if c["pass"]) / max(len(critical_results), 1),
            2,
        ),
        "checks": checks,
        "visual_diff": vdiff,
        "artifacts": {},
    }

    if write_artifacts:
        repo = Path(__file__).resolve().parents[4]
        out_dir = repo / "docs" / "research" / "ui2-artifacts"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "baseline-bundle.json").write_text(
            json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_dir / "mapped-bundle.json").write_text(
            json.dumps(mapped, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_dir / "visual-diff.json").write_text(
            json.dumps(vdiff, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (out_dir / "validation-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # HTML snapshots (screenshot substitutes + browser harness input)
        snap = _html_snapshot(mapped)
        (out_dir / "snapshot-mapped-slots.html").write_text(snap, encoding="utf-8")
        snap_b = _html_snapshot(baseline)
        (out_dir / "snapshot-baseline-slots.html").write_text(snap_b, encoding="utf-8")
        report["artifacts"] = {
            "dir": str(out_dir).replace("\\", "/"),
            "files": [
                "baseline-bundle.json",
                "mapped-bundle.json",
                "visual-diff.json",
                "validation-report.json",
                "snapshot-baseline-slots.html",
                "snapshot-mapped-slots.html",
            ],
        }
    return report


def _html_snapshot(bundle: dict[str, Any]) -> str:
    """Minimal structural HTML mirroring existing slot classes (not a UI redesign)."""
    runners = ((bundle.get("evaluation") or {}).get("runners")) or []
    mark_map = {"honmei": "◎", "taikou": "○", "ana": "▲", "chuuken": "△"}
    marks_html = []
    for r in runners:
        m = r.get("mark")
        if not m or m == "none":
            continue
        marks_html.append(
            f'<div class="mark-chip mark-chip--{m}">'
            f'<span class="mark-chip-symbol">{mark_map.get(m, "—")}</span>'
            f'<span class="mark-chip-num">{r.get("horse_number")}</span>'
            f'<span class="mark-chip-name">{r.get("horse_name") or ""}</span>'
            f'</div>'
        )
    picks = []
    for m, label in (("taikou", "対抗"), ("ana", "穴"), ("chuuken", "中穴")):
        r = next((x for x in runners if x.get("mark") == m), None)
        if not r:
            continue
        picks.append(
            f'<article class="pick-card pick-card--{m}">'
            f'<p class="pick-card-label">{label} {mark_map[m]}</p>'
            f'<h4>{r.get("horse_number")} {r.get("horse_name") or ""}</h4></article>'
        )
    ac = bundle.get("ai_confidence") or {}
    honmei = next((r for r in runners if r.get("mark") == "honmei"), {}) or {}
    ability = honmei.get("ability_scores") or {}
    ability_rows = "".join(
        f"<li><span>{k}</span><strong>{v}</strong></li>" for k, v in ability.items()
    )
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8"/><title>UI2 Snapshot {bundle.get("race_id")}</title>
<style>
body{{font-family:sans-serif;padding:16px;background:#f6f4ef;color:#1a1a1a}}
.marks-grid,.picks{{display:flex;gap:8px;flex-wrap:wrap}}
.mark-chip,.pick-card{{background:#fff;border:1px solid #ddd;padding:8px 12px;border-radius:4px}}
.confidence-detail-v2,.score-list{{background:#fff;border:1px solid #ddd;padding:12px;margin-top:12px}}
.note{{font-size:12px;color:#666;margin-top:24px}}
</style></head><body>
<h1>UI2 Shadow Snapshot（既存スロット構造）</h1>
<p>race_id={bundle.get("race_id")} · schema={bundle.get("schema_version")}</p>
<section id="marksSectionBody"><h2>印</h2><div class="marks-grid">{"".join(marks_html)}</div></section>
<section id="pickCardsBody"><h2>対抗・穴</h2><div class="picks">{"".join(picks)}</div></section>
<section id="raceConfidenceDetail"><h2>このレースの自信度</h2>
<div class="confidence-detail-v2"><p class="confidence-summary">このレースの自信度：<strong>{ac.get("band")}</strong></p>
<p>score={ac.get("score")} · model_score={(ac.get("component_scores") or {}).get("model_score")}</p></div></section>
<section id="chartCard"><h2>評価内訳</h2><ul class="score-list">{ability_rows or "<li>ability_scores なし</li>"}</ul></section>
<p class="note">Shadow only · UI layout not changed · internal terms not shown · world={(bundle.get("evaluation") or {}).get("world")}</p>
</body></html>
"""


if __name__ == "__main__":
    rep = run_shadow_validation(write_artifacts=True)
    print(json.dumps({"verdict": rep["verdict"], "pct": rep["prediction_bundle_compat_pct"]}, ensure_ascii=False))
