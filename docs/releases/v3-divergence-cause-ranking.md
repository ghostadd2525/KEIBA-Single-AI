# Divergence Cause Ranking & Fix-Stage Proposal

**Status:** Analysis Complete — **実装なし**  
**Date:** 2026-07-24  
**PRR:** HOLD 継続

---

## 1. 原因ランキング（優先度順）

| Rank | Cause | Evidence weight | Impact on Offline ΔHit |
|------|-------|-----------------|------------------------|
| **1** | **A-03 Admission 誤 promote（実フィールド過剰発火）** | Worsened 27/29 promote; pick=promoted 26/29; Lab promote のみ Pool×9 vs Real 53% | **Dominant（本命破壊 ×29）** |
| **2** | **Lab コーパス非代表性（field / favorite / history 分布）** | Lab field mean 8.13 vs Real 14.6; winner_rank1 76% vs 21% | Lab 279 を過大に見せる評価バイアス |
| **3** | **D1 が Admission 書換 rank を増幅** | promote 後 top-1 が必ず非本命化 | A-03 誤りの増幅器（D1 単体バグではない） |
| **4** | **A-04 History Crowding 稀発火** | Worsened で A-04 promote 3/29 | Secondary |
| **5** | **A-01 Evaluation** | Worsened 支配因に非該当 | Low for this divergence |
| **6** | Flag 誤適用 / リーク | 検証で否定 | Ruled out |
| **7** | Metric 定義不一致 | Lab/Offline Gate は同一 top-1 | Ruled out |

---

## 2. Lab 279 が成立した理由（要約）

1. Hit 層 field=8 → A-03 不発火 → 本命維持  
2. A-01 が Eval を回復  
3. A-04 が Boundary/Reorder を回復（A-03 と非干渉）  
4. A-03 は Pool のみ → Accuracy 設計どおりの加点

---

## 3. Offline 42 になった理由（要約）

1. Real の 86% が field≥12 → A-03 ゲート開放  
2. Style rarity が半数超で発火 → 誤深い馬を昇格  
3. Control 正解の winner_rank=1 を 29 件破壊  
4. 正しい深掘り +12 では不足 → net −17 → Hit 42

---

## 4. 修正対象ステージ提案（実装しない）

### Primary（必須）

**Stage: Admission（A-03）**

提案テーマ（次ラウンド用・本ラウンドでは未実装）:

- 本命保護（例: rank-1 / 高 win_prob 帯の promote 禁止または大幅減衰）
- 実データ向け field / style 閾値の再校正
- Offline Gate を回帰ゲートとして固定

### Secondary

**Stage: Evaluation corpus / Lab harness**

- Lab Accuracy に実フィールド分布を混ぜ、A-03 過適合を早期検知

### Tertiary（A-03 安定後）

**Stage: Selection（A-04）**

- history_score 実スケールでの crowding 再検証

### Explicitly Not Now

| Item | Reason |
|------|--------|
| A-05 新アルゴリズム | Divergence 未解消のまま新段追加は禁止意図と整合 |
| Shadow / Production | PRR HOLD; Offline FAIL 継続 |
| Phase 3 | 同上 |
| Flag default ON | 危険 |

---

## 5. Recommended Next Action（人間判断用）

1. **Admission A-03 再設計ラウンド**（Lab + Offline 同時回帰）を起票  
2. PRR は **HOLD** のまま  
3. 本 Divergence Analysis で停止（本ラウンド完了）

---

## 6. Stop Condition Acknowledgement

本ドキュメント提出をもって Divergence Analysis 完了。  
A-05 / Shadow / Production / Phase3 には着手しない。
