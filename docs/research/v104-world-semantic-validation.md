# Version104 — World Semantic Validation

**Generated:** `2026-07-28T13:33:50+00:00`  
**n_races:** 285  
**Mode:** Shadow Observation · **実装禁止**  
**評価:** Semantic Fidelity（思想忠実度）— Completeness / Hit / ROI ではない

## Verdict

**`FIDELITY_ACCEPTABLE_SEPARATION_WEAK`**

Contract / Near Miss / Explainability の忠実度は高い。  
一方、概念プロファイル（top_gap 等）の World 間 cosine≈0.996 で **意味的分離は弱い**。  
区別の主戦場は **decision_trace（Must/Exclusion）** であり、連続概念平均だけでは World を見分けにくい。

| Metric | Value |
|---|---:|
| mean positive World fidelity | 1.0000 |
| unsatisfied residual fidelity | 1.0000 |
| Near Miss fidelity | 1.0000 |
| Explainability fidelity | 1.0000 |
| mean pairwise concept cosine | 0.9960 |
| concept-profile separation | **WEAK** |

## 方法（要約）

1. V43 Required/Forbidden 方向 × コーパス中央値で信号整合を観測
2. CEW 正例で must∧¬exclude∧match の契約整合を観測
3. Near Miss は must∧exclude + affinity=1 + 正例プロファイル近接
4. Explainability は Affinity/Exclusion/Trace（EC proxy）のみで所属説明可能か

定義・Logic は変更しない。

## 関連

- `v104-world-fidelity-report.md`
- `v104-world-separation-report.md`
- `v104-governance.md`
