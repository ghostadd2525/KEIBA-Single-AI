# Version77 — World Validation（Contract / Stability / Separation）

**Generated:** `2026-07-28T08:35:42+00:00`

## Contract Metrics（G-C1 テスト記録）

| Test ID | Scope | n | Value | Threshold | Pass |
|---|---|---:|---:|---|---|
| `rank7.MUST.2.field_size_attenuate` | full | 65 | -0.1131 | <= -0.05 | PASS |
| `rank7.MUST.1.history_winprob_peer_band` | full | 65 | 0.0172 | both in top3 AND |Δ| <= 0.25 (observability) | PASS |
| `rank7.MUST.3.not_sashi_oikomi_primary` | full | 65 | 逃げ | not in {差し, 追込} | PASS |
| `midhole.MUST.1.history_leads` | full | 24 | 0.4209 | > 0.15 | PASS |
| `midhole.MUST.2.winprob_not_primary` | full | 24 | 3 | not rank 1 (top3[0] != win_prob_z) | PASS |
| `midhole.MUST.3.upper_band_attenuate` | full | 24 | -0.2337 | <= -0.05 | PASS |
| `rank7.MUST.2.field_size_attenuate` | split1 | 27 | -0.1181 | <= -0.05 | PASS |
| `rank7.MUST.1.history_winprob_peer_band` | split1 | 27 | 0.0616 | both in top3 AND |Δ| <= 0.25 (observability) | PASS |
| `rank7.MUST.3.not_sashi_oikomi_primary` | split1 | 27 | 逃げ | not in {差し, 追込} | PASS |
| `midhole.MUST.1.history_leads` | split1 | 14 | 0.3859 | > 0.15 | PASS |
| `midhole.MUST.2.winprob_not_primary` | split1 | 14 | 3 | not rank 1 (top3[0] != win_prob_z) | PASS |
| `midhole.MUST.3.upper_band_attenuate` | split1 | 14 | -0.4198 | <= -0.05 | PASS |
| `rank7.MUST.2.field_size_attenuate` | split2 | 38 | -0.1132 | <= -0.05 | PASS |
| `rank7.MUST.1.history_winprob_peer_band` | split2 | 38 | 0.0732 | both in top3 AND |Δ| <= 0.25 (observability) | PASS |
| `rank7.MUST.3.not_sashi_oikomi_primary` | split2 | 38 | 先行 | not in {差し, 追込} | PASS |
| `midhole.MUST.1.history_leads` | split2 | 10 | 0.4697 | > 0.15 | PASS |
| `midhole.MUST.2.winprob_not_primary` | split2 | 10 | 99 | not rank 1 (top3[0] != win_prob_z) | PASS |
| `midhole.MUST.3.upper_band_attenuate` | split2 | 10 | -0.1260 | <= -0.05 | PASS |
| `unsatisfied.MUST.fallback_coverage_popularity` | full | 176 | 0.1705 | document coverage (no pass threshold in V76 except measured) | PASS |

## rank7 Gate

- **G-S1:** PASS — `{"pass": true, "n_full": 65, "threshold": 40}`
- **G-S2:** PASS — `{"pass": true, "n_split1": 27, "n_split2": 38, "threshold_each": 15}`
- **G-C1:** PASS — `{"pass": true, "note": "MUST tests recorded"}`
- **G-R1:** PASS — `{"pass": true, "top3_jaccard": 1.0, "threshold": 0.6}`
- **Separation:** PASS
- **World-specific:** PASS `{'split1_r': -0.11814249606565776, 'split2_r': -0.11322764875495767, 'rule': 'both <= -0.05'}`
- **Ready Gate:** **PASS**

## midhole Gate

- **G-S1:** FAIL — `{"pass": false, "n_full": 24, "threshold": 40}`
- **G-S2:** FAIL — `{"pass": false, "n_split1": 14, "n_split2": 10, "threshold_each": 15}`
- **G-C1:** PASS — `{"pass": true, "note": "MUST tests recorded"}`
- **G-R1:** FAIL — `{"pass": false, "top3_jaccard": 0.5, "threshold": 0.6}`
- **Separation:** PASS
- **World-specific:** PASS `{'hist_gap_s1': 0.3859235364462736, 'hist_gap_s2': 0.4697147656073158, 'upper_r_s1': -0.41984904281536817, 'upper_r_s2': -0.12595483446479255}`
- **Ready Gate:** **FAIL**

## unsatisfied Residual Gate

- n=176 n_ok=True
- misapplication legacy→positive: 1.0000
- misapplication v69→positive: 0.0000
- popularity_coverage: 0.1705
- fallback_needed_rate: 0.8295
- top3_jaccard_splits: 1.0000
- **Ready Gate:** **PASS**

## Blocked re-eval

| World | n | →Partial? | Readiness |
|---|---:|---|---|
| `core_world` | 8 | FAIL | **Blocked** |
| `midupper_world` | 6 | FAIL | **Blocked** |
| `mixed_world` | 6 | FAIL | **Blocked** |
| `bug_world` | 0 | FAIL | **Blocked** |
