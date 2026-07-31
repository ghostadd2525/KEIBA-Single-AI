# Version37 — World→PE Policy Simulation

**Status:** Research / Simulation only — **no Production / PE / CE / AI / World mutation**  
**Generated:** `2026-07-27T23:26:36+00:00`  
**N races (ranking-evaluable):** `51`  
**Corpus note:** `research_prediction_corpus` の結果付きは 335 件だが、Production bundle に `evaluation.runners`（model_rank/win_prob）があるのは **51 件**のみ。本 Simulation は順位差分評価のため後者に限定。  
**Verdict:** **FAIL**

## Method

```text
Frozen Production ranking (win_prob / model_rank)
        ↓
Virtual PE Policy Layer
  score = (1-w)·norm(win_prob) + w·norm(WorldRankKernel[world, subworld])
        ↓
Simulated Candidate Ranking → Prediction top1 / miss buckets
```

- Weights: `[0.0, 0.25, 0.5, 0.75, 1.0]`
- Kernels: design priors (not Hit-fitted) — see JSON `method.kernels`
- Purchase proxy: top1 Hit（V34 同型）

## Corpus

- World counts: `{"midupper_world": 51}`
- SubWorld counts: `{"midupper_route": 42, "midupper_spread": 9}`

## Aggregate by weight

| Weight | Hit | ΔHit | Purchase | ΔPurch | rank710 | Δ710 | other_miss | Δother | Top1 change | mean |rank| move |
|-------:|----:|-----:|---------:|-------:|--------:|-----:|-----------:|-------:|------------:|------------------:|
| 0% | 8 (15.7%) | +0 | 8 | +0 | 9 | +0 | 19 | +0 | 0 (0.0%) | 0.000 |
| 25% | 7 (13.7%) | -1 | 7 | -1 | 9 | +0 | 17 | -2 | 47 (92.2%) | 1.002 |
| 50% | 6 (11.8%) | -2 | 6 | -2 | 9 | +0 | 16 | -3 | 49 (96.1%) | 1.094 |
| 75% | 6 (11.8%) | -2 | 6 | -2 | 9 | +0 | 17 | -2 | 50 (98.0%) | 1.100 |
| 100% | 7 (13.7%) | -1 | 7 | -1 | 11 | +2 | 15 | -4 | 50 (98.0%) | 1.335 |

## Governance (summary)

- Final: **FAIL**
- Reason: No weight satisfies Hit non-worse + rank710/other_miss non-worse + meaningful influence with Hit lift
- Any NI+influence: `False`
- Any Hit improvement: `False`

## Index

| Doc | Content |
|-----|---------|
| `v37-world-pe-simulation.md` | 本ファイル |
| `v37-policy-impact.md` | World 別影響 |
| `v37-ranking-diff.md` | 順位変化 |
| `v37-world-weight-analysis.md` | Sensitivity |
| `v37-governance.md` | PASS/FAIL |

## Guardrails

- Prediction / PE / CE / AI / World / Signal Service / Production — unchanged
