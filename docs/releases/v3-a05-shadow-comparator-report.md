# Version 3 — A-05 Shadow Comparator Report

**Date:** 2026-07-24  
**Status:** 実装仕様 + 出力フォーマット · **実評価窓レポートは未生成**  
**Module:** `research/v3_lab/shadow/comparator.py`  
**Artifact path (when batch written):** `research/v3_lab/baselines/a05_shadow/shadow_comparator_report.json`

---

## 1. 目的

Control pick と Shadow pick のレース単位 Diff を標準化する。

---

## 2. Diff クラス

| status | 定義 |
|--------|------|
| `unchanged_hit` | 両方 Hit |
| `unchanged_miss` | 両方 Miss |
| `improved` | Control Miss → Shadow Hit |
| `worsened` | Control Hit → Shadow Miss（winner_rank≠1） |
| `worsened_winner_rank1` | Control Hit → Shadow Miss かつ winner_rank=1 |
| `unlabeled` | 着順未結合 |
| `pick_changed_unlabeled` | pick 変更 · 未ラベル |

---

## 3. Report JSON スキーマ

```json
{
  "n": 0,
  "improved_count": 0,
  "worsened_count": 0,
  "worsened_winner_rank1_count": 0,
  "unchanged_hit_count": 0,
  "unchanged_miss_count": 0,
  "pick_changed_count": 0,
  "shadow_error_count": 0,
  "improved_races": [],
  "worsened_races": [],
  "worsened_winner_rank1_races": [],
  "all_diffs": []
}
```

各 race 要素:

```json
{
  "race_id": "...",
  "status": "improved",
  "control_pick": "...",
  "shadow_pick": "...",
  "pick_changed": true,
  "control_hit": false,
  "shadow_hit": true,
  "winner_rank": 8,
  "a05_promote": true,
  "favsafe_blocked": false,
  "worsened_winner_rank1": false
}
```

---

## 4. Metrics との対応

| Comparator | Metrics |
|------------|---------|
| improved_count | `improved` |
| worsened_count | `worsened` / `churn_hit` |
| worsened_winner_rank1_count | `worsened_winner_rank1` |
| pick_changed_count | `pick_churn` |

Acceptance Hard Gate（計測）: H1–H3 は Comparator 集計と一致させる。

---

## 5. 本 Round

Comparator 実装と仕様を提出。  
実開催 Shadow 評価に基づく数値レポートは **未実施**（停止条件）。
