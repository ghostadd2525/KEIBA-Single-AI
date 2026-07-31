# Version101 — Confidence Contract（Explanation Confidence）

**Date:** 2026-07-28  
**Status:** Contract（定義）· **実装禁止**  
**ADR:** ADR-010  
**Parents:** ADR-009 · V100 · V95/V96 Taxonomy

---

## 1. 用語契約

| 用語 | 定義 | 禁止される同一視 |
|---|---|---|
| **Explanation Confidence** | Core 説明の完全性・一貫性・Trace 充足・Must/Exclusion 確定性 | 勝率 / オッズ / Calibration |
| **Prediction Confidence** | （本 Contract 対象外）予測確率の確信度 | Core 出力として扱わない |
| **Score / win_prob** | Prediction 出力 | Explanation Confidence に代入しない |

**MUST:** Core ドキュメント・Shadow で単に `Confidence` と書くとき、断りがなければ **Explanation Confidence** を指す。  
**MUST NOT:** Explanation Confidence を Ticket ROI や Skip の直接閾値に使う（Decision 別契約が必要）。

---

## 2. 入出力契約（設計・未実装）

### 入力（読取のみ）

- CEW `world_id`
- `decision_trace`（must / must_gaps / exclude / match）
- Transition / trigger_path
- Near Miss Metadata（class / near_world / affinity / exclusion_reasons）— unsatisfied 時
- Expected Strategy 参照可否（V75 マップ）

### 出力（設計）

```text
ExplanationConfidenceBundle
  semantic_confidence: float | null     # EC-S [0,1]
  world_confidence: float | null        # EC-W [0,1]
  near_miss_confidence: float | null    # EC-N [0,1] or null if N/A
  trace_confidence: float | null        # EC-T [0,1]
  explanation_confidence: float | null  # optional aggregate
  definition_version: "v101/1.0"
  not: ["prediction_probability", "odds", "calibration"]
```

**MUST NOT:** Rank / Score / win_prob を mutate する。  
**MUST NOT:** Prediction Confidence フィールドを本 Bundle で埋める。

---

## 3. 各軸の充足条件（Contract）

### EC-S Semantic Confidence

説明可能要素の充足率:

- world_label 既知
- must_satisfied または must_gaps 既知
- exclusion 理由または「exclude=false / pure residual」が既知
- near_miss 理由（該当時）または N/A 明示
- expected_strategy 解決可能
- transition / trigger_path 既知

`semantic_confidence = (#真の要素) / (#適用要素)`

### EC-W World Confidence

- label 存在
- trace 存在
- must / exclusion / match トレース完全
- match ⇔ must∧¬exclude 一貫
- expected_strategy マップ可能

欠落・矛盾があれば低減。

### EC-N Near Miss Confidence

- `world_id != unsatisfied` → **null（N/A）**（欠落ではない）
- unsatisfied 時: residual_class、NEAR_MISS なら near_world、affinity ベクトル、must_gaps、exclusion_reasons、transition

### EC-T Trace Confidence

- Must Trace / Exclusion Trace / Match Trace / Decision-tree path / Transition の充足率

### Aggregate（任意）

```text
explanation_confidence =
  mean( non-null among {EC-S, EC-W, EC-T, EC-N} )
```

N/A（null）は平均から除外。ゼロ埋めして「低い」と偽らない。

---

## 4. Decision への渡し方（境界）

| Decision がしてよい | Decision がしてはならない |
|---|---|
| Explanation Confidence を説明 UI に表示 | 勝率ラベルとして表示 |
| 低 EC を「説明不足」警告に使う | 低 EC = Skip を自動正当化（別契約なし） |
| Trace 欠落を監査 | EC で Rank を並べ替え |

---

## 5. V100 との関係

| V100 指標 | V101 後の扱い |
|---|---|
| prediction confidence_coverage = 0 | Core 必須欠落としない（Prediction Confidence 非返却） |
| semantic / world / near_miss / trace Completeness | Explanation Confidence の観測入力 |

---

## 関連

- ADR-010
- `v101-confidence-taxonomy.md`
- `v101-governance.md`
