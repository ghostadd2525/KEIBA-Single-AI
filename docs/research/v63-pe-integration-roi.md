# Version63 — PE Integration ROI Study

**Date:** 2026-07-28  
**Subject:** World を PE が消費した場合の ROI 可能性（反実仮想）  
**Locks:** Production / PE / Prediction / Signal / Trigger / Threshold — **変更禁止・実装禁止**  
**Parents:** V35（PE 非消費） / V36（接続点 C） / V37（51R midupper 飽和 FAIL） / V62（Exclusion 単独 ΔHit=0）

---

## 結論（1行）

Legacy World を Virtual PE Policy に結合すると **順位は動く**が、**NI（rank710/other_miss 非悪化）付きの Hit↑ はどの weight でも成立しない**。実用帯（25–75%）は Hit 悪化。極端 100% のみ Hit↑ だが rank710 悪化 → **ROI 期待は限定的（B）**。

---

## ① PE Integration Point（接続点）

| 項目 | 内容 |
|---|---|
| 現行（V35） | `Feature → Scorer → Ranker → Prediction`。World は **順位確定後のラベル** |
| 本 Simulation | V36 推奨 **Option C**: Ranker 後・Prediction 前に **Virtual PE Policy Layer** |
| 式 | `score = (1-w)·norm(win_prob) + w·norm(WorldRankKernel[world])` |
| 実装 | **未実施**。研究再利用: `world_pe_policy_sim.py` の kernel / blend（製品コード未変更） |

```text
Frozen Production scores (285R model_rank / win_prob)
        ↓
[SIM ONLY] World-conditioned blend (weight w)
        ↓
Simulated top1 / miss buckets
```

---

## ② Ranking Policy

| 要素 | 定義 |
|---|---|
| Kernel | Design prior（Hit 非フィット）。core→上位、midupper→2–5、midhole→5–8、rank7→6–9、bug→深層、mixed→中帯 |
| Weights | `0 / 0.25 / 0.50 / 0.75 / 1.0` |
| World 入力（主） | **Legacy**（dual-eval `legacy_world` = Production decision） |
| 副アーム | V44（unsatisfied→identity） / V44+False Exclusion 解除（V62 反実仮想ラベル） |

---

## 指標定義（推測禁止）

| 指標 | 定義（本フェーズ） |
|---|---|
| **PE Ranking Hit** | `top1(horse_id) == winner_id`（model_rank / policy_rank） |
| **Purchase** | 同上（V34/V37 同型 proxy） |
| **rank710 / other_miss** | winner の policy_rank バケツ |

**測定メモ:** fixture `hit_at_1` = **218** だが、`predicted_top1 == winner` は **59** 件のみ（`predicted_top1` は常に model_rank1）。本 ROI は **PE Ranking Hit（baseline 59/285）** のみを用い、fixture 218 を再順位の基準にしない。

---

## ③ Top1 変化率（Legacy 主アーム）

| Weight | Top1 changed | Rate | mean \|Δrank\| |
|-------:|-------------:|-----:|---------------:|
| 0% | 0 | 0.0% | 0 |
| 25% | 42 | **14.7%** | （meaningful ≥5%） |
| 50% | 123 | **43.2%** | |
| 75% | 180 | **63.2%** | |
| 100% | 227 | **79.6%** | |

→ PE 結合は **inert ではない**（影響は証明された）。

---

## ④〜⑥ Hit / Purchase / rank710（Legacy）

| Weight | Hit | ΔHit | Purchase Δ | rank710 Δ | other_miss Δ |
|-------:|----:|-----:|-----------:|------------:|-------------:|
| 0% | 59 | 0 | 0 | 0 | 0 |
| 25% | 54 | **-5** | -5 | **+2** | +5 |
| 50% | 51 | **-8** | -8 | **+7** | -1 |
| 75% | 37 | **-22** | -22 | **+11** | +4 |
| 100% | 104 | **+45** | +45 | **+3** | -39 |

| Gate | 結果 |
|---|---|
| Hit↑ ∧ rank710≤0 ∧ other_miss≤0 ∧ influence | **どの weight でも不成立** |
| 実用帯 25–75% | Hit **常に悪化** |
| 100% | Hit↑ だが rank710 悪化（domination） |

---

## ⑦ World Weight 感度

```text
ΔHit(Legacy):  0 → -5 → -8 → -22 → +45
Δrank710:      0 → +2 → +7 → +11 → +3
```

- 低〜中 weight: 順位は動くが Hit は下がる  
- 高 weight: Hit は上がり得るが miss 構造が壊れ、rank710 が悪化  
- **単調な安全 ROI 曲線は存在しない**

---

## ⑧ ROI 期待値

| 条件 | 期待 |
|---|---|
| NI 制約付き（本 Governance） | **証明された正の ROI なし**（ΔHit_safe = 不在） |
| 実用 weight 25–75% | **負**（ΔHit ∈ [-5, -22]） |
| 制約なし・w=100% | Hit +45 観測あるが rank710 悪化 → **採用不可の反実仮想** |

---

## 副アーム（参考・主判定ではない）

| Mode | 特記 |
|---|---|
| V44 | unsatisfied 176 は identity。w=25% ΔHit=0 だが Δrank710=+19。w=100% ΔHit=+11 かつ rank710+17 |
| V44+False解除 | w=25% ΔHit=+1 だが rank710+19。安全 ROI なし |

---

## V35 / V62 との整合

| 事実 | 含意 |
|---|---|
| V35: PE は World 非消費 | 結合しない限り Hit 不変 |
| V62: Exclusion 緩和のみ | Hit Δ0 |
| V63: 結合しても NI 付き Hit↑ なし | **「結合すれば ROI」は未証明** |

---

## 変更していないもの

Production / PE / Prediction / Signal / Trigger / Threshold / Exclusion 実装 — **すべて未変更**。
