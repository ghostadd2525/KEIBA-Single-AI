# Version85 — Candidate Definition（Base Probability 再定義案）

**Generated:** `2026-07-28T10:06:08+00:00`  
**制約:** Interaction 変更禁止 / PE・Production 実装禁止 / 改善実装禁止。定義案の文書化のみ。

## ④ win_prob 以外を含む候補一覧

| ID | 定義 | 意図 |
|---|---|---|
| C0 | `wp[top1]/sum(wp)` | V84 現行 p_base |
| C1 | `wp[top1]` raw | 正規化なし |
| C2 | `1/field_size` | 一様事前 |
| C3 | World empirical hit_rate (train) | World 定数 prior |
| C4 | `(1/odds[top1]) / sum(1/odds)` | 市場確率 |
| C5 | `wp[top1]/(wp[top1]+wp[top2])` | 対抗馬マージン |
| C6/C6b | softmax(log wp / T) | 温度付き質量 |
| C7/C7b/C7c | `(1-λ)·C0 + λ·C3` | 質量×World prior 混合 |

## test ECE 上位（調査）

1. `C3_world_empirical_prior_train` — ECE=0.0319, Brier=0.1836, bias=0.0151
2. `C7c_blend_mass_0_9_prior` — ECE=0.0491, Brier=0.1857, bias=-0.0491
3. `C7b_blend_mass_0_7_prior` — ECE=0.1776, Brier=0.2150, bias=-0.1776
4. `C5_top1_over_top1_plus_top2` — ECE=0.1902, Brier=0.2284, bias=-0.1902
5. `C7_blend_mass_0_3_prior` — ECE=0.4402, Brier=0.3736, bias=-0.4346

## ⑤ Base Probability 再定義案（文書）

### 案 A — World Prior Anchor（推奨候補・非実装）

```text
p_base' = (1-λ) * (wp[top1]/sum(wp)) + λ * HitRate_CEW(world; train_window)
λ ∈ {0.7, 0.9} を Shadow で感度（別 Decision）
```

- **理由:** C0 の underconfidence を World 実績スケールへ引き上げる。V84 constant-shift と同型だが、明示的 prior。
- **Risk:** 時系列 prior のリーク / World 標本不足（core 等）。
- **Interaction:** 触らない。Confidence Integration は p_base' 安定後。

### 案 B — Market Mass

```text
p_base' = (1/odds[top1]) / sum_j (1/odds[j])
```

- **理由:** 市場は経験的にスケールが異なる可能性（C4）。
- **Risk:** odds 欠損・市場歪み。Prediction Rank との不一致。

### 案 C — Margin Mass（C5）

```text
p_base' = wp[top1] / (wp[top1] + wp[top2])
```

- **理由:** フィールド全体正規化より「対抗」相対に寄せる。
- **Risk:** なお underconfident の可能性（要 Shadow）。

### 案 D — 禁止・非推奨

| 案 | 理由 |
|---|---|
| Interaction で p_base を補正 | V84 で主因でないと判明。Contract も変更禁止対象に近い誤用 |
| 単体 Feature Weight で Score/Rank 変更 | V80 失敗モード |
| Production PE 即時切替 | 本フェーズ禁止 |

### 推奨順序（設計のみ）

1. **案 A（C7b/C7c 系）** を次 Shadow の主仮説とする
2. 案 B/C を対照アーム
3. Interaction Confidence は p_base' の ECE/Brier が安定してから再評価

**本フェーズでは採用実装しない。**
