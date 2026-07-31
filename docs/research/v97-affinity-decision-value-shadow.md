# Version97 — Affinity Decision Value Shadow

**Generated:** `2026-07-28T12:27:45+00:00`  
**Scope:** Near Miss only (n=104)  
**Locks:** Prediction / Trigger / CEW / World · **製品実装禁止**  
**Question:** Affinity は Decision に統計的価値を持つか？

## Verdict

**`NO_VALUE`** — affinity_has_decision_value = **False**

Affinity Risk 抑制は Buy を大きく減らすが、残購入の Purchase Hit が有意に悪化し Ticket PnL も悪化。 Near Miss Affinity の高抑制 SKIP は本コーパスで Decision 価値を示さない。

## Policies

- Baseline: `unsatisfied conservative BUY Top1 UNIT`
- Affinity-aware: `{"core_world/midupper_world": "SKIP (high_suppress)", "midhole_world/rank7_world": "BUY stake=0.5×UNIT (mid_suppress)", "forbidden": "Positive World Ticket Strategy copy"}`

## Metrics（Near Miss）

| Metric | Baseline | Affinity-aware | Δ |
|---|---:|---:|---:|
| Ticket ROI | 0.3981 | -0.4500 | -0.8481 |
| Ticket PnL | 4140.0000 | -315.0000 | -4455.0000 |
| Purchase Hit | 0.2596 | 0.0714 | -0.1882 |
| Coverage | 0.2596 | 0.2596 | 0.0000 |
| Buy Rate | 1.0000 | 0.1346 | -0.8654 |
| Skip Rate | 0.0000 | 0.8654 | — |

## Bootstrap（統計）

- ΔROI mean=-0.8329 CI95=[-1.8174038461538462, 0.4404326923076921] excludes0+=False
- ΔPurchaseHit mean=-0.1885 CI95=[-0.3173076923076923, -0.019162087912088274]
- ΔBuyRate mean=-0.8650 CI95=[-0.9326923076923077, -0.7980769230769231]

## Decision Stability

- Prediction fingerprint identical: **True**
- Action agreement: **0.1346**
- Template change rate: **1.0000**
- Transitions: `{'BUY->SKIP': 90}`

低 action_agreement は Risk 抑制が効いていることを示す。 Prediction 安定（fingerprint）が Decision Stability の必須条件。

## By near_world

| near_world | n | ΔROI | ΔPnL | ΔBuy | ΔHit |
|---|---:|---:|---:|---:|---:|
| `core_world` | 81 | — | -4550.0000 | -1.0000 | — |
| `midhole_world` | 13 | 0.0000 | 265.0000 | 0.0000 | 0.0000 |
| `midupper_world` | 9 | — | -220.0000 | -1.0000 | — |
| `rank7_world` | 1 | 0.0000 | 50.0000 | 0.0000 | 0.0000 |

## 方法

1. CEW=unsatisfied かつ Near Miss（must∧exclude）のみ。
2. Baseline = unsatisfied 保守 BUY。
3. Affinity-aware = V95 Risk（高抑制 SKIP / 中抑制 stake半減）。Positive Ticket コピー禁止。
4. Prediction fingerprint 不変を必須ゲート。

## 関連

- `v96-affinity-matrix.md`
- `v95-decision-policy.md`
- `v97-governance.md`
