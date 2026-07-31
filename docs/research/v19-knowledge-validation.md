# Version19 Research - Knowledge Validation

**Date:** 2026-07-27T10:05:31+00:00  
**Run:** `kv-9e9d2d2e78c1`  
**Week:** `2026-W31`  
**Scope:** Shadow validation only / Prediction FORBIDDEN  

## Summary

- Candidates validated: `36`
- Passed governance: `6`
- Validated: `6`
- Rejected: `9`
- Production Candidate (label only): `3`
- Shadow flags generated: `36`

## Governance gate

```json
{
  "min_n": 20,
  "min_strict_rate": 0.18,
  "min_strict_improvement_vs_baseline": 0.0,
  "min_wilson_ci_low": 0.12,
  "min_coverage": 0.4,
  "min_reliability": 50.0,
  "max_knowledge_drift": 0.2,
  "min_shadow_win_rate": 0.15,
  "production_candidate_min_strict": 0.25,
  "production_candidate_top_n": 3
}
```

## Results

| ID | Type | N | Strict | Soft | ROI | Drift | Passed | State |
|----|------|--:|-------:|-----:|----:|------:|--------|-------|
| `kb-72cb124b5471` | feature | 50 | 32.0% | 0.0% | -20.0% | 0.0 | True | Production_Candidate |
| `kb-0e3d73cec628` | feature | 50 | 32.0% | 0.0% | -20.0% | 0.0 | True | Production_Candidate |
| `kb-a222dc9f1218` | interaction | 35 | 40.0% | 0.0% | 0.0% | 0.0 | True | Production_Candidate |
| `kb-c05d4ddc44c6` | interaction | 20 | 40.0% | 0.0% | 0.0% | 0.0 | True | Validated |
| `kb-9d66173773b1` | interaction | 23 | 39.1% | 0.0% | -2.2% | 0.0 | True | Validated |
| `kb-ddad565c4377` | interaction | 15 | 40.0% | 0.0% | 0.0% | 0.1 | False | Candidate |
| `kb-bb8432dd2ac4` | interaction | 21 | 28.6% | 0.0% | -28.6% | 0.0 | True | Validated |
| `kb-fbaa8a834886` | interaction | 15 | 26.7% | 6.7% | -33.3% | 0.0333 | False | Candidate |
| `kb-3f39db42a18d` | interaction | 39 | 20.5% | 2.6% | -48.7% | 0.0123 | False | Rejected |
| `kb-f50586a98c65` | interaction | 25 | 24.0% | 8.0% | -40.0% | 0.04 | False | Rejected |
| `kb-eceb63668936` | interaction | 44 | 18.2% | 6.8% | -54.5% | 0.0028 | False | Rejected |
| `kb-6aa522d2526a` | interaction | 33 | 12.1% | 12.1% | -69.7% | 0.063 | False | Rejected |
| `kb-10f0692084a8` | interaction | 41 | 17.1% | 7.3% | -57.3% | 0.0213 | False | Rejected |
| `kb-8268e44d3cdd` | interaction | 23 | 21.7% | 8.7% | -45.7% | 0.0226 | False | Rejected |
| `kb-d2206b22932d` | interaction | 23 | 21.7% | 4.3% | -45.7% | 0.0031 | False | Rejected |
| `kb-7df7af302bd5` | winner | 5 | 20.0% | 0.0% | -50.0% | 0.4866 | False | Candidate |
| `kb-461f44de9db0` | winner | 4 | 25.0% | 0.0% | -37.5% | 0.0261 | False | Candidate |
| `kb-b4c8924eac20` | winner | 15 | 13.3% | 6.7% | -66.7% | 0.3443 | False | Candidate |
| `kb-7c2c1752d3af` | winner | 23 | 8.7% | 8.7% | -78.3% | 0.3757 | False | Rejected |
| `kb-cee419488701` | winner | 19 | 15.8% | 5.3% | -60.5% | 0.3346 | False | Candidate |
| `kb-f5f8031c8bcc` | winner | 15 | 6.7% | 13.3% | -83.3% | 0.1423 | False | Candidate |
| `kb-125752ee4090` | winner | 3 | 0.0% | 0.0% | -100.0% | 0.1194 | False | Candidate |
| `kb-e0545bd640e8` | winner | 1 | 0.0% | 0.0% | -100.0% | 0.1194 | False | Candidate |
| `kb-d64127c84fb7` | winner | 33 | 9.1% | 6.1% | -77.3% | 0.6703 | False | Rejected |
| `kb-fa21fb0316c8` | winner | 1 | 0.0% | 0.0% | -100.0% | 0.0896 | False | Candidate |
| `kb-d6e7035860ac` | winner | 0 | N/A | N/A | N/A | None | False | Candidate |
| `kb-d9b5db24ab01` | winner | 0 | N/A | N/A | N/A | None | False | Candidate |
| `kb-b7aa84bb878d` | winner | 0 | N/A | N/A | N/A | None | False | Candidate |
| `kb-2d5ca4087c3a` | winner | 0 | N/A | N/A | N/A | None | False | Candidate |
| `kb-1209d95472b3` | winner | 0 | N/A | N/A | N/A | None | False | Candidate |
| `kb-b5e62fb28818` | winner | 14 | 21.4% | 0.0% | -46.4% | 0.2186 | False | Candidate |
| `kb-aaa5bac744cb` | winner | 15 | 20.0% | 13.3% | -50.0% | 0.1134 | False | Candidate |
| `kb-4cd986a1f5c1` | winner | 17 | 11.8% | 17.6% | -70.6% | 0.0167 | False | Candidate |
| `kb-1235daa9ca65` | winner | 4 | 0.0% | 0.0% | -100.0% | 0.1194 | False | Candidate |
| `kb-195c781739cd` | winner | 0 | N/A | N/A | N/A | None | False | Candidate |
| `kb-8cf492ae6c37` | winner | 0 | N/A | N/A | N/A | None | False | Candidate |

## Shadow feature flags (sample)

- `shadow.knowledge.kb-72cb124b5471` mode=`field_best_feature`
- `shadow.knowledge.kb-0e3d73cec628` mode=`field_best_feature`
- `shadow.knowledge.kb-a222dc9f1218` mode=`pattern_match_pick`
- `shadow.knowledge.kb-c05d4ddc44c6` mode=`pattern_match_pick`
- `shadow.knowledge.kb-9d66173773b1` mode=`pattern_match_pick`
- `shadow.knowledge.kb-ddad565c4377` mode=`pattern_match_pick`
- `shadow.knowledge.kb-bb8432dd2ac4` mode=`pattern_match_pick`
- `shadow.knowledge.kb-fbaa8a834886` mode=`pattern_match_pick`
- `shadow.knowledge.kb-3f39db42a18d` mode=`pattern_match_pick`
- `shadow.knowledge.kb-f50586a98c65` mode=`pattern_match_pick`

## Guardrails

- Shadow flags are research-only; do not enable in Production
- Resolver unchanged
- Production_Candidate is a research label, not deployment
