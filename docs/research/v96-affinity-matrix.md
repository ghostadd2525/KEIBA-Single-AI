# Version96 — World Affinity Matrix

**Generated:** `2026-07-28T12:22:33+00:00`  
**Population:** unsatisfied n=176  
**目的:** unsatisfied 削減ではなく、各 World への近さを測定  
**Locks:** Prediction / Trigger / CEW / World — 非変更 · **実装禁止**

## Affinity 定義

- `must_affinity = (n_must − n_gaps) / n_must`（must=True なら 1.0）
- `NEAR_MISS` = must∧exclude（近さは最大、CEW は unsatisfied のまま）
- Exclusion は近さを下げない（未 MATCH の理由として保持）

## Mean Must Affinity（行=対象 World）

| World | mean affinity | Near Miss n | Partial Must n | share as affinity-top |
|---|---:|---:|---:|---:|
| `core_world` | 0.676 | 81 | 0 | 0.528 |
| `midupper_world` | 0.640 | 32 | 0 | 0.307 |
| `midhole_world` | 0.452 | 13 | 0 | 0.119 |
| `rank7_world` | 0.451 | 1 | 0 | 0.045 |

## Coverage P(affinity ≥ t)

| t | core | midupper | midhole | rank7 |
|---:|---:|---:|---:|---:|
| 0.34 | 0.892 | 0.773 | 0.830 | 0.420 |
| 0.5 | 0.892 | 0.773 | 0.830 | 0.420 |
| 0.67 | 0.460 | 0.182 | 0.074 | 0.006 |
| 1.0 | 0.460 | 0.182 | 0.074 | 0.006 |

## Affinity-top 分布

```
{
  "midupper_world": 54,
  "core_world": 93,
  "midhole_world": 21,
  "rank7_world": 8
}
```

## Affinity Confidence 分布

```
{
  "LOW": 72,
  "HIGH": 81,
  "MED": 23
}
```

Near Miss において affinity-top ≡ primary near_world 一致率: **1.000**

## Decision Impact（設計マッピング・未実装）

```
{
  "pure_residual": 72,
  "near_miss:core_world": 81,
  "near_miss:midhole_world": 13,
  "near_miss:midupper_world": 9,
  "near_miss:rank7_world": 1
}
```

## 解釈（短縮）

1. Affinity は CEW を書き換えない。
2. 高い Affinity + Exclusion = Near Miss（V95 Metadata）。
3. Pure Residual でも弱い Affinity は観測してよいが、Positive Ticket 化禁止。
