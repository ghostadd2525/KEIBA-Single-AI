# Version102 — Semantic Redundancy Report

**Generated:** `2026-07-28T13:10:35+00:00`

- near_world ≡ affinity_top rate (unsatisfied): **0.5909**（Near Miss 104件では一致、Pure Residual 72件は near_world=null のため非一致計上）

## Overlap counts

| Pair | n |
|---|---:|
| `transition_dst≡world_label` | 285 |
| `expected_strategy_key≡world_label` | 285 |
| `near_world≡affinity_top` | 104 |
| `near_world≡transition_src` | 36 |

## 解釈

expected_strategy_key≡world_label is structural redundancy (map keyed by World). near_world≡affinity_top indicates overlapping Near Miss signals.

- **Transition** は経路（from→to）を持ち World ラベルと部分重複するが、from 側に追加意味がある。
- **Expected Strategy** が World キーのみなら、World と情報理論的に冗長（レース固有戦略文なし）。
- **Near Miss vs Affinity** 高一致は重複シグナル。役割は『クラス』vs『連続近さ』で区別可能。
