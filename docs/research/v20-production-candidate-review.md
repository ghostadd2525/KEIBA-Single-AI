# Version20 Research - Production Candidate Review

**Date:** 2026-07-27T10:23:12+00:00  
**Run:** `pcr-41772dfdd5c3`  
**Week:** `2026-W31`  
**Scope:** Design review only / AI & Prediction FORBIDDEN  

## Summary

- Reviewed: `3`
- PASS: `0` → V21 Implementation Candidate
- WARNING: `3` (hold)
- FAIL: `0` (hold)
- Promoted V21 label: `0`

## Review dimensions

1. Leak Risk
2. Generalization
3. Existing PE/CE alignment
4. Shadow reproducibility
5. Corpus Drift
6. Knowledge Drift
7. Evidence Quality
8. Long-term Stability

## Candidates

### `kb-a222dc9f1218` — **WARNING**

- Type: `interaction`
- Source: `interaction:mined_2way:popularity=P1|sire=SIRE_WEAK`
- Promote V21: `False`
- Observation: Interaction `popularity=P1|sire=SIRE_WEAK` (mined_2way): rate=40.0% on n=35.

| Dimension | Verdict |
|-----------|---------|
| `leak_risk` | **WARNING** |
| `generalization` | **WARNING** |
| `pe_ce_alignment` | **WARNING** |
| `shadow_reproducibility` | **PASS** |
| `corpus_drift` | **WARNING** |
| `knowledge_drift` | **PASS** |
| `evidence_quality` | **PASS** |
| `long_term_stability` | **PASS** |

### `kb-72cb124b5471` — **WARNING**

- Type: `feature`
- Source: `feature:ALL:popularity`
- Promote V21: `False`
- Observation: In category `ALL`, Popularity resolved 50 field picks with hit rate 32.0% (tie hit 11.1%, importance=0.4718).

| Dimension | Verdict |
|-----------|---------|
| `leak_risk` | **WARNING** |
| `generalization` | **PASS** |
| `pe_ce_alignment` | **WARNING** |
| `shadow_reproducibility` | **PASS** |
| `corpus_drift` | **WARNING** |
| `knowledge_drift` | **PASS** |
| `evidence_quality` | **PASS** |
| `long_term_stability` | **PASS** |

### `kb-0e3d73cec628` — **WARNING**

- Type: `feature`
- Source: `feature:ALL:win_odds`
- Promote V21: `False`
- Observation: In category `ALL`, Win Odds resolved 50 field picks with hit rate 32.0% (tie hit 11.1%, importance=0.4718).

| Dimension | Verdict |
|-----------|---------|
| `leak_risk` | **WARNING** |
| `generalization` | **PASS** |
| `pe_ce_alignment` | **WARNING** |
| `shadow_reproducibility` | **PASS** |
| `corpus_drift` | **WARNING** |
| `knowledge_drift` | **PASS** |
| `evidence_quality` | **PASS** |
| `long_term_stability` | **PASS** |

## Guardrails

- No Prediction / PE / CE / AI / Resolver / Production changes
- PASS-only → research label `V21_Implementation_Candidate`
- Implementation remains a separate ticket
