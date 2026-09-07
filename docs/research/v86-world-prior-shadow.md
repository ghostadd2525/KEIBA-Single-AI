# Version86 — World Prior Calibration Shadow

**Generated:** `2026-07-28T10:42:56+00:00`  
**Mode:** V85 案A World Prior Anchor のみ（Shadow / Confidence only）  
**Locks:** Production / Trigger / Blueprint / PE / Interaction / World Contract / Rank / Score — 非変更  
**Audit:** rank=True / score=True / interaction_applied=False / n=285

## Shadow Path

```text
Base (C0: wp[top1]/Σwp)
  → C3 (World empirical prior from train half)
  → C7c ((1-0.9)·C0 + 0.9·C3)
Control: ConstShift ((1-λ)·C0 + λ·global_train_hit)
```

## Verdict: **PARTIAL**

C3 (pure World Prior) meets Go vs Base+ConstShift, but C7c (λ=0.9 blend) does not (C7c ECE が ConstShift 以下に届かない)。案A主形式は未達・C3単体は有望

train=142 / test=143

### Train priors

- global_rate = 0.7746
- `core_world` = 0.7500
- `midhole_world` = 0.9286
- `midupper_world` = 0.8000
- `mixed_world` = 0.6667
- `rank7_world` = 0.7778
- `unsatisfied` = 0.7529

## Test ALL（主判定）

n=143 / hit_rate=0.7552

| Arm | Brier | ECE | LogLoss | p_mean | bias |
|---|---:|---:|---:|---:|---:|
| base | 0.5802 | 0.6273 | 1.6162 | 0.1280 | -0.6273 |
| c3 | 0.1836 | 0.0319 | 0.5523 | 0.7703 | 0.0151 |
| c7c | 0.1857 | 0.0491 | 0.5576 | 0.7061 | -0.0491 |
| const_shift | 0.1870 | 0.0453 | 0.5618 | 0.7100 | -0.0453 |

### Δ ※負が改善

- C7c − Base: ECE=-0.5781, Brier=-0.3945, LL=-1.0586
- C7c − ConstShift: ECE=0.0039, Brier=-0.0012, LL=-0.0042
- C3 − Base: ECE=-0.5954, Brier=-0.3966, LL=-1.0639
- C3 − ConstShift: ECE=-0.0134, Brier=-0.0033, LL=-0.0096

## Go / No-Go

| 条件 | 結果 |
|---|---|
| C7c ECE↓ & Brier↓ vs Base | PASS |
| C7c ECE↓ & Brier↓ vs ConstShift | FAIL |
| Interaction 追加 | 禁止（未使用 PASS） |
| 順位変更 | 禁止（Audit PASS） |

## World別（test）要約

| World | n | Base ECE | C7c ECE | C7c Brier | gate_c7c |
|---|---:|---:|---:|---:|---|
| `rank7_world` | 38 | 0.7120 | 0.1054 | 0.1609 | GO |
| `midhole_world` | 10 | 0.8086 | 0.0551 | 0.0930 | GO |
| `unsatisfied` | 91 | 0.5609 | 0.0269 | 0.2087 | NO |
| `core_world` | 0 | — | — | — | empty |
| `midupper_world` | 1 | 0.8632 | 0.2663 | 0.0709 | GO |
| `mixed_world` | 3 | 0.8862 | 0.3886 | 0.1510 | NO |

## 遵守

| 制約 | |
|---|---|
| Production / Trigger / Blueprint / PE | PASS |
| Interaction 非変更・非適用 | PASS |
| World Contract 非変更 | PASS |
| 順位・Score 非変更 | PASS |

## 関連

- `v86-calibration-result.md`
- `v86-governance.md`
- `_v86-world-prior-shadow.json`
