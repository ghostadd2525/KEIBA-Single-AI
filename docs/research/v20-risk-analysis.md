# Version20 Research - Risk Analysis

**Date:** 2026-07-27T10:23:12+00:00  

## Thresholds

```json
{
  "leak_risk_fail": 0.85,
  "leak_risk_warn": 0.55,
  "min_n_pass": 40,
  "min_n_warn": 20,
  "min_segment_diversity": 2,
  "max_knowledge_drift_fail": 0.15,
  "max_knowledge_drift_warn": 0.08,
  "min_reliability_pass": 65.0,
  "min_reliability_warn": 55.0,
  "min_coverage_pass": 0.7,
  "min_coverage_warn": 0.4,
  "min_shadow_strict_pass": 0.25,
  "min_shadow_strict_warn": 0.18,
  "min_stability_pass": 0.55,
  "min_stability_warn": 0.4,
  "max_weekly_drift_fail": 0.35,
  "max_weekly_drift_warn": 0.2
}
```

## Per-candidate risks

### `kb-a222dc9f1218` (WARNING)

- **WARNING** `leak_risk` — V14 reports high asof_clamped / leak floor across Evidence features; market features may still be pre-race but require asof audit before PE/CE use.
- **WARNING** `generalization` — Small Evidence corpus (exploratory) limits out-of-sample claims; interaction patterns need multi-season confirmation.
- **WARNING** `pe_ce_alignment` — Candidate mixes PE/CE-core market signals with non-core features. Design must define ownership (PE market layer vs CE feature) to avoid conflict.
- **WARNING** `corpus_drift` — Corpus still exploratory; class/age unknown mass remains a drift risk for segment-conditioned Candidates.

  - detail `leak_risk`: {"verdict": "WARNING", "max_leak_risk": 0.7, "mean_asof_or_temporal": 1.0, "features": ["popularity", "sire"]}
  - detail `generalization`: {"verdict": "WARNING", "n": 35, "knowledge_type": "interaction", "segment_hints": [], "diversity_proxy": 0}
  - detail `pe_ce_alignment`: {"verdict": "WARNING", "pe_ce_core_features": ["popularity"], "non_core_features": ["sire"]}
  - detail `corpus_drift`: {"verdict": "WARNING", "unique_races": 335, "with_evidence": 50, "exploratory_corpus": true, "max_unknown_share_proxy": 0.8676}

### `kb-72cb124b5471` (WARNING)

- **WARNING** `leak_risk` — V14 reports high asof_clamped / leak floor across Evidence features; market features may still be pre-race but require asof audit before PE/CE use.
- **WARNING** `pe_ce_alignment` — Candidate relies only on PE/CE-core market signals (popularity/odds). Implementing as new AI Score risks double-counting market prior; prefer Shadow monitoring or explicit PE integration design — not a new CE feature.
- **WARNING** `corpus_drift` — Corpus still exploratory; class/age unknown mass remains a drift risk for segment-conditioned Candidates.

  - detail `leak_risk`: {"verdict": "WARNING", "max_leak_risk": 0.7, "mean_asof_or_temporal": 1.0, "features": ["popularity"]}
  - detail `pe_ce_alignment`: {"verdict": "WARNING", "pe_ce_core_features": ["popularity"], "non_core_features": []}
  - detail `corpus_drift`: {"verdict": "WARNING", "unique_races": 335, "with_evidence": 50, "exploratory_corpus": true, "max_unknown_share_proxy": 0.8676}

### `kb-0e3d73cec628` (WARNING)

- **WARNING** `leak_risk` — V14 reports high asof_clamped / leak floor across Evidence features; market features may still be pre-race but require asof audit before PE/CE use.
- **WARNING** `pe_ce_alignment` — Candidate relies only on PE/CE-core market signals (popularity/odds). Implementing as new AI Score risks double-counting market prior; prefer Shadow monitoring or explicit PE integration design — not a new CE feature.
- **WARNING** `corpus_drift` — Corpus still exploratory; class/age unknown mass remains a drift risk for segment-conditioned Candidates.

  - detail `leak_risk`: {"verdict": "WARNING", "max_leak_risk": 0.7, "mean_asof_or_temporal": 1.0, "features": ["win_odds"]}
  - detail `pe_ce_alignment`: {"verdict": "WARNING", "pe_ce_core_features": ["win_odds"], "non_core_features": []}
  - detail `corpus_drift`: {"verdict": "WARNING", "unique_races": 335, "with_evidence": 50, "exploratory_corpus": true, "max_unknown_share_proxy": 0.8676}

## Cross-cutting risks

- Evidence corpus remains exploratory (limited snapshot coverage).
- V14 leak_risk / asof_clamped floor affects all Evidence features.
- Market features (popularity/odds) already live in PE/CE — double-counting risk.
- Interaction bins (e.g. SIRE_WEAK) may encode selection bias, not causal edge.

## Decision

```
Action Type: Production Candidate Design Review (Research)
AI Mutation: FORBIDDEN
Prediction Mutation: FORBIDDEN
PASS-only → Version21 implementation ticket input
```
