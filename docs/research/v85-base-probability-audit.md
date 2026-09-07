# Version85 — Base Probability Audit

**Generated:** `2026-07-28T10:06:08+00:00`  
**Scope:** p_base 定義の調査のみ。Interaction / PE / Production 非変更。実装・改善禁止。

## ① 現在の p_base 生成経路

- **ラベル:** V84 Shadow p_base (research adapter; not Production PE confidence API)
- **公式:** `p_base = win_prob[predicted_top1] / sum_i win_prob[i]`
- **Top1:** fixtures/stats/baseline-285r-evaluations.json :: predicted_top1_horse_id
- **win_prob:** real_285r_corpus.json runners[].win_prob → build_race_rows horses[].win_prob
- **Outcome:** hit_at_1 (fixture) fallback pred==winner_id
- **World:** CEW from _v73-contract-intent-evaluation.json (read-only)
- **Interaction:** NOT used in this audit (V85 isolates Base Probability)
- **Production PE:** unchanged / not invoked

### Code refs

- `app/research/_v84_confidence_calibration_shadow.py :: base_confidence`
- `app/research/_v64_world_strategy_discovery.py :: build_race_rows`

### 経路図（概念）

```text
corpus.runners.win_prob ──┐
                          ├─→ build_race_rows.horses.win_prob
fixture.predicted_top1 ───┤
                          └─→ p_base = wp[top1] / sum(wp)   (V84 Shadow adapter)
fixture.hit_at_1 ────────────→ y (calibration label)
CEW label ───────────────────→ World slice (read-only)
```

**仮説（V84）:** win_prob mass for Top1 ≈ 0.07–0.14 while empirical Top1 hit_at_1 ≫ that → systematic underconfidence

## ② p_base と実績勝率の乖離（C0 = win_prob mass）

全レース n=285

| World | n | hit_rate | p_mean | bias(p−hit) | ECE | Brier | underconf? |
|---|---:|---:|---:|---:|---:|---:|---|
| `rank7_world` | 65 | 0.8000 | 0.1042 | -0.6958 | 0.6958 | 0.6408 | True |
| `midhole_world` | 24 | 0.9167 | 0.0943 | -0.8224 | 0.8224 | 0.7551 | True |
| `unsatisfied` | 176 | 0.7273 | 0.1419 | -0.5854 | 0.5854 | 0.5414 | True |
| `core_world` | 8 | 0.7500 | 0.1325 | -0.6175 | 0.6175 | 0.5698 | True |
| `midupper_world` | 6 | 0.8333 | 0.1292 | -0.7042 | 0.7042 | 0.6336 | True |
| `mixed_world` | 6 | 0.8333 | 0.1045 | -0.7289 | 0.7289 | 0.6720 | True |
| **ALL** | 285 | 0.7649 | 0.1280 | -0.6370 | 0.6370 | 0.5875 | True |

### 結論（Audit）

- 全 World で `p_mean ≪ hit_rate`（bias 大幅負）→ **systematic underconfidence** を再確認。
- 乖離は Interaction 非依存（本監査は Interaction 未使用）。
- **ラベル注意:** ここでの hit_rate は fixture `hit_at_1`（285R 全体 ≈0.76）。自然勝率そのものではなく、V84 と同じキャリブレーションラベル。p_base スケール問題の診断には十分。

## 関連

- `v85-calibration-analysis.md`
- `v85-candidate-definition.md`
- `v85-governance.md`
