# Version84 — Confidence Calibration Shadow

**Generated:** `2026-07-28T10:01:46+00:00`  
**Mode:** V83-⑤ Confidence Integration（Shadow only）  
**Locks:** Production / Trigger / Blueprint / World / Interaction Contract / Prediction Rank / Score — 非変更  
**Audit:** rank_unchanged=True / score_unchanged=True / n=285

## 方法

- `p_base` = fixture 固定 Top1 の win_prob 質量（順位・Score 非変更）
- Interaction → `signal`（V82 Must 読取のみ。Contract 非改変）
- rank7: `0.65*z(history×win_prob)+0.35*z(history×odds×win_prob)`（レース内 z）
- unsatisfied: `z(history×win_prob)`
- `p_ix = sigmoid(logit(p_base) + α · signal)` / α_fixed=0.45
- α_fit = chronological train half で LogLoss 最小化
- ROI = **rank7 test** で ECE↓ かつ Brier↓（対 base）
- Interaction 固有 = 同条件で **constant-shift control** より ECE↓ かつ Brier↓

## Verdict: **B**

rank7 test: ECE+Brier improve vs base, but not beyond constant-shift (level-shift / underconfident p_base が主因の可能性)

## Ready: `rank7_world`

n=65 / train=32 / test=33 / hit_rate=0.8000 / α_fit=1.0000

### Full-sample（参考）

| Arm | Brier | LogLoss | ECE |
|---|---:|---:|---:|
| base | 0.6408 | 1.8295 | 0.6958 |
| ix_fixed | 0.4482 | 1.1494 | 0.5508 |
| ix_fit (in-sample) | 0.2275 | 0.6496 | 0.3219 |

### Test-split（主判定）

| Arm | Brier | LogLoss | ECE |
|---|---:|---:|---:|
| base | 0.6567 | 1.8781 | 0.7162 |
| ix_fixed | 0.4667 | 1.1954 | 0.5770 |
| ix_fit | 0.2374 | 0.6688 | 0.3474 |

### Constant-shift control（test）

train_mean_signal=2.2442 / p_base_mean=0.1042 / hit_rate=0.8000

| Arm | Brier | LogLoss | ECE |
|---|---:|---:|---:|
| const_shift | 0.2322 | 0.6572 | 0.3075 |
| ix_fit | 0.2374 | 0.6688 | 0.3474 |

### Δ (test, ix − base) ※負が改善

- fixed: ECE=-0.1392, Brier=-0.1900, LL=-0.6827
- fit: ECE=-0.3688, Brier=-0.4193, LL=-1.2093
- fit−const: ECE=0.0399, Brier=0.0051, LL=0.0116

### 解釈注意

- `p_base`（win_prob 質量）は hit_at_1 に対し **系統的 underconfident**（mean conf ≪ hit_rate）。
- 予測 Top1 の Must Interaction z は平均的に正 → 上方シフトが Calibration を改善しやすい。
- **Interaction 固有**の寄与は `fit−const` で判定する。

### High / Low Confidence Accuracy（test / ix_fit）

- High: acc=0.9000, n=10, thr=0.6091
- Low: acc=0.7000, n=10, thr=0.4348

## Residual: `unsatisfied`（別集計）

n=176 / hit_rate=0.7273 / α_fit=0.8000

| Arm (test) | Brier | LogLoss | ECE |
|---|---:|---:|---:|
| base | 0.5240 | 1.4314 | 0.5613 |
| ix_fit | 0.2675 | 0.8077 | 0.1800 |

Δfit: ECE=-0.3812, Brier=-0.2565, LL=-0.6238

**注:** Residual。勝ち筋 ROI 主張なし。主判定は rank7。

## 遵守

| 制約 | |
|---|---|
| 順位変更禁止 | PASS |
| Score 変更禁止 | PASS |
| Interaction → Confidence のみ | PASS |
| Production / Trigger / Blueprint / World / Contract | PASS |

## 関連

- `v84-calibration.md`
- `v84-governance.md`
- `_v84-confidence-calibration-shadow.json`
